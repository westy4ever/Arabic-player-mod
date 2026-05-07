# -*- coding: utf-8 -*-
import re
import sys

from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse
    from html import unescape as html_unescape
else:
    from urllib import quote_plus
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

# FIX: expanded domain list — wecima.rent was dead, added .click / .show / .video
DOMAINS = [
    "https://wecima.click/",
    "https://wecima.show/",
    "https://wecima.video/",
    "https://wecima.rent/",
    "https://wecima.date/",
    "https://www.wecima.site/",
]
VALID_HOST_MARKERS = (
    "wecima.click", "wecima.show", "wecima.video",
    "wecima.rent",  "wecima.date",  "wecima.site",
)
BLOCKED_HOST_MARKERS = ("alliance4creativity.com",)
MAIN_URL = None
_HOME_HTML = None

_CATEGORY_FALLBACKS = {
    "افلام اجنبي":    "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/",
    "افلام عربي":     "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%b9%d8%b1%d8%a8%d9%8a/",
    "مسلسلات اجنبي":  "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/",
    "مسلسلات عربية":  "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b9%d8%b1%d8%a8%d9%8a%d8%a9/",
    "مسلسلات انمي":   "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d9%86%d9%85%d9%8a/",
    "تريندج":         "/",
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
    """
    FIX: Loosened check — only block on confirmed ACE/Cloudflare walls.
    No longer rejects pages merely because domain changed (CDN redirects are normal).
    """
    text = (html or "").lower()
    final = (final_url or "").lower()
    if not text:
        return True
    if "just a moment" in text and "cf-chl" in text:
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
        or "WECIMA" in text
        or "وي سيما" in text
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
        if parts.netloc != base_parts.netloc and "wecima" in parts.netloc:
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
    if any(t in text for t in ("/episode/", "الحلقة", "حلقة")):
        return "episode"
    if any(t in text for t in ("/series", "/season", "مسلسل", "series-")):
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
        blocks.append(block[: end_match.end()] if end_match else block[:2500])
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
        if any(t in lowered for t in ("/category/", "/tag/", "/page/", "/filtering", "/feed/")):
            continue

        title_match = (
            re.search(r'title="([^"]+)"', block, re.I)
            or re.search(r'<strong[^>]+class="hasyear"[^>]*>(.*?)</strong>', block, re.S | re.I)
            or re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S | re.I)
        )
        title = _clean_title(title_match.group(1) if title_match else "")
        if not title:
            continue

        poster = ""
        m = re.search(r'data-lazy-style="[^"]*url\(([^)]+)\)"', block, re.I)
        if m:
            poster = m.group(1).strip("'\" ")
        if not poster:
            m = re.search(r'(?:data-src|src)="([^"]+)"', block, re.I)
            if m:
                poster = m.group(1).strip()

        year = ""
        m = re.search(r'<span[^>]+class="year"[^>]*>\(\s*(\d{4})', block, re.I)
        if m:
            year = m.group(1)

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
    for pat in (
        r'<a[^>]+class="[^"]*next[^"]*page-numbers[^"]*"[^>]+href="([^"]+)"',
        r'<a[^>]+rel="next"[^>]+href="([^"]+)"',
    ):
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
    return _normalize_url(urljoin(_get_base(), _CATEGORY_FALLBACKS.get(label, "/")))


def _extract_servers(html):
    servers = []
    seen = set()

    # Method 1: <ul id="watch"> with data-watch
    watch_list = re.search(r'<ul[^>]+id="watch"[^>]*>(.*?)</ul>', html or "", re.S | re.I)
    if watch_list:
        for idx, m in enumerate(re.finditer(
            r'<li[^>]+data-watch="([^"]+)"[^>]*>(.*?)</li>',
            watch_list.group(1), re.S | re.I
        )):
            server_url = html_unescape(m.group(1)).strip()
            if not server_url or server_url in seen:
                continue
            seen.add(server_url)
            name = _clean_html(m.group(2)) or "Server {}".format(idx + 1)
            servers.append({"name": name, "url": server_url, "type": "direct"})
    if servers:
        return servers

    # Method 2: class containing server/watch/player
    for m in re.finditer(
        r'<(?:a|div|li|button)[^>]+(?:class|id)="[^"]*(?:server|watch|player)[^"]*"[^>]*>.*?href="([^"]+)"',
        html or "", re.S | re.I
    ):
        url = _normalize_url(m.group(1))
        if url and url not in seen and "://" in url:
            seen.add(url)
            servers.append({"name": "Server {}".format(len(servers) + 1), "url": url, "type": "direct"})

    # Method 3: iframes with embed/player/stream
    if not servers:
        for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', html or "", re.I):
            url = _normalize_url(m.group(1))
            if url and url not in seen and "://" in url:
                if any(k in url for k in ["embed", "player", "watch", "stream", "video"]):
                    seen.add(url)
                    servers.append({"name": "Player {}".format(len(servers) + 1), "url": url, "type": "direct"})

    if not servers:
        log("Wecima: no watch server list found")
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


