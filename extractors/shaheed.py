# -*- coding: utf-8 -*-
"""
Shaheed4u extractor - Fixed for current site structure (shhahidd4u.net)
Supports: Movies, Series, TV Shows, Wrestling Shows
Uses base.fetch for all HTTP requests.
"""

import re
import sys
import json
import time
from .base import fetch, urljoin, log, resolve_iframe_chain

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse, quote
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, quote
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

# Updated domains (try the new one first, then the redirect)
DOMAINS = [
    "https://shhahidd4u.net/",
    "https://shaied4u.co/",
]

BLOCKED_HOST_MARKERS = ("alliance4creativity.com",)
MAIN_URL = None
_HOME_HTML = None
_HOME_LAST_FETCH = 0

# ----------------------------------------------------------------------
# Helper functions using base.fetch
# ----------------------------------------------------------------------

def _is_blocked_page(html, final_url=""):
    """Enhanced blocked/challenge detection."""
    text = (html or "").lower()
    final = (final_url or "").lower()
    if not text:
        return True
    challenge_patterns = [
        "just a moment", "cf-chl", "cf-turnstile",
        "challenge", "cloudflare", "browser check",
        "access denied", "blocked", "forbidden",
        "captcha", "verify you are human",
        "cf-browser-verification", "security check",
    ]
    if any(p in text for p in challenge_patterns):
        return True
    if any(m in final for m in BLOCKED_HOST_MARKERS):
        return True
    if len(text) < 500 and ("error" in text or "block" in text):
        return True
    return False

def _is_valid_category_page(html):
    """Check if the HTML contains typical category elements."""
    if not html:
        return False
    if re.search(r'class="[^"]*show-card[^"]*"', html, re.I):
        return True
    if re.search(r'href="[^"]*/(film|episode|series|watch)/[^"]*"', html, re.I):
        return True
    if '<title>' in html and ('افلام' in html or 'مسلسلات' in html):
        if not _is_blocked_page(html) and len(html) > 5000:
            return True
    return False

def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)

def _get_base(force_refresh=False):
    """Determine the working base URL using base.fetch."""
    global MAIN_URL, _HOME_HTML, _HOME_LAST_FETCH
    if MAIN_URL and not force_refresh and (time.time() - _HOME_LAST_FETCH) < 21600:
        log("Shaheed: using cached base {}".format(MAIN_URL))
        return MAIN_URL

    for domain in DOMAINS:
        log("Shaheed: probing {} with base.fetch".format(domain))
        html, final_url = fetch(domain, referer=domain)
        if not html:
            log("Shaheed: no response from {}".format(domain))
            continue
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Shaheed: blocked or invalid at {}".format(final_url))
            continue
        if html and ("شاهد" in html or "shahid" in html.lower() or "film" in html.lower() or "مسلسل" in html):
            MAIN_URL = _site_root(final_url)
            _HOME_HTML = html
            _HOME_LAST_FETCH = time.time()
            log("Shaheed: selected base {}".format(MAIN_URL))
            return MAIN_URL

    # If all fail, use the first domain as fallback
    MAIN_URL = DOMAINS[0]
    log("Shaheed: fallback base {} (may not be reachable)".format(MAIN_URL))
    return MAIN_URL

def _fetch_live(url, referer=None):
    """Fetch a page; if blocked, refresh the base and retry once."""
    ref = referer or _get_base()
    log("Shaheed: _fetch_live for {}".format(url))
    html, final_url = fetch(url, referer=ref)
    if _is_blocked_page(html, final_url):
        log("Shaheed: blocked page, refreshing base and retrying")
        _get_base(force_refresh=True)
        html, final_url = fetch(url, referer=_get_base())
        if _is_blocked_page(html, final_url):
            log("Shaheed: still blocked after refresh")
            return "", ""
    log("Shaheed: fetch OK, {} bytes".format(len(html) if html else 0))
    return html, final_url or url

