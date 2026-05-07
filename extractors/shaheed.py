# -*- coding: utf-8 -*-
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
    "https://shahid4u.guru/",
    "https://shahieed4u.net/",
    "https://shaheeid4u.net/",
]
VALID_HOST_MARKERS   = ("shahid4u.guru", "shahieed4u.net", "shaheeid4u.net")
BLOCKED_HOST_MARKERS = ("alliance4creativity.com",)
MAIN_URL   = None
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
    text  = (html or "").lower()
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
        if html and ("shah" in html.lower() or "film" in html.lower()):
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
    """
    FIX: No longer rejects pages when the final URL domain doesn't match
    VALID_HOST_MARKERS — CDN / image / video URLs are fetched by other means.
    Only rejects confirmed ACE/Cloudflare walls.
    """
    ref = referer or _get_base()
    h, final_url = fetch(url, referer=ref)
    if _is_blocked_page(h, final_url):
        return "", ""
    return h, final_url or url


def get_categories():
    base = _get_base().rstrip("/")
    html, _ = _fetch_live(base)
    categories = []
    seen_urls = set()
    if html:
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html):
            url   = m.group(1)
            title = m.group(2).strip()
            if "/category/" in url and title and len(title) < 30 and url not in seen_urls:
                seen_urls.add(url)
                emoji = "🎬" if "فيلم" in title or "افلام" in title else ("📺" if "مسلسل" in title else "📁")
                categories.append({
                    "title": "{} {}".format(emoji, title),
                    "url":   _normalize_url(url),
                    "type":  "category",
                    "_action": "category",
                })
    if not categories:
        categories = [
            {"title": "🎬 افلام اجنبي",    "url": base + "/category/افلام-اجنبي",    "type": "category", "_action": "category"},
            {"title": "🎬 افلام عربي",     "url": base + "/category/افلام-عربي",     "type": "category", "_action": "category"},
            {"title": "📺 مسلسلات اجنبي",  "url": base + "/category/مسلسلات-اجنبي",  "type": "category", "_action": "category"},
            {"title": "📺 مسلسلات عربي",   "url": base + "/category/مسلسلات-عربي",   "type": "category", "_action": "category"},
        ]
    return categories


def _extract_cards(html):
    items = []
    # JSON-LD first (most reliable)
    ld_m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    if ld_m:
        try:
            data = json.loads(ld_m.group(1))
            if data.get("@type") == "ItemList":
                for entry in data.get("itemListElement", []):
                    item = entry.get("item", {})
                    if item.get("@type") in ("Movie", "TVSeries"):
                        title  = item.get("name", "")
                        url    = item.get("url", "")
                        poster = item.get("image", "")
                        if title and url:
                            items.append({
                                "title":   html_unescape(title),
                                "url":     _normalize_url(url),
                                "poster":  _normalize_url(poster),
                                "type":    "movie" if item.get("@type") == "Movie" else "series",
                                "_action": "details",
                            })
                if items:
                    return items
        except Exception:
            pass

    # HTML fallbacks
    for pattern in (
        r'<div[^>]*class="[^"]*post[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)".*?<img[^>]+src="([^"]+)".*?<h[23][^>]*>([^<]+)</h[23]>',
        r'<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)".*?<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>',
    ):
        matches = re.findall(pattern, html, re.DOTALL | re.I)
        if matches:
            for url, poster, title in matches:
                title = title.strip()
                if title and url:
                    items.append({
                        "title":   html_unescape(title),
                        "url":     _normalize_url(url),
                        "poster":  _normalize_url(poster),
                        "type":    "movie",
                        "_action": "details",
                    })
            break
    return items


def get_category_items(url):
    html, _ = _fetch_live(url)
    if not html:
        return []
    items = _extract_cards(html)
    log("Shaheed: {} -> {} items".format(url, len(items)))
    next_m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(?:التالي|Next)</a>', html, re.I)
    if next_m:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url":   _normalize_url(next_m.group(1)),
            "type":  "category",
            "_action": "category",
        })
    return items


