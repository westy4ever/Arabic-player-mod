# -*- coding: utf-8 -*-
import re
import sys
import base64
import json

from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse, quote
    from html import unescape as html_unescape
else:
    from urllib import quote_plus
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

# Updated domain list - wecima.click is currently the most active
DOMAINS = [
    "https://wecima.click/",
    "https://wecima.cx/",
    "https://wecima.bid/",
    "https://www.wecima.site/",
]
VALID_HOST_MARKERS = (
    "wecima.click", "wecima.cx", "wecima.bid", "wecima.site",
)
BLOCKED_HOST_MARKERS = ("alliance4creativity.com",)
MAIN_URL = None
_HOME_HTML = None

_CATEGORY_FALLBACKS = {
    "افلام اجنبي":    "/category/foreign-movies",
    "افلام عربي":     "/category/arabic-movies",
    "مسلسلات اجنبي":  "/category/foreign-series",
    "مسلسلات عربية":  "/category/arabic-series",
    "مسلسلات انمي":   "/category/anime-series",
    "تريندج":         "/trends",
}


def _host(url):
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def _is_valid_site_url(url):
    host = _host(url)
    if not host:
        return False
    if any(m in host for m in BLOCKED_HOST_MARKERS):
        return False
    return any(m in host for m in VALID_HOST_MARKERS)


def _is_blocked_page(html, final_url=""):
    text = (html or "").lower()
    final = (final_url or "").lower()
    if not text:
        return True
    if "just a moment" in text and ("cf-chl" in text or "challenge" in text):
        return True
    if "enable javascript and cookies to continue" in text:
        return True
    if "watch it legally" in text or "alliance for creativity" in text:
        return True
    if any(m in final for m in BLOCKED_HOST_MARKERS):
        return True
    return False


def _looks_like_wecima_page(html):
    text = html or ""
    return (
        "Grid--WecimaPosts" in text
        or "NavigationMenu" in text
        or "Thumb--GridItem" in text
        or "GridItem" in text
        or "List--Servers" in text  # New server list container
        or "WECIMA" in text
        or "وى سيما" in text
        or "wecima" in text.lower()
    )


def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)


def _get_base():
    global MAIN_URL, _HOME_HTML
    if MAIN_URL:
        return MAIN_URL
    for domain in DOMAINS:
        log("Wecima: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked {}".format(final_url))
            continue
        if html and _looks_like_wecima_page(html):
            MAIN_URL = _site_root(final_url)
            _HOME_HTML = html
            log("Wecima: selected base {}".format(MAIN_URL))
            return MAIN_URL
    MAIN_URL = DOMAINS[0]
    log("Wecima: fallback base {}".format(MAIN_URL))
    return MAIN_URL


def _search_url():
    return _get_base().rstrip("/") + "/?s="


def _normalize_url(url):
    if not url:
        return ""
    url = url.strip()
    try:
        url = url.encode("utf-8").decode("unicode_escape") if "\\u" in url else url
    except Exception:
        pass
    url = url.replace("\\u0026", "&").replace("&amp;", "&").replace("\\/", "/")
    url = html_unescape(url)
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(_get_base(), url)
    if any(m in _host(url) for m in BLOCKED_HOST_MARKERS):
        return ""
    if _is_valid_site_url(url):
        base_parts = urlparse(_get_base())
        parts = urlparse(url)
        if parts.netloc != base_parts.netloc and any(m in parts.netloc for m in VALID_HOST_MARKERS):
            clean = "{}://{}{}".format(base_parts.scheme, base_parts.netloc, parts.path or "/")
            if parts.query:
                clean += "?" + parts.query
            return clean
    return url


