# -*- coding: utf-8 -*-
"""
Extractor for Akwam - akwam.com.co/
"""

import re
import urllib.parse
from urllib.parse import urljoin, urlparse, parse_qs, quote, unquote
from .base import fetch, log

MAIN_URL = "https://akwam.com.co/"


def _clean_title(title):
    if not title:
        return ""
    title = title.replace("&amp;", "&")
    title = title.replace("مشاهدة", "")
    title = title.replace("تحميل", "")
    title = title.replace("فيلم", "")
    title = title.replace("مسلسل", "")
    title = re.sub(r'\s*[-|]\s*أكوام.*$', '', title)
    title = re.sub(r'\s*[-|]\s*Akwam.*$', '', title, flags=re.I)
    return title.strip()


def _normalize_url(url):
    """Normalize URL with proper encoding for non-ASCII characters"""
    if not url:
        return ""
    url = str(url).strip()
    url = url.replace('&amp;', '&')
    
    # 1. Handle Akwam's specific video server
    # Don't over-encode downet links; they just need standard ASCII
    if "downet.net" in url:
        # Just replace spaces with %20, nothing else
        return url.replace(" ", "%20")
    
    # 2. Re-encode raw Arabic titles for the main site
    try:
        # First unquote to avoid double-encoding existing %xx
        raw_url = unquote(url)
        # Then quote everything except the standard URL delimiters
        # This converts Arabic characters to %XX format (ASCII safe)
        return quote(raw_url, safe=':/?&=#+')
    except Exception as e:
        log("Akwam normalize_url encoding error: {}".format(e))
        # Fallback: return original URL
        return url


