# -*- coding: utf-8 -*-
"""
Extractor for Akwam - akwam.com.co/
"""

import re
from urllib.parse import urljoin, urlparse, parse_qs
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
    if not url:
        return ""
    url = str(url).strip()
    # Remove any amp; artifacts
    url = url.replace('&amp;', '&')
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(MAIN_URL, url)
    if "://" not in url:
        return urljoin(MAIN_URL, url)
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
    """Fetch items from a category page."""
    # Clean the URL first - remove any amp; artifacts
    url = url.replace('&amp;', '&')
    
    # Ensure page parameter
    if 'page=' not in url:
        if '?' in url:
            url += '&page=1'
        else:
            url += '?page=1'
    
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        log("Akwam: get_category_items failed for {}".format(url))
        return []

    items = []
    seen = set()

    # Get current page number
    current_page = 1
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    if 'page' in query_params:
        try:
            current_page = int(query_params['page'][0])
        except:
            pass

    # Add page separator
    items.append({
        "title": "━━━ Page {} ━━━".format(current_page),
        "type": "separator",
        "_action": "separator",
    })

    # Find all entry-box divs - using flexible pattern for current site structure
    entry_boxes = re.findall(r'<div[^>]*class="[^"]*entry-box[^"]*"[^>]*>(.*?)</div>\s*(?=<div|</div>)', html, re.S | re.I)
    
    # Fallback for grid items
    if not entry_boxes:
        entry_boxes = re.findall(r'<div[^>]*class="[^"]*(?:col-.*?entry-box[^"]*)"[^>]*>(.*?)</div>\s*(?=<div|</div>)', html, re.S | re.I)
    
    log("Akwam: Found {} entry boxes".format(len(entry_boxes)))
    
    for box in entry_boxes:
        link = None
        
        # Look for the play button link (icn play)
        play_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*icn play[^"]*"[^>]*>', box, re.I)
        if play_match:
            link = play_match.group(1)
        else:
            # Look for any a tag inside entry-image
            img_link = re.search(r'<div[^>]*class="[^"]*entry-image[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"', box, re.S | re.I)
            if img_link:
                link = img_link.group(1)
        
        # Also check title link
        if not link:
            title_link = re.search(r'<h3[^>]*class="[^"]*entry-title[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"', box, re.S | re.I)
            if title_link:
                link = title_link.group(1)
        
        if not link:
            continue
        
        # Extract image
        img_match = re.search(r'<img[^>]+src="([^"]+)"[^>]*>', box, re.I)
        if not img_match:
            img_match = re.search(r'<img[^>]+data-src="([^"]+)"[^>]*>', box, re.I)
        img = img_match.group(1) if img_match else ""
        
        # Extract title
        title_match = re.search(r'<h3[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h3>', box, re.S | re.I)
        if not title_match:
            alt_match = re.search(r'<img[^>]+alt="([^"]+)"[^>]*>', box, re.I)
            if alt_match:
                title = alt_match.group(1).strip()
            else:
                continue
        else:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        
        if not title:
            continue
        
        if link in seen:
            continue
        seen.add(link)
        
        full_url = _normalize_url(link)
        if not full_url:
            continue
        
        items.append({
            "title": _clean_title(title),
            "url": full_url,
            "poster": _normalize_url(img) if img else "",
            "type": "movie",
            "_action": "details",
        })

    log("Akwam: Extracted {} movie items from page {}".format(len(items) - 1, current_page))

    # Find next page URL
    next_url = None
    
    next_patterns = [
        r'<a[^>]+class="page-link"[^>]+href="([^"]+)"[^>]*>(?:&rsaquo;|»|التالي)[^<]*</a>',
        r'<a[^>]+href="([^"]+)"[^>]*rel="next"[^>]*>',
        r'<a[^>]+class="[^"]*page-link[^"]*"[^>]+href="([^"]+)"[^>]*>([^<]*?(?:التالي|next|&rsaquo;|»)[^<]*)</a>',
        r'page=(\d+)[^<]*>(?:التالي|next|&rsaquo;|»)[^<]*</a>',
    ]
    
    for pattern in next_patterns:
        next_match = re.search(pattern, html, re.I)
        if next_match:
            next_url = _normalize_url(next_match.group(1) if next_match.lastindex >= 1 else next_match.group(0))
            if next_url and next_url != url:
                log("Akwam: Found next page: {}".format(next_url))
                break

    if next_url and next_url != url:
        items.append({
            "title": "➡️ Page {} (Next)".format(current_page + 1),
            "url": next_url,
            "type": "category",
            "_action": "category",
        })

    log("Akwam: category {} -> {} items".format(url, len(items)))
    return items


def get_page(url):
    """Extract video URL from a movie page."""
    if not url or url.startswith("javascript"):
        return {"title": "Error", "servers": [], "items": [], "type": "movie"}

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

    # Look for download links section
    # The actual video URL comes from go.akwam.com.co redirect
    watch_links = re.findall(r'<a[^>]+href="(https?://go\.akwam\.com\.co/(?:watch|link)/\d+)"[^>]*>', html, re.I)
    
    for watch_url in watch_links:
        normalized_url = _normalize_url(watch_url)
        result["servers"].append({
            "name": "🎬 Watch Online",
            "url": normalized_url,
            "type": "redirect"
        })
    
    # Also look for the orange "مشاهدة" button that leads to #downloads
    watch_section_match = re.search(r'<a[^>]+href="#downloads"[^>]*class="[^"]*btn-orange[^"]*"[^>]*>', html, re.I)
    if watch_section_match and not result["servers"]:
        # If we found the button but no direct links, the server will be found when scrolling to #downloads
        # But we need to extract from the downloads section which might be loaded dynamically
        pass
    
    # Fallback: look for direct downet.net URLs
    downet_match = re.search(r'(https?://s\d+\.downet\.net[^\s"\']+\.(?:mp4|m3u8)[^\s"\']*)', html, re.I)
    if downet_match:
        video_url = _normalize_url(downet_match.group(1))
        quality = "HD"
        if "1080" in video_url.lower():
            quality = "1080p"
        elif "720" in video_url.lower():
            quality = "720p"
        result["servers"].insert(0, {
            "name": "🎬 {} Direct Stream".format(quality),
            "url": video_url,
            "type": "direct"
        })

    return result


def search(query, page=1):
    """Search functionality."""
    search_url = urljoin(MAIN_URL, "search?q=" + query.replace(" ", "+"))
    if page > 1:
        search_url = urljoin(MAIN_URL, "search?q={}&page={}".format(query.replace(" ", "+"), page))

    html, _ = fetch(search_url, referer=MAIN_URL)
    if not html:
        return []

    items = []
    entry_boxes = re.findall(r'<div[^>]*class="[^"]*entry-box[^"]*"[^>]*>(.*?)</div>', html, re.S | re.I)
    
    for box in entry_boxes:
        play_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*icn play[^"]*"[^>]*>', box, re.I)
        if not play_match:
            continue
        link = play_match.group(1)
        
        img_match = re.search(r'<img[^>]+src="([^"]+)"[^>]*>', box, re.I)
        img = img_match.group(1) if img_match else ""
        
        title_match = re.search(r'<h3[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h3>', box, re.S | re.I)
        if not title_match:
            continue
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        
        items.append({
            "title": _clean_title(title),
            "url": _normalize_url(link),
            "poster": _normalize_url(img) if img else "",
            "type": "movie",
            "_action": "details",
        })

    return items


def extract_stream(url):
    """
    Extract stream from go.akwam.com.co redirect URLs.
    """
    log("Akwam extract_stream: {}".format(url[:100]))
    
    from .base import fetch, find_mp4, find_m3u8, resolve_iframe_chain
    
    # Check if it's already a direct downet.net URL
    if 'downet.net' in url and ('.mp4' in url or '.m3u8' in url):
        q = "HD"
        if "1080" in url:
            q = "1080p"
        elif "720" in url:
            q = "720p"
        log("Akwam: Direct downet.net URL found")
        return url, q, url
    
    # Handle go.akwam.com.co redirect
    if 'go.akwam.com.co' in url:
        log("Akwam: Fetching redirect page: {}".format(url))
        html, final_url = fetch(url, referer=MAIN_URL)
        
        if html:
            # Look for the final video URL - it's often a downet.net URL
            # Pattern from the network log: https://s203d1.downet.net/download/.../video.mp4
            downet_patterns = [
                r'(https?://s\d+\.downet\.net[^\s"\']+\.mp4[^\s"\']*)',
                r'(https?://s\d+\.downet\.net[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://[^\s"\']+\.downet\.net[^\s"\']+\.(?:mp4|m3u8)[^\s"\']*)',
                r'download/([^\s"\']+\.mp4)',
            ]
            
            for pattern in downet_patterns:
                matches = re.findall(pattern, html, re.I)
                for video_url in matches:
                    if video_url.startswith('http'):
                        full_url = video_url
                    elif video_url.startswith('/'):
                        # Build full URL from the redirect domain
                        parsed = urlparse(final_url or url)
                        full_url = "{}://{}{}".format(parsed.scheme, parsed.netloc, video_url)
                    else:
                        continue
                    
                    q = "HD"
                    if "1080" in full_url:
                        q = "1080p"
                    elif "720" in full_url:
                        q = "720p"
                    log("Akwam: Found video URL: {}".format(full_url[:100]))
                    return full_url, q, final_url or url
            
            # Look for meta refresh or iframe
            meta_refresh = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;\s*url=([^"\']+)["\']', html, re.I)
            if meta_refresh:
                redirect_url = _normalize_url(meta_refresh.group(1))
                log("Akwam: Meta refresh to: {}".format(redirect_url))
                return extract_stream(redirect_url)
            
            iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.I)
            if iframe_match:
                iframe_url = _normalize_url(iframe_match.group(1))
                log("Akwam: Iframe URL: {}".format(iframe_url))
                return extract_stream(iframe_url)
    
    # Fallback to base extractor
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)