def _candidate_urls(url):
    normalized = _normalize_url(url)
    if not normalized:
        return []
    parts = urlparse(normalized)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    urls = []
    seen = set()
    seeds = []
    if MAIN_URL:
        seeds.append(MAIN_URL)
    seeds.extend(DOMAINS)
    if normalized.startswith("http"):
        seeds.insert(0, _site_root(normalized))
    for domain in seeds:
        if not domain:
            continue
        base = domain if domain.endswith("/") else domain + "/"
        candidate = urljoin(base, path.lstrip("/"))
        if candidate in seen:
            continue
        seen.add(candidate)
        urls.append(candidate)
    if normalized not in seen:
        urls.insert(0, normalized)
    return urls


def _fetch_live(url, referer=None):
    for candidate in _candidate_urls(url):
        log("Wecima: fetching {}".format(candidate))
        html, final_url = fetch(candidate, referer=referer or _get_base())
        final_url = final_url or candidate
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked {}".format(final_url))
            continue
        if html and _looks_like_wecima_page(html):
            log("Wecima: success {}".format(final_url))
            return html, final_url
        if html:
            log("Wecima: page shape mismatch {}".format(final_url))
    log("Wecima: fetch failed for {}".format(url))
    return "", ""


def _clean_html(text):
    text = html_unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title):
    title = _clean_html(title)
    for token in (
        "مشاهدة فيلم", "مشاهدة مسلسل", "مشاهدة",
        "فيلم", "مسلسل", "اون لاين", "أون لاين",
        "مترجم", "مترجمة", "مدبلج", "مدبلجة",
    ):
        title = title.replace(token, "")
    return re.sub(r"\s+", " ", title).strip(" -|")


def _home_html():
    global _HOME_HTML
    if _HOME_HTML:
        return _HOME_HTML
    base = _get_base()
    html, final_url = _fetch_live(base, referer=base)
    _HOME_HTML = html if not _is_blocked_page(html, final_url) else ""
    return _HOME_HTML


def _guess_type(title, url):
    text = "{} {}".format(title or "", url or "").lower()
    if any(t in text for t in ("/episode/", "الحلقة", "حلقة", "/season/")):
        return "episode"
    if any(t in text for t in ("/series", "/seriestv", "مسلسل", "series-", "/season/")):
        return "series"
    return "movie"


def _grid_blocks(html):
    blocks = []
    for block in re.split(r'(?=<div[^>]+class="GridItem")', html or "", flags=re.I):
        if 'class="GridItem"' not in block:
            continue
        end_match = re.search(
            r'<ul[^>]+class="PostItemStats"[^>]*>.*?</ul>\s*</div>',
            block, re.S | re.I,
        )
        if end_match:
            blocks.append(block[: end_match.end()])
        else:
            blocks.append(block[:3000])
    return blocks


def _extract_cards(html):
    cards = []
    seen = set()
    
    for block in _grid_blocks(html):
        href_match = re.search(r'<a[^>]+href="([^"]+)"', block, re.I)
        if not href_match:
            continue
        url = _normalize_url(href_match.group(1))
        if not url or url in seen:
            continue
        
        lowered = url.lower()
        if any(t in lowered for t in ("/category/", "/tag/", "/page/", "/filtering", "/feed/", "/trends")):
            continue
        
        title_match = (
            re.search(r'<h2[^>]+class="hasyear"[^>]*itemprop="name"[^>]*>(.*?)</h2>', block, re.S | re.I) or
            re.search(r'<h2[^>]+class="hasyear"[^>]*>(.*?)</h2>', block, re.S | re.I) or
            re.search(r'title="([^"]+)"', block, re.I)
        )
        title = _clean_title(title_match.group(1) if title_match else "")
        if not title:
            continue
        
        year = ""
        year_match = re.search(r'<span[^>]+class="year"[^>]*>\(?\s*(\d{4})\s*\)?</span>', block, re.I)
        if year_match:
            year = year_match.group(1)
        
        poster = ""
        poster_match = re.search(r'data-src="([^"]+)"', block, re.I)
        if poster_match:
            poster = poster_match.group(1)
        if not poster:
            poster_match = re.search(r'data-lazy-style="[^"]*url\(([^)]+)\)"', block, re.I)
            if poster_match:
                poster = poster_match.group(1).strip("'\" ")
        if not poster:
            poster_match = re.search(r'style="[^"]*--image:url\(([^)]+)\)', block, re.I)
            if poster_match:
                poster = poster_match.group(1).strip("'\" ")
        
        seen.add(url)
        cards.append({
            "title": title,
            "url": url,
            "poster": _normalize_url(poster) if poster else "",
            "plot": year,
            "type": _guess_type(title, url),
            "_action": "details",
        })
    
    log("Wecima: extracted {} cards".format(len(cards)))
    return cards