def _normalize_url(url):
    if not url:
        return ""
    url = html_unescape(url.strip())
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(_get_base(), url)
    return url

# ----------------------------------------------------------------------
# Server extraction (unchanged)
# ----------------------------------------------------------------------

def _extract_servers_from_watch(html, base_url):
    """Parse the watch page HTML to extract server information."""
    servers = []
    match = re.search(r'let\s+securedServers\s*=\s*(\[.*?\]);', html, re.DOTALL | re.I)
    if not match:
        match = re.search(r'securedServers\s*=\s*(\[.*?\]);', html, re.DOTALL | re.I)
    if match:
        try:
            servers_data = json.loads(match.group(1))
            for idx, server in enumerate(servers_data):
                name = server.get("name", "Server {}".format(idx+1))
                hash_val = server.get("hash")
                if hash_val:
                    embed_url = "{}/embed-stream/{}".format(base_url.rstrip('/'), quote(hash_val))
                    servers.append({
                        "name": name,
                        "url": embed_url,
                        "type": "embed"
                    })
            log("Shaheed: extracted {} servers from securedServers".format(len(servers)))
            return servers
        except Exception as e:
            log("Shaheed: failed to parse securedServers: {}".format(e))

    # Fallback: iframes
    iframe_matches = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    for src in iframe_matches:
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = urljoin(base_url, src)
        skip_domains = ['youtube', 'facebook', 'twitter', 'google', 'doubleclick',
                        'analytics', 'googletagmanager', 'cloudflareinsights',
                        'adsco.re', 'intelligenceadx']
        if any(x in src.lower() for x in skip_domains):
            continue
        servers.append({
            "name": "Embed Player",
            "url": src,
            "type": "iframe"
        })
    return servers

# ----------------------------------------------------------------------
# Category and item extraction (unchanged logic, just uses _fetch_live)
# ----------------------------------------------------------------------

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
    log("Shaheed: get_category_items for {}".format(url))
    html, _ = _fetch_live(url)
    if not html:
        log("Shaheed: no HTML for category")
        return []

    if not _is_valid_category_page(html):
        log("Shaheed: category page invalid, refreshing base and retrying")
        _get_base(force_refresh=True)
        html, _ = _fetch_live(url)
        if not html or not _is_valid_category_page(html):
            log("Shaheed: still invalid after refresh, returning empty")
            return []

    items = []
    seen_urls = set()

    # Extract show-card entries
    for match in re.finditer(r'<a\s[^>]*class="[^"]*show-card[^"]*"[^>]*>(.*?)</a>', html, re.DOTALL | re.I):
        tag_open = html[match.start():match.start() + 300]
        card_content = match.group(1)

        href_m = re.search(r'href="([^"]+)"', tag_open, re.I)
        if not href_m:
            continue
        full_url = _normalize_url(href_m.group(1))
        if not full_url or full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        poster_url = ""
        poster_m = re.search(r'background-image:\s*url\(([^)]+)\)', tag_open + card_content, re.I)
        if poster_m:
            poster_url = _normalize_url(poster_m.group(1).strip("'\" "))

        title_m = re.search(r'<p[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</p>', card_content, re.I)
        if not title_m:
            title_m = re.search(r'<[^>]+class="[^"]*title[^"]*"[^>]*>([^<]+)</', card_content, re.I)
        if not title_m:
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

    # Fallback: generic cards
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
    current_page = None
    max_page = None

    curr_match = re.search(
        r'<button[^>]+class="[^"]*page-link[^"]*cursor-normal[^"]*"[^>]*>(\d+)</button>',
        html, re.I
    )
    if curr_match:
        current_page = int(curr_match.group(1))

    page_nums = set()
    for match in re.finditer(r"updateQuery\('page',\s*(\d+)\)", html):
        page_nums.add(int(match.group(1)))
    if page_nums:
        max_page = max(page_nums)

    if current_page is not None and max_page is not None and max_page > current_page:
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

