# -*- coding: utf-8 -*-
"""
EgyDead extractor — WordPress site
Domain: https://tv8.egydead.live/

Site structure (confirmed from e2iplayer hostegydead.py):
  - Category pages : <ul class="posts-list"> → <li> items
  - Item page      : POST {"View":"1"} → <ul class="serversList"> → <li data-link="...">
  - Series/Seasons : <div class="seasons-list"> → <li>
  - Episodes       : <div class="EpsList"> → <li>
  - Pagination     : <div class="pagination"> next/prev page-numbers
  - Search         : MAIN_URL + "?s=" + query
"""

import re
import sys

from .base import fetch, log, extract_stream as base_extract_stream

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urljoin, urlencode, urlparse
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, urlencode
    from urlparse import urljoin
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

MAIN_URL = "https://tv8.egydead.live/"

# Words stripped when cleaning titles
_CLEAN_WORDS = [
    "مشاهدة فيلم", "مشاهدة", "فيلم", "مسلسل",
    "مترجمة اون لاين", "مترجم اون لاين",
    "مترجمة", "مترجم", "اون لاين", "أون لاين",
    "مدبلجة", "مدبلج", "كرتون", "انمي",
    "بالمصري", "سلسلة افلام", "عرض", "برنامج", "جميع مواسم",
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _strip_tags(text):
    text = html_unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title):
    title = _strip_tags(title)
    for word in _CLEAN_WORDS:
        title = title.replace(word, "")
    return re.sub(r"\s+", " ", title).strip(" -|")


def _full_url(path):
    if not path:
        return ""
    path = html_unescape(path.strip())
    if path.startswith("http"):
        return path
    if path.startswith("//"):
        return "https:" + path
    return urljoin(MAIN_URL, path)


def _encode_arabic_url(url):
    """Encode Arabic/Unicode characters in URL to percent-encoded format."""
    try:
        parsed = urlparse(url)
        # Encode the path if it contains non-ASCII
        path_segments = []
        for segment in parsed.path.split('/'):
            if segment:
                # Check if segment contains non-ASCII
                if any(ord(c) > 127 for c in segment):
                    path_segments.append(quote_plus(segment.encode('utf-8')))
                else:
                    path_segments.append(segment)
            else:
                path_segments.append('')
        encoded_path = '/'.join(path_segments)
        if not encoded_path.startswith('/'):
            encoded_path = '/' + encoded_path
        
        # Also encode query parameters if needed
        encoded_query = ''
        if parsed.query:
            try:
                # Parse query string and encode values
                query_parts = []
                for part in parsed.query.split('&'):
                    if '=' in part:
                        key, val = part.split('=', 1)
                        if any(ord(c) > 127 for c in val):
                            query_parts.append(key + '=' + quote_plus(val.encode('utf-8')))
                        else:
                            query_parts.append(part)
                    else:
                        query_parts.append(part)
                encoded_query = '&'.join(query_parts)
            except Exception:
                encoded_query = parsed.query
        
        # Rebuild URL
        encoded_url = parsed._replace(path=encoded_path, query=encoded_query).geturl()
        return encoded_url
    except Exception:
        return url


def _fetch(url, referer=None, post_data=None):
    """Thin wrapper that always sends a Referer and handles POST."""
    extra = {}
    if post_data:
        extra["Content-Type"] = "application/x-www-form-urlencoded"
    
    # Encode Arabic URLs properly
    encoded_url = _encode_arabic_url(url)
    
    return fetch(
        encoded_url,
        referer=referer or MAIN_URL,
        extra_headers=extra if extra else None,
        post_data=post_data,
    )


# ─── Item card parser (shared by category + search) ──────────────────────────

