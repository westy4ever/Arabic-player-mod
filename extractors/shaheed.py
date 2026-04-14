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

VALID_HOST_MARKERS = ("shahid4u.guru", "shahieed4u.net", "shaheeid4u.net")
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
    if any(marker in host for marker in BLOCKED_HOST_MARKERS):
        return False
    return any(marker in host for marker in VALID_HOST_MARKERS)

def _is_blocked_page(html, final_url=""):
    text = (html or "").lower()
    final = (final_url or "").lower()
    return (
        not text
        or "just a moment" in text
        or "cf-chl" in text
        or "alliance for creativity" in text
        or any(marker in final for marker in BLOCKED_HOST_MARKERS)
        or (final and not _is_valid_site_url(final))
    )

def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)

def _get_base(force_refresh=False):
    global MAIN_URL, _HOME_HTML, _HOME_LAST_FETCH
    if MAIN_URL and not force_refresh and (time.time() - _HOME_LAST_FETCH) < 21600:
        return MAIN_URL
    for domain in DOMAINS:
        log("Shaheed: probing base {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Shaheed: blocked base {}".format(final_url))
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
    if not _is_valid_site_url(url):
        log("Shaheed: rejecting invalid target {}".format(url))
        return "", ""
    ref = referer or _get_base()
    h, start_url = fetch(url, referer=ref)
    if _is_blocked_page(h, start_url):
        return "", ""
    return h, start_url

def get_categories():
    base = _get_base().rstrip("/")
    html, _ = _fetch_live(base)
    categories = []
    seen_urls = set()
    if html:
        pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
        for match in re.finditer(pattern, html):
            url = match.group(1)
            title = match.group(2).strip()
            if '/category/' in url and title and len(title) < 30 and url not in seen_urls:
                seen_urls.add(url)
                emoji = "📁"
                if 'فيلم' in title or 'افلام' in title:
                    emoji = "🎬"
                elif 'مسلسل' in title or 'مسلسلات' in title:
                    emoji = "📺"
                categories.append({"title": f"{emoji} {title}", "url": _normalize_url(url), "type": "category"})
    if not categories:
        categories = [
            {"title": "🎬 افلام اجنبي", "url": base + "/category/افلام-اجنبي", "type": "category"},
            {"title": "🎬 افلام عربي", "url": base + "/category/افلام-عربي", "type": "category"},
            {"title": "📺 مسلسلات اجنبي", "url": base + "/category/مسلسلات-اجنبي", "type": "category"},
            {"title": "📺 مسلسلات عربي", "url": base + "/category/مسلسلات-عربي", "type": "category"},
        ]
    return categories

def _extract_cards(html):
    items = []
    # Try JSON-LD first
    json_ld_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    if json_ld_match:
        try:
            data = json.loads(json_ld_match.group(1))
            if data.get("@type") == "ItemList":
                for entry in data.get("itemListElement", []):
                    item = entry.get("item", {})
                    if item.get("@type") in ("Movie", "TVSeries"):
                        title = item.get("name", "")
                        url = item.get("url", "")
                        poster = item.get("image", "")
                        if title and url:
                            items.append({
                                "title": html_unescape(title),
                                "url": _normalize_url(url),
                                "poster": _normalize_url(poster),
                                "type": "movie" if item.get("@type") == "Movie" else "series",
                                "_action": "item",
                            })
                if items:
                    return items
        except:
            pass

    # Fallback patterns
    patterns = [
        r'<div[^>]*class="[^"]*post[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)".*?<img[^>]+src="([^"]+)".*?<h[23][^>]*>([^<]+)</h[23]>',
        r'<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)".*?<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>',
        r'<div[^>]*class="[^"]*movie-card[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)".*?<img[^>]+src="([^"]+)".*?<div[^>]*class="[^"]*name[^"]*"[^>]*>([^<]+)</div>',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL | re.I)
        if matches:
            for match in matches:
                url = match[0]
                poster = match[1]
                title = match[2].strip()
                if title and url:
                    items.append({
                        "title": html_unescape(title),
                        "url": _normalize_url(url),
                        "poster": _normalize_url(poster),
                        "type": "movie",
                        "_action": "item",
                    })
            if items:
                break
    return items

