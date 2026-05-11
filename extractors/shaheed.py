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
    ref = referer or _get_base()
    h, final_url = fetch(url, referer=ref)
    if _is_blocked_page(h, final_url):
        return "", ""
    return h, final_url or url


def get_categories():
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
    html, _ = _fetch_live(url)
    if not html:
        return []

    items = []
    seen_urls = set()

    # FIX: the old pattern required a specific attribute order (href then class then style)
    # and an exact single space between attributes. Sites often vary attribute order.
    # Strategy 1: find <a class="show-card"> with any attribute order, grab poster from style
    for match in re.finditer(r'<a\s[^>]*class="[^"]*show-card[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL | re.I):
        tag_open = html[match.start():match.start() + 300]
        card_content = match.group(1)

        # href from the opening tag
        href_m = re.search(r'href="([^"]+)"', tag_open, re.I)
        if not href_m:
            continue
        full_url = _normalize_url(href_m.group(1))
        if not full_url or full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # poster from style="background-image:url(...)" — in opening tag or card content
        poster_url = ""
        poster_m = re.search(r'background-image:\s*url\(([^)]+)\)', tag_open + card_content, re.I)
        if poster_m:
            poster_url = _normalize_url(poster_m.group(1).strip("'\" "))

        # title from <p class="title">
        title_m = re.search(r'<p[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</p>', card_content, re.I)
        if not title_m:
            title_m = re.search(r'<[^>]+class="[^"]*title[^"]*"[^>]*>([^<]+)</', card_content, re.I)
        if not title_m:
            # fall back to any text in the card
            title_m = re.search(r'>([^<]{3,})<', card_content)
        title = html_unescape(title_m.group(1).strip()) if title_m else ""
        if not title:
            continue

        quality_m = re.search(r'<span[^>]*class="[^"]*sticker[^"]*"[^>]*>([^<]+)</span>', card_content, re.I)
        quality = quality_m.group(1).strip() if quality_m else ""

        categ_m = re.search(r'<span[^>]*class="[^"]*categ[^"]*"[^>]*>([^<]+)</span>', card_content, re.I)
        category = categ_m.group(1).strip() if categ_m else ""

        item_type = "series" if ("مسلسلات" in category or "عروض" in category or
                                  "/category/مسلسلات" in url or "/category/عروض" in url) else "movie"

        display_title = "{} [{}]".format(title, quality) if quality else title
        items.append({
            "title": display_title,
            "url": full_url,
            "poster": poster_url,
            "plot": category,
            "type": item_type,
            "_action": "details",
        })

    # Strategy 2 fallback: article/div cards with poster images (site may have redesigned)
    if not items:
        log("Shaheed: show-card pattern matched 0 items, trying generic card fallback")
        for match in re.finditer(
            r'<(?:article|div)[^>]+class="[^"]*(?:card|item|post|movie)[^"]*"[^>]*>(.*?)</(?:article|div)>',
            html, re.S | re.I
        ):
            block = match.group(1)
            href_m = re.search(r'href="([^"]+)"', block, re.I)
            if not href_m:
                continue
            full_url = _normalize_url(href_m.group(1))
            if not full_url or full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            title_m = (re.search(r'<h[1-4][^>]*>([^<]+)</h[1-4]>', block, re.I) or
                       re.search(r'alt="([^"]+)"', block, re.I) or
                       re.search(r'title="([^"]+)"', block, re.I))
            title = html_unescape(title_m.group(1).strip()) if title_m else ""
            if not title:
                continue

            img_m = (re.search(r'src="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', block, re.I) or
                     re.search(r'data-src="([^"]+)"', block, re.I))
            poster_url = _normalize_url(img_m.group(1)) if img_m else ""

            items.append({
                "title": title,
                "url": full_url,
                "poster": poster_url,
                "type": "movie",
                "_action": "details",
            })

    # Pagination
    pagination_pattern = r'<button[^>]+onclick="updateQuery\(\'page\',\s*(\d+)\)"[^>]*>(\d+)</button>'
    current_page = None
    max_page = None
    for match in re.finditer(pagination_pattern, html):
        page_num = int(match.group(2))
        if match.group(1) == str(page_num):
            current_page = page_num
        if page_num > (max_page or 0):
            max_page = page_num

    if current_page and max_page and current_page < max_page:
        sep = "&" if "?" in url else "?"
        items.append({
            "title": "➡️ Next Page",
            "url": url + sep + "page=" + str(current_page + 1),
            "type": "category",
            "_action": "category",
        })

    log("Shaheed: {} -> {} items".format(url, len(items)))
    return items


def search(query, page=1):
    base = _get_base()
    url = base + "/search?s=" + quote_plus(query)
    if page > 1:
        url += "&page=" + str(page)
    html, _ = _fetch_live(url)
    if not html:
        return []
    return get_category_items(url)


def get_page(url):
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

    title_match = re.search(r'<title>(.*?)</title>', html)
    if title_match:
        title = html_unescape(title_match.group(1))
        title = re.sub(r'\s*[-|]\s*شاهد\s*فور\s*يو.*$', '', title)
        title = re.sub(r'\s*[-|]\s*Shahid4u.*$', '', title, flags=re.I)
        result["title"] = title.strip()

    desc_match = re.search(r'<meta\s+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if desc_match:
        result["plot"] = html_unescape(desc_match.group(1))

    poster_match = re.search(r'<meta\s+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if poster_match:
        result["poster"] = _normalize_url(poster_match.group(1))

    # Extract servers from JavaScript array
    servers_pattern = r'let\s+servers\s*=\s*JSON\.parse\(\'([^\']+)\'\)'
    match = re.search(servers_pattern, html)
    if match:
        try:
            servers_json = match.group(1).replace('\\"', '"')
            servers_data = json.loads(servers_json)
            for server in servers_data:
                if server.get("url"):
                    result["servers"].append({
                        "name": server.get("name", "Server"),
                        "url": server["url"],
                        "type": "embed"
                    })
            log("Shaheed: extracted {} servers from JSON".format(len(result["servers"])))
        except Exception as e:
            log("Shaheed: failed to parse servers JSON: {}".format(e))

    if not result["servers"]:
        alt_pattern = r'servers\s*=\s*(\[.*?\])'
        match = re.search(alt_pattern, html, re.DOTALL)
        if match:
            try:
                for server in json.loads(match.group(1)):
                    if server.get("url"):
                        result["servers"].append({
                            "name": server.get("name", "Server"),
                            "url": server["url"],
                            "type": "embed"
                        })
            except Exception as e:
                log("Shaheed: failed to parse alt servers JSON: {}".format(e))

    if not result["servers"]:
        skip_domains = ['youtube', 'facebook', 'twitter', 'google', 'doubleclick',
                        'analytics', 'googletagmanager', 'cloudflareinsights',
                        'adsco.re', 'intelligenceadx']
        embed_domains = ['fastvid.cam', 'streamtape', 'doodstream', 'voe',
                         'filemoon', 'rpmvip', 'upn.one', 'cleantechworld',
                         'streamwish', 'mixdrop', 'vidguard']
        for iframe_match in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
            iframe_url = iframe_match.group(1)
            if any(x in iframe_url.lower() for x in skip_domains):
                continue
            if iframe_url.startswith("//"):
                iframe_url = "https:" + iframe_url
            elif iframe_url.startswith("/"):
                p = urlparse(final_url or url)
                iframe_url = "{}://{}{}".format(p.scheme, p.netloc, iframe_url)
            if any(d in iframe_url.lower() for d in embed_domains):
                result["servers"].append({"name": "Embed Player", "url": iframe_url, "type": "iframe"})

    if "/مسلسلات" in url or "series" in url.lower() or "/عروض" in url or "/post/" in url:
        result["type"] = "series"

    log("Shaheed: {} -> found {} servers".format(url, len(result["servers"])))
    return result


def extract_stream(url):
    log("Shaheed extract_stream: {}".format(url))
    referer = _get_base()
    if "|" in url:
        parts = url.split("|", 1)
        url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()

    from .base import resolve_iframe_chain
    stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=10)
    if stream:
        return stream, None, referer

    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
