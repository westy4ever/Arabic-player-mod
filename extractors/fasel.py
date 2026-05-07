# -*- coding: utf-8 -*-
import sys
import re
import time
from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse
    from html import unescape as html_unescape
else:
    from urllib import quote_plus
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

DOMAINS = [
    "https://faselhd.fit/",
    "https://www.faselhd.cam",
    "https://faselhd.pro",
    "https://faselhd.cc",
]

# FIX: removed "telegram" — it was blocking legitimate pages that link to Telegram
BLOCKED_MARKERS = ("alliance4creativity", "watch-it-legally", "just a moment", "cf-chl")

_ACTIVE_URL = None
_ACTIVE_BASE_FETCH_TIME = 0


def _get_base():
    global _ACTIVE_URL
    for domain in DOMAINS:
        log("FaselHD: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        if html and not any(m in (final_url or "").lower() for m in BLOCKED_MARKERS):
            log("FaselHD: using {}".format(domain))
            _ACTIVE_URL = domain.rstrip("/")
            return _ACTIVE_URL
    _ACTIVE_URL = DOMAINS[0].rstrip("/")
    return _ACTIVE_URL


def _base():
    global _ACTIVE_URL, _ACTIVE_BASE_FETCH_TIME
    if not _ACTIVE_URL or (time.time() - _ACTIVE_BASE_FETCH_TIME) > 3600:
        _ACTIVE_URL = _get_base()
        _ACTIVE_BASE_FETCH_TIME = time.time()
    return _ACTIVE_URL


def _normalize_url(url):
    if not url:
        return ""
    url = html_unescape(url.strip())
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(_base(), url)
    return url


def _clean_title(title):
    return html_unescape(title).replace("&amp;", "&").strip()


def get_categories():
    base = _base()
    html, _ = fetch(base, referer=base)
    categories = []
    fallback = [
        {"title": "🎬 افلام اجنبي",      "url": base + "/category/افلام-اجنبي",      "type": "category", "_action": "category"},
        {"title": "🎬 افلام عربي",       "url": base + "/category/افلام-عربي",       "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات اجنبي",    "url": base + "/category/مسلسلات-اجنبي",    "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات عربي",     "url": base + "/category/مسلسلات-عربي",     "type": "category", "_action": "category"},
        {"title": "🎌 انمي",             "url": base + "/category/انمي",             "type": "category", "_action": "category"},
    ]
    if not html:
        return fallback
    seen = set()
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html):
        url = m.group(1)
        title = m.group(2).strip()
        if "/category/" in url and title and len(title) < 30 and url not in seen:
            seen.add(url)
            emoji = "🎬" if "فيلم" in title or "افلام" in title else ("📺" if "مسلسل" in title else "📁")
            categories.append({
                "title": "{} {}".format(emoji, title),
                "url": _normalize_url(url),
                "type": "category",
                "_action": "category",
            })
    if categories:
        return categories
    return fallback


def _extract_items(html):
    items = []
    pattern = (
        r'<div[^>]*class="[^"]*grid-card[^"]*"[^>]*>.*?'
        r'<a[^>]+href="([^"]+)".*?'
        r'<img[^>]*class="[^"]*thumb-img[^"]*"[^>]*src="([^"]+)".*?'
        r'<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>'
    )
    matches = re.findall(pattern, html, re.DOTALL | re.I)
    if not matches:
        pattern = (
            r'<div[^>]*class="[^"]*post[^"]*"[^>]*>.*?'
            r'<a href="([^"]+)".*?'
            r'<img[^>]*(?:src|data-src)="([^"]+)".*?'
            r'<h[23][^>]*>([^<]+)</h[23]>'
        )
        matches = re.findall(pattern, html, re.DOTALL | re.I)
    for href, img, title in matches:
        title = _clean_title(title)
        if not title:
            continue
        items.append({
            "title": title,
            "url": _normalize_url(href),
            "poster": _normalize_url(img),
            "type": "series" if any(x in title for x in ["مسلسل", "انمي", "موسم"]) else "movie",
            "_action": "details",
        })
    return items