def _detail_title(html):
    for pattern in (
        r'<h1[^>]+itemprop="name"[^>]*>(.*?)</h1>',
        r'<h1[^>]*>(.*?)</h1>',
        r'property="og:title"[^>]+content="([^"]+)"',
        r'content="([^"]+)"[^>]+property="og:title"',
    ):
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            title = _clean_title(m.group(1))
            if title:
                return title
    return ""


def _detail_plot(html):
    for pattern in (
        r'<span[^>]+itemprop="description"[^>]*>(.*?)</span>',
        r'<meta[^>]+itemprop="description"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+itemprop="description"',
        r'property="og:description"[^>]+content="([^"]+)"',
        r'content="([^"]+)"[^>]+property="og:description"',
        r'name="description"[^>]+content="([^"]+)"',
    ):
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            text = _clean_html(m.group(1))
            if text and "موقع وي سيما" not in text and "مشاهدة احدث الافلام" not in text:
                return text
    return ""


def _detail_poster(html):
    for pattern in (
        r'<wecima[^>]+style="[^"]*--img:url\(([^)]+)\)',
        r'property="og:image"[^>]+content="([^"]+)"',
        r'content="([^"]+)"[^>]+property="og:image"',
        r'(?:data-src|src)="([^"]+)"[^>]+itemprop="image"',
    ):
        m = re.search(pattern, html or "", re.I)
        if m:
            poster = m.group(1).strip("'\" ")
            if poster:
                return _normalize_url(poster) or poster
    return ""


def _detail_year(title, html):
    m = re.search(r'\b(19\d{2}|20\d{2}|21\d{2})\b', title or "")
    if m:
        return m.group(1)
    for pat in (r'datePublished[^>]*?(\d{4})', r'"datePublished"\s*:\s*"(\d{4})'):
        m = re.search(pat, html or "", re.I)
        if m:
            return m.group(1)
    return ""


def _detail_rating(html):
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
    if not items:
        alt_html, alt_url = _fetch_live((final_url or url).rstrip("/") + "/page/1/", referer=base)
        if not _is_blocked_page(alt_html, alt_url):
            html = alt_html
            items = _extract_cards(alt_html)
    log("Wecima: {} -> {} items".format(url, len(items)))
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
    if not html and not items:
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

    title  = _detail_title(html)
    poster = _detail_poster(html)
    plot   = _detail_plot(html)
    year   = _detail_year(title, html)
    rating = _detail_rating(html)

    servers  = _extract_servers(html)
    episodes = [] if servers else _extract_episode_cards(html)
    log("Wecima: detail {} -> servers={}, episodes={}".format(url, len(servers), len(episodes)))

    item_type = m_type or _guess_type(title, final_url or url)
    if episodes:
        item_type = "series"
    elif servers and any(t in (title or "") for t in ("الحلقة", "حلقة")):
        item_type = "episode"

    return {
        "url":     final_url or url,
        "title":   title,
        "plot":    plot,
        "poster":  poster,
        "rating":  rating,
        "year":    year,
        "servers": servers,
        "items":   episodes,
        "type":    item_type,
    }


def extract_stream(url):
    """
    FIX: Removed the brittle akhbarworld/mycimafsd branch.
    All resolution now delegates to the unified base extractor which
    handles all known video hosts including the ones Wecima uses.
    """
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