def _parse_post_list(html, base_url=""):
    """
    Parse <ul class="posts-list"> blocks and return item dicts.
    Falls back to a direct <li> scan if the wrapping block is missing.
    """
    items = []
    seen = set()

    # Try to find the main listing block - multiple possible class names
    block_m = None
    for class_pattern in ['posts-list', 'post-list', 'movie-list', 'film-list']:
        block_m = re.search(
            r'<ul[^>]+class=["\'][^"\']*{}[^"\']*["\'][^>]*>(.*?)</ul>'.format(class_pattern),
            html, re.S | re.I
        )
        if block_m:
            break
    
    block = block_m.group(1) if block_m else html

    # Also look for div-based containers
    if not block_m:
        div_m = re.search(
            r'<div[^>]+class=["\'][^"\']*(?:row|movies-list|items-container)[^"\']*["\'][^>]*>(.*?)</div>',
            html, re.S | re.I
        )
        if div_m:
            block = div_m.group(1)

    # More flexible li search - look for article or movie-card patterns too
    li_patterns = [
        r'<li[^>]*>(.*?)</li>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]+class=["\'][^"\']*(?:movie|item|post)[^"\']*["\'][^>]*>(.*?)</div>',
    ]
    
    for pattern in li_patterns:
        matches = re.findall(pattern, block, re.S | re.I)
        if matches:
            for item_html in matches:
                url = re.search(r'href=["\']([^"\']+)["\']', item_html)
                if not url:
                    continue
                url = _full_url(url.group(1))
                if not url or url in seen:
                    continue

                # Skip pagination / category links
                if any(x in url for x in ("/category/", "/series-category/", "/page/", "/tag/", "/type/")):
                    continue

                seen.add(url)

                # Title: try title="..." attr first, then <h2>/<h1>, then any text
                title_m = (
                    re.search(r'title=["\']([^"\']+)["\']', item_html)
                    or re.search(r'<h[12][^>]*>(.*?)</h[12]>', item_html, re.S | re.I)
                    or re.search(r'<a[^>]+>(.*?)</a>', item_html, re.S | re.I)
                )
                title = _clean_title(title_m.group(1) if title_m else "")

                # If no title found, try to get from alt attribute of image
                if not title:
                    img_alt = re.search(r'<img[^>]+alt=["\']([^"\']+)["\']', item_html, re.I)
                    if img_alt:
                        title = _clean_title(img_alt.group(1))

                # Poster: data-lazy-style="...url(...)" → src/data-src fallback
                img = ""
                lazy_m = re.search(r'data-lazy-style=["\'][^"\']*url\(([^)]+)\)', item_html)
                if lazy_m:
                    img = lazy_m.group(1).strip("'\" ")
                if not img:
                    src_m = re.search(r'(?:data-src|src)=["\']([^"\']+)["\']', item_html)
                    if src_m:
                        img = src_m.group(1).strip()
                img = _full_url(img)

                # Category badge (optional)
                cat = _strip_tags(
                    (re.search(r'<span[^>]+class=["\'][^"\']*cat_name[^"\']*["\'][^>]*>(.*?)</span>', item_html, re.S | re.I) or
                     re.search(r'<span[^>]+class=["\'][^"\']*cat[^"\']*["\'][^>]*>(.*?)</span>', item_html, re.S | re.I) or
                     re.search(r'class=["\'][^"\']*quality[^"\']*["\'][^>]*>(.*?)</span>', item_html, re.S | re.I) or
                     type("", (), {"group": lambda s, n: ""})()
                     ).group(1) if re.search(r'<span', item_html, re.I) else type("", (), {"group": lambda s, n: ""})()
                )

                # Guess type from URL / title
                low = url.lower() + " " + title.lower()
                if any(x in low for x in ("/episode/", "الحلقة", "حلقة")):
                    item_type = "episode"
                elif any(x in low for x in ("/serie/", "/season/", "/series-category/", "مسلسل", "الموسم")):
                    item_type = "series"
                else:
                    item_type = "movie"

                if title:  # Only add if we have a title
                    items.append({
                        "title": title,
                        "url": url,
                        "poster": img,
                        "plot": cat,
                        "type": item_type,
                        "_action": "details",
                    })
            break  # Stop after first successful pattern

    return items


