# -*- coding: utf-8 -*-
"""
Shaheed4u extractor - Fixed for current site structure
Domain: shahidd4u.com
Supports: Movies, Series, TV Shows, Wrestling Shows
"""

import re
import sys
import json
import time
from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse, quote
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, quote
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

DOMAINS = [
    "https://shahidd4u.com/",
]

VALID_HOST_MARKERS = ("shahidd4u.com",)
BLOCKED_HOST_MARKERS = ("alliance4creativity.com",)
MAIN_URL = None
_HOME_HTML = None
_HOME_LAST_FETCH = 0


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
    if "just a moment" in text and "cf-chl" in text:
        return True
    if "alliance for creativity" in text:
        return True
    if any(m in final for m in BLOCKED_HOST_MARKERS):
        return True
    return False


def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)


def _get_base(force_refresh=False):
    global MAIN_URL, _HOME_HTML, _HOME_LAST_FETCH
    if MAIN_URL and not force_refresh and (time.time() - _HOME_LAST_FETCH) < 21600:
        return MAIN_URL
    for domain in DOMAINS:
        log("Shaheed: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Shaheed: blocked {}".format(final_url))
            continue
        if html and ("شاهد" in html or "shahid" in html.lower() or "film" in html.lower()):
            MAIN_URL = _site_root(final_url)
            _HOME_HTML = html
            _HOME_LAST_FETCH = time.time()
            log("Shaheed: selected base {}".format(MAIN_URL))
            return MAIN_URL
    MAIN_URL = DOMAINS[0]
    log("Shaheed: fallback base {}".format(MAIN_URL))
    return MAIN_URL


def _normalize_url(url):
    if not url:
        return ""
    url = html_unescape(url.strip())
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(_get_base(), url)
    return url


def _fetch_live(url, referer=None):
    """Fetch with proper headers and error handling"""
    ref = referer or _get_base()
    h, final_url = fetch(url, referer=ref)
    if _is_blocked_page(h, final_url):
        return "", ""
    return h, final_url or url