# ----------------------------------------------------------------------
# get_page – fetch details, servers, and episode list
# ----------------------------------------------------------------------

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

    # Metadata
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

    # Find watch URL
    watch_url = None
    if "/watch/" in url:
        watch_url = url
    else:
        watch_link_match = re.search(r'<a[^>]+href=["\']([^"\']+/watch/[^"\']*)["\'][^>]*>.*?مشاهدة', html, re.I | re.S)
        if watch_link_match:
            watch_url = _normalize_url(watch_link_match.group(1))
        else:
            watch_link_match = re.search(r'<a[^>]+class=["\'][^"\']*watch[^"\']*["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
            if watch_link_match:
                watch_url = _normalize_url(watch_link_match.group(1))

    watch_html = None
    if watch_url:
        watch_html, _ = _fetch_live(watch_url)
    else:
        if "/watch/" in url:
            watch_html = html
            watch_url = url

    if watch_html:
        base_for_embed = _get_base().rstrip('/')
        servers = _extract_servers_from_watch(watch_html, base_for_embed)
        if servers:
            result["servers"] = servers
            log("Shaheed: found {} servers on watch page".format(len(servers)))
        else:
            log("Shaheed: no servers found on watch page")

        # Extract episode list (right sidebar)
        eps_container_match = re.search(r'<div[^>]*id=["\']eps["\'][^>]*>(.*?)</div>', watch_html, re.S | re.I)
        if not eps_container_match:
            eps_container_match = re.search(r'<div[^>]*class=["\'][^"\']*eps[^"\']*["\'][^>]*>(.*?)</div>', watch_html, re.S | re.I)
        if eps_container_match:
            eps_html = eps_container_match.group(1)
            for ep_match in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', eps_html, re.S | re.I):
                ep_url = _normalize_url(ep_match.group(1))
                if not ep_url or ep_url == watch_url:
                    continue
                ep_inner = ep_match.group(2)
                ep_text = re.sub(r'<[^>]+>', '', ep_inner).strip()
                ep_num_match = re.search(r'الحلقة\s*(\d+)', ep_text)
                if ep_num_match:
                    ep_title = "حلقة {}".format(ep_num_match.group(1))
                else:
                    ep_title = ep_text or "حلقة"
                if ep_url != watch_url and ep_url not in [item.get("url") for item in result["items"]]:
                    result["items"].append({
                        "title": ep_title,
                        "url": ep_url,
                        "type": "episode",
                        "_action": "details",
                    })
        else:
            log("Shaheed: no episode list found on watch page")

    # Determine type
    if result["items"]:
        result["type"] = "series"
    elif "مسلسلات" in url or "series" in url.lower() or "/عروض" in url or "/post/" in url:
        result["type"] = "series"
    elif "/episode/" in url:
        result["type"] = "episode"
    else:
        result["type"] = "movie"

    log("Shaheed: {} -> found {} servers, {} episodes".format(url, len(result["servers"]), len(result["items"])))
    return result

# ----------------------------------------------------------------------
# extract_stream – resolve the embed URL
# ----------------------------------------------------------------------

def extract_stream(url):
    log("Shaheed extract_stream: {}".format(url))
    referer = _get_base()
    if "|" in url:
        parts = url.split("|", 1)
        url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()

    if url.startswith("/"):
        url = urljoin(_get_base(), url)

    stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=10)
    if stream:
        return stream, None, referer

    # Fallback: try a direct fetch to find video source
    html, _ = fetch(url, referer=referer)
    if html:
        video_src = re.search(r'(?:src|data-src)=["\']([^"\']+\.(?:mp4|m3u8|webm)[^"\']*)["\']', html, re.I)
        if video_src:
            return video_src.group(1), None, referer
        iframe_src = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if iframe_src:
            return extract_stream(iframe_src.group(1))

    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)