def _parse_pagination(html, current_url, item_type="category"):
    """Return a next-page item if the page has one, else None."""
    m = re.search(
        r'<a[^>]+class=["\'][^"\']*next\s+page-numbers[^"\']*["\'][^>]+href=["\']([^"\']+)["\']',
        html, re.I
    )
    if not m:
        m = re.search(r'rel=["\']next["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
    if m:
        return {
            "title": "➡️ الصفحة التالية",
            "url": _full_url(m.group(1)),
            "type": item_type,
            "_action": "category",
        }
    return None


# ─── Detail page: poster / plot / title ──────────────────────────────────────

def _extract_detail_meta(html, url=""):
    """Extract title, poster, plot, year from a WordPress item page."""
    # Title
    title = ""
    for pat in (
        r'<div[^>]+class=["\'][^"\']*singleTitle[^"\']*["\'][^>]*>(.*?)</div>',
        r'property="og:title"[^>]+content=["\']([^"\']+)["\']',
        r'<h1[^>]*>(.*?)</h1>',
        r'<title>(.*?)</title>',
    ):
        m = re.search(pat, html, re.S | re.I)
        if m:
            title = _clean_title(m.group(1))
            if title:
                break

    # Poster
    poster = ""
    for pat in (
        r'<div[^>]+class=["\'][^"\']*single-thumbnail[^"\']*["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']',
        r'property="og:image"[^>]+content=["\']([^"\']+)["\']',
        r'<img[^>]+class=["\'][^"\']*poster[^"\']*["\'][^>]+src=["\']([^"\']+)["\']',
    ):
        m = re.search(pat, html, re.S | re.I)
        if m:
            poster = _full_url(m.group(1).strip())
            if poster:
                break

    # Plot/story
    plot = ""
    for pat in (
        r'<div[^>]+class=["\'][^"\']*(?:singleStory|extra-content|story)[^"\']*["\'][^>]*>(.*?)</div>',
        r'name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
    ):
        m = re.search(pat, html, re.S | re.I)
        if m:
            plot = _strip_tags(m.group(1))
            if plot:
                break

    # Year from metadata box
    year = ""
    m = re.search(r'السنه.*?<a[^>]*>(\d{4})</a>', html, re.S | re.I)
    if not m:
        m = re.search(r'\b(19\d{2}|20\d{2}|21\d{2})\b', title + " " + plot)
    if m:
        year = m.group(1)

    return title, poster, plot, year


# ─── Server extraction from item page ────────────────────────────────────────