def get_category_items(url):
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        return []
    # Handle meta-refresh (some category pages use it)
    refresh = re.search(
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;url=([^"\']+)["\']',
        html, re.I
    )
    if refresh:
        new_url = _normalize_url(refresh.group(1))
        log("FaselHD: meta-refresh to {}".format(new_url))
        return get_category_items(new_url)

    items = _extract_items(html)

    # Pagination
    next_match = (
        re.search(r'<a[^>]+href="([^"]+)"[^>]*>(?:التالي|Next)</a>', html, re.I) or
        re.search(r'<li[^>]*class="next"[^>]*>.*?<a href="([^"]+)"', html, re.I)
    )
    if next_match:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": _normalize_url(next_match.group(1)),
            "type": "category",
            "_action": "category",
        })
    return items


def search(query, page=1):
    base = _base()
    url = base + "/?s=" + quote_plus(query)
    html, _ = fetch(url, referer=base)
    return _extract_items(html) if html else []


def get_page(url):
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        return {"title": "Error", "servers": [], "items": [], "_action": "details"}

    title_m = re.search(r'<title>(.*?)</title>', html)
    title = _clean_title(title_m.group(1)) if title_m else "FaselHD"

    poster_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(poster_m.group(1)) if poster_m else ""

    plot_m = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html)
    plot = _clean_title(plot_m.group(1)) if plot_m else ""

    servers  = []
    episodes = []
    item_type = "movie"

    if "/series/" in url or "مسلسل" in title:
        item_type = "series"
        # Episodes
        for ep_url, ep_num in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?الحلقة\s*(\d+)', html, re.I):
            episodes.append({
                "title": "الحلقة {}".format(ep_num),
                "url": _normalize_url(ep_url),
                "type": "episode",
                "_action": "details",
            })
        if not episodes:
            for s_url, s_num in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?الموسم\s*(\d+)', html, re.I):
                episodes.append({
                    "title": "الموسم {}".format(s_num),
                    "url": _normalize_url(s_url),
                    "type": "category",
                    "_action": "category",
                })

    # Servers: look for known embed URLs
    seen_servers = set()
    # FIX: broadened to catch streamwish, filemoon, dood, voe etc. not just govid
    hoster_pattern = re.compile(
        r'href=["\']'
        r'(https?://(?:govid\.live|streamtape|dood\.|mixdrop|voe\.sx|'
        r'streamwish|filemoon|lulustream|vidbom|vidshare|upstream)[^"\']+)'
        r'["\']',
        re.I,
    )
    for m in hoster_pattern.finditer(html):
        hurl = m.group(1)
        if hurl not in seen_servers:
            seen_servers.add(hurl)
            servers.append({"name": "فاصل - سيرفر", "url": hurl, "_action": "details"})

    # iframes as fallback
    if not servers:
        for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
            iframe_url = _normalize_url(m.group(1))
            if iframe_url and iframe_url not in seen_servers:
                seen_servers.add(iframe_url)
                servers.append({"name": "بلاير", "url": iframe_url, "type": "direct"})

    return {
        "url":     final_url or url,
        "title":   title,
        "plot":    plot,
        "poster":  poster,
        "servers": servers,
        "items":   episodes,
        "type":    item_type,
    }


def extract_stream(url):
    """
    FIX: Replaced the fragile follow_chain() loop with a clean chain that:
    - Has a hard media-URL guard (won't follow non-video links endlessly)
    - Delegates known hosts to base resolvers
    - Falls back to resolve_iframe_chain for unknown pages
    """
    log("FaselHD extract_stream: {}".format(url))
    referer = _base()

    from .base import resolve_iframe_chain, resolve_host, find_m3u8, find_mp4

    # Step 1: if the URL itself is a known host, resolve directly
    stream = resolve_host(url, referer=referer)
    if stream:
        q = "HD" if "720" in stream else ("FHD" if "1080" in stream else "Auto")
        return stream, q, referer

    # Step 2: fetch the page and look for a media URL or iframe chain
    html, final_url = fetch(url, referer=referer)
    if html:
        # Direct media in page
        direct = find_m3u8(html) or find_mp4(html)
        if direct:
            return direct, "Auto", referer

        # iframes
        stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=8)
        if stream:
            return stream, "Auto", referer

    # Step 3: base fallback
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