def _extract_next_page(html):
    patterns = [
        r'<a[^>]+class="[^"]*next[^"]*page-numbers[^"]*"[^>]+href="([^"]+)"',
        r'<a[^>]+rel="next"[^>]+href="([^"]+)"',
        r'<a[^>]+href="([^"]+)"[^>]*>»</a>',
    ]
    for pat in patterns:
        m = re.search(pat, html or "", re.I)
        if m:
            return _normalize_url(m.group(1))
    return ""


def _category_from_home(label, fallback):
    html = _home_html()
    for pattern in (
        r'<a[^>]+href="([^"]+)"[^>]*>\s*' + re.escape(label) + r'\s*</a>',
        r'<a[^>]+href="([^"]+)"[^>]*>\s*<span[^>]*>\s*' + re.escape(label) + r'\s*</span>',
    ):
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            url = _normalize_url(m.group(1))
            if url:
                return url
    return _normalize_url(urljoin(_get_base(), fallback))


def _decode_wecima_url(encoded):
    """
    Decode Wecima's obfuscated URLs.
    
    Steps:
    1. Clean the string - replace spaces with '+'
    2. Fix padding - add '=' if needed
    3. Base64 decode
    4. Apply URL quoting (Akwam fix) for Arabic characters
    """
    if not encoded:
        return None
    
    log("Wecima: decoding: {}".format(repr(encoded[:80])))
    
    try:
        # Step 1: Clean the string - some WeCima versions use spaces for '+'
        cleaned = encoded.strip().replace(' ', '+')
        
        # Step 2: Fix padding
        missing_padding = len(cleaned) % 4
        if missing_padding:
            cleaned += '=' * (4 - missing_padding)
        
        # Step 3: Decode
        decoded_bytes = base64.b64decode(cleaned)
        
        # Try UTF-8 first, fallback to latin-1
        try:
            decoded_url = decoded_bytes.decode('utf-8')
        except UnicodeDecodeError:
            decoded_url = decoded_bytes.decode('latin-1')
        
        # Step 4: Apply the 'Akwam Fix' - proper URL quoting for Arabic characters
        # This preserves the URL structure while encoding non-ASCII characters
        decoded_url = quote(decoded_url, safe=':/?&=#+')
        
        # Clean up any remaining non-printable characters
        decoded_url = re.sub(r'[^\x20-\x7E]', '', decoded_url)
        
        # Fix protocol if needed
        if decoded_url.startswith('//'):
            decoded_url = 'https:' + decoded_url
        elif decoded_url.startswith('https') and not decoded_url.startswith('https://'):
            decoded_url = 'https://' + decoded_url[5:]
        elif decoded_url.startswith('http') and not decoded_url.startswith('http://'):
            decoded_url = 'http://' + decoded_url[4:]
        
        # Validate the URL looks reasonable
        if decoded_url and ('http://' in decoded_url or 'https://' in decoded_url):
            log("Wecima: decode success: {}".format(decoded_url[:80]))
            return decoded_url
        else:
            log("Wecima: decoded but doesn't look like URL: {}".format(repr(decoded_url[:80])))
            
    except Exception as e:
        log("Wecima: decode failed: {}".format(str(e)[:50]))
    
    # Fallback: Try to extract URL pattern directly
    url_pattern = r'[a-zA-Z0-9\-]+\.(?:com|net|org|tv|cx|bid|site|click|show|video|rent|date|live|rip|top|xyz)(?:/[a-zA-Z0-9\-_/]+)?'
    match = re.search(url_pattern, encoded)
    if match:
        url = "https://" + match.group(0)
        log("Wecima: extracted URL pattern: {}".format(url))
        return url
    
    return None