def get_categories():
    """Return all available categories."""
    return [
        {"title": "🎬 English Movies", "url": urljoin(MAIN_URL, "movies?section=30"), "type": "category", "_action": "category"},
        {"title": "🎬 Arabic Movies", "url": urljoin(MAIN_URL, "movies?section=29"), "type": "category", "_action": "category"},
        {"title": "🎬 Indian Movies", "url": urljoin(MAIN_URL, "movies?section=31"), "type": "category", "_action": "category"},
        {"title": "🎬 Turkish Movies", "url": urljoin(MAIN_URL, "movies?section=32"), "type": "category", "_action": "category"},
        {"title": "🎬 Asian Movies", "url": urljoin(MAIN_URL, "movies?section=33"), "type": "category", "_action": "category"},
        {"title": "🎬 Anime Movies", "url": urljoin(MAIN_URL, "movies?category=30"), "type": "category", "_action": "category"},
        {"title": "🎬 Netflix Movies", "url": urljoin(MAIN_URL, "movies?category=72"), "type": "category", "_action": "category"},
        {"title": "📺 TV Series", "url": urljoin(MAIN_URL, "series"), "type": "category", "_action": "category"},
        {"title": "📡 TV Shows", "url": urljoin(MAIN_URL, "shows"), "type": "category", "_action": "category"},
        {"title": "🎭 Variety", "url": urljoin(MAIN_URL, "mix"), "type": "category", "_action": "category"},
        {"title": "🆕 Recent", "url": urljoin(MAIN_URL, "recent"), "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    """
    Fetch items from a category page.
    """
    url = url.replace('&amp;', '&')
    
    # Ensure page parameter
    if 'page=' not in url:
        if '?' in url:
            url += '&page=1'
        else:
            url += '?page=1'
    
    log("Akwam: Fetching category URL: {}".format(url))
    
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        log("Akwam: get_category_items failed for {}".format(url))
        return []

    items = []
    seen = set()

    # Get current page number
    current_page = 1
    page_match = re.search(r'[?&]page=(\d+)', url)
    if page_match:
        current_page = int(page_match.group(1))
    
    log("Akwam: Current page: {}".format(current_page))
    
    # Add page separator
    items.append({
        "title": "━━━ Page {} ━━━".format(current_page),
        "type": "separator",
        "_action": "separator",
    })

    # Find all entry-box divs and extract from each
    entry_boxes = re.split(r'<div class="entry-box entry-box-1">', html)
    
    log("Akwam: Found {} entry-box sections".format(len(entry_boxes) - 1))
    
    for box in entry_boxes[1:]:
        # Extract title and URL from h3 a tag
        title_match = re.search(r'<h3[^>]*class="[^"]*entry-title[^"]*"[^>]*>.*?<a\s+href="([^"]+)"[^>]*class="[^"]*text-white[^"]*"[^>]*>([^<]+)</a>', box, re.S | re.I)
        
        if not title_match:
            continue
            
        movie_url = title_match.group(1)
        title = title_match.group(2).strip()
        
        if movie_url in seen:
            continue
        seen.add(movie_url)
        
        full_url = _normalize_url(movie_url)
        
        # Extract poster
        poster = ""
        img_match = re.search(r'data-src="([^"]+)"', box, re.I)
        if not img_match:
            img_match = re.search(r'src="([^"]+)"', box, re.I)
        if img_match:
            poster = img_match.group(1)
            if "placeholder" in poster.lower():
                poster = ""
            else:
                poster = _normalize_url(poster)
        
        items.append({
            "title": _clean_title(title),
            "url": full_url,
            "poster": poster,
            "type": "movie",
            "_action": "details",
        })

    log("Akwam: Extracted {} movie items from page {}".format(len(items) - 1, current_page))

    # Find next page URL
    next_url = None
    next_page_num = current_page + 1
    
    # Look for the next page number link
    next_match = re.search(r'<a\s+class="page-link"[^>]+href="([^"]+)"[^>]*>{}</a>'.format(next_page_num), html, re.I)
    
    if next_match:
        next_url = _normalize_url(next_match.group(1))
        if next_url and next_url != url:
            log("Akwam: Found next page: {}".format(next_url))
            items.append({
                "title": "➡️ Page {} (Next)".format(current_page + 1),
                "url": next_url,
                "type": "category",
                "_action": "category",
            })

    log("Akwam: Total items returned: {}".format(len(items)))
    return items


def get_page(url):
    """Extract video URL from a movie page - returns only working server."""
    if not url or url.startswith("javascript"):
        return {"title": "Error", "servers": [], "items": [], "type": "movie"}

    log("Akwam: Getting movie page: {}".format(url))
    
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        log("Akwam: get_page failed for {}".format(url))
        return {"title": "Error", "servers": [], "items": []}

    result = {
        "url": final_url or url,
        "title": "",
        "poster": "",
        "plot": "",
        "servers": [],
        "items": [],
        "type": "movie",
    }

    # Extract metadata
    title_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html, re.I)
    if title_match:
        result["title"] = _clean_title(title_match.group(1))

    poster_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html, re.I)
    if poster_match:
        result["poster"] = _normalize_url(poster_match.group(1))

    plot_match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html, re.I)
    if plot_match:
        result["plot"] = _clean_title(plot_match.group(1))

    # Look for go.akwam.com.co watch links (only the working one)
    watch_match = re.search(r'href="(https?://go\.akwam\.com\.co/watch/\d+)"', html, re.I)
    
    if watch_match:
        normalized_url = _normalize_url(watch_match.group(1))
        if normalized_url:
            result["servers"].append({
                "name": "🎬 Play Movie",
                "url": normalized_url,
                "type": "redirect"
            })

    log("Akwam: Found {} servers for {}".format(len(result["servers"]), result["title"]))
    return result


def search(query, page=1):
    """Search functionality."""
    search_url = urljoin(MAIN_URL, "search?q=" + query.replace(" ", "+"))
    if page > 1:
        search_url = urljoin(MAIN_URL, "search?q={}&page={}".format(query.replace(" ", "+"), page))

    log("Akwam: Searching for: {}".format(query))
    
    html, _ = fetch(search_url, referer=MAIN_URL)
    if not html:
        return []

    items = []
    
    entry_boxes = re.split(r'<div class="entry-box entry-box-1">', html)
    
    for box in entry_boxes[1:]:
        title_match = re.search(r'<h3[^>]*class="[^"]*entry-title[^"]*"[^>]*>.*?<a\s+href="([^"]+)"[^>]*class="[^"]*text-white[^"]*"[^>]*>([^<]+)</a>', box, re.S | re.I)
        if title_match:
            movie_url = title_match.group(1)
            title = title_match.group(2).strip()
            items.append({
                "title": _clean_title(title),
                "url": _normalize_url(movie_url),
                "poster": "",
                "type": "movie",
                "_action": "details",
            })

    log("Akwam: Search found {} results".format(len(items)))
    return items


def extract_stream(url):
    """
    Extract stream from go.akwam.com.co/watch URLs.
    Returns plain URL without headers (like egydead.py does).
    CRITICAL FIX: Properly encodes non-ASCII characters for proxy compatibility.
    """
    log("Akwam extract_stream: {}".format(url[:100]))
    
    # Handle go.akwam.com.co redirect
    if 'go.akwam.com.co' in url:
        log("Akwam: Fetching redirect page: {}".format(url))
        html, final_url = fetch(url, referer=MAIN_URL)
        
        if html:
            # Look for the final watch page URL
            watch_page_match = re.search(r'href="(https?://akwam\.com\.co/watch/\d+/\d+/[^"]+)"[^>]*class="[^"]*download-link[^"]*"', html, re.I)
            
            if not watch_page_match:
                watch_page_match = re.search(r'href="(https?://akwam\.com\.co/watch/\d+/\d+/[^"]+)"', html, re.I)
            
            if watch_page_match:
                watch_page_url = watch_page_match.group(1)
                log("Akwam: Found watch page: {}".format(watch_page_url))
                
                # Fetch the watch page to get the video source
                watch_html, _ = fetch(watch_page_url, referer=url)
                if watch_html:
                    # Look for video source tag
                    source_match = re.search(r'<source\s+src="([^"]+)"\s+type="video/mp4"[^>]*>', watch_html, re.I)
                    if not source_match:
                        source_match = re.search(r'<source\s+src="([^"]+)"', watch_html, re.I)
                    
                    if source_match:
                        video_url = source_match.group(1)
                        quality = "HD"
                        if "1080" in video_url.lower():
                            quality = "1080p"
                        elif "720" in video_url.lower():
                            quality = "720p"
                        
                        # Clean URL - remove any pipe characters
                        if '|' in video_url:
                            video_url = video_url.split('|')[0]
                        
                        # ===== CRITICAL FIX FOR ARABIC/INDIAN CONTENT =====
                        # This prevents the Latin-1 encoding error:
                        # UnicodeEncodeError: 'latin-1' codec can't encode characters
                        if video_url:
                            # Check if this is a downet.net URL
                            if "downet.net" in video_url:
                                # Don't over-encode downet links; just fix spaces
                                video_url = video_url.replace(" ", "%20")
                                log("Akwam: Fixed downet.net URL (spaces only)")
                            else:
                                try:
                                    # 1. Decode to get the raw Arabic string
                                    raw_url = unquote(video_url)
                                    # 2. Re-encode specifically for the HTTP headers (Proxy fix)
                                    # The 'safe' parameter keeps the URL structure intact
                                    video_url = quote(raw_url, safe=':/?&=#+')
                                    log("Akwam: Encoded video URL for proxy compatibility")
                                except Exception as e:
                                    log("Akwam encoding error: {}".format(e))
                                    # Fallback: try direct quoting
                                    try:
                                        video_url = quote(video_url, safe=':/?&=#+')
                                    except:
                                        pass
                        # ===== END OF CRITICAL FIX =====
                        
                        log("Akwam: Found video URL: {}".format(video_url[:80]))
                        return video_url, quality, watch_page_url
                    
                    # Also look for video element
                    video_match = re.search(r'<video[^>]*>.*?<source\s+src="([^"]+)".*?</video>', watch_html, re.S | re.I)
                    if video_match:
                        video_url = video_match.group(1)
                        quality = "HD"
                        if "1080" in video_url.lower():
                            quality = "1080p"
                        elif "720" in video_url.lower():
                            quality = "720p"
                        
                        if '|' in video_url:
                            video_url = video_url.split('|')[0]
                        
                        # ===== CRITICAL FIX FOR ARABIC/INDIAN CONTENT =====
                        # Apply same encoding fix
                        if video_url:
                            # Check if this is a downet.net URL
                            if "downet.net" in video_url:
                                # Don't over-encode downet links; just fix spaces
                                video_url = video_url.replace(" ", "%20")
                                log("Akwam: Fixed downet.net URL from video element (spaces only)")
                            else:
                                try:
                                    raw_url = unquote(video_url)
                                    video_url = quote(raw_url, safe=':/?&=#+')
                                    log("Akwam: Encoded video URL from video element")
                                except Exception as e:
                                    log("Akwam encoding error in video element: {}".format(e))
                                    try:
                                        video_url = quote(video_url, safe=':/?&=#+')
                                    except:
                                        pass
                        # ===== END OF CRITICAL FIX =====
                        
                        log("Akwam: Found video URL: {}".format(video_url[:80]))
                        return video_url, quality, watch_page_url
    
    log("Akwam: Failed to find stream")
    return None, None, None