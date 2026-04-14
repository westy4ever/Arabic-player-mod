# -*- coding: utf-8 -*-
import sys
import re
import time
from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, quote, urlparse
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, quote
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

DOMAINS = [
    "https://faselhd.fit/",
    "https://www.faselhd.cam",
    "https://faselhd.pro",
    "https://faselhd.cc",
]

BLOCKED_MARKERS = ("alliance4creativity", "watch-it-legally", "just a moment", "cf-chl", "telegram")

_ACTIVE_URL = None
_ACTIVE_BASE_FETCH_TIME = 0

def _get_base():
    global _ACTIVE_URL
    for domain in DOMAINS:
        log("FaselHD: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        if html and not any(m in (final_url or "").lower() for m in BLOCKED_MARKERS):
            log("FaselHD: using domain {}".format(domain))
            _ACTIVE_URL = domain.rstrip('/')
            return _ACTIVE_URL
    _ACTIVE_URL = DOMAINS[0].rstrip('/')
    return _ACTIVE_URL

def _base():
    global _ACTIVE_URL, _ACTIVE_BASE_FETCH_TIME
    if not _ACTIVE_URL or (time.time() - _ACTIVE_BASE_FETCH_TIME) > 3600:
        _ACTIVE_URL = _get_base()
        _ACTIVE_BASE_FETCH_TIME = time.time()
    return _ACTIVE_URL

def _normalize_url(url):
    if not url: return ""
    url = html_unescape(url.strip())
    if url.startswith("//"): return "https:" + url
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
        {"title": "🎬 افلام اجنبي", "url": base + "/category/افلام-اجنبي", "type": "category"},
        {"title": "🎬 افلام عربي", "url": base + "/category/افلام-عربي", "type": "category"},
        {"title": "📺 مسلسلات اجنبي", "url": base + "/category/مسلسلات-اجنبي", "type": "category"},
        {"title": "📺 مسلسلات عربي", "url": base + "/category/مسلسلات-عربي", "type": "category"},
    ]
    if not html:
        return fallback
    pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
    for match in re.finditer(pattern, html):
        url = match.group(1)
        title = match.group(2).strip()
        if '/category/' in url and title and len(title) < 30:
            emoji = "🎬" if 'فيلم' in title or 'افلام' in title else "📺" if 'مسلسل' in title else "📁"
            categories.append({"title": f"{emoji} {title}", "url": _normalize_url(url), "type": "category"})
    if categories:
        seen = set()
        unique = []
        for cat in categories:
            if cat['url'] not in seen:
                seen.add(cat['url'])
                unique.append(cat)
        return unique
    return fallback

def _extract_items(html):
    items = []
    # New pattern for FaselHD category page (grid-card structure)
    pattern = r'<div[^>]*class="[^"]*grid-card[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)".*?<img[^>]*class="[^"]*thumb-img[^"]*"[^>]*src="([^"]+)".*?<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>'
    matches = re.findall(pattern, html, re.DOTALL | re.I)
    if not matches:
        # Fallback to older pattern
        pattern = r'<div[^>]*class="[^"]*post[^"]*"[^>]*>.*?<a href="([^"]+)".*?<img[^>]*(?:src|data-src)="([^"]+)".*?<h[23][^>]*>([^<]+)</h[23]>'
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
        })
    return items