def _extract_servers(html):
    """
    Robust server extraction for the new WeCima 'List--Servers' layout.
    Fixes the 'No servers detected' issue.
    """
    servers = []
    seen = set()
    
    if not html:
        log("Wecima: empty HTML in _extract_servers")
        return []

    # 1. Targeted Extraction: Isolate the server list container first
    # WeCima now wraps all real stream links inside this specific class
    server_block_match = re.search(r'class="List--Servers">(.*?)</ul>', html, re.S)
    
    if server_block_match:
        content = server_block_match.group(1)
        # Find all data-url elements (they can be btn, li, or div)
        items = re.findall(r'data-url="([^"]+)"[^>]*>(.*?)<\/(?:btn|li|div)>', content, re.S)
        
        for encoded_url, inner_html in items:
            # Decode the URL (Handles the base64/HM6Ly logic)
            decoded_url = _decode_wecima_url(encoded_url)
            if not decoded_url or not decoded_url.startswith('http'):
                continue
                
            if decoded_url not in seen:
                # Extract the server name (usually inside <strong>)
                name_match = re.search(r'<strong>(.*?)</strong>', inner_html)
                server_name = name_match.group(1).strip() if name_match else "Wecima Server"
                
                seen.add(decoded_url)
                servers.append({"name": server_name, "url": decoded_url, "type": "direct"})
                log("Wecima: Found server '{}' -> {}".format(server_name, decoded_url[:60]))

    # 2. Fallback Logic: Deep scan if the targeted block wasn't found
    if not servers:
        log("Wecima: Targeted block not found, running deep scan fallback...")
        # Look for any data-url that looks like a base64 encoded stream
        fallback_items = re.findall(r'data-url="([a-zA-Z0-9+/=]{20,})"', html)
        for encoded_url in fallback_items:
            decoded_url = _decode_wecima_url(encoded_url)
            if decoded_url and decoded_url.startswith('http') and decoded_url not in seen:
                seen.add(decoded_url)
                servers.append({"name": "Server Fallback", "url": decoded_url, "type": "direct"})

    if not servers:
        log("Wecima: ERROR - No servers found. The site layout may have changed.")
    else:
        log("Wecima: Successfully extracted {} servers".format(len(servers)))
        
    return servers


def _extract_episode_cards(html):
    episodes = []
    seen = set()
    for card in _extract_cards(html):
        title = card.get("title") or ""
        url = card.get("url") or ""
        if "الحلقة" not in title and "حلقة" not in title and "/episode/" not in url.lower():
            continue
        if url in seen:
            continue
        seen.add(url)
        episodes.append({
            "title": title or "حلقة",
            "url": url,
            "type": "episode",
            "_action": "details",
        })
    return episodes


def _parse_json_ld(html):
    """Extract data from JSON-LD script tags."""
    json_ld_match = re.search(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html or "", re.S | re.I)
    if not json_ld_match:
        return None
    
    try:
        data = json.loads(json_ld_match.group(1))
        return data
    except Exception:
        return None


