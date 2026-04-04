# -*- coding: utf-8 -*-
import re
import sys
import json

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
    "https://shaheeid4u.net/",
]
VALID_HOST_MARKERS = (
    "shaheeid4u.net",
    "shahid4u",
)
BLOCKED_HOST_MARKERS = (
    "alliance4creativity.com",
)
MAIN_URL = None
_HOME_HTML = None

_CATEGORY_FALLBACKS = {
    "افلام اجنبي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a",
    "افلام عربي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%b9%d8%b1%d8%a8%d9%8a",
    "افلام انمي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d9%86%d9%85%d9%8a",
    "افلام اسيوي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%b3%d9%8a%d9%88%d9%8a%d8%a9",
    "مسلسلات اجنبي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a",
    "مسلسلات عربي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b9%d8%b1%d8%a8%d9%8a",
    "مسلسلات تركي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%aa%d8%b1%d9%83%d9%8a%d8%a9",
    "مسلسلات انمي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d9%86%d9%85%d9%8a",
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
        or "__cf_chl" in text
        or "alliance for creativity" in text
        or any(marker in final for marker in BLOCKED_HOST_MARKERS)
        or (final and not _is_valid_site_url(final))
    )


def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)


def _get_base():
    global MAIN_URL, _HOME_HTML
    if MAIN_URL:
        return MAIN_URL
    for domain in DOMAINS:
        log("Shaheed: probing base {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Shaheed: blocked base {}".format(final_url))
            continue
        if html and "shah" in html.lower():
            MAIN_URL = _site_root(final_url)
            _HOME_HTML = html
            log("Shaheed: selected base {}".format(MAIN_URL))
            return MAIN_URL
    MAIN_URL = DOMAINS[0]
    log("Shaheed: fallback base {}".format(MAIN_URL))
    return MAIN_URL


def _search_url():
    return _get_base().rstrip("/") + "/search?s="


def _quote_url(url):
    if not url: return url
    try:
        from urllib.parse import urlparse, urlunparse, quote, unquote
        # Force unquote first to ensure we don't double-encode % characters
        url_dec = unquote(url)
        p = list(urlparse(url_dec))
        # Quote only the path and query parts
        p[2] = quote(p[2])
        p[4] = quote(p[4], safe='=&/%')
        return urlunparse(p)
    except Exception:
        return url


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
    url = _quote_url(url)
    log("Shaheed: fetch candidate {}".format(url))
    if not _is_valid_site_url(url):
        log("Shaheed: rejecting invalid target {}".format(url))
        return "", ""
    ref = referer or _get_base()
    h, start_url = fetch(url, referer=ref)
    if _is_blocked_page(h, start_url):
        return "", ""
    log("Shaheed: fetch success {}".format(start_url))
    return h, start_url


def _category_from_home(label, fallback):
    global _HOME_HTML
    if not _HOME_HTML:
        _get_base()
    if _HOME_HTML:
        token = '>{}<'.format(label)
        start = _HOME_HTML.find(token)
        if start > 0:
            block = _HOME_HTML[max(0, start - 200):start]
            m = re.search(r'href=["\']([^"\']+)["\']', block)
            if m:
                u = _normalize_url(m.group(1))
                if _is_valid_site_url(u):
                    return u
    return _normalize_url(urljoin(_get_base(), fallback))


def _extract_cards(html):
    items = []
    # Find all <a> tags that have class "show-card"
    blocks = re.findall(r'(<a[^>]+(?:class=["\'][^"\']*show-card[^"\']*["\']|href=["\'][^"\']+(?:/film/|/series/|/episode/|/anime/)[^"\']+["\'])[^>]*>.*?</a>)', html, re.S | re.IGNORECASE)
    
    seen = set()
    for block in blocks:
        href_m = re.search(r'href=["\']([^"\']+)["\']', block)
        if not href_m: continue
        url = href_m.group(1)
        if url in seen: continue
        seen.add(url)
        
        img_m = re.search(r'url\([\'"]?([^)\'"]+)[\'"]?\)', block)
        if not img_m:
            img_m = re.search(r'src=["\']([^"\']+)["\']', block)
        img = img_m.group(1) if img_m else ""
        
        title_m = re.search(r'class=["\']title["\']>([^<]+)<', block)
        if not title_m:
             title_m = re.search(r'alt=["\']([^"\']+)["\']', block)
        title = title_m.group(1).strip() if title_m else ""
        
        if title:
            items.append({
                "title": html_unescape(title),
                "url": _normalize_url(url),
                "poster": _normalize_url(img.strip("'\"")),
                "type": "series" if "/series" in url or "/season" in url else ("episode" if "/episode" in url else "movie"),
                "_action": "item",
            })
    return items


def _extract_next_page(html):
    m = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*rel=["\']next["\']', html)
    if m:
        return _normalize_url(m.group(1))
    return None