def get_category_items(url):
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        return []
    # Bypass Telegram wall on category pages
    if "telegram" in html.lower():
        log("FaselHD: Telegram wall on category page, trying to bypass")
        refresh = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;url=([^"\']+)["\']', html, re.I)
        if refresh:
            new_url = _normalize_url(refresh.group(1))
            log("FaselHD: Following meta refresh to {}".format(new_url))
            return get_category_items(new_url)
        link = re.search(r'<a[^>]+href="([^"]+)"[^>]*>.*?(?:متابعة|continue|here).*?</a>', html, re.I)
        if link:
            new_url = _normalize_url(link.group(1))
            log("FaselHD: Following link to {}".format(new_url))
            return get_category_items(new_url)
        return []
    items = _extract_items(html)
    # Pagination
    next_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>التالي|Next</a>', html, re.I)
    if not next_match:
        next_match = re.search(r'<li[^>]*class="next"[^>]*>.*?<a href="([^"]+)"', html, re.I)
    if next_match:
        items.append({"title": "➡️ الصفحة التالية", "url": _normalize_url(next_match.group(1)), "type": "category"})
    return items

def search(query, page=1):
    base = _base()
    url = base + "/?s=" + quote_plus(query)
    html, _ = fetch(url, referer=base)
    return _extract_items(html)

def get_page(url):
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        return {"title": "Error", "servers": [], "items": []}
    # Title
    title_match = re.search(r'<title>(.*?)</title>', html)
    title = _clean_title(title_match.group(1)) if title_match else "FaselHD"
    # Poster
    poster_match = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(poster_match.group(1)) if poster_match else ""
    # Plot
    plot_match = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html)
    plot = _clean_title(plot_match.group(1)) if plot_match else ""

    servers = []
    episodes = []
    item_type = "movie"

    # Series detection
    if '/series/' in url or 'مسلسل' in title:
        item_type = "series"
        ep_pattern = r'<a[^>]+href="([^"]+)"[^>]*>.*?الحلقة\s*(\d+)'
        ep_matches = re.findall(ep_pattern, html, re.I)
        for ep_url, ep_num in ep_matches:
            episodes.append({"title": f"الحلقة {ep_num}", "url": _normalize_url(ep_url), "type": "episode"})
        if not episodes:
            season_pattern = r'<a[^>]+href="([^"]+)"[^>]*>.*?الموسم\s*(\d+)'
            season_matches = re.findall(season_pattern, html, re.I)
            for s_url, s_num in season_matches:
                episodes.append({"title": f"الموسم {s_num}", "url": _normalize_url(s_url), "type": "category"})

    # Extract govid.live download link (or other hosters)
    download_match = re.search(r'href="(https?://govid\.live/d/[^"]+)"', html, re.I)
    if download_match:
        stream_url = download_match.group(1)
        log("FaselHD: Found govid download link: {}".format(stream_url))
        servers.append({"name": "فاصل - سيرفر رئيسي", "url": stream_url})

    other_hosters = re.findall(r'href="(https?://(?:streamtape|dood|mixdrop|voe)[^"]+)"', html, re.I)
    for hurl in other_hosters:
        servers.append({"name": "فاصل - سيرفر", "url": hurl})

    return {"url": final_url, "title": title, "plot": plot, "poster": poster, "servers": servers, "items": episodes, "type": item_type}

def extract_stream(url):
    log("Fasel extract_stream: {}".format(url))
    referer = _base()

    def follow_chain(current_url, ref, depth=0, max_depth=12):
        if depth > max_depth:
            return None
        log("Chain depth {}: {}".format(depth, current_url))
        html, final = fetch(current_url, referer=ref)
        if not html:
            return None
        # Direct m3u8
        m = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html, re.I)
        if m:
            return m.group(1)
        # Meta refresh
        refresh = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;url=([^"\']+)["\']', html, re.I)
        if refresh:
            new_url = refresh.group(1)
            if new_url.startswith("//"):
                new_url = "https:" + new_url
            elif not new_url.startswith("http"):
                new_url = urljoin(current_url, new_url)
            return follow_chain(new_url, current_url, depth+1, max_depth)
        # Iframe
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.I)
        if iframe:
            iframe_url = iframe.group(1)
            if iframe_url.startswith("//"):
                iframe_url = "https:" + iframe_url
            elif not iframe_url.startswith("http"):
                iframe_url = urljoin(current_url, iframe_url)
            return follow_chain(iframe_url, current_url, depth+1, max_depth)
        # Hoster link
        hoster = re.search(r'href=["\'](https?://(?:govid|streamtape|dood|mixdrop)[^"\']+)["\']', html, re.I)
        if hoster:
            return follow_chain(hoster.group(1), current_url, depth+1, max_depth)
        # Any other link
        any_link = re.search(r'href=["\'](https?://[^"\']+)["\']', html, re.I)
        if any_link:
            next_url = any_link.group(1)
            if next_url != current_url and not next_url.endswith("/"):
                return follow_chain(next_url, current_url, depth+1, max_depth)
        return None

    stream = follow_chain(url, referer)
    if stream:
        quality = "HD" if "1080" in stream else ("720p" if "720" in stream else "Auto")
        return stream, quality, referer
    # Fallback
    from .base import resolve_iframe_chain
    stream, _ = resolve_iframe_chain(url, referer=referer)
    if stream:
        return stream, "Auto", referer
    return None, None, referer