def get_category_items(url):
    html, final_url = _fetch_live(url)
    if not html:
        return []
    items = _extract_cards(html)
    log("Shaheed: category {} -> {} items".format(url, len(items)))
    # Pagination
    next_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>التالي|Next</a>', html, re.I)
    if next_match:
        items.append({"title": "➡️ الصفحة التالية", "url": _normalize_url(next_match.group(1)), "type": "category", "_action": "category"})
    return items

def search(query, page=1):
    base = _get_base()
    url = base + "/search?s=" + quote_plus(query) + "&page=" + str(page)
    html, _ = _fetch_live(url)
    return _extract_cards(html)

def get_page(url):
    html, final_url = _fetch_live(url)
    if not html:
        return {"title": "Error", "servers": [], "items": []}
    # Title
    title_match = re.search(r'<title>(.*?)</title>', html)
    title = html_unescape(title_match.group(1)) if title_match else ""
    # Poster
    poster_match = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(poster_match.group(1)) if poster_match else ""
    # Plot
    plot_match = re.search(r'class=["\']description["\'][^>]*>(.*?)</p>', html, re.S)
    plot = ""
    if plot_match:
        plot = re.sub(r'<[^>]+>', ' ', plot_match.group(1)).strip()
        plot = html_unescape(plot)
    # Servers and episodes
    servers = []
    episodes = []
    # Check if series
    if '/series/' in final_url or 'مسلسل' in title:
        ep_pattern = r'<a[^>]+href="([^"]+)"[^>]*>.*?الحلقة\s*(\d+)'
        ep_matches = re.findall(ep_pattern, html, re.I)
        for ep_url, ep_num in ep_matches:
            episodes.append({"title": f"الحلقة {ep_num}", "url": _normalize_url(ep_url), "type": "episode"})
        if not episodes:
            season_pattern = r'<a[^>]+href="([^"]+)"[^>]*>.*?الموسم\s*(\d+)'
            season_matches = re.findall(season_pattern, html, re.I)
            for s_url, s_num in season_matches:
                episodes.append({"title": f"الموسم {s_num}", "url": _normalize_url(s_url), "type": "category"})
    # Extract watch page link
    watch_match = re.search(r'href=["\']([^"\']+/watch/[^"\']+)["\']', html)
    if watch_match:
        watch_url = _normalize_url(watch_match.group(1))
        wh, _ = _fetch_live(watch_url, referer=final_url)
        if wh:
            # Look for servers in JSON
            js_servers = re.search(r'let servers = JSON\.parse\(\'(.*?)\'\)', wh)
            if not js_servers:
                js_servers = re.search(r'var servers = (\[.*?\])', wh, re.S)
            if js_servers:
                try:
                    srv_str = js_servers.group(1).replace("'", '"')
                    srv_data = json.loads(srv_str)
                    for s in srv_data:
                        if s.get("url"):
                            servers.append({"name": s.get("name", "Server"), "url": s["url"] + "|Referer=" + _site_root(final_url)})
                except:
                    pass
            else:
                iframe = re.search(r'<iframe[^>]+src="([^"]+)"', wh)
                if iframe:
                    servers.append({"name": "Stream", "url": iframe.group(1) + "|Referer=" + _site_root(final_url)})
    return {
        "url": final_url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "servers": servers,
        "items": episodes,
        "type": "series" if episodes else "movie",
    }

def extract_stream(url):
    log("Shaheed extract_stream: {}".format(url))
    referer = _get_base()
    if "|" in url:
        parts = url.split("|", 1)
        url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()
    from .base import resolve_iframe_chain
    stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=6)
    if stream:
        return stream, None, referer
    return url, None, referer