# -*- coding: utf-8 -*-
"""
EgyDead extractor — WordPress site
Domain: https://tv8.egydead.live/
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

_CLEAN_WORDS = [
    "مشاهدة فيلم", "مشاهدة", "فيلم", "مسلسل",
    "مترجمة اون لاين", "مترجم اون لاين",
    "مترجمة", "مترجم", "اون لاين", "أون لاين",
    "مدبلجة", "مدبلج", "كرتون", "انمي",
    "بالمصري", "سلسلة افلام", "عرض", "برنامج", "جميع مواسم",
]


def _strip_tags(text):
    text = html_unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title):
    title = _strip_tags(title)
    for word in _CLEAN_WORDS:
        title = title.replace(word, "")
    title = re.sub(r"\s*\|\s*$", "", title)
    title = re.sub(r"\s*\-\s*$", "", title)
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
    try:
        parsed = urlparse(url)
        path_segments = []
        for segment in parsed.path.split('/'):
            if segment:
                if any(ord(c) > 127 for c in segment):
                    path_segments.append(quote_plus(segment.encode('utf-8')))
                else:
                    path_segments.append(segment)
            else:
                path_segments.append('')
        encoded_path = '/'.join(path_segments)
        if not encoded_path.startswith('/'):
            encoded_path = '/' + encoded_path
        
        encoded_query = ''
        if parsed.query:
            try:
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
        
        encoded_url = parsed._replace(path=encoded_path, query=encoded_query).geturl()
        return encoded_url
    except Exception:
        return url


def _fetch(url, referer=None, post_data=None):
    extra = {}
    if post_data:
        extra["Content-Type"] = "application/x-www-form-urlencoded"
        extra["X-Requested-With"] = "XMLHttpRequest"
    
    # Add browser-like headers
    extra["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    extra["Accept-Language"] = "ar-EG,ar;q=0.9,en;q=0.8"
    extra["Cache-Control"] = "no-cache"
    extra["Pragma"] = "no-cache"
    extra["Sec-Fetch-Dest"] = "document"
    extra["Sec-Fetch-Mode"] = "navigate"
    extra["Sec-Fetch-Site"] = "none"
    extra["Sec-Fetch-User"] = "?1"
    extra["Upgrade-Insecure-Requests"] = "1"
    
    encoded_url = _encode_arabic_url(url)
    
    return fetch(
        encoded_url,
        referer=referer or MAIN_URL,
        extra_headers=extra if extra else None,
        post_data=post_data,
    )


def _parse_category_list(html):
    """Parse category page with movie items"""
    items = []
    seen = set()

    # Find all movie items
    for li in re.findall(r'<li[^>]*class=["\'][^"\']*movieItem[^"\']*["\'][^>]*>(.*?)</li>', html, re.S | re.I):
        
        # Extract URL
        url_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\']', li)
        if not url_match:
            continue
        
        url = _full_url(url_match.group(1))
        if not url or url in seen:
            continue
        seen.add(url)
        
        # Skip pagination
        if any(x in url for x in ("/page/", "page=")):
            continue
        
        # Extract title
        title_match = (
            re.search(r'<h1[^>]*class=["\'][^"\']*BottomTitle[^"\']*["\'][^>]*>(.*?)</h1>', li, re.S | re.I) or
            re.search(r'<img[^>]+alt=["\']([^"\']+)["\']', li) or
            re.search(r'<a[^>]+title=["\']([^"\']+)["\']', li)
        )
        title = _clean_title(title_match.group(1) if title_match else "")
        
        # Extract poster
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', li)
        poster = _full_url(img_match.group(1)) if img_match else ""
        
        # Extract quality label
        quality_match = re.search(r'<span[^>]*class=["\'][^"\']*label[^"\']*["\'][^>]*>(.*?)</span>', li)
        quality = _strip_tags(quality_match.group(1)) if quality_match else ""
        
        if title:
            display_title = f"{title} [{quality}]" if quality else title
            items.append({
                "title": display_title,
                "url": url,
                "poster": poster,
                "plot": quality,
                "type": "movie",
                "_action": "details",
            })
    
    return items


def _parse_pagination(html, current_url):
    """Return next page item if available"""
    # Look for next page link
    next_match = re.search(r'<a[^>]+class=["\'][^"\']*next[^"\']*page-numbers[^"\']*["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
    if next_match:
        next_url = _full_url(next_match.group(1))
        if next_url and next_url != current_url:
            return {
                "title": "➡️ Next Page",
                "url": next_url,
                "type": "category",
                "_action": "category",
            }
    return None


def _extract_detail_meta(html):
    """Extract title, poster, plot, year from item page"""
    # Title from og:title
    title = ""
    title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if title_match:
        title = _clean_title(title_match.group(1))
    
    if not title:
        title_match = re.search(r'<title>(.*?)</title>', html, re.I)
        if title_match:
            title = _clean_title(title_match.group(1).split('|')[0])
    
    # Poster from og:image
    poster = ""
    poster_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if poster_match:
        poster = _full_url(poster_match.group(1))
    
    # Description
    plot = ""
    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if desc_match:
        plot = _strip_tags(desc_match.group(1))
    
    # Year
    year = ""
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', title + " " + plot)
    if year_match:
        year = year_match.group(1)
    
    return title, poster, plot, year


def _extract_servers(html, page_url):
    """
    Extract video servers from EgyDead page.
    Uses POST request with {"View":"1"} as shown in the JSON data.
    """
    servers = []
    seen = set()
    
    # First try to find servers in current HTML
    servers_html = _find_servers_html(html)
    
    # If not found, try POST request (as shown in the JSON)
    if not servers_html:
        log(f"EgyDead: No servers in GET, POSTing {{'View':'1'}} to {page_url}")
        try:
            # This is the key fix - POST {"View": "1"} exactly as shown in the JSON
            post_data = urlencode({"View": "1"}).encode("utf-8")
            post_html, _ = _fetch(page_url, referer=page_url, post_data=post_data)
            if post_html:
                servers_html = _find_servers_html(post_html)
                if servers_html:
                    log("EgyDead: Found servers after POST request with View=1")
        except Exception as e:
            log(f"EgyDead: POST request failed: {e}")
    
    # Parse servers from serversList
    if servers_html:
        # Find all li elements with data-link attribute
        for li_match in re.finditer(r'<li[^>]*data-link=["\']([^"\']+)["\'][^>]*>(.*?)</li>', servers_html, re.S | re.I):
            video_url = html_unescape(li_match.group(1).strip())
            li_content = li_match.group(2)
            
            if not video_url or video_url in seen:
                continue
            
            if video_url.startswith("//"):
                video_url = "https:" + video_url
            seen.add(video_url)
            
            # Extract server name
            name_match = re.search(r'<p[^>]*>([^<]+)</p>', li_content, re.I) or \
                        re.search(r'<span[^>]*>([^<]+)</span>', li_content, re.I)
            
            name = _strip_tags(name_match.group(1)) if name_match else f"Server {len(servers) + 1}"
            
            servers.append({"name": name.strip(), "url": video_url, "type": "embed"})
    
    # Also check for video source tags
    if not servers:
        # Look for video src in page
        video_match = re.search(r'<video[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if video_match:
            video_url = video_match.group(1)
            if video_url and video_url not in seen:
                seen.add(video_url)
                servers.append({"name": "Direct Video", "url": video_url, "type": "direct"})
    
    log(f"EgyDead: Found {len(servers)} servers for {page_url}")
    return servers


def _find_servers_html(html):
    """Extract content of <ul class="serversList"> from html"""
    m = re.search(
        r'<ul[^>]+class=["\'][^"\']*serversList[^"\']*["\'][^>]*>(.*?)</ul>',
        html, re.S | re.I
    )
    return m.group(1) if m else ""


def get_categories(mtype="movie"):
    """Return category list"""
    if mtype == "movie":
        return [
            {"title": "🎬 English Movies",        "url": _full_url("/category/english-movies/"),    "type": "category", "_action": "category"},
            {"title": "🇪🇬 Arabic Movies",          "url": _full_url("/category/افلام-عربي/"),        "type": "category", "_action": "category"},
            {"title": "🌏 Asian Movies",           "url": _full_url("/category/افلام-اسيوية/"),      "type": "category", "_action": "category"},
            {"title": "🇹🇷 Turkish Movies",         "url": _full_url("/category/افلام-تركية/"),       "type": "category", "_action": "category"},
            {"title": "🇮🇳 Indian Movies",          "url": _full_url("/category/افلام-هندية/"),       "type": "category", "_action": "category"},
            {"title": "🎭 Cartoon Movies",         "url": _full_url("/category/افلام-كرتون/"),       "type": "category", "_action": "category"},
            {"title": "🎌 Anime Movies",           "url": _full_url("/category/افلام-انمي/"),        "type": "category", "_action": "category"},
            {"title": "📽️ Documentary Movies",     "url": _full_url("/category/افلام-وثائقية/"),     "type": "category", "_action": "category"},
            {"title": "🌍 Dubbed Movies",          "url": _full_url("/category/افلام-اجنبية-مدبلجة/"), "type": "category", "_action": "category"},
        ]
    # series
    return [
        {"title": "📺 English Series",        "url": _full_url("/series-category/english-series/"),  "type": "category", "_action": "category"},
        {"title": "🇪🇬 Arabic Series",         "url": _full_url("/series-category/arabic-series/"),   "type": "category", "_action": "category"},
        {"title": "🇹🇷 Turkish Series",       "url": _full_url("/series-category/turkish-series/"),  "type": "category", "_action": "category"},
        {"title": "🌏 Asian Series",          "url": _full_url("/series-category/asian-series/"),    "type": "category", "_action": "category"},
        {"title": "🎌 Anime Series",          "url": _full_url("/series-category/anime-series/"),    "type": "category", "_action": "category"},
        {"title": "🎠 Cartoon Series",        "url": _full_url("/series-category/cartoon-series/"),  "type": "category", "_action": "category"},
    ]


def get_category_items(url, page=None):
    """Get items from a category page"""
    fetch_url = url
    if page and page > 1:
        if '?' in url:
            fetch_url = f"{url}&page={page}"
        else:
            fetch_url = f"{url}?page={page}"
    
    html, final_url = _fetch(fetch_url)
    if not html:
        log(f"EgyDead: get_category_items failed: {fetch_url}")
        return []

    items = _parse_category_list(html)

    if not page or page == 1:
        nxt = _parse_pagination(html, fetch_url)
        if nxt:
            items.append(nxt)

    log(f"EgyDead: category {url} page {page or 1} → {len(items)} items")
    return items


def search(query, page=1):
    """Search for movies/series"""
    search_url = MAIN_URL.rstrip("/") + "/?s=" + quote_plus(query)
    if page > 1:
        search_url += f"&page={page}"
    
    html, final_url = _fetch(search_url)
    if not html:
        log(f"EgyDead: search failed for '{query}'")
        return []

    items = _parse_category_list(html)

    if page == 1:
        nxt = _parse_pagination(html, search_url)
        if nxt:
            items.append(nxt)

    log(f"EgyDead: search '{query}' → {len(items)} items")
    return items


def get_page(url, m_type=None):
    """Fetch and parse an item page"""
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
        log(f"EgyDead: get_page failed: {url}")
        return result

    # Extract metadata
    title, poster, plot, year = _extract_detail_meta(html)
    result["title"] = title
    result["poster"] = poster
    result["plot"] = plot
    result["year"] = year

    # Extract servers (this will now use POST if needed)
    servers = _extract_servers(html, final_url or url)
    result["servers"] = servers

    # Determine type from URL
    low = url.lower()
    if any(x in low for x in ("/serie/", "/season/", "مسلسل")):
        result["type"] = "series"
    else:
        result["type"] = m_type or "movie"

    log(f"EgyDead: item type={result['type']}, servers={len(servers)}")
    return result


def extract_stream(url):
    """Resolve a server URL to a playable stream"""
    from .base import resolve_streamruby, resolve_host

    low = (url or "").lower()

    # StreamRuby needs special handling
    if "stmruby" in low or "streamruby" in low:
        stream = resolve_streamruby(url)
        if stream:
            return (
                stream + "|Referer=https://stmruby.com/&Origin=https://stmruby.com",
                None,
                "https://stmruby.com/",
            )

    # For other hosts like hgcloud, minochinos, mixdrop, voe, forafile, etc.
    return base_extract_stream(url)