def search(query, page=1):
    base = _get_base()
    url  = base + "/search?s=" + quote_plus(query) + "&page=" + str(page)
    html, _ = _fetch_live(url)
    return _extract_cards(html) if html else []


def get_page(url):
    html, final_url = _fetch_live(url)
    if not html:
        return {"title": "Error", "servers": [], "items": [], "type": "movie"}

    title_m = re.search(r'<title>(.*?)</title>', html)
    title   = html_unescape(title_m.group(1)) if title_m else ""

    poster_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster   = _normalize_url(poster_m.group(1)) if poster_m else ""

    plot = ""
    plot_m = re.search(r'class=["\']description["\'][^>]*>(.*?)</p>', html, re.S)
    if plot_m:
        plot = re.sub(r'<[^>]+>', ' ', plot_m.group(1)).strip()
        plot = html_unescape(plot)

    servers  = []
    episodes = []

    if "/series/" in (final_url or url) or "مسلسل" in title:
        for ep_url, ep_num in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?الحلقة\s*(\d+)', html, re.I):
            episodes.append({
                "title":   "الحلقة {}".format(ep_num),
                "url":     _normalize_url(ep_url),
                "type":    "episode",
                "_action": "details",
            })
        if not episodes:
            for s_url, s_num in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?الموسم\s*(\d+)', html, re.I):
                episodes.append({
                    "title":   "الموسم {}".format(s_num),
                    "url":     _normalize_url(s_url),
                    "type":    "category",
                    "_action": "category",
                })

    # Watch page servers
    watch_m = re.search(r'href=["\']([^"\']+/watch/[^"\']+)["\']', html)
    if watch_m:
        watch_url = _normalize_url(watch_m.group(1))
        wh, _ = _fetch_live(watch_url, referer=final_url or url)
        if wh:
            # FIX: improved server JSON parsing — handles both let/var and inline arrays
            servers = _parse_watch_servers(wh, final_url or url)

    return {
        "url":     final_url or url,
        "title":   title,
        "plot":    plot,
        "poster":  poster,
        "servers": servers,
        "items":   episodes,
        "type":    "series" if episodes else "movie",
    }


def _parse_watch_servers(html, base_url):
    """
    FIX: More robust server parsing — tries JSON array, then iframe fallback.
    No longer crashes silently on schema changes.
    """
    servers = []
    seen = set()
    site_root = _site_root(base_url)

    # Pattern 1: servers JSON variable
    for pat in (
        r"let\s+servers\s*=\s*JSON\.parse\(['\"](.+?)['\"]\)",
        r"var\s+servers\s*=\s*(\[.*?\])",
        r"servers\s*=\s*(\[.*?\])",
    ):
        m = re.search(pat, html, re.S | re.I)
        if m:
            try:
                raw = m.group(1).replace("\\'", "'").replace('\\"', '"')
                # JSON.parse input uses single-quote escaping sometimes
                if raw.startswith("["):
                    srv_data = json.loads(raw)
                else:
                    srv_data = json.loads(raw.replace("'", '"'))
                for s in srv_data:
                    if s.get("url"):
                        u = s["url"] + "|Referer=" + site_root
                        if u not in seen:
                            seen.add(u)
                            servers.append({"name": s.get("name", "Server"), "url": u, "type": "direct"})
                if servers:
                    return servers
            except Exception as exc:
                log("Shaheed: server JSON parse failed: {}".format(exc))

    # Pattern 2: iframes
    for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
        u = _normalize_url(m.group(1))
        if u and u not in seen:
            seen.add(u)
            servers.append({"name": "Stream", "url": u + "|Referer=" + site_root, "type": "direct"})

    return servers


def extract_stream(url):
    log("Shaheed extract_stream: {}".format(url))
    referer = _get_base()
    if "|" in url:
        parts = url.split("|", 1)
        url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()

    # FIX: increased max_depth to 10 for deeper iframe chains
    from .base import resolve_iframe_chain
    stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=10)
    if stream:
        return stream, None, referer

    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