def get_categories():
    # Adding a clear User-Agent to mimic a real browser to help with Cloudflare
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
    }
    return [
        {"title": "🎬 الأفلام الأجنبية", "url": MAIN_URL + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a-foreign-movies/", "type": "category", "_action": "category"},
        {"title": "📺 المسلسلات الأجنبية", "url": MAIN_URL + "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a-foreign-series/", "type": "category", "_action": "category"},
        {"title": "🎭 عروض المصارعة", "url": MAIN_URL + "/category/%d8%b9%d8%b1%d9%88%d8%b6-%d8%a7%d9%84%d9%85%d8%b5%d8%a7%d8%b1%d8%b9%d8%a9-wrestling/", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات عربية", "url": _category_from_home("مسلسلات عربي", _CATEGORY_FALLBACKS["مسلسلات عربي"]), "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات تركية", "url": _category_from_home("مسلسلات تركية", _CATEGORY_FALLBACKS["مسلسلات تركي"]), "type": "category", "_action": "category"},
        {"title": "📺 أفلام أنمي", "url": _category_from_home("افلام انمي", _CATEGORY_FALLBACKS["افلام انمي"]), "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أنمي", "url": _category_from_home("مسلسلات انمي", _CATEGORY_FALLBACKS["مسلسلات انمي"]), "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, final_url = _fetch_live(url)
    if not html:
        return []

    items = _extract_cards(html)
    log("Shaheed: category {} -> {} items".format(url, len(items)))
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def search(query, page=1):
    items = []
    html, final_url = _fetch_live(_search_url() + quote_plus(query) + "&page=" + str(page))
    if not html:
        return items

    items = _extract_cards(html)
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})

    return items


def _detail_title(html):
    m = re.search(r'<title>(.*?)</title>', html)
    if m:
        return html_unescape(m.group(1))
    return ""


def _detail_poster(html):
    m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    return _normalize_url(m.group(1)) if m else ""


def _detail_plot(html):
    m = re.search(r'class=["\']description["\'][^>]*>(.*?)</p>', html, re.S)
    if m:
        txt = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()
        return html_unescape(txt)
    return ""


def get_page(url):
    # Shaheed4u places servers on a separate generic player page, or inline via JSON.
    html, final_url = _fetch_live(url)
    if not html:
        log("Shaheed: detail failed {}".format(url))
        return {"title": "Error", "servers": [], "items": []}

    title = _detail_title(html)
    poster = _detail_poster(html)
    plot = _detail_plot(html)
    
    servers = []
    episodes = []

    # Could be a series page
    if "/series/" in final_url or "مسلسل" in title:
        ep_cards = re.findall(r'<a[^>]+href=["\'](https://shaheeid4u\.net/episode/[^"\']+)["\'][^>]*class=["\']ep-card["\'][^>]*>.*?<span[^>]*>([^<]+)</span>', html, re.S)
        for ep_url, ep_title in ep_cards:
            episodes.append({
                "title": html_unescape(ep_title.strip()),
                "url": _normalize_url(ep_url),
                "type": "episode",
                "_action": "item"
            })
    
    # If it's a film or episode, extract servers
    watch_page_link = None
    m = re.search(r'href=["\']([^"\']+/watch/[^"\']+)["\']', html)
    if m:
        watch_page_link = _normalize_url(m.group(1))
    
    if watch_page_link:
        wh, wfinal = _fetch_live(watch_page_link, referer=final_url)
        js_servers = re.search(r'let servers = JSON\.parse\(\'(.*?)\'\)', wh)
        if js_servers:
            try:
                srv_data = json.loads(js_servers.group(1))
                for s in srv_data:
                    if s.get("url"):
                        servers.append({
                            "name": s.get("name", "Server"),
                            "url": s["url"] + "|Referer=" + _site_root(final_url)
                        })
            except Exception as e:
                log("Shaheed: JSON decode error: {}".format(e))
    else:
        # Fallback: Maybe they are inline
        js_servers = re.search(r'let servers = JSON\.parse\(\'(.*?)\'\)', html)
        if js_servers:
            try:
                srv_data = json.loads(js_servers.group(1))
                for s in srv_data:
                    if s.get("url"):
                        servers.append({
                            "name": s.get("name", "Server"),
                            "url": s["url"] + "|Referer=" + _site_root(final_url)
                        })
            except Exception as e:
                log("Shaheed: JSON decode error inline: {}".format(e))

    item_type = "series" if episodes else "movie"
    if "/episode/" in final_url:
        item_type = "episode"

    return {
        "url": final_url or url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "servers": servers,
        "items": episodes,
        "type": item_type,
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
    resolved = resolve_iframe_chain(url, referer=referer)
    if resolved:
        return resolved, None, referer
    return url, None, referer
