# -*- coding: utf-8 -*-
import sys
import re
from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, quote
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, quote
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

DOMAINS = ["https://web33012x.faselhdx.bid", "https://faselhd.center", "https://www.faselhdx.bid", "https://faselhd.fm", "https://www.fasel-hd.com"]
MAIN_URL = DOMAINS[0]

BLOCKED_MARKERS = ("alliance4creativity", "watch-it-legally")

def _get_base():
    """Try all domains and return the first working one"""
    for domain in DOMAINS:
        html, final_url = fetch(domain, referer=domain)
        if html and not any(m in (final_url or "").lower() for m in BLOCKED_MARKERS):
            log("FaselHD: using domain {}".format(domain))
            return domain
        log("FaselHD: domain {} is blocked or down".format(domain))
    return DOMAINS[0]

_ACTIVE_URL = None
def _base():
    global _ACTIVE_URL, MAIN_URL
    if not _ACTIVE_URL:
        _ACTIVE_URL = _get_base()
        MAIN_URL = _ACTIVE_URL
    return _ACTIVE_URL

def _normalize_url(url):
    if not url: return ""
    url = html_unescape(url.strip())
    if url.startswith("//"): return "https:" + url
    if not url.startswith("http"): return urljoin(MAIN_URL, url)
    return url

def _clean_title(title):
    title = html_unescape(title)
    return title.replace("&amp;", "&").strip()

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
    ]

def _extract_items(html):
    items = []
    # Pattern for post grid
    matches = re.findall(r'<div class="postDiv[^>]*>.*?<a href="([^"]+)".*?<img[^>]*?(?:data-src|src)="([^"]+)".*?class="h1">([^<]+)</div>', html, re.DOTALL)
    
    for href, img, title in matches:
        title = _clean_title(title)
        href = _normalize_url(href)
        img = _normalize_url(img)
        
        item_type = "movie"
        if any(x in title for x in [u"مسلسل", u"انمي", u"موسم"]):
            item_type = "series"
            
        items.append({
            "title": title,
            "url": href,
            "poster": img,
            "type": item_type,
            "_action": "item"
        })
    return items

def get_category_items(url):
    base = _base()
    # Rebuild URL with active domain if needed
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc not in base:
        path = parsed.path
        url = base.rstrip('/') + path
    html, final_url = fetch(url, referer=base)
    if not html:
        log("FaselHD: fetch returned None for {}".format(url))
        return []
    items = _extract_items(html)
    
    # Pagination
    nav_match = re.search(r'<ul class="pagination">.*?<li class="active">.*?</li>.*?<li><a href="([^"]+)">', html, re.DOTALL)
    if nav_match:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": _normalize_url(nav_match.group(1)),
            "type": "category",
            "_action": "category"
        })
    return items

def search(query, page=1):
    url = MAIN_URL + "/?s=" + quote_plus(query)
    html, final_url = fetch(url, referer=MAIN_URL)
    return _extract_items(html)