def _detail_title(html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if data.get("name"):
                return _clean_title(data["name"])
            if "@graph" in data:
                for item in data["@graph"]:
                    if item.get("name") and ("فيلم" in item.get("name", "") or "مسلسل" in item.get("name", "")):
                        return _clean_title(item["name"])
    
    # Fallback to HTML patterns
    patterns = [
        r'<h1[^>]+itemprop="name"[^>]*>(.*?)</h1>',
        r'<h1[^>]+class="[^"]*title[^"]*"[^>]*>(.*?)</h1>',
        r'<h1[^>]*>(.*?)</h1>',
        r'property="og:title"[^>]+content="([^"]+)"',
    ]
    for pattern in patterns:
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            title = _clean_title(m.group(1))
            if title:
                return title
    return ""


def _detail_plot(html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if data.get("description"):
                desc = _clean_html(data["description"])
                if desc and len(desc) > 30:
                    return desc
            if "@graph" in data:
                for item in data["@graph"]:
                    if item.get("description"):
                        desc = _clean_html(item["description"])
                        if desc and len(desc) > 30:
                            return desc
    
    # Fallback to meta tags
    patterns = [
        r'<meta[^>]+itemprop="description"[^>]+content="([^"]+)"',
        r'property="og:description"[^>]+content="([^"]+)"',
        r'name="description"[^>]+content="([^"]+)"',
        r'<div[^>]+class="StoryMovieContent"[^>]*>(.*?)</div>',
    ]
    for pattern in patterns:
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            text = _clean_html(m.group(1))
            if text and "موقع وي سيما" not in text.lower() and len(text) > 30:
                return text
    return ""


def _detail_poster(html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if data.get("image") and isinstance(data["image"], dict):
                poster = data["image"].get("url", "")
                if poster:
                    return _normalize_url(poster)
            if "@graph" in data:
                for item in data["@graph"]:
                    if item.get("image") and isinstance(item["image"], dict):
                        poster = item["image"].get("url", "")
                        if poster:
                            return _normalize_url(poster)
                    if item.get("thumbnailUrl"):
                        return _normalize_url(item["thumbnailUrl"])
    
    # Fallback to meta tags
    patterns = [
        r'property="og:image"[^>]+content="([^"]+)"',
        r'<meta[^>]+itemprop="thumbnailUrl"[^>]+content="([^"]+)"',
        r'data-lazy-style="[^"]*--img:url\(([^)]+)\)',
        r'data-src="([^"]+)"',
    ]
    for pattern in patterns:
        m = re.search(pattern, html or "", re.I)
        if m:
            poster = m.group(1).strip("'\" ")
            if poster:
                return _normalize_url(poster) or poster
    return ""


def _detail_year(title, html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if data.get("datePublished"):
                year_match = re.search(r'(\d{4})', data["datePublished"])
                if year_match:
                    return year_match.group(1)
            if "@graph" in data:
                for item in data["@graph"]:
                    if item.get("datePublished"):
                        year_match = re.search(r'(\d{4})', item["datePublished"])
                        if year_match:
                            return year_match.group(1)
    
    # Fallback to patterns
    m = re.search(r'<span[^>]+class="year"[^>]*>\(?\s*(\d{4})\s*\)?</span>', html or "", re.I)
    if m:
        return m.group(1)
    m = re.search(r'\b(19\d{2}|20\d{2})\b', title or "")
    if m:
        return m.group(1)
    return ""


def _detail_rating(html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if "aggregateRating" in data:
                rating = data["aggregateRating"].get("ratingValue", "")
                if rating:
                    return str(rating)
            if "@graph" in data:
                for item in data["@graph"]:
                    if "aggregateRating" in item:
                        rating = item["aggregateRating"].get("ratingValue", "")
                        if rating:
                            return str(rating)
    
    # Fallback to regex patterns
    m = re.search(r'"ratingValue"\s*:\s*"?(\\?\d+(?:\.\d+)?)', html or "", re.I)
    if m:
        return m.group(1).replace("\\", "")
    m = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', html or "", re.I)
    if m:
        return m.group(1)
    return ""


def get_categories(mtype="movie"):
    return [
        {"title": "أفلام أجنبية",   "url": _category_from_home("افلام اجنبي",   _CATEGORY_FALLBACKS["افلام اجنبي"]),   "type": "category", "_action": "category"},
        {"title": "أفلام عربية",    "url": _category_from_home("افلام عربي",    _CATEGORY_FALLBACKS["افلام عربي"]),    "type": "category", "_action": "category"},
        {"title": "مسلسلات أجنبية", "url": _category_from_home("مسلسلات اجنبي", _CATEGORY_FALLBACKS["مسلسلات اجنبي"]), "type": "category", "_action": "category"},
        {"title": "مسلسلات عربية",  "url": _category_from_home("مسلسلات عربية", _CATEGORY_FALLBACKS["مسلسلات عربية"]), "type": "category", "_action": "category"},
        {"title": "كارتون وانمي",   "url": _category_from_home("مسلسلات انمي",  _CATEGORY_FALLBACKS["مسلسلات انمي"]),  "type": "category", "_action": "category"},
        {"title": "ترند",           "url": _category_from_home("تريندج",        _CATEGORY_FALLBACKS["تريندج"]),        "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    base = _get_base()
    html, final_url = _fetch_live(url, referer=base)
    if _is_blocked_page(html, final_url):
        log("Wecima: category blocked {}".format(url))
        return []
    items = _extract_cards(html)
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def search(query, page=1):
    base = _get_base()
    items = []
    html = ""
    for search_url in [
        _search_url() + quote_plus(query),
        urljoin(base, "search/") + quote_plus(query),
    ]:
        html, final_url = _fetch_live(search_url, referer=base)
        if _is_blocked_page(html, final_url):
            continue
        items = _extract_cards(html)
        if items:
            break
    log("Wecima: search '{}' -> {} items".format(query, len(items)))
    if not items:
        return []
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def get_page(url, m_type=None):
    base = _get_base()
    html, final_url = _fetch_live(url, referer=base)
    if _is_blocked_page(html, final_url) or not html:
        log("Wecima: detail failed {}".format(url))
        return {"title": "Error", "servers": [], "items": [], "type": m_type or "movie"}

    title = _detail_title(html)
    poster = _detail_poster(html)
    plot = _detail_plot(html)
    year = _detail_year(title, html)
    rating = _detail_rating(html)

    servers = _extract_servers(html)
    episodes = [] if servers else _extract_episode_cards(html)
    log("Wecima: detail {} -> servers={}, episodes={}".format(url, len(servers), len(episodes)))

    item_type = m_type or _guess_type(title, final_url or url)
    if episodes:
        item_type = "series"
    elif servers and any(t in (title or "") for t in ("الحلقة", "حلقة")):
        item_type = "episode"

    return {
        "url": final_url or url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "rating": rating,
        "year": year,
        "servers": servers,
        "items": episodes,
        "type": item_type,
    }


def extract_stream(url):
    """
    Extract stream URL with proper referer header to avoid 403 errors.
    Includes fallback in case base_extract_stream doesn't accept referer parameter.
    """
    from .base import extract_stream as base_extract_stream
    
    # Add referer for Wecima to avoid 403 errors on streaming URLs
    referer = _get_base()
    
    # Try with referer first (preferred method)
    try:
        result = base_extract_stream(url, referer=referer)
        # Check if result is valid (has URL as first element)
        if result and result[0]:
            log("Wecima: extract_stream success with referer")
            return result
    except TypeError as e:
        # base_extract_stream doesn't accept referer parameter
        log("Wecima: base_extract_stream doesn't accept referer, using fallback")
    except Exception as e:
        # Other error occurred
        log("Wecima: extract_stream with referer error: {}".format(str(e)[:50]))
    
    # Fallback to no referer parameter
    try:
        result = base_extract_stream(url)
        if result and result[0]:
            log("Wecima: extract_stream success without referer")
            return result
    except Exception as e:
        log("Wecima: extract_stream fallback failed: {}".format(str(e)[:50]))
    
    # Second fallback: Try using the base fetch with referer to get the stream URL
    try:
        log("Wecima: attempting direct fetch with referer: {}".format(url))
        html, final_url = fetch(url, referer=referer)
        if html and final_url:
            # If we got a redirect or final URL, return it
            log("Wecima: direct fetch got: {}".format(final_url[:80]))
            return final_url, "HD", url
    except Exception as e:
        log("Wecima: direct fetch failed: {}".format(str(e)[:50]))
    
    log("Wecima: all extract_stream methods failed")
    return None, None, None