def get_categories():
    """Return category list for Shaheed4u"""
    base = _get_base().rstrip("/")
    return [
        {"title": "🎬 افلام اجنبي", "url": base + "/category/افلام-اجنبي", "type": "category", "_action": "category"},
        {"title": "🎬 افلام عربي", "url": base + "/category/افلام-عربي", "type": "category", "_action": "category"},
        {"title": "🎬 افلام هندي", "url": base + "/category/افلام-هندي", "type": "category", "_action": "category"},
        {"title": "🎬 افلام انمي", "url": base + "/category/افلام-انمي", "type": "category", "_action": "category"},
        {"title": "🎬 افلام تركية", "url": base + "/category/افلام-تركية", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات اجنبي", "url": base + "/category/مسلسلات-اجنبي", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات تركية", "url": base + "/category/مسلسلات-تركية", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات انمي", "url": base + "/category/مسلسلات-انمي", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات مدبلجة", "url": base + "/category/مسلسلات-مدبلجة", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات عربي", "url": base + "/category/مسلسلات-عربي", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات هندية", "url": base + "/category/مسلسلات-هندية", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات اسيوية", "url": base + "/category/مسلسلات-اسيوية", "type": "category", "_action": "category"},
        {"title": "🤼 عروض مصارعة", "url": base + "/category/عروض-مصارعة", "type": "category", "_action": "category"},
        {"title": "📺 برامج تلفزيونية", "url": base + "/category/برامج-تلفزيونية", "type": "category", "_action": "category"},
        {"title": "🌙 مسلسلات رمضان 2026", "url": base + "/category/مسلسلات-رمضان-2026", "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    """Parse category page with movie/show cards"""
    html, _ = _fetch_live(url)
    if not html:
        return []
    
    items = []
    seen_urls = set()
    
    # Find all show-card elements (works for both /film/ and /post/ URLs)
    card_pattern = r'<a\s+href="([^"]+)"\s+class="show-card"[^>]*style="background-image:\s*url\(([^)]+)\)"[^>]*>(.*?)</a>'
    
    for match in re.finditer(card_pattern, html, re.DOTALL | re.I):
        url_path = match.group(1)
        poster_url = match.group(2).strip()
        card_content = match.group(3)
        
        full_url = _normalize_url(url_path)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        # Extract title from <p class="title">
        title_match = re.search(r'<p\s+class="title">([^<]+)</p>', card_content)
        title = html_unescape(title_match.group(1).strip()) if title_match else ""
        
        if not title:
            title_match = re.search(r'title="([^"]+)"', card_content)
            title = html_unescape(title_match.group(1).strip()) if title_match else ""
        
        # Extract category
        categ_match = re.search(r'<span\s+class="categ">([^<]+)</span>', card_content)
        category = categ_match.group(1).strip() if categ_match else ""
        
        # Extract quality sticker
        quality_match = re.search(r'<span\s+class="sticker"[^>]*>([^<]+)</span>', card_content)
        quality = quality_match.group(1).strip() if quality_match else ""
        
        # Determine type
        if "مسلسلات" in category or "عروض" in category or "/category/مسلسلات" in url or "/category/عروض" in url:
            item_type = "series"
        else:
            item_type = "movie"
        
        if title:
            display_title = f"{title} [{quality}]" if quality else title
            items.append({
                "title": display_title,
                "url": full_url,
                "poster": _normalize_url(poster_url),
                "plot": category,
                "type": item_type,
                "_action": "details",
            })
    
    # Check for pagination
    pagination_pattern = r'<button[^>]+onclick="updateQuery\(\'page\',\s*(\d+)\)"[^>]*>(\d+)</button>'
    current_page = None
    max_page = None
    
    for match in re.finditer(pagination_pattern, html):
        page_num = int(match.group(2))
        if match.group(1) == str(page_num):
            current_page = page_num
        if page_num > (max_page or 0):
            max_page = page_num
    
    # Add next page button
    if current_page and max_page and current_page < max_page:
        if '?' in url:
            next_url = url + "&page=" + str(current_page + 1)
        else:
            next_url = url + "?page=" + str(current_page + 1)
        items.append({
            "title": "➡️ Next Page",
            "url": next_url,
            "type": "category",
            "_action": "category",
        })
    
    log("Shaheed: {} -> {} items".format(url, len(items)))
    return items


def search(query, page=1):
    """Search for movies/series"""
    base = _get_base()
    url = base + "/search?s=" + quote_plus(query)
    if page > 1:
        url += "&page=" + str(page)
    
    html, _ = _fetch_live(url)
    if not html:
        return []
    
    return get_category_items(url)


def get_page(url):
    """
    Fetch and parse a movie/series/show detail/watch page.
    Extracts servers from the JavaScript servers array.
    Works for /film/, /post/, and /watch/ URLs.
    """
    html, final_url = _fetch_live(url)
    
    result = {
        "url": final_url or url,
        "title": "",
        "plot": "",
        "poster": "",
        "servers": [],
        "items": [],
        "type": "movie",
    }
    
    if not html:
        log("Shaheed: get_page failed for {}".format(url))
        return result
    
    # Extract title
    title_match = re.search(r'<title>(.*?)</title>', html)
    if title_match:
        title = html_unescape(title_match.group(1))
        title = re.sub(r'\s*[-|]\s*شاهد\s*فور\s*يو.*$', '', title)
        title = re.sub(r'\s*[-|]\s*Shahid4u.*$', '', title, re.I)
        result["title"] = title.strip()
    
    # Extract description
    desc_match = re.search(r'<meta\s+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if desc_match:
        result["plot"] = html_unescape(desc_match.group(1))
    
    # Extract poster from og:image or meta
    poster_match = re.search(r'<meta\s+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if poster_match:
        result["poster"] = _normalize_url(poster_match.group(1))
    
    # ===== CRITICAL: Extract servers from JavaScript array =====
    # Pattern: let servers = JSON.parse('[...]');
    servers_pattern = r'let\s+servers\s*=\s*JSON\.parse\(\'([^\']+)\'\)'
    
    match = re.search(servers_pattern, html)
    if match:
        try:
            servers_json = match.group(1)
            # Fix escaped characters
            servers_json = servers_json.replace('\\"', '"')
            servers_data = json.loads(servers_json)
            
            for server in servers_data:
                if server.get("url"):
                    server_url = server["url"]
                    server_name = server.get("name", "Server")
                    result["servers"].append({
                        "name": server_name,
                        "url": server_url,
                        "type": "embed"
                    })
            log("Shaheed: extracted {} servers from JSON".format(len(result["servers"])))
        except Exception as e:
            log("Shaheed: failed to parse servers JSON: {}".format(e))
    
    # Alternative pattern: standalone servers array
    if not result["servers"]:
        alt_pattern = r'servers\s*=\s*(\[.*?\])'
        match = re.search(alt_pattern, html, re.DOTALL)
        if match:
            try:
                servers_data = json.loads(match.group(1))
                for server in servers_data:
                    if server.get("url"):
                        result["servers"].append({
                            "name": server.get("name", "Server"),
                            "url": server["url"],
                            "type": "embed"
                        })
                log("Shaheed: extracted {} servers from alt JSON".format(len(result["servers"])))
            except Exception as e:
                log("Shaheed: failed to parse alt servers JSON: {}".format(e))
    
    # Fallback: look for iframe embeds (like fastvid.cam)
    if not result["servers"]:
        iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
        skip_domains = ['youtube', 'facebook', 'twitter', 'google', 'doubleclick', 
                       'analytics', 'googletagmanager', 'google-analytics', 
                       'cloudflareinsights', 'adsco.re', 'intelligenceadx']
        
        for iframe_match in re.finditer(iframe_pattern, html, re.I):
            iframe_url = iframe_match.group(1)
            
            # Skip obvious ad/tracking domains
            if any(x in iframe_url.lower() for x in skip_domains):
                continue
            
            # Make absolute URL if needed
            if iframe_url.startswith("//"):
                iframe_url = "https:" + iframe_url
            elif iframe_url.startswith("/"):
                p = urlparse(final_url or url)
                iframe_url = "{}://{}{}".format(p.scheme, p.netloc, iframe_url)
            
            # Check if it's a video embed domain
            embed_domains = ['fastvid.cam', 'streamtape', 'doodstream', 'voe', 
                            'filemoon', 'rpmvip', 'upn.one', 'cleantechworld']
            if any(d in iframe_url.lower() for d in embed_domains):
                result["servers"].append({
                    "name": "Embed Player",
                    "url": iframe_url,
                    "type": "iframe"
                })
    
    # Also look for direct links to m3u8 in the page
    if not result["servers"]:
        direct_patterns = [
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'"(https?://[^"]+\.m3u8[^"]+)"',
        ]
        for pattern in direct_patterns:
            matches = re.findall(pattern, html, re.I)
            for m in matches:
                if 'fastvid.cam' in m or 'rpmvip' in m or 'upn.one' in m:
                    result["servers"].append({
                        "name": "Direct Stream",
                        "url": m,
                        "type": "direct"
                    })
    
    # Determine type from URL and content
    if "/مسلسلات" in url or "series" in url.lower() or "/عروض" in url:
        result["type"] = "series"
    elif "/post/" in url:
        result["type"] = "series"
    
    log("Shaheed: {} -> found {} servers".format(url, len(result["servers"])))
    return result


def extract_stream(url):
    """Resolve a server URL to a playable stream"""
    log("Shaheed extract_stream: {}".format(url))
    
    referer = _get_base()
    if "|" in url:
        parts = url.split("|", 1)
        url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()
    
    from .base import resolve_iframe_chain, resolve_host
    
    # Try iframe chain first
    stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=10)
    if stream:
        return stream, None, referer
    
    # Try host resolver
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)