def get_page(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    
    title_m = re.search(r'<title>(.*?)</title>', html)
    title = _clean_title(title_m.group(1)) if title_m else "FaselHD"
    
    poster_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(poster_m.group(1)) if poster_m else ""
    
    plot_m = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html)
    plot = _clean_title(plot_m.group(1)) if plot_m else ""

    servers = []
    items = [] # Used for seasons or episodes
    item_type = "movie"

    # 1. Check if it's a Season page (lists episodes)
    if '/seasons/' in url:
        item_type = "series"
        ep_matches = re.findall(r'<div class="epAll">.*?<a href="([^"]+)">([^<]+)</a>', html, re.DOTALL)
        for e_url, e_title in ep_matches:
            items.append({
                "title": _clean_title(e_title),
                "url": _normalize_url(e_url),
                "type": "episode",
                "_action": "item"
            })
    
    # 2. Check if it's a Series page (lists seasons)
    elif '/series/' in url:
        item_type = "series"
        s_matches = re.findall(r'<div class="seasonDiv[^>]*>.*?<a href="([^"]+)">.*?<div class="title">([^<]+)</div>', html, re.DOTALL)
        for s_url, s_title in s_matches:
            items.append({
                "title": _clean_title(s_title),
                "url": _normalize_url(s_url),
                "type": "category", # Seasons act as categories
                "_action": "category"
            })
        
        # If no seasons, maybe episodes directly
        if not items:
            ep_matches = re.findall(r'<div class="epAll">.*?<a href="([^"]+)">([^<]+)</a>', html, re.DOTALL)
            for e_url, e_title in ep_matches:
                items.append({
                    "title": _clean_title(e_title),
                    "url": _normalize_url(e_url),
                    "type": "episode",
                    "_action": "item"
                })

    # 3. Handle playback (movies or episodes)
    # Look for the "Watch" page or direct player
    player_match = re.search(r'player_iframe\.location\.href\s*=\s*\'([^\']+)\'', html)
    if not player_match:
        # Check for watch button
        watch_m = re.search(r'<a href="([^"]+)"[^>]*>مشاهدة وتحميل</a>', html)
        if watch_m:
            watch_url = _normalize_url(watch_m.group(1))
            w_html, _ = fetch(watch_url, referer=url)
            player_match = re.search(r'player_iframe\.location\.href\s*=\s*\'([^\']+)\'', w_html)
            if player_match:
                html = w_html # Use watch page html for server parsing
    
    if player_match:
        player_url = player_match.group(1)
        # Parse servers from the watch page tabs if available
        # <ul class="tabs-ul"> ... <li onclick="player_iframe.location.href = 'URL'">NAME</li>
        # Parse servers from the watch page tabs if available
        # <ul class="tabs-ul"> ... <li onclick="player_iframe.location.href = 'URL'">NAME</li>
        srv_matches = re.findall(r'<li[^>]*onclick=["\']player_iframe\.location\.href\s*=\s*[\\"\']([^\\"\']+)[\\"\'][^>]*>(.*?)</li>', html, re.DOTALL | re.IGNORECASE)
        for srv_url, srv_name in srv_matches:
            name = _clean_title(re.sub(r'<[^>]+>', '', srv_name))
            if not name: name = u"سيرفر"
            servers.append({
                "name": u"فاصل - " + name,
                "url": _normalize_url(srv_url)
            })
        
        # Fallback if no list found but player_match worked
        if not servers:
            servers.append({
                "name": u"فاصل - سيرفر رئيسي",
                "url": _normalize_url(player_url)
            })

    return {
        "url": final_url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "servers": servers,
        "items": items,
        "type": item_type
    }

def extract_stream(url):
    log("Fasel: extracting from {}".format(url))
    # Fetch player page with MAIN_URL as referer
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html: return url, None, MAIN_URL
    
    # Use the final_url of the player as the referer for subsequent requests
    player_referer = final_url or url
    
    # 1. Try simple data-url buttons
    btn_matches = re.findall(r'data-url=["\']([^"\']+)["\']', html, re.I)
    if btn_matches:
        return _normalize_url(btn_matches[0]), None, player_referer

    # 2. Try the obfuscated JS cipher used by faselhdx.bid
    # var t="...".replace(/(.)/g,(function(e,t){return String.fromCharCode(e.charCodeAt(0)-t%2)}))
    cipher_match = re.search(r'var\s+t\s*=\s*[\"\']([^\"\']+)[\"\']\.replace', html)
    if cipher_match:
        encoded = cipher_match.group(1)
        decoded = "".join([chr(ord(c) - (i % 2)) for i, c in enumerate(encoded)])
        
        # Look for the file URL in the decoded string
        file_m = re.search(r'file\s*:\s*[\"\']([^\"\']+)[\"\']', decoded)
        if file_m:
            v_url = _normalize_url(file_m.group(1))
            # Handle .txt obfuscated extensions
            if v_url.endswith(".txt"):
                v_url = v_url.replace(".txt", "/master.m3u8") # common pattern for these mirrors
            return v_url, None, player_referer

    # 3. Try fallback regexes
    m3u8_match = re.search(r'https?://[^\s\'"]+?\.m3u8[^\s\'"]*', html)
    if not m3u8_match:
        m3u8_match = re.search(r'https?://[^\s\'"]+?\.txt[^\s\'"]*', html) # Some mirrors use .txt extension
        
    if m3u8_match:
        v_url = m3u8_match.group(0)
        # Final safety check for .txt obfuscation
        if ".txt" in v_url:
            # Some mirrors use /v/token.txt?params which needs to become /v/token.m3u8?params
            v_url = v_url.replace(".txt", ".m3u8")
            if "/master." not in v_url and ".m3u8" in v_url:
                # Common fix for certain mirrors
                v_url = v_url.replace(".m3u8", "/master.m3u8")
        return v_url, None, player_referer

    # 4. Concatenated strings
    parts = re.findall(r"'(?:https?:|//)[^']+'", html)
    if parts:
        combined = "".join([p.strip("'") for p in parts])
        m3u8_match = re.search(r'(https?://[^\s\'"]+?\.m3u8)', combined)
        if m3u8_match:
            return m3u8_match.group(1), None, player_referer

    log("Fasel: could not extract stream from player page")
    return "", None, MAIN_URL