def _extract_servers(html, page_url):
    """
    EgyDead server extraction:
      1. GET the item page (already fetched → html)
      2. POST {"View":"1"} to same URL
      3. Parse <ul class="serversList"> → <li data-link="..."> <p>name</p>
      4. Also look for direct player links in divs with class "player"
    """
    servers = []
    seen = set()
    page_url = _encode_arabic_url(page_url)

    # ── salery-list / seasons-list: this is a series index, not a playable item ──
    # (handled upstream in get_page, but guard here too)
    if re.search(r'class=["\'][^"\']*(?:salery-list|seasons-list)[^"\']*["\']', html, re.I):
        return []

    # Step 1: try to find serversList already in GET html (some pages embed it)
    servers_html = _find_servers_html(html)
    
    if servers_html:
        log("EgyDead: found serversList in GET response")
    else:
        # Step 2: Look for player div with data-src or iframe
        player_m = re.search(r'<div[^>]+class=["\'][^"\']*player[^"\']*["\'][^>]+data-src=["\']([^"\']+)["\']', html, re.I)
        if player_m:
            video_url = player_m.group(1)
            if video_url and video_url not in seen:
                seen.add(video_url)
                servers.append({"name": "Server", "url": video_url, "type": "direct"})
                log("EgyDead: found player data-src: {}".format(video_url[:80]))
        
        # Step 3: Look for direct iframe
        iframe_m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if iframe_m and not servers:
            iframe_url = iframe_m.group(1)
            if iframe_url and iframe_url not in seen:
                seen.add(iframe_url)
                servers.append({"name": "Server", "url": iframe_url, "type": "direct"})
                log("EgyDead: found iframe src: {}".format(iframe_url[:80]))
        
        # Step 4: POST {"View":"1"} if not found yet
        if not servers:
            log("EgyDead: no servers in GET, trying POST for {}".format(page_url))
            post_html, _ = _fetch(page_url, referer=page_url,
                                  post_data=urlencode({"View": "1"}).encode("utf-8"))
            if post_html:
                servers_html = _find_servers_html(post_html)
                if servers_html:
                    log("EgyDead: found serversList after POST")
                else:
                    # Also check for direct links after POST
                    player_m = re.search(r'<div[^>]+class=["\'][^"\']*player[^"\']*["\'][^>]+data-src=["\']([^"\']+)["\']', post_html, re.I)
                    if player_m:
                        video_url = player_m.group(1)
                        if video_url and video_url not in seen:
                            seen.add(video_url)
                            servers.append({"name": "Server", "url": video_url, "type": "direct"})
                    
                    iframe_m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', post_html, re.I)
                    if iframe_m and not servers:
                        iframe_url = iframe_m.group(1)
                        if iframe_url and iframe_url not in seen:
                            seen.add(iframe_url)
                            servers.append({"name": "Server", "url": iframe_url, "type": "direct"})

    # Parse servers from serversList if found
    if servers_html:
        for li in re.findall(r'<li[^>]*>(.*?)</li>', servers_html, re.S | re.I):
            # data-link attribute on the <li> itself
            link_m = re.search(r'data-link=["\']([^"\']+)["\']', li)
            if not link_m:
                # sometimes it's on a child element
                link_m = re.search(r'href=["\']([^"\']+)["\']', li)
            if not link_m:
                continue
            video_url = html_unescape(link_m.group(1).strip())
            if not video_url or video_url in seen:
                continue
            if video_url.startswith("//"):
                video_url = "https:" + video_url
            seen.add(video_url)

            # Server name: <p>…</p> or <span>…</span>
            name_m = (
                re.search(r'<p[^>]*>([^<]+)</p>', li, re.I) or
                re.search(r'<span[^>]*>([^<]+)</span>', li, re.I)
            )
            name = _strip_tags(name_m.group(1)) if name_m else "Server {}".format(len(servers) + 1)
            
            servers.append({"name": name, "url": video_url, "type": "direct"})

    # Step 5: Try to extract from JavaScript variables
    if not servers:
        # Look for jwplayer setup
        jw_m = re.search(r'jwplayer\("[^"]+"\)\.setup\(\{.*?file:\s*["\']([^"\']+)["\']', html, re.S | re.I)
        if jw_m:
            video_url = jw_m.group(1)
            if video_url and video_url not in seen:
                seen.add(video_url)
                servers.append({"name": "Video", "url": video_url, "type": "direct"})
                log("EgyDead: found jwplayer file: {}".format(video_url[:80]))
        
        # Look for video src
        video_m = re.search(r'<video[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if video_m and not servers:
            video_url = video_m.group(1)
            if video_url and video_url not in seen:
                seen.add(video_url)
                servers.append({"name": "Video", "url": video_url, "type": "direct"})
                log("EgyDead: found video src: {}".format(video_url[:80]))

    log("EgyDead: found {} servers for {}".format(len(servers), page_url))
    return servers


def _find_servers_html(html):
    """Extract content of <ul class="serversList">…</ul> from html."""
    m = re.search(
        r'<ul[^>]+class=["\'][^"\']*serversList[^"\']*["\'][^>]*>(.*?)</ul>',
        html, re.S | re.I
    )
    return m.group(1) if m else ""


# ─── Series / seasons / episodes ─────────────────────────────────────────────

def _extract_seasons(html):
    """Return season items from <div class="seasons-list">."""
    items = []
    m = re.search(
        r'<div[^>]+class=["\'][^"\']*seasons-list[^"\']*["\'][^>]*>(.*?)</div>',
        html, re.S | re.I
    )
    if not m:
        return items
    for li in re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), re.S | re.I):
        url_m = re.search(r'href=["\']([^"\']+)["\']', li)
        if not url_m:
            continue
        url = _full_url(url_m.group(1))
        title_m = (
            re.search(r'title=["\']([^"\']+)["\']', li) or
            re.search(r'>([^<]+)</a>', li)
        )
        title = _clean_title(title_m.group(1) if title_m else "موسم")
        items.append({"title": title, "url": url, "type": "series", "_action": "details"})
    items.reverse()
    return items


def _extract_episodes(html):
    """Return episode items from <div class="EpsList">."""
    items = []
    m = re.search(
        r'<div[^>]+class=["\'][^"\']*EpsList[^"\']*["\'][^>]*>(.*?)</div>',
        html, re.S | re.I
    )
    if not m:
        return items
    for li in re.findall(r'<li[^>]*>(.*?)</li>', m.group(1), re.S | re.I):
        url_m = re.search(r'href=["\']([^"\']+)["\']', li)
        if not url_m:
            continue
        url = _full_url(url_m.group(1))
        title_m = (
            re.search(r'title=["\']([^"\']+)["\']', li) or
            re.search(r'>([^<]+)</a>', li)
        )
        title = _clean_title(title_m.group(1) if title_m else "حلقة")
        items.append({"title": title, "url": url, "type": "episode", "_action": "details"})
    items.reverse()
    return items


# ─── Public API ───────────────────────────────────────────────────────────────

def get_categories(mtype="movie"):
    """
    Return hardcoded category list matching the actual WordPress site taxonomy.
    Confirmed from e2iplayer hostegydead.py listMainMenu().
    """
    if mtype == "movie":
        return [
            {"title": "🎬 أفلام إنجليزية",        "url": _full_url("/category/english-movies/"),               "type": "category", "_action": "category"},
            {"title": "🇪🇬 أفلام عربية",          "url": _full_url("/category/افلام-عربي/"),                    "type": "category", "_action": "category"},
            {"title": "🌏 أفلام آسيوية",          "url": _full_url("/category/افلام-اسيوية/"),                  "type": "category", "_action": "category"},
            {"title": "🇹🇷 أفلام تركية",          "url": _full_url("/category/افلام-تركية/"),                   "type": "category", "_action": "category"},
            {"title": "🇮🇳 أفلام هندية",          "url": _full_url("/category/افلام-هندية/"),                   "type": "category", "_action": "category"},
            {"title": "🎭 أفلام كرتون",           "url": _full_url("/category/افلام-كرتون/"),                   "type": "category", "_action": "category"},
            {"title": "📽️ أفلام وثائقية",         "url": _full_url("/category/افلام-وثائقية/"),                 "type": "category", "_action": "category"},
            {"title": "🎌 أفلام أنمي",            "url": _full_url("/category/افلام-انمي/"),                    "type": "category", "_action": "category"},
            {"title": "🌍 أفلام مدبلجة إنجليزية", "url": _full_url("/category/افلام-اجنبية-مدبلجة/"),           "type": "category", "_action": "category"},
        ]
    # series
    return [
        {"title": "📺 مسلسلات إنجليزية",     "url": _full_url("/series-category/english-series/"),          "type": "category", "_action": "category"},
        {"title": "🇪🇬 مسلسلات عربية",       "url": _full_url("/series-category/arabic-series/"),           "type": "category", "_action": "category"},
        {"title": "🇹🇷 مسلسلات تركية",       "url": _full_url("/series-category/turkish-series/"),          "type": "category", "_action": "category"},
        {"title": "🌏 مسلسلات آسيوية",       "url": _full_url("/series-category/asian-series/"),            "type": "category", "_action": "category"},
        {"title": "🎌 أنمي",                 "url": _full_url("/series-category/anime-series/"),            "type": "category", "_action": "category"},
        {"title": "🎠 كارتون",               "url": _full_url("/series-category/cartoon-series/"),          "type": "category", "_action": "category"},
        {"title": "🌍 مسلسلات مدبلجة",       "url": _full_url("/series-category/english-series-dubbed/"),   "type": "category", "_action": "category"},
        {"title": "📋 مسلسلات كاملة",        "url": _full_url("/serie/"),                                   "type": "category", "_action": "category"},
    ]


def get_category_items(url, page=None):
    """
    Get items from a category page.
    page parameter is ignored (EgyDead uses URL-based pagination).
    """
    html, final_url = _fetch(url)
    if not html:
        log("EgyDead: get_category_items failed: {}".format(url))
        return []

    items = _parse_post_list(html, final_url or url)

    nxt = _parse_pagination(html, url)
    if nxt:
        items.append(nxt)

    log("EgyDead: category {} → {} items".format(url, len(items)))
    return items


def search(query, page=1):
    url = MAIN_URL.rstrip("/") + "/?s=" + quote_plus(query)
    html, final_url = _fetch(url)
    if not html:
        log("EgyDead: search failed for '{}'".format(query))
        return []

    items = _parse_post_list(html, final_url or url)

    nxt = _parse_pagination(html, url)
    if nxt:
        items.append(nxt)

    log("EgyDead: search '{}' → {} items".format(query, len(items)))
    return items


def get_page(url, m_type=None):
    """
    Fetch and parse an item/series/episode page.
    Returns the standard dict: title, poster, plot, year, servers, items, type.
    """
    html, final_url = _fetch(url)
    result = {
        "url": url,
        "title": "",
        "poster": "",
        "plot": "",
        "year": "",
        "rating": "",
        "servers": [],
        "items": [],
        "type": m_type or "movie",
    }

    if not html:
        log("EgyDead: get_page failed: {}".format(url))
        return result

    active_url = final_url or url
    title, poster, plot, year = _extract_detail_meta(html, active_url)
    result["title"]  = title
    result["poster"] = poster
    result["plot"]   = plot
    result["year"]   = year

    # ── Detect page type ──────────────────────────────────────────────────────
    # 1. seasons-list  → series with multiple seasons to navigate into
    seasons = _extract_seasons(html)
    if seasons:
        result["type"]  = "series"
        result["items"] = seasons
        log("EgyDead: series page, {} seasons".format(len(seasons)))
        return result

    # 2. EpsList → season page with direct episode links
    episodes = _extract_episodes(html)
    if episodes:
        result["type"]  = "series"
        result["items"] = episodes
        log("EgyDead: season page, {} episodes".format(len(episodes)))
        return result

    # 3. salery-list → multi-part movie (treat parts as "episodes")
    salery_m = re.search(
        r'<div[^>]+class=["\'][^"\']*salery-list[^"\']*["\'][^>]*>(.*?)</div>',
        html, re.S | re.I
    )
    if salery_m:
        for li in re.findall(r'<li[^>]*>(.*?)</li>', salery_m.group(1), re.S | re.I):
            url_m = re.search(r'href=["\']([^"\']+)["\']', li)
            if not url_m:
                continue
            part_url = _full_url(url_m.group(1))
            title_m  = re.search(r'title=["\']([^"\']+)["\']', li) or re.search(r'>([^<]+)</a>', li)
            part_title = _clean_title(title_m.group(1) if title_m else "جزء")
            result["items"].append({"title": part_title, "url": part_url, "type": "movie", "_action": "details"})
        if result["items"]:
            result["type"] = "series"
            return result

    # 4. Direct playable item → extract servers via POST with improved extraction
    servers = _extract_servers(html, active_url)
    result["servers"] = servers

    # If still no servers and it's an episode, try alternative approach
    if not servers and ('/episode/' in active_url.lower() or 'الحلقة' in title.lower()):
        log("EgyDead: episode with no servers, trying direct player extraction")
        # Try to extract redirect URL
        redirect_m = re.search(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', html)
        if redirect_m:
            redirect_url = redirect_m.group(1)
            log("EgyDead: found redirect to: {}".format(redirect_url))
            # Follow the redirect
            redirect_html, _ = _fetch(redirect_url, referer=active_url)
            if redirect_html:
                # Try to find iframe or player in redirected page
                iframe_m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', redirect_html, re.I)
                if iframe_m:
                    result["servers"] = [{"name": "Server", "url": iframe_m.group(1), "type": "direct"}]

    # Refine type from URL / title context
    low = active_url.lower() + " " + title.lower()
    if any(x in low for x in ("/episode/", "الحلقة", "حلقة")):
        result["type"] = "episode"
    elif any(x in low for x in ("/serie/", "/season/", "مسلسل")):
        result["type"] = "series" if not servers else "episode"
    else:
        result["type"] = m_type or "movie"

    log("EgyDead: item page type={}, servers={}".format(result["type"], len(servers)))
    return result


def extract_stream(url):
    """
    Resolve a raw server URL (data-link value) to a playable stream.
    StreamRuby requires Origin: stmruby.com header for HLS segments.
    """
    from .base import resolve_streamruby, resolve_iframe_chain

    low = (url or "").lower()

    if "stmruby" in low or "streamruby" in low:
        stream = resolve_streamruby(url)
        if stream:
            return (
                stream + "|Referer=https://stmruby.com/&Origin=https://stmruby.com",
                None,
                "https://stmruby.com/",
            )

    return base_extract_stream(url)