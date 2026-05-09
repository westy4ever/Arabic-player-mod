# Directory Structure
```
extractors/
  __init__.py
  akoam.py
  akwam.py
  akwams.py
  arablionztv.py
  arabseed.py
  base.py
  egydead.py
  fasel.py
  shaheed.py
  topcinema.py
  wecima.py
images/
  bg_detail.png
  bg_search.png
  bg_settings.png
  bg.png
  playback_a_ff.png
  playback_a_pause.png
  playback_a_play.png
  playback_a_rew.png
  playback_banner_sd.png
  playback_banner.png
  playback_buff_progress.png
  playback_cbuff_progress.png
  playback_ffmpeg_logo.png
  playback_gstreamer_logo.png
  playback_loop_off.png
  playback_loop_on.png
  playback_pointer.png
  playback_progress.png
  playerclock.xml
  playerskin.xml
  settings.json
  splash.png
  sub_synchro.png
plugin.png
plugin.py
README.md
repomix-output-westy4ever-Arabic-player-mod.md
```

# Files

## File: extractors/__init__.py
`````python
# ArabicPlayer Extractors Package
`````

## File: extractors/akoam.py
`````python
# -*- coding: utf-8 -*-
import re
from urllib.parse import urljoin
from .base import fetch, log

# Updated to work with both akwams.com.co and akwam.com.co
# (with or without trailing slash)
MAIN_URL = "https://akwam.com.co/one/"


def _clean_title(title):
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("تحميل", "")
        .strip()
    )


def _extract_items_from_homepage(html):
    """
    Extract movies/series/anime from the new akwam.com.co homepage structure.
    Pattern matches: div with class="item" or similar, containing an <a> with poster image.
    """
    items = []
    seen = set()
    
    # Primary pattern for akwam.com.co
    patterns = [
        # Format: <div class="item"> <a href="URL" class="movie"> <img data-src="POSTER" alt="TITLE">
        r'<div class="item">\s*<a href="([^"]+)" class="movie">\s*<img[^>]+data-src="([^"]+)"[^>]+alt="([^"]+)"',
        # Fallback: simpler pattern
        r'<a href="(/[^"]+)" class="movie">\s*<img[^>]+(?:data-src|src)="([^"]+)"[^>]+alt="([^"]+)"',
        # Another variant
        r'<div[^>]*class="[^"]*item[^"]*"[^>]*>.*?<a href="([^"]+)".*?<img[^>]+(?:data-src|src)="([^"]+)"[^>]+alt="([^"]+)"',
    ]
    
    for pattern in patterns:
        for match in re.findall(pattern, html or "", re.S):
            link, img, title = match
            if link in seen or not link.startswith("/"):
                continue
            seen.add(link)
            
            # Determine type from URL or context
            if "/series/" in link or "/مسلسل" in link or "series" in title.lower():
                item_type = "series"
            elif "/anime/" in link or "/انمي" in link:
                item_type = "anime"
            else:
                item_type = "movie"
            
            # Build full URL
            full_url = urljoin(MAIN_URL, link)
            
            items.append({
                "title": _clean_title(title),
                "url": full_url,
                "poster": img,
                "type": item_type,
                "_action": "details",
            })
    
    return items


def get_categories():
    """Return main category links (Movies, Series, Anime)"""
    # The new site uses query parameters for filtering
    return [
        {"title": "🎬 Movies",    "url": urljoin(MAIN_URL, "?filter=movies"), "type": "category", "_action": "category"},
        {"title": "📺 TV Series", "url": urljoin(MAIN_URL, "?filter=series"), "type": "category", "_action": "category"},
        {"title": "🍥 Anime",     "url": urljoin(MAIN_URL, "?filter=anime"),  "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    """
    Fetch items from a category page (movies, series, anime, or search results)
    """
    html, _ = fetch(url, referer=MAIN_URL)
    if not html:
        return []

    items = _extract_items_from_homepage(html)
    seen_urls = {item["url"] for item in items}
    
    # Pagination - look for next page link
    next_patterns = [
        r'<a href="([^"]+)"[^>]*class="[^"]*next[^"]*"[^>]*>',
        r'<link[^>]*rel=["\']next["\'][^>]*href=["\']([^"\']+)["\']',
        r'<a[^>]*>\s*التالي\s*</a>\s*<a href="([^"]+)"',
    ]
    
    for pattern in next_patterns:
        next_match = re.search(pattern, html, re.I)
        if next_match:
            next_url = next_match.group(1).replace("&amp;", "&")
            if not next_url.startswith("http"):
                next_url = urljoin(MAIN_URL, next_url)
            if next_url not in seen_urls:
                items.append({
                    "title": "➡️ Next Page",
                    "url": next_url,
                    "type": "category",
                    "_action": "category",
                })
            break
    
    return items


def _quote_url(url):
    from urllib.parse import quote
    return quote(url, safe=":/%?=&")


def get_page(url):
    """
    Extract details (title, poster, plot, episodes, servers) from a movie/series/episode page
    """
    url = _quote_url(url)
    html, final_url = fetch(url, referer=MAIN_URL)
    
    result = {
        "url": url,
        "title": "",
        "poster": "",
        "plot": "",
        "servers": [],
        "items": [],
        "type": "movie",
    }
    
    if not html:
        return result

    # Extract title
    title_patterns = [
        r'<h1[^>]*>(.*?)</h1>',
        r'<div[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</div>',
        r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"',
    ]
    for pattern in title_patterns:
        m = re.search(pattern, html, re.S | re.I)
        if m:
            result["title"] = _clean_title(m.group(1))
            break

    # Extract poster
    poster_patterns = [
        r'<img[^>]+class="[^"]*img-fluid[^"]*"[^>]+src="([^"]+)"',
        r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"',
        r'<div[^>]*class="[^"]*poster[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"',
        r'<img[^>]+data-src="([^"]+)"[^>]+alt="[^"]*poster',
    ]
    for pattern in poster_patterns:
        m = re.search(pattern, html, re.I)
        if m:
            result["poster"] = m.group(1).replace("&amp;", "&")
            break

    # Extract plot/summary
    plot_patterns = [
        r'<p[^>]+class="[^"]*plot[^"]*"[^>]*>(.*?)</p>',
        r'<div[^>]*class="[^"]*summary[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>',
        r'القصة\s*:?\s*</?(?:strong|span|div)?[^>]*>\s*(.*?)(?:</|$)',
    ]
    for pattern in plot_patterns:
        m = re.search(pattern, html, re.S | re.I)
        if m:
            result["plot"] = _clean_title(re.sub(r'<[^>]+>', '', m.group(1)))
            break

    # Check if this is a series page (has episodes)
    is_series = (
        "/series/" in (final_url or url) or
        "/مسلسل" in result["title"] or
        "مسلسل" in result["title"] or
        ("الحلقة" in html and ("episode" in html.lower() or "حلقة" in html))
    ) and "/episode/" not in (final_url or url)

    if is_series:
        result["type"] = "series"
        seen_eps = set()
        
        # Episode extraction patterns for akwam.com.co
        episode_patterns = [
            # Pattern: <a href="/series/.../episode/1"> <div class="episode-number">1</div>
            r'<a[^>]+href="([^"]+/(?:episode|حلقة)/[^"]+)"[^>]*>.*?(?:<div[^>]*class="[^"]*episode[^"]*"[^>]*>(.*?)</div>|<span[^>]*>(?:Episode|حلقة)\s*(\d+))',
            # Simple pattern for episode links
            r'<a[^>]+href="([^"]*episode[^"]*)"[^>]*>(.*?)</a>',
            # Any link containing /episode/ or /حلقة/
            r'href="([^"]*(?:/episode/|/حلقة/)[^"]*)"',
        ]
        
        for pattern in episode_patterns:
            for match in re.findall(pattern, html, re.S | re.I):
                if isinstance(match, tuple):
                    ep_url = match[0]
                    ep_title = match[1] if len(match) > 1 else ""
                else:
                    ep_url = match
                    ep_title = ""
                
                full_url = urljoin(final_url or url, ep_url).replace("&amp;", "&")
                if full_url in seen_eps:
                    continue
                seen_eps.add(full_url)
                
                if not ep_title or ep_title.strip() == "":
                    ep_num = len(result["items"]) + 1
                    ep_title = f"Episode {ep_num}"
                else:
                    ep_title = _clean_title(ep_title)
                
                result["items"].append({
                    "title": ep_title,
                    "url": full_url,
                    "type": "episode",
                    "_action": "details",
                })
        
        # Sort episodes by number if possible
        def extract_ep_num(item):
            match = re.search(r'(\d+)', item["title"])
            return int(match.group(1)) if match else 999
        result["items"].sort(key=extract_ep_num)
        
        return result

    # For movies or episode pages, extract watch/download servers
    watch_links = []
    
    # Find watch/download links
    link_patterns = [
        r'href="(https?://(?:go\.)?akwam(?:s)?\.com\.co/(?:watch|download|episode)/[^"]+)"',
        r'href="(/watch/[^"]+)"',
        r'href="(/download/[^"]+)"',
        r'<a[^>]+class="[^"]*btn[^"]*watch[^"]*"[^>]+href="([^"]+)"',
        r'<a[^>]+href="([^"]+)"[^>]*>(?:مشاهدة|تحميل|Watch|Download)',
    ]
    
    for pattern in link_patterns:
        for link in re.findall(pattern, html, re.I):
            if link.startswith("/"):
                link = urljoin(MAIN_URL, link)
            link = link.replace("&amp;", "&").strip()
            if link not in watch_links:
                watch_links.append(link)
    
    # Build server entries
    watch_count = 1
    download_count = 1
    for link in watch_links:
        if "/watch/" in link or "/episode/" in link:
            result["servers"].append({
                "name": f"🎬 Watch {watch_count}",
                "url": link,
                "type": "direct"
            })
            watch_count += 1
        elif "/download/" in link:
            result["servers"].append({
                "name": f"⬇️ Download {download_count}",
                "url": link,
                "type": "direct"
            })
            download_count += 1
        else:
            result["servers"].append({
                "name": f"🌐 Server {len(result['servers']) + 1}",
                "url": link,
                "type": "direct"
            })
    
    return result


def extract_stream(url):
    """
    Extract direct video stream URL from a watch page.
    Handles go.akwam shortener and extracts m3u8/mp4 sources.
    """
    url = (url or "").replace("&amp;", "&").strip()

    # Resolve go.akwam.sv or go.akwams.com.co shortener
    if "go.akwam" in url or "go.akwams" in url:
        html, final_url = fetch(url, referer=MAIN_URL)
        if html:
            resolved = re.search(r'https?://akwam(?:s)?\.com\.co/(?:watch|episode)/[^\s\'"<>]+', html, re.I)
            if resolved:
                url = resolved.group(0).replace("&amp;", "&")
            elif final_url and ("akwam" in final_url or "akwams" in final_url):
                url = final_url

    # Handle akwam watch pages
    if "akwam.com.co/watch/" in url or "akwams.com.co/watch/" in url or \
       "akwam.com.co/episode/" in url or "akwams.com.co/episode/" in url:
        html, final_url = fetch(url, referer=MAIN_URL)
        if html:
            # Try multiple patterns to find video source
            patterns = [
                r'<source[^>]+src="([^"]+)"[^>]*type="video/mp4"',
                r'<source[^>]+src="([^"]+(?:m3u8|mp4)[^"]*)"',
                r'"file"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
                r'"videoUrl"\s*:\s*"([^"]+)"',
                r'data-video-url=["\']([^"\']+)["\']',
                r'src:\s*["\']([^"\']+\.(?:m3u8|mp4))',
                r'<video[^>]+src="([^"]+)"',
                r'<iframe[^>]+src="([^"]+)"',
            ]
            
            for pattern in patterns:
                m = re.search(pattern, html, re.I)
                if m:
                    video_url = m.group(1).replace("\\u0026", "&").replace("&amp;", "&")
                    # If it's an iframe, resolve it recursively
                    if "iframe" in pattern or video_url.startswith("http") and "iframe" not in pattern.lower():
                        # Could be an embedded player
                        from .base import resolve_iframe_chain
                        resolved_stream, _ = resolve_iframe_chain(video_url, referer=url)
                        if resolved_stream:
                            return resolved_stream, None, MAIN_URL
                    if video_url.startswith("http") and (".m3u8" in video_url or ".mp4" in video_url):
                        return video_url, None, MAIN_URL

    # Fallback to base extractor which handles all major video hosts
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
`````

## File: extractors/akwam.py
`````python
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
`````

## File: extractors/akwams.py
`````python
# -*- coding: utf-8 -*-
"""
Extractor for Akwams - akwams.com.co
Includes Recent category (latest added content)
"""

import re
import json
from urllib.parse import urljoin
from .base import fetch, log

MAIN_URL = "https://akwams.com.co/"


def _clean_title(title):
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("تحميل", "")
        .replace("فيلم", "")
        .replace("مسلسل", "")
        .strip()
    )


def _normalize_url(url):
    if not url:
        return ""
    url = str(url).strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(MAIN_URL, url)
    if not url.startswith("http") and "://" not in url:
        return urljoin(MAIN_URL, url)
    return url


def get_categories():
    """Return all categories from Akwams navigation menu with proper English names."""
    return [
        {"title": "🆕 Recent (أضيف حديثا)",   "url": "https://akwams.com.co/recent/", "type": "category", "_action": "category"},
        {"title": "🎬 English Movies",          "url": "https://akwams.com.co/category/movies/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/", "type": "category", "_action": "category"},
        {"title": "🎬 Dubbed English Movies",    "url": "https://akwams.com.co/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a%d8%a9-%d9%85%d8%af%d8%a8%d9%84%d8%ac%d8%a9/", "type": "category", "_action": "category"},
        {"title": "🎬 Arabic Movies",           "url": "https://akwams.com.co/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%b9%d8%b1%d8%a8%d9%8a/", "type": "category", "_action": "category"},
        {"title": "🎬 Asian Movies",            "url": "https://akwams.com.co/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%b3%d9%8a%d9%88%d9%8a%d8%a9/", "type": "category", "_action": "category"},
        {"title": "🎬 Anime Movies",            "url": "https://akwams.com.co/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d9%86%d9%85%d9%8a/", "type": "category", "_action": "category"},
        {"title": "🎬 Turkish Movies",          "url": "https://akwams.com.co/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%aa%d8%b1%d9%83%d9%8a%d8%a9/", "type": "category", "_action": "category"},
        {"title": "🎬 Indian Movies",           "url": "https://akwams.com.co/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d9%87%d9%86%d8%af%d9%8a%d8%a9/", "type": "category", "_action": "category"},
        {"title": "🎬 Cartoon Movies",          "url": "https://akwams.com.co/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d9%83%d8%b1%d8%aa%d9%88%d9%86/", "type": "category", "_action": "category"},
        {"title": "📺 English Series",          "url": "https://akwams.com.co/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/", "type": "category", "_action": "category"},
        {"title": "📺 Anime Series",            "url": "https://akwams.com.co/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d9%86%d9%85%d9%8a/", "type": "category", "_action": "category"},
        {"title": "📺 Turkish Series",          "url": "https://akwams.com.co/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%aa%d8%b1%d9%83%d9%8a%d8%a9/", "type": "category", "_action": "category"},
        {"title": "📺 Cartoon Series",          "url": "https://akwams.com.co/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d9%83%d8%b1%d8%aa%d9%88%d9%86/", "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    """
    Fetch items from a category page.
    Adds page number indicator and next page button at bottom.
    """
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        log("Akwams: get_category_items failed for {}".format(url))
        return []

    items = []
    seen = set()

    # Extract current page number from URL
    current_page = 1
    page_match = re.search(r'/page/(\d+)/', url)
    if page_match:
        current_page = int(page_match.group(1))
    
    # Add page indicator as first item
    items.append({
        "title": "━━━ Page {} ━━━".format(current_page),
        "type": "separator",
        "_action": "separator",
    })

    # Pattern for category pages (works for both /category/ and /recent/)
    pattern = r'<a[^>]+href="([^"]+)"[^>]*class="box"[^>]*>.*?<img[^>]+data-src="([^"]+)"[^>]+alt="([^"]+)"'
    
    for match in re.findall(pattern, html, re.S | re.I):
        link, img, title = match
        if link in seen or "/category/" in link:
            continue
        seen.add(link)
        
        full_url = _normalize_url(link)
        if not full_url:
            continue
        
        items.append({
            "title": _clean_title(title),
            "url": full_url,
            "poster": _normalize_url(img),
            "type": "movie",
            "_action": "details",
        })

    # Find next page URL
    next_url = None
    
    next_match = re.search(r'<a[^>]+class="page-link"[^>]+href="([^"]+)"[^>]*>\s*التالي\s*»\s*</a>', html, re.I)
    if not next_match:
        next_match = re.search(r'<link[^>]+rel="next"[^>]+href="([^"]+)"', html, re.I)
    
    if next_match:
        next_url = _normalize_url(next_match.group(1))
    
    # Also check for numbered pagination
    if not next_url:
        next_page_num = current_page + 1
        next_match = re.search(r'<a[^>]+class="page-link"[^>]+href="([^"]+)"[^>]*>{}</a>'.format(next_page_num), html, re.I)
        if next_match:
            next_url = _normalize_url(next_match.group(1))

    if next_url and next_url != url:
        items.append({
            "title": "➡️ Page {} (Next)".format(current_page + 1),
            "url": next_url,
            "type": "category",
            "_action": "category",
        })

    log("Akwams: category {} -> {} items (page {})".format(url, len(items), current_page))
    return items


def get_page(url):
    """Extract details from a movie page."""
    if not url or url.startswith("javascript"):
        return {"title": "Error", "servers": [], "items": [], "type": "movie"}

    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        log("Akwams: get_page failed for {}".format(url))
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

    # Extract title
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
    if title_match:
        result["title"] = _clean_title(title_match.group(1))
    else:
        og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html, re.I)
        if og_title:
            result["title"] = _clean_title(og_title.group(1))

    # Extract poster
    poster_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html, re.I)
    if poster_match:
        result["poster"] = _normalize_url(poster_match.group(1))

    # Extract plot
    plot_match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html, re.I)
    if plot_match:
        result["plot"] = _clean_title(plot_match.group(1))

    # Fetch watch page
    base_url = url.rstrip('/')
    watch_url = base_url + '/watch'

    log("Akwams: Fetching watch page: {}".format(watch_url))
    watch_html, _ = fetch(watch_url, referer=url)

    if watch_html:
        server_links = re.findall(r'data-link=["\']([^"\']+)["\']', watch_html, re.I)
        if not server_links:
            server_links = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', watch_html, re.I)

        seen_servers = set()
        for idx, server_url in enumerate(server_links):
            if any(ext in server_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', 'wp-content/uploads']):
                continue
            if server_url in seen_servers:
                continue
            seen_servers.add(server_url)

            full_server_url = _normalize_url(server_url)
            if full_server_url:
                host_match = re.search(r'https?://([^/]+)', full_server_url)
                host_name = host_match.group(1) if host_match else ""
                
                if "hgcloud" in host_name:
                    display_name = "🎬 HGCloud"
                elif "mixdrop" in host_name:
                    display_name = "🎬 MixDrop"
                elif "bysekoze" in host_name:
                    display_name = "🎬 Bysekoze"
                elif "minochinos" in host_name:
                    display_name = "🎬 Minochinos"
                elif "playmogo" in host_name:
                    display_name = "🎬 PlayMogo"
                elif "forafile" in host_name:
                    display_name = "🎬 Forafile"
                elif "smoothpre" in host_name:
                    display_name = "🎬 SmoothPre"
                else:
                    display_name = "🎬 Server {}".format(idx + 1)

                result["servers"].append({
                    "name": display_name,
                    "url": full_server_url,
                    "type": "direct",
                })

    return result


def search(query, page=1):
    """Search functionality."""
    search_url = urljoin(MAIN_URL, "?s=" + query.replace(" ", "+"))
    if page > 1:
        search_url = urljoin(MAIN_URL, "page/{}/?s={}".format(page, query.replace(" ", "+")))

    html, _ = fetch(search_url, referer=MAIN_URL)
    if not html:
        return []

    items = []
    pattern = r'<a[^>]+href="([^"]+)"[^>]*class="box"[^>]*>.*?<img[^>]+data-src="([^"]+)"[^>]+alt="([^"]+)"'

    for link, img, title in re.findall(pattern, html, re.S | re.I):
        if not link.startswith("javascript") and "/category/" not in link:
            items.append({
                "title": _clean_title(title),
                "url": _normalize_url(link),
                "poster": _normalize_url(img),
                "type": "movie",
                "_action": "details",
            })

    return items


def extract_stream(url):
    """Delegate to base extractor for video host resolution."""
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
`````

## File: extractors/arablionztv.py
`````python
# -*- coding: utf-8 -*-
"""
Plugin for arablionztv.xyz
FIX: Replaced f-strings with .format() for Python 2/3.5 compatibility.
FIX: Improved card/episode regex to match modern layouts.
FIX: get_page() now catches data-src/data-lazy-src iframe patterns.
"""

import re
from urllib.parse import urljoin
from .base import fetch, extract_stream as base_extract_stream

MAIN_URL = "https://arablionztv.xyz/"


def _clean_title(title):
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("تحميل", "")
        .replace("فيلم", "")
        .replace("مسلسل", "")
        .strip()
    )


def _full_url(path):
    if not path:
        return ""
    path = path.strip()
    if path.startswith("http"):
        return path
    if path.startswith("//"):
        return "https:" + path
    return urljoin(MAIN_URL, path)


def _extract_boxes(html):
    """
    FIX: Reworked to use a more general card-finding strategy that works
    across common WordPress / custom CMS layouts.
    Returns list of (link, img, title) tuples.
    """
    results = []
    seen = set()

    # Strategy 1: article or post-type containers
    for container in re.findall(
        r'<(?:article|div)[^>]+class="[^"]*(?:item|post|movie|entry)[^"]*"[^>]*>(.*?)</(?:article|div)>',
        html or "", re.S | re.I
    ):
        link_m  = re.search(r'href=["\']([^"\']+)["\']', container)
        title_m = (
            re.search(r'title=["\']([^"\']+)["\']', container) or
            re.search(r'alt=["\']([^"\']+)["\']', container) or
            re.search(r'<h[1-4][^>]*>([^<]+)</h[1-4]>', container, re.I)
        )
        img_m   = re.search(r'(?:data-src|data-lazy-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', container, re.I)

        if link_m and title_m:
            link  = _full_url(link_m.group(1))
            title = _clean_title(title_m.group(1))
            img   = _full_url(img_m.group(1)) if img_m else ""
            if link and link not in seen:
                seen.add(link)
                results.append((link, img, title))

    if results:
        return results

    # Strategy 2: plain <a href> + <img> pattern (broad fallback)
    for m in re.finditer(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*'
        r'(?:[^<]*<[^>]+>[^<]*)*?'
        r'<img[^>]+(?:data-src|data-lazy-src|src)=["\']([^"\']+)["\'][^>]+alt=["\']([^"\']+)["\']',
        html or "", re.S | re.I
    ):
        link  = _full_url(m.group(1))
        img   = _full_url(m.group(2))
        title = _clean_title(m.group(3))
        if link and link not in seen:
            seen.add(link)
            results.append((link, img, title))

    return results


def _extract_episodes(html, base_url):
    episodes = []
    seen = set()

    # Pattern: links containing episode/حلقة with a number
    for m in re.finditer(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(?:[^<]*<[^>]*>)*?'
        r'(?:حلقة|Episode|EP)\s*(\d+)',
        html or "", re.I | re.S
    ):
        url    = _full_url(m.group(1).replace("&amp;", "&"))
        ep_num = m.group(2)
        if url in seen:
            continue
        seen.add(url)
        episodes.append({
            "title":    "حلقة {}".format(ep_num),
            "url":      url,
            "type":     "episode",
            "_action":  "details",
        })
        if len(episodes) >= 100:
            return episodes

    # Fallback: any link containing episode/season in URL
    if not episodes:
        for link in re.findall(r'href=["\']([^"\']*(?:episode|season|ep)[^"\']*)["\']', html, re.I):
            url = _full_url(link.replace("&amp;", "&"))
            if url in seen or "category" in url:
                continue
            seen.add(url)
            episodes.append({
                "title":   "حلقة",
                "url":     url,
                "type":    "episode",
                "_action": "details",
            })
    return episodes


def get_categories():
    return [
        {"title": "🎬 أفلام إنجليزية",  "url": urljoin(MAIN_URL, "category/movies/english-movies/"), "type": "category", "_action": "category"},
        {"title": "🎬 أفلام عربية",     "url": urljoin(MAIN_URL, "category/movies/arabic-movies/"),  "type": "category", "_action": "category"},
        {"title": "🎬 كارتون",          "url": urljoin(MAIN_URL, "category/movies/cartoon/"),        "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات إنجليزية","url": urljoin(MAIN_URL, "category/series/english-series/"),"type": "category", "_action": "category"},
        {"title": "📺 مسلسلات عربية",   "url": urljoin(MAIN_URL, "category/series/arabic-series/"),  "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات تركية",   "url": urljoin(MAIN_URL, "category/series/turkish-series/"), "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        return []

    items = []
    seen  = set()

    for link, img, title in _extract_boxes(html):
        if link in seen:
            continue
        seen.add(link)
        low = link.lower() + " " + title.lower()
        is_series = "/series/" in low or "مسلسل" in low
        items.append({
            "title":   title,
            "url":     link,
            "poster":  img,
            "type":    "series" if is_series else "movie",
            "_action": "details",
        })

    # Pagination
    next_m = (
        re.search(r'<a[^>]+class="next"[^>]+href=["\']([^"\']+)["\']', html, re.I) or
        re.search(r'<link[^>]+rel="next"[^>]+href=["\']([^"\']+)["\']', html, re.I)
    )
    if next_m:
        items.append({
            "title":   "➡️ الصفحة التالية",
            "url":     next_m.group(1).replace("&amp;", "&"),
            "type":    "category",
            "_action": "category",
        })

    return items


def get_page(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    result = {
        "url":     url,
        "title":   "",
        "poster":  "",
        "plot":    "",
        "servers": [],
        "items":   [],
        "type":    "movie",
    }
    if not html:
        return result

    # Title
    title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
    if title_m:
        result["title"] = _clean_title(title_m.group(1))

    # Poster
    poster_m = (
        re.search(r'<img[^>]+class="[^"]*(?:poster|cover|img-fluid)[^"]*"[^>]+src=["\']([^"\']+)["\']', html, re.I) or
        re.search(r'<meta[^>]+property="og:image"[^>]+content=["\']([^"\']+)["\']', html, re.I)
    )
    if poster_m:
        result["poster"] = poster_m.group(1).replace("&amp;", "&")

    # Plot
    plot_m = (
        re.search(r'<div[^>]*class="[^"]*(?:description|summary|plot)[^"]*"[^>]*>(.*?)</div>', html, re.S | re.I) or
        re.search(r'<p[^>]*class="[^"]*desc[^"]*"[^>]*>(.*?)</p>', html, re.S | re.I)
    )
    if plot_m:
        result["plot"] = re.sub(r'<[^>]+>', ' ', plot_m.group(1)).strip()

    # Series check
    is_series = "/series/" in (final_url or url) or "مسلسل" in result["title"]
    if is_series:
        result["type"]  = "series"
        result["items"] = _extract_episodes(html, final_url or url)
        return result

    # Servers — FIX: added data-src and data-lazy-src to iframe search
    seen_servers = set()
    for m in re.finditer(
        r'<iframe[^>]+(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']',
        html, re.I
    ):
        iframe_url = m.group(1).strip()
        if iframe_url.startswith("//"):
            iframe_url = "https:" + iframe_url
        if not iframe_url.startswith("http") or iframe_url in seen_servers:
            continue
        seen_servers.add(iframe_url)
        result["servers"].append({
            "name":  "سيرفر {}".format(len(result["servers"]) + 1),
            "url":   iframe_url,
            "type":  "direct",
        })

    # Direct video host links
    for m in re.finditer(
        r'href=["\']'
        r'(https?://(?:streamtape|dood|mixdrop|uqload|voe|vidbom|upstream|'
        r'streamwish|filemoon|lulustream|ok\.ru)[^"\']+)'
        r'["\']',
        html, re.I
    ):
        link = m.group(1)
        if link not in seen_servers:
            seen_servers.add(link)
            result["servers"].append({
                "name":  "مشاهدة {}".format(len(result["servers"]) + 1),
                "url":   link,
                "type":  "direct",
            })

    # Direct media URL fallback
    if not result["servers"]:
        for pat in (
            r'file\s*:\s*["\']([^"\']+)["\']',
            r'src\s*:\s*["\']([^"\']+)["\']',
            r'data-video=["\']([^"\']+)["\']',
        ):
            m = re.search(pat, html, re.I)
            if m:
                result["servers"].append({
                    "name":  "مشاهدة",
                    "url":   m.group(1),
                    "type":  "direct",
                })
                break

    return result


def extract_stream(url):
    if url.startswith("http") and any(x in url.lower() for x in (".m3u8", ".mp4", ".mkv")):
        return url, None, MAIN_URL
    return base_extract_stream(url)
`````

## File: extractors/arabseed.py
`````python
# -*- coding: utf-8 -*-
import base64
import json
import re
from .base import fetch, log, urljoin

MAIN_URL     = "https://asd.pics/"
QUALITY_ORDER = {"1080": 0, "720": 1, "480": 2}
BLOCKED_HOSTS = ("vidara.to", "bysezejataos.com")


def _clean_title(title):
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("فيلم", "")
        .strip()
    )


def _extract_first(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text or "", re.S)
        if match:
            return match.group(1).strip()
    return ""


def _decode_hidden_url(url):
    url = (url or "").replace("\\/", "/").replace("&amp;", "&").strip()
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith("http"):
        url = urljoin(MAIN_URL, url)
    for key in ("url", "id"):
        marker = key + "="
        if marker not in url:
            continue
        raw = url.split(marker, 1)[1].split("&", 1)[0]
        try:
            raw += "=" * ((4 - len(raw) % 4) % 4)
            decoded = base64.b64decode(raw).decode("utf-8")
            if decoded.startswith("http"):
                return decoded
        except Exception:
            pass
    return url


def _server_priority(server_url):
    lowered = server_url.lower()
    if "reviewrate" in lowered or "reviewtech" in lowered:
        return 0
    if "vidmoly" in lowered:
        return 1
    return 9


def _server_name(server_url, label_hint=""):
    lowered = (server_url or "").lower()
    if "reviewrate" in lowered or "reviewtech" in lowered:
        return "عرب سيد"
    if "vidmoly" in lowered:
        return "VidMoly"
    if label_hint:
        return label_hint.strip()
    domain_match = re.search(r'https?://([^/]+)', server_url or "")
    return domain_match.group(1) if domain_match else "Server"


def _collect_ajax_servers(watch_html, watch_url):
    token = _extract_first(
        [
            r"csrf__token['\"]?\s*[:=]\s*['\"]([^'\"]+)",
            r"csrf_token['\"]?\s*[:=]\s*['\"]([^'\"]+)",
        ],
        watch_html,
    )
    post_id = _extract_first(
        [
            r"psot_id['\"]?\s*[:=]\s*['\"](\d+)",
            r"post_id['\"]?\s*[:=]\s*['\"](\d+)",
        ],
        watch_html,
    )
    home_url = _extract_first([r"main__obj\s*=\s*\{'home__url':\s*'([^']+)'"], watch_html) or MAIN_URL
    if not token or not post_id:
        log("ArabSeed: Missing AJAX token/post_id")
        return []

    quality_url     = urljoin(home_url, "get__quality__servers/")
    watch_server_url = urljoin(home_url, "get__watch__server/")
    results = []
    seen    = set()

    for quality in ("1080", "720", "480"):
        body, _ = fetch(
            quality_url,
            post_data={"post_id": post_id, "quality": quality, "csrf_token": token},
            referer=watch_url,
        )
        if not body:
            continue
        try:
            data = json.loads(body)
        except Exception:
            log("ArabSeed: Failed to decode quality JSON for {}p".format(quality))
            continue
        if data.get("type") != "success":
            continue

        # Direct server in response
        direct_server = _decode_hidden_url(data.get("server", ""))
        if direct_server.startswith("http") and not any(h in direct_server for h in BLOCKED_HOSTS):
            key = (quality, direct_server)
            if key not in seen:
                seen.add(key)
                results.append({
                    "quality": quality,
                    "url":     direct_server,
                    "name":    _server_name(direct_server, "سيرفر عرب سيد"),
                })

        # Server list rows
        server_rows = re.findall(
            r'<li[^>]+data-post="([^"]+)"[^>]+data-server="([^"]+)"[^>]+data-qu="([^"]+)"[^>]*>.*?<span>([^<]+)</span>',
            data.get("html", ""),
            re.S,
        )
        for row_post_id, server_id, row_quality, label in server_rows:
            watch_body, _ = fetch(
                watch_server_url,
                post_data={
                    "post_id":   row_post_id,
                    "quality":   row_quality,
                    "server":    server_id,
                    "csrf_token": token,
                },
                referer=watch_url,
            )
            if not watch_body:
                continue
            try:
                watch_data = json.loads(watch_body)
            except Exception:
                continue
            if watch_data.get("type") != "success" or not watch_data.get("server"):
                continue

            server_url_decoded = _decode_hidden_url(watch_data.get("server", ""))
            if not server_url_decoded.startswith("http"):
                continue
            if any(h in server_url_decoded for h in BLOCKED_HOSTS):
                continue

            key = (row_quality, server_url_decoded)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "quality": row_quality,
                "url":     server_url_decoded,
                "name":    _server_name(server_url_decoded, label),
            })

    # FIX: if AJAX returned nothing at all, log clearly rather than silent empty
    if not results:
        log("ArabSeed: AJAX returned 0 servers for watch_url={}".format(watch_url))

    results.sort(key=lambda item: (
        QUALITY_ORDER.get(item["quality"], 9),
        _server_priority(item["url"]),
        item["name"],
    ))
    return results


def get_categories():
    return [
        {"title": "🌍 أفلام أجنبي",    "url": urljoin(MAIN_URL, "category/foreign-movies-12/"),  "type": "category", "_action": "category"},
        {"title": "🇪🇬 أفلام عربي",   "url": urljoin(MAIN_URL, "category/arabic-movies-12/"),   "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أجنبي",  "url": urljoin(MAIN_URL, "category/foreign-series-5/"),   "type": "category", "_action": "category"},
        {"title": "🇸🇦 مسلسلات عربي", "url": urljoin(MAIN_URL, "category/arabic-series-10/"),   "type": "category", "_action": "category"},
        {"title": "🎭 مسلسلات انمي",   "url": urljoin(MAIN_URL, "category/anime-series-1/"),     "type": "category", "_action": "category"},
        {"title": "🎮 عروض مصارعة",    "url": urljoin(MAIN_URL, "category/wwe-shows-1/"),        "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, _ = fetch(url, referer=MAIN_URL)
    if not html:
        return []

    items = []
    seen  = set()

    # FIX: try structured blocks first, then broader fallback
    blocks = re.findall(
        r'<div[^>]+class=["\'](?:recent--block|post--block|item)[^>]*>(.*?)</div>',
        html, re.S | re.IGNORECASE
    )
    if not blocks:
        blocks = re.findall(
            r'(<a[^>]+href=["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\'][^>]*>.*?</a>)',
            html, re.S | re.IGNORECASE
        )

    for block in blocks:
        m = (
            re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]+title=["\']([^"\']+)["\'][^>]*>', block, re.S) or
            re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?<img[^>]+alt=["\']([^"\']+)["\']', block, re.S)
        )
        if m:
            link, title = m.groups()
            img_m = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', block)
            img   = img_m.group(1) if img_m else ""
            if link in seen or "/category/" in link:
                continue
            seen.add(link)
            title     = _clean_title(title)
            item_type = "series" if ("/series-" in link or "مسلسل" in title) else "movie"
            items.append({"title": title, "url": link, "poster": img, "type": item_type, "_action": "details"})

    # Broad fallback if nothing found yet
    if not items:
        regex = r'<a[^>]+href=["\']([^"\']+)["\'][^>]+title=["\']([^"\']+)["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']'
        for link, title, img in re.findall(regex, html, re.S | re.IGNORECASE):
            if link in seen or "/category/" in link:
                continue
            seen.add(link)
            item_type = "series" if ("/series-" in link or "مسلسل" in title) else "movie"
            items.append({"title": title.strip(), "url": link, "poster": img, "type": item_type, "_action": "details"})

    next_page = re.search(r'href="([^"]+/page/\d+/)"', html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page.group(1), "type": "category", "_action": "category"})
    return items


def get_page(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        return {"title": "Error", "servers": []}

    result = {
        "url":     final_url or url,
        "title":   "",
        "plot":    "",
        "poster":  "",
        "rating":  "",
        "year":    "",
        "servers": [],
        "items":   [],
    }

    title_match = (
        re.search(r'og:title[^>]+content="([^"]+)"', html) or
        re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    )
    if title_match:
        result["title"] = _clean_title(title_match.group(1).split("-")[0])

    poster_match = re.search(r'og:image"[^>]+content="([^"]+)"', html)
    if poster_match:
        result["poster"] = poster_match.group(1)

    plot_match = re.search(r'name="description"[^>]+content="([^"]+)"', html)
    if plot_match:
        result["plot"] = plot_match.group(1)

    is_series = (
        any(m in (final_url or url) for m in ("/series-", "/season-", "/episode-"))
        or "مسلسل" in result["title"]
    )

    # Determine watch URL
    watch_url   = (final_url or url).rstrip("/") + "/watch/"
    watch_match = re.search(r'href="([^"]+/watch/)"', html)
    if watch_match:
        watch_url = watch_match.group(1)

    watch_html, watch_final = fetch(watch_url, referer=final_url or url)
    if not watch_html:
        watch_html, watch_final = html, (final_url or url)

    for server in _collect_ajax_servers(watch_html, watch_final or watch_url):
        result["servers"].append({
            "name": "[{}p] {}".format(server["quality"], server["name"]),
            "url":  server["url"],
            "type": "direct",
        })

    if is_series:
        seen_eps   = set()
        blocks_html = (
            " ".join(re.findall(
                r'<div[^>]+class=["\'](?:Blocks-Episodes|Episode--List|seasons--episodes|'
                r'Blocks-Container|List--Episodes|List--Seasons|episodes)[^>]*>(.*?)</section>',
                html, re.S | re.I
            )) or html
        )
        for ep_url, ep_title in re.findall(
            r'<a[^>]+href="(https?://[^/]+/[^"]+)"[^>]+title="([^"]+)"',
            blocks_html, re.S
        ):
            if ("الحلقة" not in ep_title and "حلقة" not in ep_title) or ep_url in seen_eps:
                continue
            if not any(x in ep_url for x in ("series-", "-season", "episode")):
                continue
            seen_eps.add(ep_url)
            result["items"].append({
                "title":   ep_title.strip(),
                "url":     ep_url,
                "type":    "episode",
                "_action": "details",
            })

    # Data-link fallback if AJAX produced nothing
    if not result["servers"]:
        for fallback in re.findall(r'data-(?:link|url|iframe|src|href)="([^"]+)"', watch_html or "", re.S):
            fallback = _decode_hidden_url(fallback)
            if not fallback.startswith("http"):
                continue
            if any(h in fallback for h in BLOCKED_HOSTS):
                continue
            if fallback not in [s["url"] for s in result["servers"]]:
                result["servers"].append({"name": "Fallback", "url": fallback, "type": "direct"})

    return result


def extract_stream(url):
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
`````

## File: extractors/base.py
`````python
# -*- coding: utf-8 -*-
"""
Base extractor — common utilities + video host resolvers
Improvements over previous version:
  - Fixed egydead referer (tv8.egydead.live instead of stale x7k9f.sbs)
  - fetch() retry on transient failures (503 / timeout)
  - New resolvers: ok.ru, filemoon, streamwish family, lulustream, vidguard
  - Improved: streamtape (3 fallback patterns), doodstream (15+ domains),
               voe (base64 + newer layouts), resolve_iframe_chain (meta-refresh,
               JS location, data-src)
  - _best_media_url: richer source patterns (jwplayer, sources[], clappr)
  - Unicode URL support for Arabic characters
  - Added fastvid.cam resolver
  - Added rpmvip/upshare/cleantechworld resolvers
  - NEW: Added faselhd specific resolvers for scdns.io and datahowa.asia
  - NEW: Added downet.net resolver for Akwam direct MP4s
  - NEW: Added govid.live resolver for faselhd.rip
  - NEW: Added referer support for faselhd.rip and datahowa.asia
"""

import re
import json
import time
import random
import base64  # <-- Make sure this is present
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor, HTTPSHandler
from urllib.parse import urljoin, urlparse, unquote, urlencode, quote_plus
from urllib.error import URLError, HTTPError
import http.cookiejar as cookiejar
import ssl
import gzip
import zlib
import io
import sys

try:
    import brotli
except Exception:
    brotli = None

UA      = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 30
ACCEPT_ENCODING = "gzip, deflate, br" if brotli is not None else "gzip, deflate"

_opener = None


def log(msg):
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = "[{}] {}\n".format(ts, msg)
        with open("/tmp/arabicplayer.log", "a") as f:
            f.write(line)
        print("[ArabicPlayer] {}".format(msg))
    except Exception:
        pass


def _get_opener():
    global _opener
    if _opener:
        return _opener
    cj = cookiejar.CookieJar()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    except AttributeError:
        ctx = ssl._create_unverified_context()
    _opener = build_opener(HTTPCookieProcessor(cj), HTTPSHandler(context=ctx))
    return _opener


def _decode_response_body(raw, info):
    ce = info.get("Content-Encoding", "").lower()
    if "gzip" in ce:
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    elif "deflate" in ce:
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except Exception:
            raw = zlib.decompress(raw)
    elif "br" in ce and brotli is not None:
        raw = brotli.decompress(raw)
    charset = "utf-8"
    ctype = info.get("Content-Type", "").lower()
    if "charset=" in ctype:
        charset = ctype.split("charset=")[-1].split(";")[0].strip()
    try:
        return raw.decode(charset)
    except Exception:
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return raw.decode("latin-1", errors="ignore")


def _encode_unicode_url(url):
    """Encode Unicode characters in URL to percent-encoded format."""
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


def fetch(url, referer=None, extra_headers=None, post_data=None):
    """
    Robust fetch with:
    - Smart per-domain referer defaults
    - Auto retry on transient errors (503, timeout, connection reset)
    - Brotli / gzip / deflate decompression
    - Cookie jar (shared session)
    - Unicode URL support (properly encodes Arabic/etc. characters)
    """
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            opener = _get_opener()
            
            # Handle Unicode URLs - encode to percent-encoded format
            encoded_url = _encode_unicode_url(url)
            
            parsed = urlparse(encoded_url)
            domain = parsed.netloc.lower()

            if not referer:
                # ── per-domain referer defaults ───────────────────────────
                if "tv8.egydead" in domain or "egydead" in domain:
                    referer = "https://tv8.egydead.live/"
                elif "wecima" in domain or "mycima" in domain:
                    referer = "https://wecima.click/"
                elif "fasel" in domain or "faselhdx" in domain or "fasel-hd" in domain:
                    referer = "https://www.fasel-hd.cam/"
                elif "faselhd.rip" in domain:
                    referer = "https://faselhd.rip/"
                elif "govid.live" in domain:
                    referer = "https://faselhd.rip/"
                elif "datahowa.asia" in domain:
                    referer = "https://faselhd.rip/"
                elif "scdns.io" in domain:
                    referer = "https://www.fasel-hd.cam/"
                elif "downet.net" in domain:
                    referer = "https://akwam.com.co/"
                elif "topcinema" in domain:
                    referer = "https://topcinemaa.com/"
                elif "shaheed" in domain or "shahid" in domain:
                    referer = "https://shahidd4u.com/"
                elif "streamwish" in domain or "wishfast" in domain:
                    referer = "https://streamwish.to/"
                elif "filemoon" in domain:
                    referer = "https://filemoon.sx/"
                elif "lulustream" in domain:
                    referer = "https://lulustream.com/"
                elif "ok.ru" in domain:
                    referer = "https://ok.ru/"
                elif "vidguard" in domain or "vgfplay" in domain:
                    referer = "https://vidguard.to/"
                elif "filelion" in domain or "vidhide" in domain or "streamhide" in domain:
                    referer = "https://filelions.to/"
                elif "fastvid" in domain:
                    referer = "https://fastvid.cam/"
                elif "rpmvip" in domain:
                    referer = "https://shaaheid4u.rpmvip.com/"
                elif "upn.one" in domain or "upshare" in domain:
                    referer = "https://shiid4u.upn.one/"
                else:
                    referer = "{}://{}/".format(parsed.scheme, domain)

            headers = {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "ar,en-US,en;q=0.9",
                "Accept-Encoding": ACCEPT_ENCODING,
                "Connection": "keep-alive",
                "Referer": referer,
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
            if any(x in encoded_url.lower() for x in ["ajax", "get__watch", "api/", ".json"]):
                headers.update({
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                })
            if extra_headers:
                headers.update(extra_headers)

            data = post_data
            if data and isinstance(data, dict):
                data = urlencode(data).encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            elif data and isinstance(data, (str, bytes)):
                if isinstance(data, str):
                    data = data.encode("utf-8")

            log("Fetching (attempt {}): {}".format(attempt + 1, encoded_url))
            req = Request(encoded_url, headers=headers, data=data)

            with opener.open(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                final_url = resp.geturl()
                info = resp.info()

                if any(x in final_url.lower() for x in ("alliance4creativity.com", "watch-it-legally")):
                    log("!!! ACE Redirect detected for {} !!!".format(encoded_url))
                    return None, final_url

                html = _decode_response_body(raw, info)
                log("Fetch OK: {} ({} bytes)".format(final_url, len(html)))
                return html, final_url

        except HTTPError as e:
            # Retry on 503 / 429
            if attempt < max_retries and e.code in (503, 429, 502):
                log("Fetch HTTPError {}, retrying in 2s: {}".format(e.code, url))
                time.sleep(2)
                continue
            try:
                raw = e.read()
                html = _decode_response_body(raw, e.info()) if raw else ""
                log("Fetch HTTPError: {} → {} {} ({} bytes)".format(url, e.code, e.reason, len(html)))
            except Exception:
                log("Fetch HTTPError: {} → {} {}".format(url, getattr(e, "code", "?"), getattr(e, "reason", e)))
            return None, url

        except URLError as e:
            if attempt < max_retries:
                log("Fetch URLError (retry {}): {} → {}".format(attempt + 1, url, e))
                global _opener
                _opener = None           # reset opener on network error
                time.sleep(1.5)
                continue
            log("Fetch URLError: {} → {}".format(url, e))
            _opener = None
            return None, url

        except UnicodeEncodeError as e:
            # Handle Unicode encoding errors specifically
            log("Fetch UnicodeEncodeError: {} → {}".format(url, e))
            # Try with manual encoding
            try:
                # Fallback: try to encode the URL explicitly
                encoded_url = url.encode('utf-8').decode('ascii', errors='ignore')
                if encoded_url != url:
                    log("Retrying with encoded URL: {}".format(encoded_url))
                    return fetch(encoded_url, referer, extra_headers, post_data)
            except Exception:
                pass
            return None, url

        except Exception as e:
            if attempt < max_retries:
                log("Fetch Error (retry {}): {} → {}".format(attempt + 1, url, e))
                time.sleep(1)
                continue
            log("Fetch Error: {} → {}".format(url, e))
            return None, url

    return None, url


# ─── HTML helpers ─────────────────────────────────────────────────────────────

def extract_iframes(html, base_url=""):
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    result = []
    for src in iframes:
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/") and base_url:
            p = urlparse(base_url)
            src = "{}://{}{}".format(p.scheme, p.netloc, src)
        if src.startswith("http"):
            result.append(src)
    return result


def find_m3u8(html):
    if not html:
        return None
    patterns = [
        r'["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'hls\.loadSource\(["\']([^"\']+)["\']',
        r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'data-(?:url|src)=["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'hlsManifestUrl["\']?\s*:\s*["\']([^"\']+)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").replace("\\u0026", "&").strip()
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith("http") and ".m3u8" in url:
                return url
    return None


def find_mp4(html):
    if not html:
        return None
    patterns = [
        r'["\']([^"\']+\.mp4[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
        r'data-(?:url|src)=["\']([^"\']+\.mp4[^"\']*)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").strip()
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith("http") and ".mp4" in url:
                return url
    return None


def _best_media_url(text):
    """
    Pick the highest-quality video URL visible in plain or unpacked JS.
    Covers: direct URLs, JWPlayer setup, sources[], Clappr, HLS manifests.
    """
    if not text:
        return None
    candidates = []
    seen = set()

    def score(url):
        lowered = url.lower()
        if "2160" in lowered or "4k" in lowered:   return 5000
        if "1080" in lowered or "fhd" in lowered:  return 4000
        if "720" in lowered  or "hd" in lowered:   return 3000
        if "480" in lowered:                        return 2000
        if "360" in lowered:                        return 1000
        if "240" in lowered or "sd" in lowered:     return 500
        if ".m3u8" in lowered:                      return 3500
        return 100

    patterns = [
        # JWPlayer / sources array
        r'sources\s*:\s*\[{[^}]*file\s*:\s*["\']([^"\']+)["\']',
        r'"file"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        r"'file'\s*:\s*'([^']+(?:m3u8|mp4)[^']*)'",
        # Clappr / hls.js
        r'"source"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        r"'source'\s*:\s*'([^']+(?:m3u8|mp4)[^']*)'",
        r'"src"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        # Direct URLs
        r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
        r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)',
        # hlsManifestUrl (ok.ru, etc.)
        r'hlsManifestUrl["\']?\s*:\s*["\']([^"\']+)["\']',
        # playlist / stream
        r'"(?:playlist|stream|hls|hls2|master)"\s*:\s*"([^"]+)"',
        r"'(?:playlist|stream|hls|hls2|master)'\s*:\s*'([^']+)'",
    ]
    for pat in patterns:
        for match in re.findall(pat, text, re.I):
            url = match.replace("\\/", "/").replace("&amp;", "&").replace("\\u0026", "&").strip()
            if url.startswith("//"):
                url = "https:" + url
            if not url.startswith("http"):
                continue
            if url in seen:
                continue
            seen.add(url)
            candidates.append((score(url), url))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# ─── Packer / obfuscation ─────────────────────────────────────────────────────

def _extract_packer_blocks(html):
    blocks = []
    marker = "eval(function(p,a,c,k,e,d){"
    tail   = ".split('|')))"
    pos = 0
    while True:
        start = (html or "").find(marker, pos)
        if start == -1:
            break
        end = (html or "").find(tail, start)
        if end == -1:
            break
        blocks.append(html[start : end + len(tail)])
        pos = end + len(tail)
    return blocks


def decode_packer(packed):
    try:
        def read_js_string(text, start_idx):
            quote = text[start_idx]
            i = start_idx + 1
            out = []
            while i < len(text):
                ch = text[i]
                if ch == "\\" and i + 1 < len(text):
                    out.append(text[i + 1])
                    i += 2
                    continue
                if ch == quote:
                    return "".join(out), i + 1
                out.append(ch)
                i += 1
            return "", -1

        start = packed.find("}(")
        if start == -1:
            return ""
        idx = start + 2
        while idx < len(packed) and packed[idx] in " \t\r\n":
            idx += 1
        if idx >= len(packed) or packed[idx] not in ("'", '"'):
            return ""

        p, idx = read_js_string(packed, idx)
        if idx == -1:
            return ""

        nums = re.match(r"\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*", packed[idx:], re.S)
        if not nums:
            return ""
        a, c = nums.group(1), nums.group(2)
        idx += nums.end()
        if idx >= len(packed) or packed[idx] not in ("'", '"'):
            return ""

        k, idx = read_js_string(packed, idx)
        if idx == -1:
            return ""

        a, c = int(a), int(c)
        k = k.split("|")

        def e(c_val):
            result = ""
            while True:
                result = "0123456789abcdefghijklmnopqrstuvwxyz"[c_val % a] + result
                c_val //= a
                if c_val == 0:
                    break
            return result

        d = {e(i): k[i] or e(i) for i in range(c)}
        return re.sub(r'\b(\w+)\b', lambda x: d.get(x.group(1), x.group(1)), p)
    except Exception:
        return ""


def find_packed_links(html):
    for ev in _extract_packer_blocks(html):
        dec = decode_packer(ev)
        if dec:
            res = find_m3u8(dec) or find_mp4(dec)
            if res:
                return res
    # fallback broader eval pattern
    for ev in re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S):
        dec = decode_packer(ev)
        if dec:
            res = find_m3u8(dec) or find_mp4(dec)
            if res:
                return res
    return None


def _unpack_all(html):
    """Return list of (original_html + all unpacked JS blocks) for thorough scanning."""
    texts = [html]
    for block in _extract_packer_blocks(html):
        dec = decode_packer(block)
        if dec:
            texts.append(dec)
    return texts


# ─── Video Host Resolvers ─────────────────────────────────────────────────────

def resolve_streamtape(url):
    """streamtape.com — tries 3 extraction patterns as the site changes often."""
    try:
        html, _ = fetch(url, referer="https://streamtape.com/")
        if not html:
            return None

        # Pattern 1: robotlink innerHTML concat (classic)
        m = re.search(r"robotlink\)\.innerHTML\s*=\s*'([^']+)'\s*\+\s*'([^']+)'", html)
        if m:
            link = m.group(1) + m.group(2)
            if not link.startswith("http"):
                link = "https:" + link
            return link.replace("//streamtape.com", "https://streamtape.com")

        # Pattern 2: single innerHTML assignment
        m = re.search(r"robotlink\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]", html)
        if m:
            link = m.group(1)
            return ("https:" + link) if link.startswith("//") else link

        # Pattern 3: /get_video?... inside JS
        m = re.search(r'(/get_video\?[^"\'&\s]+)', html)
        if m:
            return "https://streamtape.com" + m.group(1)

        # Pattern 4: direct mp4 URL
        return find_mp4(html)
    except Exception:
        pass
    return None


def resolve_doodstream(url):
    """dood.* / doodstream / dsv* / d0o0d and 20+ domain variants."""
    DOOD_DOMAINS = [
        "dood.re", "dood.to", "dood.so", "dood.pm", "dood.ws",
        "dood.watch", "dood.sh", "dood.la", "dood.li", "dood.cx",
        "dood.xyz", "dood.wf", "d0o0d.com", "dsvplay.com",
        "doods.pro", "ds2play.com", "dooood.com", "doodstream.com",
    ]
    try:
        # Normalise to a working domain
        working_html = None
        working_url  = url
        for dom in DOOD_DOMAINS:
            candidate = re.sub(r'dood\.[a-z]+|dsvplay\.[a-z]+|d0o0d\.[a-z]+|doodstream\.[a-z]+', dom, url)
            html, final = fetch(candidate, referer=candidate)
            if html and "pass_md5" in html:
                working_html = html
                working_url  = candidate
                break
        if not working_html:
            working_html, _ = fetch(url, referer=url)
        if not working_html:
            return None

        m = re.search(r'\$\.get\(["\'](/pass_md5/[^"\']+)["\']', working_html)
        if not m:
            m = re.search(r'pass_md5/([^"\'.\s&]+)', working_html)
            if m:
                pass_path = "/pass_md5/" + m.group(1)
            else:
                return None
        else:
            pass_path = m.group(1)

        # Extract base domain from working URL
        parsed = urlparse(working_url)
        dood_base = "{}://{}".format(parsed.scheme, parsed.netloc)

        token_html, _ = fetch(dood_base + pass_path, referer=working_url)
        if not token_html:
            return None

        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        rand = "".join(random.choice(chars) for _ in range(10))
        token = pass_path.split("/")[-1]
        return "{}{}&token={}&expiry={}".format(
            token_html.strip(), rand, token, int(time.time() * 1000)
        )
    except Exception:
        pass
    return None


def resolve_vidbom(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    except Exception:
        pass
    return None


def resolve_uqload(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        m = re.search(r'sources:\s*\["([^"]+)"\]', html)
        if m:
            return m.group(1)
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_govid(url):
    """govid.live - enhanced resolver for faselhd.rip streams"""
    try:
        # If it's already a m3u8, return it
        if '.m3u8' in url:
            log("resolve_govid: direct m3u8 URL")
            return url
        
        html, _ = fetch(url, referer="https://faselhd.rip/")
        if not html:
            return None
        
        # Look for m3u8 in the response
        m3u8 = find_m3u8(html)
        if m3u8:
            log("resolve_govid: found m3u8: {}".format(m3u8[:80]))
            return m3u8
        
        return find_mp4(html)
    except Exception:
        pass
    return None


def resolve_upstream(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_mixdrop(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        # Direct MDCore pattern
        m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', html)
        if m:
            link = m.group(1)
            return ("https:" + link) if link.startswith("//") else link
        # Packed JS
        for txt in _unpack_all(html):
            m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', txt)
            if m:
                link = m.group(1)
                return ("https:" + link) if link.startswith("//") else link
    except Exception:
        pass
    return None


def resolve_voe(url):
    """voe.sx — handles multiple obfuscation layers including base64 and newer layouts."""
    try:
        html, final = fetch(url, referer="https://voe.sx/")
        if not html:
            return None

        # Layer 1: direct hls / sources patterns
        for pat in [
            r"'hls'\s*:\s*'([^']+)'",
            r'"hls"\s*:\s*"([^"]+)"',
            r"sources\s*=\s*\[{[^}]*file\s*:\s*'([^']+)'",
            r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        ]:
            m = re.search(pat, html, re.I)
            if m:
                return m.group(1).replace("\\/", "/")

        # Layer 2: base64 atob() blobs
        import base64
        for enc in re.finditer(r'atob\([\'"]([A-Za-z0-9+/=]+)[\'"]\)', html):
            try:
                dec = base64.b64decode(enc.group(1) + "==").decode("utf-8", errors="ignore")
                mm = re.search(r'(https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*)', dec)
                if mm:
                    return mm.group(1)
            except Exception:
                pass

        # Layer 3: packed JS
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_streamruby(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        res = find_m3u8(html) or find_mp4(html)
        if res:
            return res
        for txt in _unpack_all(html):
            res = find_m3u8(txt) or find_mp4(txt)
            if res:
                return res
    except Exception:
        pass
    return None


def resolve_hgcloud(url):
    """hgcloud.to - redirects to masukestin.com or other host"""
    try:
        html, final_url = fetch(url, referer="https://hgcloud.to/")
        if not html:
            return None
        
        # Check if there's an iframe pointing to masukestin.com
        iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+masukestin\.com[^"\']+)["\']', html, re.I)
        if iframe_match:
            embed_url = iframe_match.group(1)
            log("hgcloud: Found masukestin embed: {}".format(embed_url))
            # Resolve the masukestin URL
            from .base import resolve_host
            return resolve_host(embed_url)
        
        # Check for meta refresh redirect
        meta_refresh = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;\s*url=([^"\']+)["\']', html, re.I)
        if meta_refresh:
            redirect_url = meta_refresh.group(1)
            if "masukestin" in redirect_url:
                log("hgcloud: Redirecting to masukestin: {}".format(redirect_url))
                from .base import resolve_host
                return resolve_host(redirect_url)
        
        # Check if the page has JavaScript that loads masukestin
        if "masukestin" in html:
            masukestin_urls = re.findall(r'(https?://masukestin\.com/[^\s"\']+)', html)
            for masukestin_url in masukestin_urls:
                log("hgcloud: Found masukestin URL: {}".format(masukestin_url))
                from .base import resolve_host
                result = resolve_host(masukestin_url)
                if result:
                    return result
        
        return None
    except Exception as e:
        log("resolve_hgcloud error: {}".format(e))
        return None


def resolve_vidtube(url):
    """vidtube.one — JWPlayer behind packer, optional domain restriction bypass."""
    try:
        html, _ = fetch(url, referer="https://topcinema.fan/")
        if not html or "restricted for this domain" in html.lower():
            html, _ = fetch(url, referer="https://topcinema.fan/")
        if not html:
            return None
        best = _best_media_url(html)
        if best:
            return best
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best
    except Exception:
        pass
    return None

def resolve_masukestin(url):
    """masukestin.com - extracts m3u8 video URL from embed page"""
    try:
        html, final_url = fetch(url, referer="https://masukestin.com/")
        if not html:
            return None

        # Look for the stream URL pattern in the page
        stream_patterns = [
            r'(https?://masukestin\.com/stream/[^\s"\']+\.m3u8[^\s"\']*)',
            r'(https?://masukestin\.com/stream/[^\s"\']+)',
            r'streamUrl\s*:\s*["\']([^"\']+)["\']',
            r'videoUrl\s*:\s*["\']([^"\']+)["\']',
            r'src:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]

        for pattern in stream_patterns:
            match = re.search(pattern, html, re.I)
            if match:
                stream_url = match.group(1)
                stream_url = stream_url.replace("\\/", "/").replace("&amp;", "&")
                if stream_url.startswith("//"):
                    stream_url = "https:" + stream_url
                if ".m3u8" in stream_url:
                    log("masukestin: Found m3u8 stream: {}".format(stream_url[:80]))
                    return stream_url

        # Look in script tags
        script_tags = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S | re.I)
        for script in script_tags:
            for pattern in stream_patterns:
                match = re.search(pattern, script, re.I)
                if match:
                    stream_url = match.group(1)
                    if ".m3u8" in stream_url:
                        log("masukestin: Found m3u8 in script: {}".format(stream_url[:80]))
                        return stream_url

        # Look for base64 encoded URLs
        b64_patterns = [
            r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)',
            r'Base64\.decode\(["\']([A-Za-z0-9+/=]+)["\']\)',
        ]
        for pattern in b64_patterns:
            for match in re.findall(pattern, html):
                try:
                    import base64
                    decoded = base64.b64decode(match).decode('utf-8')
                    stream_match = re.search(r'(https?://masukestin\.com/stream/[^\s"\']+\.m3u8[^\s"\']*)', decoded)
                    if stream_match:
                        log("masukestin: Found m3u8 in base64: {}".format(stream_match.group(1)[:80]))
                        return stream_match.group(1)
                except:
                    pass

        log("masukestin: No stream URL found")
        return None
    except Exception as e:
        log("resolve_masukestin error: {}".format(e))
        return None

# ── NEW resolvers ──────────────────────────────────────────────────────────────

def resolve_streamwish(url):
    """
    StreamWish / WishFast / Filelions / VidHide / StreamHide / DHTpre —
    all run the same JWPlayer-based platform.
    """
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None

        # Try direct patterns first (fastest)
        best = _best_media_url(html)
        if best:
            return best

        # Packed JS (all these sites heavily pack their JS)
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_filemoon(url):
    """
    Filemoon.sx / .to / .nl / .wf — packed JS containing JWPlayer setup.
    Uses parserBYSE in e2iplayer (= packed → JWPlayer sources).
    """
    try:
        html, _ = fetch(url, referer="https://filemoon.sx/")
        if not html:
            return None

        # Direct scan first
        best = _best_media_url(html)
        if best:
            return best

        # Unpack all eval blocks
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        # base64 blobs
        import base64
        for b64 in re.findall(r'atob\(["\']([A-Za-z0-9+/=]{40,})["\']\)', html, re.I):
            try:
                dec = base64.b64decode(b64 + "==").decode("utf-8", "ignore")
                best = _best_media_url(dec)
                if best:
                    return best
            except Exception:
                pass

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_lulustream(url):
    """
    LuluStream — JWPlayer based, similar to streamwish family.
    Requires Referer: https://1fo1ndyf09qz.tnmr.org (confirmed from e2iplayer).
    """
    try:
        html, _ = fetch(url, referer="https://1fo1ndyf09qz.tnmr.org",
                        extra_headers={"Origin": "https://lulustream.com"})
        if not html:
            html, _ = fetch(url, referer="https://lulustream.com/")
        if not html:
            return None

        best = _best_media_url(html)
        if best:
            return best

        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_okru(url):
    """
    ok.ru — uses the /dk/video.playJSON API (confirmed from e2iplayer parserOKRU).
    Extracts HLS manifest URL.
    """
    try:
        # Normalise URL → extract video ID
        m = re.search(r'ok\.ru/(?:video(?:embed)?/|videoembed/)(\d+)', url)
        if not m:
            m = re.search(r'/(\d{10,})', url)
        if not m:
            return None
        video_id = m.group(1)

        # API endpoint (same as e2iplayer parserOKRU)
        api_url = "https://ok.ru/dk/video.playJSON?movieId={}".format(video_id)
        mobile_ua = ("Mozilla/5.0 (iPad; U; CPU OS 3_2 like Mac OS X; en-us) "
                     "AppleWebKit/531.21.10 (KHTML, like Gecko) "
                     "Version/4.0.4 Mobile/7B334b Safari/531.21.10")
        body, _ = fetch(api_url,
                        referer=url,
                        extra_headers={
                            "User-Agent": mobile_ua,
                            "Accept": "application/json",
                        })
        if body:
            try:
                data = json.loads(body)
                hls = data.get("hlsManifestUrl", "")
                if hls:
                    return hls.replace("\\u0026", "&").replace("\\/", "/")
                # Fallback: videos array
                for vid in (data.get("videos") or []):
                    u = vid.get("url") or ""
                    if u.startswith("http"):
                        return u.replace("\\u0026", "&").replace("\\/", "/")
            except Exception:
                pass

        # Fallback: scrape embed page
        embed_url = "https://ok.ru/videoembed/{}".format(video_id)
        html, _ = fetch(embed_url, referer="https://ok.ru/",
                        extra_headers={"User-Agent": mobile_ua})
        if html:
            best = _best_media_url(html)
            if best:
                return best
            m2 = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+)"', html)
            if m2:
                return m2.group(1).replace("\\u0026", "&").replace("\\/", "/")
    except Exception:
        pass
    return None


def resolve_vidguard(url):
    """
    VidGuard / vgfplay — obfuscated JS, exposes stream_url or packed m3u8.
    """
    try:
        html, _ = fetch(url, referer="https://vidguard.to/")
        if not html:
            return None

        # Common direct patterns
        for pat in [
            r'stream_url\s*=\s*["\']([^"\']+)["\']',
            r'"(?:file|src|url)"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r"'(?:file|src|url)'\s*:\s*'([^']+\.m3u8[^']*)'",
        ]:
            m = re.search(pat, html, re.I)
            if m:
                u = m.group(1).replace("\\/", "/").replace("\\u0026", "&")
                return u

        # Packed JS
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        # base64 decode attempts
        import base64
        for b64 in re.findall(r'atob\(["\']([A-Za-z0-9+/=]{40,})["\']\)', html, re.I):
            try:
                dec = base64.b64decode(b64 + "==").decode("utf-8", "ignore")
                best = _best_media_url(dec)
                if best:
                    return best
            except Exception:
                pass

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


# ── fastvid.cam resolver ──────────────────────────────────────────────────────

def resolve_fastvid(url):
    """fastvid.cam - extracts direct m3u8 URLs from the embed page"""
    try:
        html, final_url = fetch(url, referer="https://fastvid.cam/")
        if not html:
            return None
        
        # Look for master.m3u8 or index-*.m3u8 in the page
        patterns = [
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'"(https?://[^"]+\.m3u8[^"]+)"',
            r"'(https?://[^']+\.m3u8[^']+)'",
            r'stream/([^\s"\']+\.m3u8)',
        ]
        
        found_urls = []
        for pattern in patterns:
            matches = re.findall(pattern, html, re.I)
            for match in matches:
                if match.startswith('/'):
                    # Build full URL
                    parsed = urlparse(final_url or url)
                    full_url = f"{parsed.scheme}://{parsed.netloc}{match}"
                    found_urls.append(full_url)
                elif match.startswith('http'):
                    found_urls.append(match)
        
        # Prefer master.m3u8, then index-f2 (720p), then index-f1 (480p)
        for url in found_urls:
            if 'master.m3u8' in url:
                log(f"resolve_fastvid: found master.m3u8: {url}")
                return url
        for url in found_urls:
            if 'index-f2' in url:  # 720p
                log(f"resolve_fastvid: found 720p stream: {url}")
                return url
        for url in found_urls:
            if 'index-f1' in url:  # 480p
                log(f"resolve_fastvid: found 480p stream: {url}")
                return url
        for url in found_urls:
            if '.m3u8' in url:
                log(f"resolve_fastvid: found m3u8: {url}")
                return url
        
        # Also check for JWPlayer configuration
        jw_pattern = r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
        match = re.search(jw_pattern, html, re.I)
        if match:
            stream_url = match.group(1)
            if stream_url.startswith('/'):
                parsed = urlparse(final_url or url)
                stream_url = f"{parsed.scheme}://{parsed.netloc}{stream_url}"
            log(f"resolve_fastvid: found JWPlayer stream: {stream_url}")
            return stream_url
        
        return None
    except Exception as e:
        log(f"resolve_fastvid error: {e}")
        return None


# ── rpmvip / upshare / cleantechworld resolvers ──────────────────────────────

def resolve_rpmvip(url):
    """rpmvip.com - direct m3u8 URLs"""
    # These are already direct m3u8 URLs
    if '.m3u8' in url:
        return url
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        return url if '.m3u8' in url else None


def resolve_upshare(url):
    """upshare / upn.one - direct m3u8 URLs"""
    if '.m3u8' in url:
        return url
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        return url if '.m3u8' in url else None


def resolve_cleantechworld(url):
    """cleantechworld.shop - serves .txt files that are actually m3u8 content"""
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        # If it returns m3u8 content directly, it's already a stream
        if "#EXTM3U" in html:
            return url
        # Otherwise look for m3u8 in the response
        m = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m:
            return m.group(1)
        return None
    except Exception as e:
        log(f"resolve_cleantechworld error: {e}")
        return None


# ========== NEW: FaselHD CDN Resolvers ==========

def resolve_scdns(url):
    """scdns.io - FaselHD's CDN for m3u8 streams (web596x.faselhdx.bid)"""
    try:
        # If it's already a direct m3u8 URL, return it
        if '.m3u8' in url:
            log("resolve_scdns: direct m3u8 URL")
            return url
        
        # Fetch the page to get the actual stream
        html, final_url = fetch(url, referer="https://www.fasel-hd.cam/")
        if html:
            # Look for m3u8 streams in various formats
            m3u8_patterns = [
                r'(https?://[^\s"\']+\.scdns\.io[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://[^\s"\']+\.c\.scdns\.io[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://master\.[^\s"\']+\.scdns\.io[^\s"\']+\.m3u8[^\s"\']*)',
                r'(https?://r[0-9]+--[^\s"\']+\.c\.scdns\.io[^\s"\']+\.m3u8[^\s"\']*)',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html, re.I)
                for stream_url in matches:
                    stream_url = stream_url.replace('\\/', '/').replace('&amp;', '&')
                    # Prefer higher quality streams
                    if 'hd1080' in stream_url or '1080' in stream_url:
                        log("resolve_scdns: found 1080p stream")
                        return stream_url
                    elif 'hd720' in stream_url or '720' in stream_url:
                        log("resolve_scdns: found 720p stream")
                        return stream_url
            
            # Also try to find any m3u8 using the generic finder
            stream = find_m3u8(html)
            if stream:
                log("resolve_scdns: found m3u8 via generic finder")
                return stream
        
        return None
    except Exception as e:
        log(f"resolve_scdns error: {e}")
        return None


def resolve_datahowa(url):
    """datahowa.asia - CDN for govid.live streams (faselhd.rip)"""
    try:
        log("resolve_datahowa: processing {}".format(url[:80]))
        
        # If it's a segment URL, try to get the base m3u8
        if '.ts' in url:
            base_m3u8 = re.sub(r'/seg_[0-9]+\.ts.*$', '/playlist.m3u8', url)
            if base_m3u8 != url:
                log("resolve_datahowa: converting segment to playlist: {}".format(base_m3u8[:80]))
                return base_m3u8
        
        # If it's already a m3u8, return it
        if '.m3u8' in url:
            return url
        
        # Fetch to get actual stream
        html, _ = fetch(url, referer="https://faselhd.rip/")
        if html:
            m3u8 = find_m3u8(html)
            if m3u8:
                return m3u8
        
        return None
    except Exception as e:
        log(f"resolve_datahowa error: {e}")
        return None


def resolve_downet(url):
    """downet.net - Direct MP4 resolver for Akwam"""
    try:
        log("resolve_downet: processing {}".format(url[:80]))
        
        # If it's already a direct MP4 or m3u8, return it
        if '.mp4' in url or '.m3u8' in url:
            q = "HD"
            if "1080" in url:
                q = "1080p"
            elif "720" in url:
                q = "720p"
            return url
        
        # Fetch to get actual stream
        html, _ = fetch(url, referer="https://akwam.com.co/")
        if html:
            mp4 = find_mp4(html) or find_m3u8(html)
            if mp4:
                return mp4
        
        return None
    except Exception as e:
        log(f"resolve_downet error: {e}")
        return None


# ========== START: Wecima CDN Resolvers ==========

def resolve_tnmr(url):
    """tnmr.org - HLS stream resolver for Wecima"""
    try:
        html, _ = fetch(url, referer="https://wecima.cx/")
        if not html:
            return None
        # Look for master.m3u8 or direct stream
        m = re.search(r'(https?://[^\s"\']+\.tnmr\.org[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m:
            return m.group(1)
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        return None


def resolve_mxcontent(url):
    """mxcontent.net - MP4 stream resolver for Wecima"""
    try:
        # Direct MP4 URL - just return it
        if '.mp4' in url:
            return url
        html, _ = fetch(url, referer="https://wecima.cx/")
        if html:
            return find_mp4(html)
    except Exception:
        return None


def resolve_delucloud(url):
    """delucloud.xyz - HLS stream resolver for Wecima"""
    try:
        html, _ = fetch(url, referer="https://wecima.cx/")
        if not html:
            return None
        # Look for master.m3u8
        m = re.search(r'(https?://[^\s"\']+\.delucloud\.xyz[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m:
            return m.group(1)
        return find_m3u8(html)
    except Exception:
        return None


def resolve_savefiles(url):
    """savefiles.com - HLS stream resolver for Wecima"""
    try:
        html, _ = fetch(url, referer="https://wecima.cx/")
        if not html:
            return None
        m = re.search(r'(https?://s[0-9]+\.savefiles\.com[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m:
            return m.group(1)
        return find_m3u8(html)
    except Exception:
        return None


def resolve_sprintcdn(url):
    """sprintcdn.com - HLS stream resolver for Wecima"""
    try:
        html, _ = fetch(url, referer="https://wecima.cx/")
        if not html:
            return None
        return find_m3u8(html)
    except Exception:
        return None


def resolve_aurorafieldnetwork(url):
    """aurorafieldnetwork.store - HLS stream resolver for Wecima"""
    try:
        html, _ = fetch(url, referer="https://wecima.cx/")
        if not html:
            return None
        # Return the .txt file URL which may contain the actual stream
        if '.txt' in url:
            # Fetch the .txt file to get the real stream URL
            content, _ = fetch(url, referer="https://wecima.cx/")
            if content:
                m = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', content)
                if m:
                    return m.group(1)
        return find_m3u8(html)
    except Exception:
        return None

# ========== END: Wecima CDN Resolvers ==========

def resolve_savefiles(url):
    """savefiles.com - HLS stream resolver"""
    try:
        html, _ = fetch(url, referer="https://savefiles.com/")
        if not html:
            return None
        # Look for m3u8 in the page
        m = re.search(r'(https?://[^\s"\']+\.savefiles\.com[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m:
            return m.group(1)
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        return None


def resolve_abstream(url):
    """abstream.to - HLS stream resolver"""
    try:
        html, _ = fetch(url, referer="https://abstream.to/")
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        return None


def resolve_byselapuix(url):
    """byselapuix.com - Filemoon variant"""
    try:
        html, _ = fetch(url, referer="https://byselapuix.com/")
        if not html:
            return None
        # Use filemoon resolver logic
        best = _best_media_url(html)
        if best:
            return best
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        return None


def resolve_dhcplay(url):
    """dhcplay.com - Doodstream variant"""
    try:
        # Use doodstream resolver logic
        return resolve_doodstream(url)
    except Exception:
        return None
    
# Add after existing resolvers, before HOST_RESOLVERS

def resolve_go_akwam(url):
    """go.akwam.com.co - Akwam redirect resolver"""
    try:
        html, final_url = fetch(url, referer="https://akwam.com.co/")
        if not html:
            return None
        
        # Look for the final video URL in the page
        # Pattern 1: video source tag
        source_match = re.search(r'<source[^>]+src="([^"]+\.(?:mp4|m3u8)[^"]*)"', html, re.I)
        if source_match:
            return source_match.group(1)
        
        # Pattern 2: downet.net direct URL
        downet_match = re.search(r'(https?://s\d+\.downet\.net[^\s"\']+\.(?:mp4|m3u8)[^\s"\']*)', html, re.I)
        if downet_match:
            return downet_match.group(1)
        
        # Pattern 3: meta refresh
        meta_match = re.search(r'<meta[^>]+http-equiv="refresh"[^>]+content="\d+;\s*url=([^"]+)"', html, re.I)
        if meta_match:
            redirect_url = meta_match.group(1)
            if redirect_url.startswith("//"):
                redirect_url = "https:" + redirect_url
            # Recursively resolve
            return resolve_host(redirect_url, referer=url)
        
        # Pattern 4: iframe
        iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"[^>]*>', html, re.I)
        if iframe_match:
            iframe_url = iframe_match.group(1)
            if iframe_url.startswith("//"):
                iframe_url = "https:" + iframe_url
            return resolve_host(iframe_url, referer=url)
        
        return None
    except Exception as e:
        log("resolve_go_akwam error: {}".format(e))
        return None


def resolve_abstream(url):
    """abstream.to - HLS stream resolver for Akwam/Wecima"""
    try:
        html, _ = fetch(url, referer="https://abstream.to/")
        if not html:
            return None
        # Look for video source or m3u8
        source_match = re.search(r'<source[^>]+src="([^"]+\.(?:mp4|m3u8)[^"]*)"', html, re.I)
        if source_match:
            return source_match.group(1)
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        return None


def resolve_savefiles_akwam(url):
    """savefiles.com - HLS stream resolver for Akwam"""
    try:
        html, _ = fetch(url, referer="https://savefiles.com/")
        if not html:
            return None
        m = re.search(r'(https?://s[0-9]+\.savefiles\.com[^\s"\']+\.m3u8[^\s"\']*)', html)
        if m:
            return m.group(1)
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        return None


# ─── Host dispatcher ──────────────────────────────────────────────────────────

HOST_RESOLVERS = {
    # Existing
    "streamtape":  resolve_streamtape,
    "dood":        resolve_doodstream,
    "dsvplay":     resolve_doodstream,
    "d0o0d":       resolve_doodstream,
    "doods":       resolve_doodstream,
    "ds2play":     resolve_doodstream,
    "dooood":      resolve_doodstream,
    "vidbom":      resolve_vidbom,
    "vidshare":    resolve_vidbom,
    "uqload":      resolve_uqload,
    "govid":       resolve_govid,
    "upstream":    resolve_upstream,
    "mixdrop":     resolve_mixdrop,
    "voe":         resolve_voe,
    "streamruby":  resolve_streamruby,
    "hgcloud":     resolve_hgcloud,
    "masukestin":  resolve_masukestin,
    "masukestin.com": resolve_masukestin,
    "vidtube":     resolve_vidtube,
    # New
    "streamwish":  resolve_streamwish,
    "wishfast":    resolve_streamwish,
    "filelion":    resolve_streamwish,
    "filelions":   resolve_streamwish,
    "vidhide":     resolve_streamwish,
    "streamhide":  resolve_streamwish,
    "dhtpre":      resolve_streamwish,
    "embedrise":   resolve_streamwish,
    "hglamioz":    resolve_streamwish,
    "filemoon":    resolve_filemoon,
    "lulustream":  resolve_lulustream,
    "ok.ru":       resolve_okru,
    "okru":        resolve_okru,
    "vidguard":    resolve_vidguard,
    "vgfplay":     resolve_vidguard,
    # Fastvid
    "fastvid":     resolve_fastvid,
    "fastvid.cam": resolve_fastvid,
    # RPMVip and friends
    "rpmvip":      resolve_rpmvip,
    "upshare":     resolve_upshare,
    "upn.one":     resolve_upshare,
    "cleantechworld": resolve_cleantechworld,
    "cleantechworld.shop": resolve_cleantechworld,
    
    # ========== FaselHD CDN Resolvers (NEW) ==========
    "scdns":              resolve_scdns,
    "scdns.io":           resolve_scdns,
    "c.scdns.io":         resolve_scdns,
    "datahowa":           resolve_datahowa,
    "datahowa.asia":      resolve_datahowa,
    "govid.live":         resolve_govid,
    
    # ========== Akwam Resolvers (NEW) ==========
    "downet":             resolve_downet,
    "downet.net":         resolve_downet,
    
    # ========== Wecima CDN Resolvers ==========
    "tnmr.org":        resolve_tnmr,
    "tnmr":            resolve_tnmr,
    "mxcontent":       resolve_mxcontent,
    "mxcontent.net":   resolve_mxcontent,
    "delucloud":       resolve_delucloud,
    "delucloud.xyz":   resolve_delucloud,
    "savefiles":       resolve_savefiles,
    "savefiles.com":   resolve_savefiles,
    "abstream":        resolve_abstream,
    "abstream.to":     resolve_abstream,
    "byselapuix":      resolve_byselapuix,
    "byselapuix.com":  resolve_byselapuix,
    "dhcplay":         resolve_dhcplay,
    "dhcplay.com":     resolve_dhcplay,
    "sprintcdn":       resolve_sprintcdn,
    "sprintcdn.com":   resolve_sprintcdn,
    "aurorafieldnetwork": resolve_aurorafieldnetwork,
    "aurorafieldnetwork.store": resolve_aurorafieldnetwork,
    
    # ========== Akwam Redirect Resolvers ==========
    "go.akwam.com.co":  resolve_go_akwam,
    "go.akwam":         resolve_go_akwam,
}


def resolve_generic_embed(url):
    """Generic resolver — m3u8/mp4 scan → packer unpack → iframe follow."""
    try:
        html, final = fetch(url, referer=url)
        if not html:
            return None
        best = _best_media_url(html)
        if best:
            return best
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best
        # Follow one level of iframes
        for iframe_url in extract_iframes(html, final or url)[:3]:
            h2, _ = fetch(iframe_url, referer=url)
            if h2:
                best = _best_media_url(h2)
                if best:
                    return best
    except Exception:
        pass
    return None


# ─── Multi-provider premium resolvers (TMDB-based) ───────────────────────────

def _get_stream_moviesapi(tmdb_id, m_type, season=None, episode=None):
    url = ("https://moviesapi.club/api/v1/movies/{}".format(tmdb_id) if m_type == "movie"
           else "https://moviesapi.club/api/v1/tv/{}/{}/{}".format(tmdb_id, season or 1, episode or 1))
    body, _ = fetch(url, extra_headers={"Accept": "application/json"})
    if not body:
        return None
    try:
        data = json.loads(body)
        for src in (data.get("sources") or []):
            f = src.get("file") or src.get("url") or ""
            if ".m3u8" in f:
                return f
        for src in (data.get("sources") or []):
            f = src.get("file") or src.get("url") or ""
            if f.startswith("http"):
                return f
    except Exception:
        pass
    return find_m3u8(body) or find_mp4(body)


def _get_stream_vidsrc(tmdb_id, m_type, season=None, episode=None):
    url = ("https://vidsrc.me/embed/movie/{}".format(tmdb_id) if m_type == "movie"
           else "https://vidsrc.me/embed/tv/{}/{}/{}".format(tmdb_id, season or 1, episode or 1))
    html, _ = fetch(url, referer="https://vidsrc.me/")
    if not html:
        return None
    m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    if m:
        iframe_url = m.group(1)
        if iframe_url.startswith("//"):
            iframe_url = "https:" + iframe_url
        h2, _ = fetch(iframe_url, referer=url)
        if h2:
            return find_m3u8(h2) or find_mp4(h2)
    return find_m3u8(html) or find_mp4(html)


def _get_stream_autoembed(tmdb_id, m_type, season=None, episode=None):
    url = ("https://autoembed.cc/movie/tmdb-{}".format(tmdb_id) if m_type == "movie"
           else "https://autoembed.cc/tv/tmdb-{}-{}-{}".format(tmdb_id, season or 1, episode or 1))
    html, _ = fetch(url)
    if not html:
        return None
    return find_m3u8(html) or find_mp4(html)


_PREMIUM_METHODS = {
    "moviesapi": _get_stream_moviesapi,
    "vidsrc":    _get_stream_vidsrc,
    "autoembed": _get_stream_autoembed,
}


def get_premium_servers(m_type, tmdb_id, season=None, episode=None):
    suffix = ":{}:{}".format(season, episode) if (season and episode) else ""
    return [
        {"name": "Premium: AutoEmbed 🚀", "url": "autoembed://{}:{}{}".format(m_type, tmdb_id, suffix)},
        {"name": "Premium: VidSrc 🔥",    "url": "vidsrc://{}:{}{}".format(m_type, tmdb_id, suffix)},
    ]


# ─── Main host dispatcher ─────────────────────────────────────────────────────

def resolve_host(url, referer=None):
    """Detect host from domain and dispatch to the right resolver."""
    # Premium protocol shortcuts  (autoembed://, vidsrc://, etc.)
    m = re.match(r'(\w+)://(movie|series|tv|episode):(\d+)(?::(\d+):(\d+))?', url)
    if m:
        method_name, m_type, tmdb_id, season, episode = m.groups()
        m_type = "movie" if m_type in ("movie", "film") else "series"
        if method_name in _PREMIUM_METHODS:
            return _PREMIUM_METHODS[method_name](tmdb_id, m_type, season, episode)
        if method_name == "auto":
            for func in _PREMIUM_METHODS.values():
                try:
                    res = func(tmdb_id, m_type, season, episode)
                    if res:
                        return res
                except Exception:
                    pass
        return None

    domain = urlparse(url).netloc.lower()
    log("resolve_host: domain={} url={}".format(domain, url[:80]))

    # Exact-key match first, then substring scan
    for key, resolver in HOST_RESOLVERS.items():
        if key in domain:
            log("Using resolver: {}".format(key))
            result = resolver(url)
            if result:
                return result
            log("Resolver {} returned nothing, trying generic".format(key))
            break

    log("Generic fallback for: {}".format(domain))
    return resolve_generic_embed(url)


# ─── iframe chain resolver ────────────────────────────────────────────────────

def resolve_iframe_chain(url, referer=None, depth=0, max_depth=8):
    """
    Follow iframes / meta-refresh / JS location redirects recursively.
    Returns (stream_url, domain) or (None, "").
    """
    if depth > max_depth:
        return None, ""

    html, final_url = fetch(url, referer=referer)
    if not html:
        return None, ""

    active_url = final_url or url
    domain = urlparse(active_url).netloc.lower()

    # 1. Direct media URL in page
    stream = find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    if stream:
        return stream, domain

    # 2. Meta-refresh redirect
    m = re.search(
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+\s*;\s*url=([^"\']+)["\']',
        html, re.I
    )
    if m:
        new_url = m.group(1).strip()
        if new_url.startswith("//"):
            new_url = "https:" + new_url
        elif not new_url.startswith("http"):
            new_url = urljoin(active_url, new_url)
        if new_url != active_url:
            return resolve_iframe_chain(new_url, referer=active_url, depth=depth + 1, max_depth=max_depth)

    # 3. JS window.location redirect
    m = re.search(r'(?:window\.location(?:\.href)?\s*=|location\.replace\()\s*["\']([^"\']+)["\']', html, re.I)
    if m:
        new_url = m.group(1).strip()
        if new_url.startswith("//"):
            new_url = "https:" + new_url
        elif not new_url.startswith("http"):
            new_url = urljoin(active_url, new_url)
        if new_url != active_url and "://" in new_url:
            return resolve_iframe_chain(new_url, referer=active_url, depth=depth + 1, max_depth=max_depth)

    # 4. iframes (src, data-src, data-url, data-lazy-src)
    iframe_srcs = re.findall(
        r'<(?:iframe|embed|frame)[^>]+(?:src|data-src|data-url|data-lazy-src)=["\']([^"\']+)["\']',
        html, re.I
    )
    for src in iframe_srcs:
        if src.startswith("//"):
            src = "https:" + src
        elif not src.startswith("http"):
            p = urlparse(active_url)
            if src.startswith("/"):
                src = "{}://{}{}".format(p.scheme, p.netloc, src)
            else:
                continue

        if any(x in src.lower() for x in ("facebook.com", "twitter.com", "googletag", "doubleclick", "analytics")):
            continue

        # Check if this is a known host — resolve directly rather than fetching page
        src_domain = urlparse(src).netloc.lower()
        for key, resolver in HOST_RESOLVERS.items():
            if key in src_domain:
                result = resolver(src)
                if result:
                    return result, src_domain
                break

        res, h = resolve_iframe_chain(src, referer=active_url, depth=depth + 1, max_depth=max_depth)
        if res:
            return res, h

    return None, ""


# ─── Main extract_stream entry point ─────────────────────────────────────────

def extract_stream(url):
    """
    Standard entry point used by all extractors.
    Returns (stream_url, quality_label, referer).
    """
    log("--- extract_stream START: {} ---".format(url))
    raw_url = (url or "").strip()
    if not raw_url:
        return None, "", url

    # Split piped headers (url|Referer=xxx&User-Agent=yyy)
    piped_headers = {}
    main_url = raw_url
    if "|" in raw_url:
        main_url, raw_hdrs = raw_url.split("|", 1)
        for part in raw_hdrs.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                piped_headers[k.strip()] = v.strip()

    lower = main_url.lower()

    # Fast path: already a direct media URL
    if main_url.startswith("http") and any(ext in lower for ext in (".m3u8", ".mp4", ".mkv", ".mp3")):
        ref = piped_headers.get("Referer") or "{}://{}/".format(*urlparse(main_url)[:2])
        
        # Detect quality from filename
        q = "HD"
        if "2160" in lower or "4k" in lower:
            q = "2160p"
        elif "1080" in lower or "fhd" in lower:
            q = "1080p"
        elif "720" in lower or "hd" in lower:
            q = "720p"
        elif "480" in lower:
            q = "480p"
        elif "360" in lower:
            q = "360p"
        
        # Check for index-f2 (720p) or index-f1 (480p)
        if "index-f2" in lower:
            q = "720p"
        elif "index-f1" in lower:
            q = "480p"
        elif "master.m3u8" in lower:
            q = "720p"
            
        log("extract_stream DIRECT: {}".format(main_url))
        return raw_url, q, ref

    _, final_ref = fetch(main_url, referer=piped_headers.get("Referer"))

    stream = resolve_host(main_url, referer=piped_headers.get("Referer"))
    if not stream:
        log("resolve_host failed, trying iframe chain")
        stream, _ = resolve_iframe_chain(main_url, referer=piped_headers.get("Referer"))

    if stream:
        # Detect quality from stream URL
        q = "HD"
        if "1080" in stream or "fhd" in stream:
            q = "1080p"
        elif "720" in stream or "hd" in stream:
            q = "720p"
        elif "480" in stream:
            q = "480p"
        elif "index-f2" in stream:
            q = "720p"
        elif "index-f1" in stream:
            q = "480p"
        log("extract_stream SUCCESS: {}".format(stream[:120]))
        return stream, q, final_ref or main_url

    log("extract_stream FAILED for: {}".format(main_url))
    return None, "", final_ref or main_url
`````

## File: extractors/egydead.py
`````python
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
`````

## File: extractors/fasel.py
`````python
# -*- coding: utf-8 -*-
import sys
import re
import time
import json
from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse, unquote
    from html import unescape as html_unescape
else:
    from urllib import quote_plus
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

# Working domains for FaselHD
DOMAINS = [
    "https://web596x.faselhdx.bid/",
    "https://faselhd.rip/",
    "https://www.fasel-hd.cam/",
]

BLOCKED_MARKERS = ("alliance4creativity", "watch-it-legally", "just a moment", "cf-chl")

_ACTIVE_URL = None
_ACTIVE_BASE_FETCH_TIME = 0


def _get_base():
    global _ACTIVE_URL
    for domain in DOMAINS:
        log("FaselHD: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        if html and not any(m in (html + (final_url or "")).lower() for m in BLOCKED_MARKERS):
            log("FaselHD: using {}".format(domain))
            _ACTIVE_URL = domain.rstrip("/")
            return _ACTIVE_URL
    _ACTIVE_URL = DOMAINS[0].rstrip("/")
    return _ACTIVE_URL


def _base():
    global _ACTIVE_URL, _ACTIVE_BASE_FETCH_TIME
    if not _ACTIVE_URL or (time.time() - _ACTIVE_BASE_FETCH_TIME) > 3600:
        _ACTIVE_URL = _get_base()
        _ACTIVE_BASE_FETCH_TIME = time.time()
    return _ACTIVE_URL


def _normalize_url(url):
    if not url:
        return ""
    url = html_unescape(str(url).strip())
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(_base(), url)
    return url


def _clean_title(title):
    if not title:
        return ""
    title = html_unescape(title)
    title = title.replace("&amp;", "&")
    title = title.replace("فاصل إعلاني", "")
    title = title.replace("FaselHD", "")
    title = re.sub(r'\s*[-|]\s*فاصل\s*إعلاني.*$', '', title)
    title = re.sub(r'\s*[-|]\s*FaselHD.*$', '', title, flags=re.I)
    return title.strip()


def get_categories():
    """Return category list for FaselHD."""
    base = _base()
    
    if "faselhd.rip" in base:
        # Categories for faselhd.rip (different structure)
        return [
            {"title": "🎬 حديث", "url": base + "latest", "type": "category", "_action": "category"},
            {"title": "🎬 افلام", "url": base + "movies", "type": "category", "_action": "category"},
            {"title": "📺 مسلسلات", "url": base + "series", "type": "category", "_action": "category"},
            {"title": "🎌 انمي", "url": base + "anime", "type": "category", "_action": "category"},
        ]
    else:
        # Categories for the modern site structure
        return [
            {"title": "🎬 المضاف حديثا", "url": base + "most_recent", "type": "category", "_action": "category"},
            {"title": "🎬 افلام اجنبي", "url": base + "movies", "type": "category", "_action": "category"},
            {"title": "🎬 افلام مدبلجة", "url": base + "dubbed-movies", "type": "category", "_action": "category"},
            {"title": "🎬 افلام هندي", "url": base + "hindi", "type": "category", "_action": "category"},
            {"title": "🎬 افلام اسيوي", "url": base + "asian-movies", "type": "category", "_action": "category"},
            {"title": "🎬 افلام انمي", "url": base + "anime-movies", "type": "category", "_action": "category"},
            {"title": "📺 مسلسلات اجنبي", "url": base + "series", "type": "category", "_action": "category"},
            {"title": "📺 مسلسلات اسيوي", "url": base + "asian-series", "type": "category", "_action": "category"},
            {"title": "📺 مسلسلات انمي", "url": base + "anime", "type": "category", "_action": "category"},
            {"title": "📡 برامج تلفزيونية", "url": base + "tvshows", "type": "category", "_action": "category"},
            {"title": "⭐ الاعلي تصويتا", "url": base + "movies_top_votes", "type": "category", "_action": "category"},
            {"title": "👁 الاعلي مشاهدة", "url": base + "movies_top_views", "type": "category", "_action": "category"},
            {"title": "🎯 الاعلي تقييما IMDB", "url": base + "movies_top_imdb", "type": "category", "_action": "category"},
        ]


def get_category_items(url):
    """Parse category page for movies/series items."""
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        log("FaselHD: get_category_items failed for {}".format(url))
        return []
    
    items = []
    seen_urls = set()
    
    # Check if this is faselhd.rip domain
    if "faselhd.rip" in base:
        # Pattern for faselhd.rip - card-content structure
        card_pattern = r'<div[^>]*class="[^"]*card-content[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)"[^>]*>.*?<div[^>]*class="[^"]*card-title[^"]*"[^>]*>([^<]+)</div>'
        
        for match in re.finditer(card_pattern, html, re.DOTALL | re.I):
            href = match.group(1)
            img = match.group(2)
            title = _clean_title(match.group(3))
            
            full_url = _normalize_url(href)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            
            # Determine type from URL
            if "/series" in full_url or "/anime" in full_url:
                item_type = "series"
            else:
                item_type = "movie"
            
            items.append({
                "title": title,
                "url": full_url,
                "poster": _normalize_url(img.strip()) if img else "",
                "type": item_type,
                "_action": "details",
            })
    else:
        # Pattern for the modern theme's postDiv structure
        post_pattern = r'<div[^>]*class="[^"]*postDiv[^"]*"[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>.*?<div[^>]*class="[^"]*imgdiv-class[^"]*"[^>]*>.*?<img[^>]+data-src="([^"]+)"[^>]*>.*?<div[^>]*class="[^"]*h1[^"]*"[^>]*>([^<]+)</div>.*?</a>'
        
        alt_pattern = r'<div[^>]*class="[^"]*col-xl-2[^"]*"[^>]*>.*?<div[^>]*class="[^"]*postDiv[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+data-src="([^"]+)"[^>]*>.*?<div[^>]*class="[^"]*h1[^"]*"[^>]*>([^<]+)</div>'
        
        # Try main pattern first
        for pattern in [post_pattern, alt_pattern]:
            for match in re.finditer(pattern, html, re.DOTALL | re.I):
                href = match.group(1)
                img = match.group(2)
                title = _clean_title(match.group(3))
                
                full_url = _normalize_url(href)
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                if "/series" in full_url or "/anime" in full_url or "مسلسل" in title:
                    item_type = "series"
                else:
                    item_type = "movie"
                
                # Extract rating if available
                rating = ""
                rating_match = re.search(r'<span[^>]*class="[^"]*pImdb[^"]*"[^>]*>.*?<i[^>]*class="fa fa-star"[^>]*></i>\s*([0-9.]+)', html[match.start():match.end()+500], re.I)
                if rating_match:
                    rating = rating_match.group(1)
                
                items.append({
                    "title": title,
                    "url": full_url,
                    "poster": _normalize_url(img.strip()) if img else "",
                    "rating": rating,
                    "type": item_type,
                    "_action": "details",
                })
            if items:
                break
    
    # Pagination
    pagination_patterns = [
        r'<a[^>]+class="page-link"[^>]+href="([^"]+)"[^>]*>.*?(?:التالي|&rsaquo;|»)[^<]*</a>',
        r'<a[^>]+href="([^"]+)"[^>]*rel="next"[^>]*>',
        r'<div[^>]*class="[^"]*pagination[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>.*?&rsaquo;.*?</a>',
    ]
    
    next_url = None
    for pattern in pagination_patterns:
        next_match = re.search(pattern, html, re.DOTALL | re.I)
        if next_match:
            next_url = _normalize_url(next_match.group(1))
            if next_url and next_url != url:
                log("FaselHD: Found next page: {}".format(next_url))
                break
    
    if next_url and next_url != url:
        items.append({
            "title": "➡️ Next Page",
            "url": next_url,
            "type": "category",
            "_action": "category",
        })
    
    log("FaselHD: {} -> {} items".format(url, len(items)))
    return items


def search(query, page=1):
    """Search for movies/series using the site's search."""
    base = _base()
    url = base + "?s=" + quote_plus(query)
    if page > 1:
        url += "&page=" + str(page)
    
    html, _ = fetch(url, referer=base)
    if not html:
        return []
    
    items = []
    seen_urls = set()
    
    # Search result patterns
    if "faselhd.rip" in base:
        result_pattern = r'<div[^>]*class="[^"]*card-content[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)"[^>]*>.*?<div[^>]*class="[^"]*card-title[^"]*"[^>]*>([^<]+)</div>'
    else:
        result_pattern = r'<div[^>]*class="[^"]*postDiv[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+data-src="([^"]+)"[^>]*>.*?<div[^>]*class="[^"]*h1[^"]*"[^>]*>([^<]+)</div>'
    
    for match in re.finditer(result_pattern, html, re.DOTALL | re.I):
        href = match.group(1)
        img = match.group(2)
        title = _clean_title(match.group(3))
        
        full_url = _normalize_url(href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        items.append({
            "title": title,
            "url": full_url,
            "poster": _normalize_url(img.strip()) if img else "",
            "type": "movie",
            "_action": "details",
        })
    
    return items


def get_page(url):
    """Fetch and parse a movie/series detail page."""
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        log("FaselHD: get_page failed for {}".format(url))
        return {"title": "Error", "servers": [], "items": [], "type": "movie"}
    
    # Extract title
    title_match = re.search(r'<h1[^>]*class="[^"]*post-title[^"]*"[^>]*>(.*?)</h1>', html, re.I)
    if not title_match:
        title_match = re.search(r'<title>([^<]+)</title>', html, re.I)
    if not title_match:
        title_match = re.search(r'property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    title = _clean_title(title_match.group(1)) if title_match else ""
    
    # Extract poster
    poster_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    if not poster_match:
        poster_match = re.search(r'<img[^>]+class="[^"]*poster[^"]*"[^>]+src="([^"]+)"', html, re.I)
    poster = _normalize_url(poster_match.group(1)) if poster_match else ""
    
    # Extract plot
    plot_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html)
    if not plot_match:
        plot_match = re.search(r'<div[^>]*class="[^"]*summary[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL | re.I)
    plot = _clean_title(plot_match.group(1)) if plot_match else ""
    
    # Extract year
    year_match = re.search(r'سنة الإنتاج[^<]*<a[^>]*>(\d{4})</a>', html, re.I)
    year = year_match.group(1) if year_match else ""
    
    # Extract rating
    rating_match = re.search(r'<span[^>]*class="[^"]*imdb-rating[^"]*"[^>]*>([0-9.]+)</span>', html, re.I)
    if not rating_match:
        rating_match = re.search(r'<i[^>]*class="fa fa-star"[^>]*></i>\s*([0-9.]+)', html, re.I)
    rating = rating_match.group(1) if rating_match else ""
    
    servers = []
    episodes = []
    item_type = "movie"
    
    # Check if it's a series
    if "/series" in url or "مسلسل" in title or "/anime" in url:
        item_type = "series"
        
        # Extract episodes
        if "faselhd.rip" in base:
            ep_pattern = r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*episode-link[^"]*"[^>]*>.*?الحلقة\s*(\d+)'
        else:
            ep_pattern = r'<li[^>]*class="[^"]*playlist-video[^"]*"[^>]*data-postid="[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>.*?الحلقة\s*(\d+)'
        
        for match in re.finditer(ep_pattern, html, re.I):
            ep_url = _normalize_url(match.group(1))
            ep_num = match.group(2)
            episodes.append({
                "title": "الحلقة {}".format(ep_num),
                "url": ep_url,
                "type": "episode",
                "_action": "details",
            })
    
    # Extract server links
    if "faselhd.rip" in base:
        # For faselhd.rip, look for modal-tab buttons or watch button
        server_pattern = r'<button[^>]*class="[^"]*modal-tab[^"]*"[^>]*data-server-url="([^"]+)"[^>]*>.*?سيرفر\s*(\d+)'
        for match in re.finditer(server_pattern, html, re.I):
            server_url = _normalize_url(match.group(1))
            server_num = match.group(2)
            servers.append({
                "name": "🎬 Server {}".format(server_num),
                "url": server_url,
                "type": "embed"
            })
        
        # Also look for the main watch button
        watch_pattern = r'<button[^>]*class="[^"]*btn-watch[^"]*"[^>]*data-server-url="([^"]+)"'
        watch_match = re.search(watch_pattern, html, re.I)
        if watch_match:
            servers.insert(0, {
                "name": "🎬 Main Stream",
                "url": _normalize_url(watch_match.group(1)),
                "type": "embed"
            })
    else:
        # For the modern site, look for iframe player and server tabs
        player_pattern = r'<iframe[^>]+name="player_iframe"[^>]+data-src="([^"]+)"'
        iframe_match = re.search(player_pattern, html, re.I)
        if iframe_match:
            servers.append({
                "name": "🎬 Stream (1080p)",
                "url": iframe_match.group(1),
                "type": "embed"
            })
        
        # Look for alternative server links
        server_tabs = re.findall(r'<li[^>]*onclick="[^"]*player_iframe\.location\.href\s*=\s*\'([^\']+)\'[^"]*"[^>]*>.*?سيرفر المشاهدة #(\d+)', html, re.I)
        for server_url, server_num in server_tabs:
            servers.append({
                "name": "🎬 Server {}".format(server_num),
                "url": _normalize_url(server_url),
                "type": "embed"
            })
        
        # Look for download links
        download_pattern = r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*link-download[^"]*"[^>]*>'
        for match in re.finditer(download_pattern, html, re.I):
            download_url = _normalize_url(match.group(1))
            if download_url not in [s.get("url") for s in servers]:
                servers.append({
                    "name": "📥 Download Link",
                    "url": download_url,
                    "type": "direct"
                })
    
    result = {
        "url": final_url or url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "year": year,
        "rating": rating,
        "servers": servers,
        "items": episodes,
        "type": item_type,
    }
    
    log("FaselHD: {} -> found {} servers, {} episodes".format(url, len(servers), len(episodes)))
    return result


def extract_stream(url):
    """
    Resolve a server URL to a playable stream.
    Handles: scdns.io, govid.live, datahowa.asia
    """
    log("FaselHD extract_stream: {}".format(url[:100]))
    referer = _base()
    
    from .base import resolve_iframe_chain, resolve_host, find_m3u8, find_mp4, fetch
    
    # Check if it's already a direct m3u8 URL
    if '.m3u8' in url:
        q = "HD"
        if "1080" in url or "hd1080" in url:
            q = "1080p"
        elif "720" in url or "hd720" in url:
            q = "720p"
        elif "480" in url:
            q = "480p"
        elif "360" in url or "sd360" in url:
            q = "360p"
        log("FaselHD: Direct m3u8 URL found")
        return url, q, referer
    
    # Check for govid.live (from faselhd.rip)
    if 'govid.live' in url:
        log("FaselHD: Detected govid.live stream")
        # These are already m3u8 URLs, just return them
        if '.m3u8' in url:
            q = "HD"
            if "1080" in url:
                q = "1080p"
            elif "720" in url:
                q = "720p"
            return url, q, referer
        
        # Fetch the page to get the m3u8
        html, _ = fetch(url, referer=referer)
        if html:
            stream = find_m3u8(html) or find_mp4(html)
            if stream:
                q = "HD"
                if "1080" in stream:
                    q = "1080p"
                elif "720" in stream:
                    q = "720p"
                return stream, q, referer
    
    # Check for datahowa.asia (CDN for govid)
    if 'datahowa.asia' in url:
        log("FaselHD: Detected datahowa.asia CDN")
        if '.ts' in url:
            # This is a segment, try to get the base m3u8
            base_m3u8 = re.sub(r'/seg_[0-9]+\.ts.*$', '/playlist.m3u8', url)
            if base_m3u8 != url:
                return extract_stream(base_m3u8)
        return url, "HD", referer
    
    # Try to resolve via host resolver (handles scdns.io)
    stream = resolve_host(url, referer=referer)
    if stream:
        q = "HD"
        if "1080" in stream:
            q = "1080p"
        elif "720" in stream:
            q = "720p"
        log("FaselHD: Resolved stream via host resolver")
        return stream, q, referer
    
    # Fetch the embed page to find the actual stream
    html, final_url = fetch(url, referer=referer)
    if html:
        # Look for scdns.io m3u8 URLs
        stream_patterns = [
            r'(https?://master\.[^\s"\']+\.scdns\.io[^\s"\']+\.m3u8[^\s"\']*)',
            r'(https?://r[0-9]+--[^\s"\']+\.c\.scdns\.io[^\s"\']+\.m3u8[^\s"\']*)',
            r'(https?://[^\s"\']+\.scdns\.io[^\s"\']+\.m3u8[^\s"\']*)',
            r'(https?://[^\s"\']+\.govid\.live[^\s"\']+\.m3u8[^\s"\']*)',
            r'(https?://[^\s"\']+\.datahowa\.asia[^\s"\']+\.m3u8[^\s"\']*)',
        ]
        
        for pattern in stream_patterns:
            matches = re.findall(pattern, html, re.I)
            for stream_url in matches:
                stream_url = stream_url.replace('\\/', '/').replace('&amp;', '&')
                q = "HD"
                if "1080" in stream_url or "hd1080" in stream_url:
                    q = "1080p"
                elif "720" in stream_url or "hd720" in stream_url:
                    q = "720p"
                log("FaselHD: Found stream: {}".format(stream_url[:100]))
                return stream_url, q, referer
        
        # Look for video source
        direct = find_m3u8(html) or find_mp4(html)
        if direct:
            q = "HD" if "720" in direct else ("FHD" if "1080" in direct else "Auto")
            return direct, q, referer
    
    # Try iframe chain resolution
    stream, domain = resolve_iframe_chain(url, referer=referer, max_depth=5)
    if stream:
        q = "HD"
        if "1080" in stream:
            q = "1080p"
        elif "720" in stream:
            q = "720p"
        return stream, q, referer
    
    log("FaselHD: Could not extract stream for {}".format(url[:100]))
    return None, "", referer
`````

## File: extractors/shaheed.py
`````python
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


def _is_valid_site_url(url):
    host = _host(url)
    if not host:
        return False
    if any(m in host for m in BLOCKED_HOST_MARKERS):
        return False
    return any(m in host for m in VALID_HOST_MARKERS)


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
    """Fetch with proper headers and error handling"""
    ref = referer or _get_base()
    h, final_url = fetch(url, referer=ref)
    if _is_blocked_page(h, final_url):
        return "", ""
    return h, final_url or url


def get_categories():
    """Return category list for Shaheed4u"""
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
    """Parse category page with movie/show cards"""
    html, _ = _fetch_live(url)
    if not html:
        return []
    
    items = []
    seen_urls = set()
    
    # Find all show-card elements (works for both /film/ and /post/ URLs)
    card_pattern = r'<a\s+href="([^"]+)"\s+class="show-card"[^>]*style="background-image:\s*url\(([^)]+)\)"[^>]*>(.*?)</a>'
    
    for match in re.finditer(card_pattern, html, re.DOTALL | re.I):
        url_path = match.group(1)
        poster_url = match.group(2).strip()
        card_content = match.group(3)
        
        full_url = _normalize_url(url_path)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        
        # Extract title from <p class="title">
        title_match = re.search(r'<p\s+class="title">([^<]+)</p>', card_content)
        title = html_unescape(title_match.group(1).strip()) if title_match else ""
        
        if not title:
            title_match = re.search(r'title="([^"]+)"', card_content)
            title = html_unescape(title_match.group(1).strip()) if title_match else ""
        
        # Extract category
        categ_match = re.search(r'<span\s+class="categ">([^<]+)</span>', card_content)
        category = categ_match.group(1).strip() if categ_match else ""
        
        # Extract quality sticker
        quality_match = re.search(r'<span\s+class="sticker"[^>]*>([^<]+)</span>', card_content)
        quality = quality_match.group(1).strip() if quality_match else ""
        
        # Determine type
        if "مسلسلات" in category or "عروض" in category or "/category/مسلسلات" in url or "/category/عروض" in url:
            item_type = "series"
        else:
            item_type = "movie"
        
        if title:
            display_title = f"{title} [{quality}]" if quality else title
            items.append({
                "title": display_title,
                "url": full_url,
                "poster": _normalize_url(poster_url),
                "plot": category,
                "type": item_type,
                "_action": "details",
            })
    
    # Check for pagination
    pagination_pattern = r'<button[^>]+onclick="updateQuery\(\'page\',\s*(\d+)\)"[^>]*>(\d+)</button>'
    current_page = None
    max_page = None
    
    for match in re.finditer(pagination_pattern, html):
        page_num = int(match.group(2))
        if match.group(1) == str(page_num):
            current_page = page_num
        if page_num > (max_page or 0):
            max_page = page_num
    
    # Add next page button
    if current_page and max_page and current_page < max_page:
        if '?' in url:
            next_url = url + "&page=" + str(current_page + 1)
        else:
            next_url = url + "?page=" + str(current_page + 1)
        items.append({
            "title": "➡️ Next Page",
            "url": next_url,
            "type": "category",
            "_action": "category",
        })
    
    log("Shaheed: {} -> {} items".format(url, len(items)))
    return items


def search(query, page=1):
    """Search for movies/series"""
    base = _get_base()
    url = base + "/search?s=" + quote_plus(query)
    if page > 1:
        url += "&page=" + str(page)
    
    html, _ = _fetch_live(url)
    if not html:
        return []
    
    return get_category_items(url)


def get_page(url):
    """
    Fetch and parse a movie/series/show detail/watch page.
    Extracts servers from the JavaScript servers array.
    Works for /film/, /post/, and /watch/ URLs.
    """
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
    
    # Extract title
    title_match = re.search(r'<title>(.*?)</title>', html)
    if title_match:
        title = html_unescape(title_match.group(1))
        title = re.sub(r'\s*[-|]\s*شاهد\s*فور\s*يو.*$', '', title)
        title = re.sub(r'\s*[-|]\s*Shahid4u.*$', '', title, re.I)
        result["title"] = title.strip()
    
    # Extract description
    desc_match = re.search(r'<meta\s+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if desc_match:
        result["plot"] = html_unescape(desc_match.group(1))
    
    # Extract poster from og:image or meta
    poster_match = re.search(r'<meta\s+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if poster_match:
        result["poster"] = _normalize_url(poster_match.group(1))
    
    # ===== CRITICAL: Extract servers from JavaScript array =====
    # Pattern: let servers = JSON.parse('[...]');
    servers_pattern = r'let\s+servers\s*=\s*JSON\.parse\(\'([^\']+)\'\)'
    
    match = re.search(servers_pattern, html)
    if match:
        try:
            servers_json = match.group(1)
            # Fix escaped characters
            servers_json = servers_json.replace('\\"', '"')
            servers_data = json.loads(servers_json)
            
            for server in servers_data:
                if server.get("url"):
                    server_url = server["url"]
                    server_name = server.get("name", "Server")
                    result["servers"].append({
                        "name": server_name,
                        "url": server_url,
                        "type": "embed"
                    })
            log("Shaheed: extracted {} servers from JSON".format(len(result["servers"])))
        except Exception as e:
            log("Shaheed: failed to parse servers JSON: {}".format(e))
    
    # Alternative pattern: standalone servers array
    if not result["servers"]:
        alt_pattern = r'servers\s*=\s*(\[.*?\])'
        match = re.search(alt_pattern, html, re.DOTALL)
        if match:
            try:
                servers_data = json.loads(match.group(1))
                for server in servers_data:
                    if server.get("url"):
                        result["servers"].append({
                            "name": server.get("name", "Server"),
                            "url": server["url"],
                            "type": "embed"
                        })
                log("Shaheed: extracted {} servers from alt JSON".format(len(result["servers"])))
            except Exception as e:
                log("Shaheed: failed to parse alt servers JSON: {}".format(e))
    
    # Fallback: look for iframe embeds (like fastvid.cam)
    if not result["servers"]:
        iframe_pattern = r'<iframe[^>]+src=["\']([^"\']+)["\']'
        skip_domains = ['youtube', 'facebook', 'twitter', 'google', 'doubleclick', 
                       'analytics', 'googletagmanager', 'google-analytics', 
                       'cloudflareinsights', 'adsco.re', 'intelligenceadx']
        
        for iframe_match in re.finditer(iframe_pattern, html, re.I):
            iframe_url = iframe_match.group(1)
            
            # Skip obvious ad/tracking domains
            if any(x in iframe_url.lower() for x in skip_domains):
                continue
            
            # Make absolute URL if needed
            if iframe_url.startswith("//"):
                iframe_url = "https:" + iframe_url
            elif iframe_url.startswith("/"):
                p = urlparse(final_url or url)
                iframe_url = "{}://{}{}".format(p.scheme, p.netloc, iframe_url)
            
            # Check if it's a video embed domain
            embed_domains = ['fastvid.cam', 'streamtape', 'doodstream', 'voe', 
                            'filemoon', 'rpmvip', 'upn.one', 'cleantechworld']
            if any(d in iframe_url.lower() for d in embed_domains):
                result["servers"].append({
                    "name": "Embed Player",
                    "url": iframe_url,
                    "type": "iframe"
                })
    
    # Also look for direct links to m3u8 in the page
    if not result["servers"]:
        direct_patterns = [
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'"(https?://[^"]+\.m3u8[^"]+)"',
        ]
        for pattern in direct_patterns:
            matches = re.findall(pattern, html, re.I)
            for m in matches:
                if 'fastvid.cam' in m or 'rpmvip' in m or 'upn.one' in m:
                    result["servers"].append({
                        "name": "Direct Stream",
                        "url": m,
                        "type": "direct"
                    })
    
    # Determine type from URL and content
    if "/مسلسلات" in url or "series" in url.lower() or "/عروض" in url:
        result["type"] = "series"
    elif "/post/" in url:
        result["type"] = "series"
    
    log("Shaheed: {} -> found {} servers".format(url, len(result["servers"])))
    return result


def extract_stream(url):
    """Resolve a server URL to a playable stream"""
    log("Shaheed extract_stream: {}".format(url))
    
    referer = _get_base()
    if "|" in url:
        parts = url.split("|", 1)
        url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()
    
    from .base import resolve_iframe_chain, resolve_host
    
    # Try iframe chain first
    stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=10)
    if stream:
        return stream, None, referer
    
    # Try host resolver
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
`````

## File: extractors/topcinema.py
`````python
# -*- coding: utf-8 -*-
import sys
import re
from .base import fetch, urljoin, log, resolve_iframe_chain

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse, urlunparse, quote, urlencode
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, quote, urlencode
    from urlparse import urlparse, urlunparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

DOMAINS = ["https://topcinemaa.com"]
MAIN_URL = DOMAINS[0]

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
    return [
        {"title": "🎬 المضاف حديثا", "url": MAIN_URL + "/recent/", "type": "category", "_action": "category"},
        {"title": "🎬 أفلام أجنبية", "url": MAIN_URL + "/category/%D8%A7%D9%81%D9%84%D8%A7%D9%85-%D8%A7%D8%AC%D9%86%D8%A8%D9%8A-8/", "type": "category", "_action": "category"},
        {"title": "🎬 أفلام أنمي", "url": MAIN_URL + "/category/%D8%A7%D9%81%D9%84%D8%A7%D9%85-%D8%A7%D9%86%D9%85%D9%8A-2/", "type": "category", "_action": "category"},
        {"title": "🎬 أفلام أسيوية", "url": MAIN_URL + "/category/%D8%A7%D9%81%D9%84%D8%A7%D9%85-%D8%A7%D8%B3%D9%8A%D9%88%D9%8A/", "type": "category", "_action": "category"},
        {"title": "🎬 أفلام نتفليكس", "url": MAIN_URL + "/netflix-movies/", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أجنبية", "url": MAIN_URL + "/category/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%A7%D8%AC%D9%86%D8%A8%D9%8A/", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أسيوية", "url": MAIN_URL + "/category/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%A7%D8%B3%D9%8A%D9%88%D9%8A%D8%A9/", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أنمي", "url": MAIN_URL + "/category/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%A7%D9%86%D9%85%D9%8A/", "type": "category", "_action": "category"},
    ]

def _extract_blocks(html):
    items = []
    # Match any <a> that has a class with 'block' and contains an <img> with src/data-src
    # Using a more permissive regex that doesn't strictly depend on attribute order
    blocks = re.findall(r'(<a[^>]+href=["\'][^"\']+["\'][^>]*title=["\'][^"\']+["\'][^>]*class=["\'][^"\']*block[^"\']*["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\']([^"\']+)["\'][^>]*>)', html, re.DOTALL | re.IGNORECASE)
    
    if not blocks:
        # Final fallback for older pattern
        blocks = re.findall(r'(<a[^>]+href=["\'][^"\']+["\'][^>]*title=["\'][^"\']+["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\']([^"\']+)["\'][^>]*>)', html, re.DOTALL | re.IGNORECASE)

    for block_html, img in blocks:
        link_m = re.search(r'href=["\']([^"\']+)["\']', block_html)
        title_m = re.search(r'title=["\']([^"\']+)["\']', block_html)
        
        if link_m and title_m:
            link = _normalize_url(link_m.group(1))
            title = _clean_title(title_m.group(1))
            if not img or img.strip() in ("", "http:", "https:"):
                for _ipat in [
                    r'data-lazy=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)["\']',
                    r'data-original=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)["\']',
                    r'data-bg=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)["\']',
                    r'background(?:-image)?:\s*url\(["\']?([^"\')\s]+)',
                ]:
                    _im = re.search(_ipat, block_html, re.I)
                    if _im:
                        img = _im.group(1).strip("'\" ")
                        break
            img = _normalize_url(img)

            item_type = "movie"
            if "مسلسل" in title or "حلقة" in title or "انمي" in title:
                item_type = "series"

            items.append({
                "title": title,
                "url": link,
                "poster": img,
                "type": item_type,
                "_action": "details"
            })
    return items

def get_category_items(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        log("TopCinema: fetch returned no content for {}".format(url))
        return []
    items = _extract_blocks(html)

    # Next page pagination
    next_page_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*class=["\']next page-numbers["\']', html)
    if next_page_match:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": _normalize_url(next_page_match.group(1)),
            "type": "category",
            "_action": "category"
        })
        
    return items

def search(query, page=1):
    items = []
    url = MAIN_URL + "/search/?query=" + quote_plus(query) + "&type=all"
    html, final_url = fetch(url, referer=MAIN_URL)
    items = _extract_blocks(html)
    return items

def get_page(url):
    html, final_url = fetch(url, referer=MAIN_URL)

    title_m = re.search(r'<title>(.*?)</title>', html, re.I | re.S)
    title = _clean_title(title_m.group(1)) if title_m else "Unknown Title"

    poster_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    poster = _normalize_url(poster_m.group(1)) if poster_m else ""

    plot_m = re.search(r'class=["\']description["\'][^>]*>(.*?)</', html, re.S | re.I)
    plot = _clean_title(re.sub(r'<[^>]+>', '', plot_m.group(1))) if plot_m else ""

    servers = []
    episodes = []
    item_type = "movie"

    watch_page_html = html or ""
    movie_url = final_url
    watch_url = ""

    watch_url_m = re.search(
        r'<a[^>]+class=["\'][^"\']*watch[^"\']*["\'][^>]+href=["\']([^"\']+/watch/?)[\"\']',
        html,
        re.I
    )
    if watch_url_m:
        watch_url = _normalize_url(watch_url_m.group(1))
        watch_page_html, _ = fetch(watch_url, referer=final_url)
        watch_page_html = watch_page_html or ""
        final_url = watch_url

    post_id = ""
    for pat in [
        r'data-id=["\'](\d+)["\']',
        r'\?p=(\d+)',
        r'postid["\']?\s*[:=]\s*["\']?(\d+)["\']?',
        r'post_id["\']?\s*[:=]\s*["\']?(\d+)["\']?'
    ]:
        m = re.search(pat, watch_page_html, re.I)
        if m:
            post_id = m.group(1)
            break

    def _server_name_ok(name):
        if not name:
            return False
        n = _clean_title(name).strip()
        if not n:
            return False
        bad_exact = [u"صالة العرض", u"صالة", u"Gallery", u"السيرفرات", u"مشاهدة", u"watch"]
        if n in bad_exact:
            return False
        # reject section titles / headings
        low = n.lower()
        for bad in ["gallery", "watch servers", "servers"]:
            if low == bad:
                return False
        return True

    server_candidates = []

    # 1) الشكل الصحيح: لازم نمسك الـ li كامل لأن data-id/data-server بيبقوا على العنصر نفسه
    old_matches = re.findall(
        r'<li[^>]*class=["\'][^"\']*server--item[^"\']*["\'][^>]*data-id=["\'](\d+)["\'][^>]*data-server=["\'](\d+)["\'][^>]*>(.*?)</li>',
        watch_page_html,
        re.I | re.S
    )
    for pid, idx, inner in old_matches:
        name = re.sub(r'<[^>]+>', ' ', inner)
        name = _clean_title(re.sub(r'\s+', ' ', name)).strip()
        if _server_name_ok(name):
            server_candidates.append((pid, idx, name))

    # 2) fallback: data-server موجود على أي عنصر
    if not server_candidates:
        generic_matches = re.findall(
            r'<(?:li|a|button|div)[^>]*data-id=["\'](\d+)["\'][^>]*data-server=["\'](\d+)["\'][^>]*>(.*?)</(?:li|a|button|div)>',
            watch_page_html,
            re.I | re.S
        )
        for pid, idx, inner in generic_matches:
            name = re.sub(r'<[^>]+>', ' ', inner)
            name = _clean_title(re.sub(r'\s+', ' ', name)).strip()
            if _server_name_ok(name):
                server_candidates.append((pid, idx, name))

    # 3) fallback بالأسماء المعروفة فقط
    if not server_candidates and post_id:
        visible_servers = [
            "متعدد الجودات",
            "UpDown",
            "StreamWish",
            "Doodstream",
            "Filelions",
            "Streamtape",
            "LuluStream",
            "Filemoon",
            "Mixdrop",
            "VidGuard",
            "Okru"
        ]
        found_names = []
        for srv in visible_servers:
            if re.search(re.escape(srv), watch_page_html, re.I):
                found_names.append(srv)
        for i, srv_name in enumerate(found_names, 1):
            server_candidates.append((post_id, str(i), srv_name))

    log("TopCinema FIX: post_id={} servers_found={}".format(post_id, repr(server_candidates[:10])))

    seen = set()
    ajax_endpoint = MAIN_URL + "/wp-content/themes/movies2023/Ajaxat/Single/Server.php"

    for pid, idx, name in server_candidates:
        if not pid or not idx:
            continue
        clean_name = _clean_title(name or "").strip()
        if not _server_name_ok(clean_name):
            continue
        key = (pid, idx)
        if key in seen:
            continue
        seen.add(key)

        s_url = "topcinema_server|{}|{}|{}|{}".format(
            ajax_endpoint, pid, idx, watch_url or movie_url
        )
        servers.append({
            "name": "توب سينما " + clean_name,
            "url": s_url,
        })

    # حلقات: شغّلها فقط لو واضح إنه مسلسل، عشان الفيلم ما يتحسبش item واحد بالغلط
    is_series_like = (
        ("مسلسل" in title) or
        ("الحلقة" in watch_page_html) or
        ("episodes" in watch_page_html.lower()) or
        ("season" in watch_page_html.lower())
    )

    if is_series_like:
        episodes_patterns = [
            r'<div[^>]+class=[\"\'][^\"]*(?:episodes|series-episodes|season-episodes|ep_list|episodes-list|series-list|all-episodes)[^\"]*[\"\'][^>]*>(.*?)</div>',
            r'<ul[^>]*class=[\"\'][^\"]*(?:episodes|series-episodes|list-episodes|ep_list)[^\"]*[\"\'][^>]*>(.*?)</ul>',
            r'<section[^>]*class=[\"\'][^\"]*(?:episodes|series)[^\"]*[\"\'][^>]*>(.*?)</section>',
            r'<div[^>]+id=[\"\'][^\"]*(?:episodes|episodes-list|episodes-all)[^\"]*[\"\'][^>]*>(.*?)</div>'
        ]

        eps_html = ""
        for pat in episodes_patterns:
            matches = re.findall(pat, watch_page_html, re.S | re.I)
            if matches:
                eps_html = "".join(matches)
                break

        if not eps_html:
            eps_html = watch_page_html

        eps_matches = re.findall(
            r'<a[^>]+href=["\']([^"\']+/(?:watch|episode)[^"\']*)["\'][^>]*>(.*?)</a>',
            eps_html,
            re.DOTALL | re.I
        )
        seen_eps = set()
        for e_link, e_inner in eps_matches:
            full_link = _normalize_url(e_link)
            if not full_link or full_link == watch_url:
                continue
            if full_link in seen_eps:
                continue
            seen_eps.add(full_link)

            e_text = re.sub(r'<[^>]+>', '', e_inner).strip()
            e_num_m = re.search(r'الحلقة\s*(\d+)', e_text)
            if not e_num_m:
                e_num_m = re.search(r'(\d+)', e_text)

            e_num = e_num_m.group(1).strip() if e_num_m else (e_text[:30] if e_text else "Episode")
            episodes.append({
                "title": "حلقة " + e_num if e_num.isdigit() else e_num,
                "url": full_link,
                "type": "episode",
                "_action": "item"
            })

    if episodes:
        item_type = "series"

    return {
        "url": final_url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "servers": servers,
        "items": episodes,
        "type": item_type
    }

def extract_stream(url):
    log("TopCinema: resolving {}".format(url))
    if url.startswith("topcinema_server|"):
        parts = url.split("|")
        ajax_url = parts[1]
        post_id = parts[2]
        server_index = parts[3]
        referer_url = parts[4] if len(parts) > 4 else MAIN_URL
        
        postdata = {
            "id": post_id,
            "i": server_index
        }
        
        html, _ = fetch(ajax_url, referer=referer_url, extra_headers={"X-Requested-With": "XMLHttpRequest"}, post_data=postdata)
        
        v_url = ""
        ifr_m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
        if ifr_m:
            v_url = _normalize_url(ifr_m.group(1))
            log("TopCinema: Found iframe '{}'".format(v_url))
            resolved = resolve_iframe_chain(v_url, referer=MAIN_URL)
            if resolved:
                if isinstance(resolved, tuple):
                    return resolved[0], None, (resolved[1] if len(resolved)>1 and resolved[1] else MAIN_URL)
                return resolved, None, MAIN_URL
            return v_url, None, MAIN_URL
            
    return url, None, MAIN_URL
`````

## File: extractors/wecima.py
`````python
# -*- coding: utf-8 -*-
import re
import sys
import base64
import json

from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse
    from html import unescape as html_unescape
else:
    from urllib import quote_plus
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

# Updated domain list - wecima.cx is the current active domain
DOMAINS = [
    "https://wecima.cx/",
    "https://wecima.click/",
    "https://wecima.show/",
    "https://wecima.video/",
    "https://wecima.rent/",
    "https://wecima.date/",
    "https://www.wecima.site/",
]
VALID_HOST_MARKERS = (
    "wecima.cx", "wecima.click", "wecima.show", "wecima.video",
    "wecima.rent", "wecima.date", "wecima.site",
)
BLOCKED_HOST_MARKERS = ("alliance4creativity.com",)
MAIN_URL = None
_HOME_HTML = None

_CATEGORY_FALLBACKS = {
    "افلام اجنبي":    "/category/foreign-movies",
    "افلام عربي":     "/category/arabic-movies",
    "مسلسلات اجنبي":  "/category/foreign-series",
    "مسلسلات عربية":  "/category/arabic-series",
    "مسلسلات انمي":   "/category/anime-series",
    "تريندج":         "/trends",
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
    if any(m in host for m in BLOCKED_HOST_MARKERS):
        return False
    return any(m in host for m in VALID_HOST_MARKERS)


def _is_blocked_page(html, final_url=""):
    text = (html or "").lower()
    final = (final_url or "").lower()
    if not text:
        return True
    if "just a moment" in text and ("cf-chl" in text or "challenge" in text):
        return True
    if "enable javascript and cookies to continue" in text:
        return True
    if "watch it legally" in text or "alliance for creativity" in text:
        return True
    if any(m in final for m in BLOCKED_HOST_MARKERS):
        return True
    return False


def _looks_like_wecima_page(html):
    text = html or ""
    return (
        "Grid--WecimaPosts" in text
        or "NavigationMenu" in text
        or "Thumb--GridItem" in text
        or "GridItem" in text
        or "WECIMA" in text
        or "وى سيما" in text
        or "wecima" in text.lower()
    )


def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)


def _get_base():
    global MAIN_URL, _HOME_HTML
    if MAIN_URL:
        return MAIN_URL
    for domain in DOMAINS:
        log("Wecima: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked {}".format(final_url))
            continue
        if html and _looks_like_wecima_page(html):
            MAIN_URL = _site_root(final_url)
            _HOME_HTML = html
            log("Wecima: selected base {}".format(MAIN_URL))
            return MAIN_URL
    MAIN_URL = DOMAINS[0]
    log("Wecima: fallback base {}".format(MAIN_URL))
    return MAIN_URL


def _search_url():
    return _get_base().rstrip("/") + "/?s="


def _normalize_url(url):
    if not url:
        return ""
    url = url.strip()
    try:
        url = url.encode("utf-8").decode("unicode_escape") if "\\u" in url else url
    except Exception:
        pass
    url = url.replace("\\u0026", "&").replace("&amp;", "&").replace("\\/", "/")
    url = html_unescape(url)
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(_get_base(), url)
    if any(m in _host(url) for m in BLOCKED_HOST_MARKERS):
        return ""
    if _is_valid_site_url(url):
        base_parts = urlparse(_get_base())
        parts = urlparse(url)
        if parts.netloc != base_parts.netloc and any(m in parts.netloc for m in VALID_HOST_MARKERS):
            clean = "{}://{}{}".format(base_parts.scheme, base_parts.netloc, parts.path or "/")
            if parts.query:
                clean += "?" + parts.query
            return clean
    return url


def _candidate_urls(url):
    normalized = _normalize_url(url)
    if not normalized:
        return []
    parts = urlparse(normalized)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    urls = []
    seen = set()
    seeds = []
    if MAIN_URL:
        seeds.append(MAIN_URL)
    seeds.extend(DOMAINS)
    if normalized.startswith("http"):
        seeds.insert(0, _site_root(normalized))
    for domain in seeds:
        if not domain:
            continue
        base = domain if domain.endswith("/") else domain + "/"
        candidate = urljoin(base, path.lstrip("/"))
        if candidate in seen:
            continue
        seen.add(candidate)
        urls.append(candidate)
    if normalized not in seen:
        urls.insert(0, normalized)
    return urls


def _fetch_live(url, referer=None):
    for candidate in _candidate_urls(url):
        log("Wecima: fetching {}".format(candidate))
        html, final_url = fetch(candidate, referer=referer or _get_base())
        final_url = final_url or candidate
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked {}".format(final_url))
            continue
        if html and _looks_like_wecima_page(html):
            log("Wecima: success {}".format(final_url))
            return html, final_url
        if html:
            log("Wecima: page shape mismatch {}".format(final_url))
    log("Wecima: fetch failed for {}".format(url))
    return "", ""


def _clean_html(text):
    text = html_unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title):
    title = _clean_html(title)
    for token in (
        "مشاهدة فيلم", "مشاهدة مسلسل", "مشاهدة",
        "فيلم", "مسلسل", "اون لاين", "أون لاين",
        "مترجم", "مترجمة", "مدبلج", "مدبلجة",
    ):
        title = title.replace(token, "")
    return re.sub(r"\s+", " ", title).strip(" -|")


def _home_html():
    global _HOME_HTML
    if _HOME_HTML:
        return _HOME_HTML
    base = _get_base()
    html, final_url = _fetch_live(base, referer=base)
    _HOME_HTML = html if not _is_blocked_page(html, final_url) else ""
    return _HOME_HTML


def _guess_type(title, url):
    text = "{} {}".format(title or "", url or "").lower()
    if any(t in text for t in ("/episode/", "الحلقة", "حلقة", "/season/")):
        return "episode"
    if any(t in text for t in ("/series", "/seriestv", "مسلسل", "series-", "/season/")):
        return "series"
    return "movie"


def _grid_blocks(html):
    blocks = []
    for block in re.split(r'(?=<div[^>]+class="GridItem")', html or "", flags=re.I):
        if 'class="GridItem"' not in block:
            continue
        end_match = re.search(
            r'<ul[^>]+class="PostItemStats"[^>]*>.*?</ul>\s*</div>',
            block, re.S | re.I,
        )
        if end_match:
            blocks.append(block[: end_match.end()])
        else:
            blocks.append(block[:3000])
    return blocks


def _extract_cards(html):
    cards = []
    seen = set()
    
    for block in _grid_blocks(html):
        href_match = re.search(r'<a[^>]+href="([^"]+)"', block, re.I)
        if not href_match:
            continue
        url = _normalize_url(href_match.group(1))
        if not url or url in seen:
            continue
        
        lowered = url.lower()
        if any(t in lowered for t in ("/category/", "/tag/", "/page/", "/filtering", "/feed/", "/trends")):
            continue
        
        title_match = (
            re.search(r'<h2[^>]+class="hasyear"[^>]*itemprop="name"[^>]*>(.*?)</h2>', block, re.S | re.I) or
            re.search(r'<h2[^>]+class="hasyear"[^>]*>(.*?)</h2>', block, re.S | re.I) or
            re.search(r'title="([^"]+)"', block, re.I)
        )
        title = _clean_title(title_match.group(1) if title_match else "")
        if not title:
            continue
        
        year = ""
        year_match = re.search(r'<span[^>]+class="year"[^>]*>\(?\s*(\d{4})\s*\)?</span>', block, re.I)
        if year_match:
            year = year_match.group(1)
        
        poster = ""
        poster_match = re.search(r'data-src="([^"]+)"', block, re.I)
        if poster_match:
            poster = poster_match.group(1)
        if not poster:
            poster_match = re.search(r'data-lazy-style="[^"]*url\(([^)]+)\)"', block, re.I)
            if poster_match:
                poster = poster_match.group(1).strip("'\" ")
        if not poster:
            poster_match = re.search(r'style="[^"]*--image:url\(([^)]+)\)', block, re.I)
            if poster_match:
                poster = poster_match.group(1).strip("'\" ")
        
        seen.add(url)
        cards.append({
            "title": title,
            "url": url,
            "poster": _normalize_url(poster) if poster else "",
            "plot": year,
            "type": _guess_type(title, url),
            "_action": "details",
        })
    
    log("Wecima: extracted {} cards".format(len(cards)))
    return cards


def _extract_next_page(html):
    patterns = [
        r'<a[^>]+class="[^"]*next[^"]*page-numbers[^"]*"[^>]+href="([^"]+)"',
        r'<a[^>]+rel="next"[^>]+href="([^"]+)"',
        r'<a[^>]+href="([^"]+)"[^>]*>»</a>',
    ]
    for pat in patterns:
        m = re.search(pat, html or "", re.I)
        if m:
            return _normalize_url(m.group(1))
    return ""


def _category_from_home(label, fallback):
    html = _home_html()
    for pattern in (
        r'<a[^>]+href="([^"]+)"[^>]*>\s*' + re.escape(label) + r'\s*</a>',
        r'<a[^>]+href="([^"]+)"[^>]*>\s*<span[^>]*>\s*' + re.escape(label) + r'\s*</span>',
    ):
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            url = _normalize_url(m.group(1))
            if url:
                return url
    return _normalize_url(urljoin(_get_base(), fallback))


def _decode_b64(data):
    """
    Decode base64 string correctly.
    The plus signs (+) are valid base64 characters and should be preserved.
    """
    try:
        # Clean the string - remove whitespace
        data = data.strip()
        
        # Fix URL-safe base64 (replace - with +, _ with /)
        # But preserve existing plus signs (they are correct)
        if '-' in data or '_' in data:
            data = data.replace('-', '+').replace('_', '/')
        
        # Ensure correct padding
        padding = 4 - (len(data) % 4)
        if padding != 4 and padding > 0:
            data += "=" * padding
        
        # Decode bytes
        decoded_bytes = base64.b64decode(data)
        
        # Convert to string - try UTF-8 first, fallback to latin-1
        try:
            result = decoded_bytes.decode('utf-8')
        except UnicodeDecodeError:
            result = decoded_bytes.decode('latin-1')
        
        # Clean up the decoded URL
        result = result.replace("\\/", "/").replace("&amp;", "&").replace("\\u0026", "&")
        
        # Remove any non-printable control characters
        result = ''.join(c for c in result if c.isprintable() or c in '/:.-_?=&%')
        
        return result
    except Exception as e:
        log("Wecima: base64 decode error: {}".format(e))
        return None


def _extract_servers(html):
    servers = []
    seen = set()
    
    # Method 1: btn elements with data-url (current wecima format)
    btn_pattern = r'<btn[^>]+data-url="([^"]+)"[^>]*>'
    for match in re.finditer(btn_pattern, html or "", re.I):
        encoded_url = match.group(1).strip()
        if not encoded_url:
            continue
        
        decoded_url = _decode_b64(encoded_url)
        if not decoded_url:
            continue
        
        # Fix protocol if needed
        if decoded_url.startswith("//"):
            decoded_url = "https:" + decoded_url
        elif not decoded_url.startswith("http") and '://' not in decoded_url:
            # Check if it looks like a domain with path
            if '.' in decoded_url and '/' in decoded_url:
                decoded_url = "https://" + decoded_url
            else:
                continue
        
        # Extract server name
        server_name = "Server"
        name_match = re.search(r'<strong>(.*?)</strong>', match.group(0), re.S | re.I)
        if name_match:
            server_name = name_match.group(1).strip()
        
        # Validate URL has proper scheme
        if decoded_url and decoded_url not in seen and ('http://' in decoded_url or 'https://' in decoded_url):
            seen.add(decoded_url)
            servers.append({"name": server_name, "url": decoded_url, "type": "direct"})
            log("Wecima: added server {}: {}".format(server_name, decoded_url[:80]))
    
    if servers:
        log("Wecima: extracted {} servers from btn elements".format(len(servers)))
        return servers
    
    # Method 2: Download links with data-href
    download_pattern = r'<li[^>]+class="download-item[^"]*"[^>]*data-href="([^"]+)"'
    for match in re.finditer(download_pattern, html or "", re.I):
        encoded_url = match.group(1).strip()
        decoded_url = _decode_b64(encoded_url)
        if decoded_url and decoded_url not in seen:
            if not decoded_url.startswith("http"):
                decoded_url = "https://" + decoded_url
            seen.add(decoded_url)
            servers.append({"name": "Download", "url": decoded_url, "type": "direct"})
            log("Wecima: added download: {}".format(decoded_url[:80]))
    
    # Method 3: Look for iframe embeds
    if not servers:
        iframe_pattern = r'<iframe[^>]+src="([^"]+)"[^>]*>'
        for match in re.finditer(iframe_pattern, html or "", re.I):
            iframe_url = match.group(1)
            if iframe_url and iframe_url not in seen:
                # Skip known non-video domains
                skip_domains = ['youtube', 'google', 'facebook', 'twitter', 'instagram', 'doubleclick', 'googletag']
                if iframe_url.startswith("blob:"):
                    continue
                if not any(d in iframe_url.lower() for d in skip_domains):
                    iframe_url = _normalize_url(iframe_url)
                    if iframe_url and 'http' in iframe_url:
                        seen.add(iframe_url)
                        servers.append({"name": "Embed Player", "url": iframe_url, "type": "direct"})
                        log("Wecima: added iframe embed: {}".format(iframe_url[:80]))
    
    if not servers:
        log("Wecima: WARNING - no servers found in page")
        # Debug: log a few btn elements
        btn_snippet = re.findall(r'<btn[^>]+data-url="[^"]+"', html or "")
        if btn_snippet:
            log("Wecima: Found btn elements: {}".format(btn_snippet[:2]))
    
    return servers


def _extract_episode_cards(html):
    episodes = []
    seen = set()
    for card in _extract_cards(html):
        title = card.get("title") or ""
        url = card.get("url") or ""
        if "الحلقة" not in title and "حلقة" not in title and "/episode/" not in url.lower():
            continue
        if url in seen:
            continue
        seen.add(url)
        episodes.append({
            "title": title or "حلقة",
            "url": url,
            "type": "episode",
            "_action": "details",
        })
    return episodes


def _parse_json_ld(html):
    """Extract data from JSON-LD script tags."""
    json_ld_match = re.search(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html or "", re.S | re.I)
    if not json_ld_match:
        return None
    
    try:
        data = json.loads(json_ld_match.group(1))
        return data
    except Exception:
        return None


def _detail_title(html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if data.get("name"):
                return _clean_title(data["name"])
            if "@graph" in data:
                for item in data["@graph"]:
                    if item.get("name") and ("فيلم" in item.get("name", "") or "مسلسل" in item.get("name", "")):
                        return _clean_title(item["name"])
    
    # Fallback to HTML patterns
    patterns = [
        r'<h1[^>]+itemprop="name"[^>]*>(.*?)</h1>',
        r'<h1[^>]+class="[^"]*title[^"]*"[^>]*>(.*?)</h1>',
        r'<h1[^>]*>(.*?)</h1>',
        r'property="og:title"[^>]+content="([^"]+)"',
    ]
    for pattern in patterns:
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            title = _clean_title(m.group(1))
            if title:
                return title
    return ""


def _detail_plot(html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if data.get("description"):
                desc = _clean_html(data["description"])
                if desc and len(desc) > 30:
                    return desc
            if "@graph" in data:
                for item in data["@graph"]:
                    if item.get("description"):
                        desc = _clean_html(item["description"])
                        if desc and len(desc) > 30:
                            return desc
    
    # Fallback to meta tags
    patterns = [
        r'<meta[^>]+itemprop="description"[^>]+content="([^"]+)"',
        r'property="og:description"[^>]+content="([^"]+)"',
        r'name="description"[^>]+content="([^"]+)"',
        r'<div[^>]+class="StoryMovieContent"[^>]*>(.*?)</div>',
    ]
    for pattern in patterns:
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            text = _clean_html(m.group(1))
            if text and "موقع وي سيما" not in text.lower() and len(text) > 30:
                return text
    return ""


def _detail_poster(html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if data.get("image") and isinstance(data["image"], dict):
                poster = data["image"].get("url", "")
                if poster:
                    return _normalize_url(poster)
            if "@graph" in data:
                for item in data["@graph"]:
                    if item.get("image") and isinstance(item["image"], dict):
                        poster = item["image"].get("url", "")
                        if poster:
                            return _normalize_url(poster)
                    if item.get("thumbnailUrl"):
                        return _normalize_url(item["thumbnailUrl"])
    
    # Fallback to meta tags
    patterns = [
        r'property="og:image"[^>]+content="([^"]+)"',
        r'<meta[^>]+itemprop="thumbnailUrl"[^>]+content="([^"]+)"',
        r'data-lazy-style="[^"]*--img:url\(([^)]+)\)',
        r'data-src="([^"]+)"',
    ]
    for pattern in patterns:
        m = re.search(pattern, html or "", re.I)
        if m:
            poster = m.group(1).strip("'\" ")
            if poster:
                return _normalize_url(poster) or poster
    return ""


def _detail_year(title, html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if data.get("datePublished"):
                year_match = re.search(r'(\d{4})', data["datePublished"])
                if year_match:
                    return year_match.group(1)
            if "@graph" in data:
                for item in data["@graph"]:
                    if item.get("datePublished"):
                        year_match = re.search(r'(\d{4})', item["datePublished"])
                        if year_match:
                            return year_match.group(1)
    
    # Fallback to patterns
    m = re.search(r'<span[^>]+class="year"[^>]*>\(?\s*(\d{4})\s*\)?</span>', html or "", re.I)
    if m:
        return m.group(1)
    m = re.search(r'\b(19\d{2}|20\d{2})\b', title or "")
    if m:
        return m.group(1)
    return ""


def _detail_rating(html):
    # Check JSON-LD first
    data = _parse_json_ld(html)
    if data:
        if isinstance(data, dict):
            if "aggregateRating" in data:
                rating = data["aggregateRating"].get("ratingValue", "")
                if rating:
                    return str(rating)
            if "@graph" in data:
                for item in data["@graph"]:
                    if "aggregateRating" in item:
                        rating = item["aggregateRating"].get("ratingValue", "")
                        if rating:
                            return str(rating)
    
    # Fallback to regex patterns
    m = re.search(r'"ratingValue"\s*:\s*"?(\\?\d+(?:\.\d+)?)', html or "", re.I)
    if m:
        return m.group(1).replace("\\", "")
    m = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', html or "", re.I)
    if m:
        return m.group(1)
    return ""


def get_categories(mtype="movie"):
    return [
        {"title": "أفلام أجنبية",   "url": _category_from_home("افلام اجنبي",   _CATEGORY_FALLBACKS["افلام اجنبي"]),   "type": "category", "_action": "category"},
        {"title": "أفلام عربية",    "url": _category_from_home("افلام عربي",    _CATEGORY_FALLBACKS["افلام عربي"]),    "type": "category", "_action": "category"},
        {"title": "مسلسلات أجنبية", "url": _category_from_home("مسلسلات اجنبي", _CATEGORY_FALLBACKS["مسلسلات اجنبي"]), "type": "category", "_action": "category"},
        {"title": "مسلسلات عربية",  "url": _category_from_home("مسلسلات عربية", _CATEGORY_FALLBACKS["مسلسلات عربية"]), "type": "category", "_action": "category"},
        {"title": "كارتون وانمي",   "url": _category_from_home("مسلسلات انمي",  _CATEGORY_FALLBACKS["مسلسلات انمي"]),  "type": "category", "_action": "category"},
        {"title": "ترند",           "url": _category_from_home("تريندج",        _CATEGORY_FALLBACKS["تريندج"]),        "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    base = _get_base()
    html, final_url = _fetch_live(url, referer=base)
    if _is_blocked_page(html, final_url):
        log("Wecima: category blocked {}".format(url))
        return []
    items = _extract_cards(html)
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def search(query, page=1):
    base = _get_base()
    items = []
    html = ""
    for search_url in [
        _search_url() + quote_plus(query),
        urljoin(base, "search/") + quote_plus(query),
    ]:
        html, final_url = _fetch_live(search_url, referer=base)
        if _is_blocked_page(html, final_url):
            continue
        items = _extract_cards(html)
        if items:
            break
    log("Wecima: search '{}' -> {} items".format(query, len(items)))
    if not items:
        return []
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def get_page(url, m_type=None):
    base = _get_base()
    html, final_url = _fetch_live(url, referer=base)
    if _is_blocked_page(html, final_url) or not html:
        log("Wecima: detail failed {}".format(url))
        return {"title": "Error", "servers": [], "items": [], "type": m_type or "movie"}

    title = _detail_title(html)
    poster = _detail_poster(html)
    plot = _detail_plot(html)
    year = _detail_year(title, html)
    rating = _detail_rating(html)

    servers = _extract_servers(html)
    episodes = [] if servers else _extract_episode_cards(html)
    log("Wecima: detail {} -> servers={}, episodes={}".format(url, len(servers), len(episodes)))

    item_type = m_type or _guess_type(title, final_url or url)
    if episodes:
        item_type = "series"
    elif servers and any(t in (title or "") for t in ("الحلقة", "حلقة")):
        item_type = "episode"

    return {
        "url": final_url or url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "rating": rating,
        "year": year,
        "servers": servers,
        "items": episodes,
        "type": item_type,
    }


def extract_stream(url):
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
`````

## File: images/playerclock.xml
`````xml
<widget name="clockTime" noWrap="1" position="35,6" size="500,40" zPosition="3" transparent="1" foregroundColor="#66ccff" backgroundColor="#251f1f1f" font="Regular;%d" halign="left" valign="center" />
`````

## File: images/playerskin.xml
`````xml
<screen name="IPTVExtMoviePlayer"    position="center,center" size="%d,%d" flags="wfNoBorder" backgroundColor="#FFFFFFFF" >
                    <widget name="pleaseWait"         noWrap="1" position="center,30"        size="500,40"    zPosition="3" transparent="1" foregroundColor="#999999"   backgroundColor="transparent" font="Regular;25" halign="center"  valign="center"/>
                    
                    <widget name="logoIcon"           position="1176,110"        size="160,40"    zPosition="4"             transparent="1" alphatest="blend" />
                    <widget name="playbackInfoBaner"  position="0,0"           size="1280,177"  zPosition="2" pixmap="%s" />
                    <widget name="progressBar"        position="220,86"        size="840,7"     zPosition="5" pixmap="%s" transparent="1" borderWidth="1" borderColor="#888888" />
                    <widget name="bufferingCBar"      position="220,86"        size="840,7"     zPosition="4" pixmap="%s" transparent="1" borderWidth="1" borderColor="#888888" />
                    <widget name="bufferingBar"       position="220,86"        size="840,7"     zPosition="3" pixmap="%s" borderWidth="1" borderColor="#888888" />
                    <widget name="statusIcon"         position="135,55"        size="72,72"     zPosition="4"             transparent="1" alphatest="blend" />
                    <widget name="loopIcon"           position="60,80"       size="40,40"     zPosition="4"             transparent="1" alphatest="blend" />
                    
                    <widget name="goToSeekPointer"    position="94,30"          size="150,60"  zPosition="8" pixmap="%s" transparent="1" alphatest="blend" />
                    <widget name="goToSeekLabel"      noWrap="1" position="94,30"         size="150,40"   zPosition="9" transparent="1" foregroundColor="white"     backgroundColor="#251f1f1f" font="Regular;27" halign="center" valign="center"/>
                    <widget name="infoBarTitle"       noWrap="1" position="220,41"        size="1000,50"  zPosition="3" transparent="1" foregroundColor="white"     backgroundColor="#251f1f1f" font="Regular;29" halign="left" valign="center"/>
                    <widget name="currTimeLabel"      noWrap="1" position="220,100"       size="200,40"   zPosition="3" transparent="1" foregroundColor="#66ccff"   backgroundColor="#251f1f1f" font="Regular;27" halign="left"   valign="top"/>
                    <widget name="lengthTimeLabel"    noWrap="1" position="540,115"       size="200,40"   zPosition="3" transparent="1" foregroundColor="#999999"   backgroundColor="#251f1f1f" font="Regular;30" halign="center" valign="top"/>
                    <widget name="remainedLabel"      noWrap="1" position="860,100"       size="200,40"   zPosition="3" transparent="1" foregroundColor="#66ccff"   backgroundColor="#251f1f1f" font="Regular;27" halign="right"  valign="top"/>
                    <widget name="videoInfo"          noWrap="1" position="732,8"        size="500,30"   zPosition="3" transparent="1" foregroundColor="#c8cedb"   backgroundColor="#251f1f1f" font="Regular;23" halign="right"  valign="top"/>
                    
                    %s
                    
                    <widget name="subSynchroIcon"     position="0,0"           size="180,66"  zPosition="4" transparent="1" alphatest="blend" />
                    <widget name="subSynchroLabel"    position="1,3"           size="135,50"  zPosition="5" transparent="1" foregroundColor="white"      backgroundColor="transparent" font="Regular;24" halign="center"  valign="center"/>
                    
                    %s
</screen>
`````

## File: images/settings.json
`````json
{
"clockFontSize_SD" : 24,
"clockFontSize_HD" : 24,
"clockFontSize_FHD" : 24,
"clockFormat_24H" : "%H:%M:%S",
"clockFormat_12H" : "%I:%M"  
}
`````

## File: plugin.py
`````python
# -*- coding: utf-8 -*-
"""
ArabicPlayer Plugin for Enigma2
================================
تشغيل مواقع الأفلام العربية مباشرة من الرسيفر
الموقع الأول: EgyDead

الأزرار:
  OK         → فتح / تشغيل
  Back       → رجوع
  Red        → أحدث أفلام
  Green      → أحدث مسلسلات
  Yellow     → بحث
  Blue       → إعدادات
  Info       → معلومات العنصر
"""

import os
import sys
import json
import re
import threading
import time
import http.server
import urllib.request as urllib2

try:
    from urllib.parse import quote, unquote, urlparse, parse_qs, urlencode
except ImportError:
    from urllib import quote, unquote, urlencode
    from urlparse import urlparse, parse_qs

# Dynamic plugin path
PLUGIN_PATH = os.path.dirname(__file__)
if PLUGIN_PATH not in sys.path:
    sys.path.insert(0, PLUGIN_PATH)

from Plugins.Plugin          import PluginDescriptor
from Screens.Screen          import Screen
from Screens.MessageBox      import MessageBox
from Components.ActionMap    import ActionMap
from Components.Label        import Label
from Components.Pixmap       import Pixmap
from Components.MenuList     import MenuList
from Components.ScrollLabel  import ScrollLabel
from enigma import eTimer, ePicLoad, eServiceReference, iPlayableService
from Components.ServiceEventTracker import ServiceEventTracker

_PLUGIN_VERSION = "2.0.2"
_PLUGIN_NAME    = "ArabicPlayer"
_PLUGIN_OWNER   = "أحمد إبراهيم"
_DEFAULT_TMDB_API_KEY = "01fd9e035ea1458748e99eb7216b0259"
_TYPE_LABELS    = {"movie": "فيلم", "series": "مسلسل", "episode": "حلقة"}
_TMDB_API_BASE  = "https://api.themoviedb.org/3"
_TMDB_IMG_BASE  = "https://image.tmdb.org/t/p/w500"
# FIX #1: removed invalid concatenated "shaheed""yts2" → was missing comma
_SEARCH_SITE_ORDER = ("egydead", "akwam", "akwams", "arabseed", "wecima", "topcinema", "fasel", "shaheed")

# ─── Neon Color Palette ──────────────────────────────────────────────────────
_CLR = {
    "bg":           "#0D1117",
    "surface":      "#161B22",
    "surface2":     "#1C2333",
    "selected":     "#21262D",
    "border":       "#30363D",
    "cyan":         "#00E5FF",
    "purple":       "#E040FB",
    "gold":         "#FFD740",
    "green":        "#39D98A",
    "red":          "#FF6B6B",
    "blue":         "#58A6FF",
    "text":         "#F0F6FC",
    "text2":        "#8B949E",
    "text_dim":     "#484F58",
}

# ─── Poster Cache ────────────────────────────────────────────────────────────
import hashlib
_POSTER_CACHE_DIR = "/tmp/ap_cache"

def _poster_cache_path(url):
    if not url: return None
    try:
        if not os.path.isdir(_POSTER_CACHE_DIR):
            os.makedirs(_POSTER_CACHE_DIR)
    except Exception: pass
    url_hash = hashlib.md5(url.encode("utf-8", "ignore")).hexdigest()
    return os.path.join(_POSTER_CACHE_DIR, "{}.jpg".format(url_hash))

def _is_poster_cached(url):
    path = _poster_cache_path(url)
    return path and os.path.exists(path)

def _get_cached_poster(url):
    path = _poster_cache_path(url)
    if path and os.path.exists(path):
        return path
    return None

# ─── Extractor Factory ───────────────────────────────────────────────────────
_EXTRACTOR_MAP = {
    "egydead":    "extractors.egydead",
    "akwam":      "extractors.akwam",
    "akwams":     "extractors.akwams",
    "akoam":      "extractors.akoam",
    "arabseed":   "extractors.arabseed",
    "wecima":     "extractors.wecima",
    "shaheed":    "extractors.shaheed",
    "topcinema":  "extractors.topcinema",
    "fasel":      "extractors.fasel",
}

def _get_extractor(site):
    module_name = _EXTRACTOR_MAP.get(site)
    if not module_name:
        module_name = _EXTRACTOR_MAP.get("egydead")
    return __import__(module_name, fromlist=["get_categories", "get_category_items", "get_page", "search", "extract_stream"])

_SITE_META = {
    "egydead": {
        "title": "EgyDead",
        "tagline": "واجهة حديثة وبوسترات ومكتبة متجددة",
    },
    "akwam": {
        "title": "Akwam (Classic)",
        "tagline": "موقع اكوام الكلاسيكي - افلام ومسلسلات عربية واجنبية",
    },
    "akwams": {
        "title": "Akwams (Modern)",
        "tagline": "موقع اكوام الحديث - واجهة سريعة ومحتوى محدث",
    },
    "arabseed": {
        "title": "Arabseed",
        "tagline": "تصنيفات عربية وأجنبية وحلقات مرتبة",
    },
    "wecima": {
        "title": "Wecima",
        "tagline": "أقسام واسعة وبحث وسيرفرات مباشرة",
    },
    "shaheed": {
        "title": "Shaheed4u",
        "tagline": "تحديثات المسلسلات والأفلام الحصرية بجميع الجودات",
    },
    "topcinema": {
        "title": "TopCinemaa",
        "tagline": "مكتبة ضخمة من الأفلام والمسلسلات والسلاسل",
    },
    "fasel": {
        "title": "FaselHD",
        "tagline": "دقة عالية وسيرفرات متعددة للمشاهدة بدون تقطيع",
    },
}

# ─── Logging ─────────────────────────────────────────────────────────────────
from extractors.base import log as base_log, UA, fetch as base_fetch

SAFE_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_STATE_CACHE = None

def my_log(msg):
    base_log(msg)


# ─── Helper ──────────────────────────────────────────────────────────────────
def _site_label(site):
    return (_SITE_META.get(site) or {}).get("title", str(site or "").capitalize())


def _site_tagline(site):
    return (_SITE_META.get(site) or {}).get("tagline", "")


def _normalize_query(text):
    text = (text or "").strip().lower()
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    return "".join(ch for ch in text if ch.isalnum())


def _strip_arabic_from_english_title(title):
    """
    If a title is predominantly English/Latin (Arabic chars < 30% of non-space chars),
    strip all Arabic words and clean up leftover punctuation.
    Pure Arabic titles are returned unchanged.
    """
    if not title:
        return title
    stripped = title.replace(" ", "")
    if not stripped:
        return title
    ar_count = sum(1 for c in stripped if "\u0600" <= c <= "\u06ff")
    if ar_count / len(stripped) >= 0.30:
        return title
    cleaned = re.sub(r"[\u0600-\u06ff]+", " ", title)
    cleaned = re.sub(r"[\s|\-–_]+$", "", cleaned)
    cleaned = re.sub(r"^[\s|\-–_]+", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -|_")
    return cleaned if cleaned.strip() else title


def _clean_title_for_tmdb(title):
    if not title: return ""
    junk = [
        u"مترجم", u"اون لاين", u"بجودة", u"عالية", u"كامل", u"تحميل", u"مشاهدة", u"فيلم", u"مسلسل",
        u"انمي", u"كرتون", u"حصري", u"شاشه", u"كامله", u"نسخة", u"اصلية", u"bluray", u"web-dl", u"hdtv", u"720p", u"1080p", u"4k"
    ]
    title = title.lower()
    for word in junk:
        title = title.replace(word, "")
    title = re.sub(r'\s+\d{4}\s*$', '', title)
    return re.sub(r'\s+', ' ', title).strip()


def _wrap_ui_text(text, width=40, max_lines=2, fallback=""):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return fallback
    words = text.split(" ")
    lines = []
    current = ""

    for word in words:
        candidate = word if not current else "{} {}".format(current, word)
        if len(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
            if len(lines) >= max_lines:
                break
        current = word

    if len(lines) < max_lines and current:
        lines.append(current)
    if not lines:
        lines = [text[:width]]

    consumed = " ".join(lines)
    if len(consumed) < len(text):
        lines[-1] = lines[-1].rstrip(" .،") + "..."
    return "\n".join(lines[:max_lines])


def _single_line_text(text, width=54, fallback=""):
    return _wrap_ui_text(text, width=width, max_lines=1, fallback=fallback)


def _search_scope_label(scope):
    if scope == "all":
        return "كل المصادر: EgyDead / Akoam / Arabseed / Wecima / TopCinemaa"
    return "المصدر الحالي: {}".format(_site_label(scope))


def _site_search_item(site):
    return {
        "title": "بحث داخل {}".format(_site_label(site)),
        "_action": "search_site",
        "_site": site,
        "type": "tool",
        "plot": "ابحث داخل {} فقط بدون خلط النتائج مع باقي المصادر.".format(_site_label(site)),
    }


def _dedupe_items(items):
    unique = []
    seen = set()
    for item in items or []:
        key = item.get("url") or item.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _rank_search_items(items, query):
    q = _normalize_query(query)
    q_words = [w for w in q.split() if len(w) >= 2] if q else []

    strong   = []
    weak     = []
    no_match = []

    for item in _dedupe_items(items):
        title  = item.get("title", "")
        ntitle = _normalize_query(title)
        rank   = 9

        if not q:
            rank = 5
        elif ntitle == q:
            rank = 0
        elif ntitle.startswith(q):
            rank = 1
        elif q in ntitle:
            rank = 2
        elif q_words:
            matched_words = sum(1 for w in q_words if w in ntitle)
            if matched_words == len(q_words):
                rank = 3
            elif matched_words >= max(1, len(q_words) * 2 // 3):
                rank = 4
            elif matched_words > 0:
                rank = 5

        entry = (rank, title.lower(), item)
        if rank <= 3:
            strong.append(entry)
        elif rank <= 5:
            weak.append(entry)
        else:
            no_match.append(item)

    strong.sort(key=lambda r: (r[0], r[1]))
    weak.sort(key=lambda r: (r[0], r[1]))

    result = [r[2] for r in strong]

    if len(result) < 3:
        result += [r[2] for r in weak[:max(0, 5 - len(result))]]

    if not result and weak:
        result = [r[2] for r in weak]

    return result


def _quality_rank(server_name):
    text = (server_name or "").lower()
    if "2160" in text or "4k" in text:
        return 0
    if "1080" in text:
        return 1
    if "720" in text or "hd" in text:
        return 2
    if "480" in text:
        return 3
    if "360" in text:
        return 4
    return 9


def _sort_servers(servers):
    return sorted(servers or [], key=lambda s: (_quality_rank(s.get("name", "")), s.get("name", "").lower()))


def _decorate_item_title(item, site=None):
    action = item.get("_action", "")
    
    # Handle separators (non-clickable divider lines)
    if action == "separator" or item.get("type") == "separator":
        return "─── {} ───".format(item.get("title", ""))
    
    title = _strip_arabic_from_english_title((item.get("title") or "---").strip())
    item_type = item.get("type", action)
    
    if action.startswith("site_"):
        return title

    # For filter page items (they have type="category" but contain movie data)
    # Check if this is actually a movie from a filter page
    if item_type == "category" and item.get("url") and "release-year" in item.get("url", ""):
        # This is a movie from filter page, show as movie
        return "[فيلم] {}".format(title)
    
    if item_type == "movie":
        prefix = "[فيلم]"
    elif item_type == "series":
        prefix = "[مسلسل]"
    elif item_type == "episode":
        prefix = "[حلقة]"
    elif item_type == "category":
        # Categories - show without prefix
        return title
    else:
        prefix = "•"

    item_site = item.get("_site") or site
    
    # Only show site label for tools, not for movies/series/episodes
    if item_site and item_type in ("movie", "series", "episode"):
        return "{} {}".format(prefix, title)
    elif item_site and item_type == "tool":
        return "{} [{}] {}".format(prefix, _site_label(item_site), title)
    
    return "{} {}".format(prefix, title)


def _state_path():
    for candidate in ("/etc/enigma2/arabicplayer_state.json", os.path.join(PLUGIN_PATH, "arabicplayer_state.json"), "/tmp/arabicplayer_state.json"):
        try:
            parent = os.path.dirname(candidate)
            if parent and os.path.isdir(parent) and os.access(parent, os.W_OK):
                return candidate
        except Exception:
            pass
    return "/tmp/arabicplayer_state.json"


# Thread-safe main-loop dispatcher
_CMIT_QUEUE = []
_CMIT_LOCK  = threading.Lock()
_CMIT_TIMER = None


def _default_state():
    return {
        "config": {
            "owner": _PLUGIN_OWNER,
            "tmdb_api_key": _DEFAULT_TMDB_API_KEY,
        },
        "favorites": [],
        "history": [],
    }


def _load_state():
    global _STATE_CACHE
    if _STATE_CACHE is not None:
        return _STATE_CACHE
    state = _default_state()
    path = _state_path()
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                state.update(loaded)
                state["config"] = dict(_default_state()["config"], **(loaded.get("config") or {}))
    except Exception as e:
        my_log("State load error: {}".format(e))
    _STATE_CACHE = state
    return _STATE_CACHE


def _save_state(state=None):
    global _STATE_CACHE
    _STATE_CACHE = state or _load_state()
    path = _state_path()
    tmp  = path + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(_STATE_CACHE, f)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, path)
    except Exception as e:
        my_log("State save error: {}".format(e))
        try: os.remove(tmp)
        except Exception: pass


def _get_config(key, default=""):
    value = (_load_state().get("config") or {}).get(key, default)
    if key == "tmdb_api_key" and not value:
        return _DEFAULT_TMDB_API_KEY
    if key == "owner" and not value:
        return _PLUGIN_OWNER
    return value


def _set_config(key, value):
    state = _load_state()
    state.setdefault("config", {})[key] = value
    _save_state(state)


def _entry_from_item(item, site, m_type, extra=None):
    entry = {
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "poster": item.get("poster") or item.get("image") or "",
        "plot": item.get("plot", ""),
        "year": item.get("year", ""),
        "rating": item.get("rating", ""),
        "type": item.get("type", "") or m_type,
        "_action": item.get("_action", "details"),
        "_site": item.get("_site", site),
        "_m_type": item.get("_m_type", m_type),
        "_saved_at": int(time.time()),
    }
    if extra:
        entry.update(extra)
    return entry


def _upsert_library_item(bucket, entry, limit=100):
    state = _load_state()
    items = state.setdefault(bucket, [])
    key   = entry.get("url")
    if not entry.get("last_position_sec"):
        for _old in items:
            if _old.get("url") == key and _old.get("last_position_sec"):
                entry["last_position_sec"] = _old["last_position_sec"]
                break
    items = [i for i in items if i.get("url") != key]
    items.insert(0, entry)
    state[bucket] = items[:limit]
    _save_state(state)


def _toggle_favorite_entry(entry):
    state = _load_state()
    favorites = state.setdefault("favorites", [])
    key = entry.get("url")
    for idx, item in enumerate(favorites):
        if item.get("url") == key:
            favorites.pop(idx)
            _save_state(state)
            return False
    favorites.insert(0, entry)
    state["favorites"] = favorites[:100]
    _save_state(state)
    return True


def _is_favorite(url):
    return any(item.get("url") == url for item in (_load_state().get("favorites") or []))


def _history_items():
    return _load_state().get("history") or []


def _favorite_items():
    return _load_state().get("favorites") or []


def _get_saved_position(url):
    for item in (_load_state().get("history") or []):
        if item.get("url") == url:
            pos = int(item.get("last_position_sec") or 0)
            return pos if pos > 30 else 0
    return 0


def _save_position(url, seconds):
    seconds = int(seconds or 0)
    if 0 < seconds < 30:
        my_log("_save_position: skipping {}s (< 30s threshold)".format(seconds))
        return
    state = _load_state()
    for item in (state.get("history") or []):
        if item.get("url") == url:
            item["last_position_sec"] = seconds
            _save_state(state)
            return


# Global position tracker
_GLOBAL_POS_TIMER      = None
_GLOBAL_POS_SESSION    = None
_GLOBAL_POS_ITEM       = ""
_GLOBAL_PLAY_START_WALL  = 0.0
_GLOBAL_PLAY_START_POS   = 0
_GLOBAL_LAST_SEEK_TARGET = -1


def _global_pos_tick():
    global _GLOBAL_POS_ITEM, _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
    if not _GLOBAL_POS_ITEM or not _GLOBAL_PLAY_START_WALL:
        return
    try:
        elapsed = time.time() - _GLOBAL_PLAY_START_WALL
        secs    = int(_GLOBAL_PLAY_START_POS + elapsed)
        if secs < 5:
            my_log("Pos tracker: skipping suspicious pos {}s".format(secs))
            return
        _save_position(_GLOBAL_POS_ITEM, secs)
        my_log("Pos tracker saved: {}s for {}".format(secs, _GLOBAL_POS_ITEM[:50]))
    except Exception as e:
        my_log("Pos tracker error: {}".format(e))


def _start_pos_tracker(session, item_url, start_pos=0):
    global _GLOBAL_POS_TIMER, _GLOBAL_POS_SESSION, _GLOBAL_POS_ITEM
    global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
    global _GLOBAL_LAST_SEEK_TARGET
    _GLOBAL_LAST_SEEK_TARGET = -1
    _GLOBAL_POS_SESSION     = session
    _GLOBAL_POS_ITEM        = item_url or ""
    _GLOBAL_PLAY_START_WALL = time.time()
    _GLOBAL_PLAY_START_POS  = int(start_pos or 0)
    if _GLOBAL_POS_TIMER is None:
        _GLOBAL_POS_TIMER = eTimer()
        _GLOBAL_POS_TIMER.callback.append(_global_pos_tick)
    try:
        _GLOBAL_POS_TIMER.stop()
    except Exception:
        pass
    if _GLOBAL_POS_ITEM:
        _GLOBAL_POS_TIMER.start(20000, False)
        my_log("Pos tracker started (wall-clock base={}s): {}".format(
            _GLOBAL_PLAY_START_POS, item_url[:50]))


def _stop_pos_tracker():
    global _GLOBAL_POS_ITEM
    _GLOBAL_POS_ITEM = ""
    try:
        if _GLOBAL_POS_TIMER:
            _GLOBAL_POS_TIMER.stop()
    except Exception:
        pass


def _library_search_suggestions(query="", current_site="", limit=8):
    q = _normalize_query(query)
    rows = []
    seen = set()
    for source_name, items, source_rank in (
        ("المفضلة", _favorite_items(), 0),
        ("السجل", _history_items(), 1),
    ):
        for item in items or []:
            title = re.sub(r"\s+", " ", item.get("title", "") or "").strip()
            if not title:
                continue
            norm = _normalize_query(title)
            if not norm or norm in seen:
                continue
            if q:
                if norm == q:
                    score = 0
                elif norm.startswith(q):
                    score = 1
                elif q in norm:
                    score = 2
                else:
                    continue
            else:
                score = 5
            if current_site and item.get("_site") == current_site:
                score -= 1
            seen.add(norm)
            rows.append((
                score,
                source_rank,
                -int(item.get("_saved_at") or 0),
                {
                    "title": title,
                    "query": title,
                    "source": source_name,
                    "site": item.get("_site", ""),
                    "kind": _TYPE_LABELS.get(item.get("type", ""), ""),
                    "year": item.get("year", ""),
                }
            ))
    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    return [row[3] for row in rows[:limit]]


def _tmdb_enabled():
    return bool((_get_config("tmdb_api_key", "") or "").strip())


def _tmdb_request(path, params=None):
    api_key = (_get_config("tmdb_api_key", "") or "").strip()
    if not api_key:
        return None
    base_payload = {"api_key": api_key}
    if params:
        base_payload.update(params)
    for language in ("ar", "en-US"):
        payload = dict(base_payload)
        payload["language"] = language
        url = "{}{}?{}".format(_TMDB_API_BASE, path, urlencode(payload))
        try:
            raw, _ = base_fetch(
                url,
                referer="https://www.themoviedb.org/",
                extra_headers={"Accept": "application/json"}
            )
            if not raw:
                continue
            data = json.loads(raw)
            if isinstance(data, dict):
                if data.get("overview") or data.get("results") or language == "en-US":
                    return data
        except Exception as e:
            my_log("TMDb request failed {} [{}]: {}".format(path, language, e))
    return None


def _tmdb_request_language(path, language="ar", params=None, accept_any=False):
    api_key = (_get_config("tmdb_api_key", "") or "").strip()
    if not api_key:
        return None
    payload = {"api_key": api_key, "language": language}
    if params:
        payload.update(params)
    url = "{}{}?{}".format(_TMDB_API_BASE, path, urlencode(payload))
    try:
        raw, _ = base_fetch(
            url,
            referer="https://www.themoviedb.org/",
            extra_headers={"Accept": "application/json"}
        )
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if accept_any or data.get("overview") or data.get("results"):
            return data
    except Exception as e:
        my_log("TMDb language request failed {} [{}]: {}".format(path, language, e))
    return None


def _tmdb_poster_url(path):
    if not path:
        return ""
    if path.startswith("http"):
        return path
    return _TMDB_IMG_BASE + path


def _tmdb_pick_poster(media_kind, tmdb_id, fallback_path=""):
    if not tmdb_id:
        return _tmdb_poster_url(fallback_path or "")
    images = _tmdb_request_language(
        "/{}/{}/images".format(media_kind, tmdb_id),
        language="en-US",
        params={"include_image_language": "ar,en,null"},
        accept_any=True,
    ) or {}
    posters = images.get("posters") or []
    for wanted_lang in ("ar", None, "en"):
        for poster in posters:
            if poster.get("iso_639_1") == wanted_lang and poster.get("file_path"):
                return _tmdb_poster_url(poster.get("file_path"))
    return _tmdb_poster_url(fallback_path or "")


def _tmdb_media_kind(item_type):
    if item_type in ("series", "episode", "tv"):
        return "tv"
    return "movie"


def _tmdb_pick_best(results, query, year=""):
    query_norm = _normalize_query(query)
    target_year = (year or "")[:4]
    scored = []
    for result in results or []:
        title = result.get("title") or result.get("name") or ""
        title_norm = _normalize_query(title)
        score = 9
        if title_norm == query_norm:
            score = 0
        elif title_norm.startswith(query_norm):
            score = 1
        elif query_norm and query_norm in title_norm:
            score = 2
        release = str(result.get("release_date") or result.get("first_air_date") or "")
        if target_year and release[:4] == target_year:
            score -= 1
        scored.append((score, title.lower(), result))
    scored.sort(key=lambda row: (row[0], row[1]))
    return scored[0][2] if scored else None


def _tmdb_search_metadata(title, year="", item_type="movie"):
    if not title or not _tmdb_enabled():
        return None
    media_kind = _tmdb_media_kind(item_type)
    variants = [title.strip()]
    simple = re.sub(r"\s*\(\d{4}\)\s*$", "", title).strip()
    if simple and simple not in variants:
        variants.append(simple)
    plain = re.sub(r"[:|_\-]+", " ", simple).strip()
    if plain and plain not in variants:
        variants.append(plain)
    clean = re.sub(r"\b(bluray|webrip|web-dl|hdrip|hdcam|cam|1080p|720p|480p|360p)\b", "", plain, flags=re.I).strip()
    clean = re.sub(r"\s+", " ", clean).strip(" -|")
    if clean and clean not in variants:
        variants.append(clean)
    arabic_clean = re.sub(
        r"\b(مشاهدة|فيلم|مسلسل|الحلقة|حلقة|الموسم|مترجم(?:ة)?|مدبلج(?:ة)?|اون لاين|أون لاين)\b",
        "",
        clean,
        flags=re.I,
    ).strip()
    arabic_clean = re.sub(r"\s+", " ", arabic_clean).strip(" -|")
    if arabic_clean and arabic_clean not in variants:
        variants.append(arabic_clean)

    best = None
    for query in variants:
        params = {"query": query}
        if year:
            if media_kind == "movie":
                params["year"] = year[:4]
            else:
                params["first_air_date_year"] = year[:4]
        data = _tmdb_request("/search/{}".format(media_kind), params) or {}
        best = _tmdb_pick_best(data.get("results") or [], query, year)
        if not best:
            params.pop("year", None)
            params.pop("first_air_date_year", None)
            best = _tmdb_pick_best((_tmdb_request("/search/{}".format(media_kind), params) or {}).get("results") or [], query, "")
        if best:
            break
    if not best:
        return None
    detail_ar = _tmdb_request_language(
        "/{}/{}".format(media_kind, best.get("id")),
        language="ar",
        params={"append_to_response": "credits"},
        accept_any=True,
    ) or {}
    detail_en = _tmdb_request_language(
        "/{}/{}".format(media_kind, best.get("id")),
        language="en-US",
        params={"append_to_response": "credits"},
        accept_any=True,
    ) or {}
    detail = detail_ar or detail_en
    if not detail:
        detail = _tmdb_request("/{}/{}".format(media_kind, best.get("id"))) or {}
    if not detail:
        detail = best
    genres_source = detail_ar or detail_en or detail
    genres = ", ".join([g.get("name", "") for g in genres_source.get("genres") or [] if g.get("name")])
    localized_plot = (
        (detail_ar.get("overview") or "").strip()
        or (detail_en.get("overview") or "").strip()
        or (best.get("overview") or "").strip()
    )
    localized_title = (
        detail_ar.get("title")
        or detail_ar.get("name")
        or detail_en.get("title")
        or detail_en.get("name")
        or detail.get("title")
        or detail.get("name")
        or title
    )
    return {
        "title": localized_title,
        "plot": localized_plot,
        "poster": _tmdb_pick_poster(media_kind, best.get("id"), detail_ar.get("poster_path") or detail_en.get("poster_path") or detail.get("poster_path") or ""),
        "rating": "{:.1f}".format(float(detail.get("vote_average") or 0)) if detail.get("vote_average") else "",
        "year": str(detail.get("release_date") or detail.get("first_air_date") or "")[:4],
        "genres": genres,
        "tmdb_id": detail.get("id"),
        "tmdb_kind": media_kind,
    }


def _merge_tmdb_data(data):
    if not data or not data.get("title"):
        return data
    data = dict(data)
    if not data.get("plot") and data.get("desc"):
        data["plot"] = data.get("desc")
    item_type = data.get("type", "movie")
    if item_type == "episode":
        return data
    tmdb = _tmdb_search_metadata(data.get("title"), data.get("year", ""), item_type)
    if not tmdb:
        return data
    merged = dict(data)
    if tmdb.get("title") and len((data.get("title") or "").strip()) < 2:
        merged["title"] = tmdb["title"]
    if tmdb.get("poster") and (not merged.get("poster")):
        merged["poster"] = tmdb["poster"]
    if tmdb.get("plot") and len(tmdb.get("plot", "")) > len(merged.get("plot", "")):
        merged["plot"] = tmdb["plot"]
    if tmdb.get("rating") and not merged.get("rating"):
        merged["rating"] = tmdb["rating"]
    if tmdb.get("year") and not merged.get("year"):
        merged["year"] = tmdb["year"]
    if tmdb.get("genres"):
        merged["genres"] = tmdb["genres"]
    if tmdb.get("plot") or tmdb.get("poster") or tmdb.get("rating") or tmdb.get("genres") or tmdb.get("year"):
        merged["_tmdb"] = tmdb
    return merged


def _tmdb_search_suggestions(query, limit=8):
    query = re.sub(r"\s+", " ", query or "").strip()
    if len(query) < 2 or not _tmdb_enabled():
        return []

    suggestions = []
    seen = set()
    for media_kind, kind_label in (("movie", "فيلم"), ("tv", "مسلسل")):
        try:
            data = _tmdb_request("/search/{}".format(media_kind), {"query": query, "page": 1}) or {}
            for result in data.get("results") or []:
                title = (result.get("title") or result.get("name") or "").strip()
                if not title:
                    continue
                norm = _normalize_query(title)
                if not norm or norm in seen:
                    continue
                seen.add(norm)
                year = str(result.get("release_date") or result.get("first_air_date") or "")[:4]
                suggestions.append({
                    "title": title,
                    "query": title,
                    "source": "TMDb",
                    "site": "",
                    "kind": kind_label,
                    "year": year,
                })
                if len(suggestions) >= limit:
                    return suggestions[:limit]
        except Exception as e:
            my_log("TMDb suggestions failed for {}: {}".format(media_kind, e))
    return suggestions[:limit]


def _display_plot_text(value):
    text = re.sub(r"\s+", " ", value or "").strip()
    return text or "القصة غير متوفرة حالياً لهذا العنصر."


def _pick_plot_text_with_source(*sources):
    best = ""
    best_source = ""
    for source in sources:
        if isinstance(source, dict):
            candidates = [
                ("plot", source.get("plot")),
                ("overview", source.get("overview")),
                ("desc", source.get("desc")),
                ("tmdb.plot", (source.get("_tmdb") or {}).get("plot")),
            ]
        else:
            candidates = [("value", source)]
        for label, candidate in candidates:
            text = _display_plot_text(candidate)
            if text == "القصة غير متوفرة حالياً لهذا العنصر.":
                continue
            if len(text) > len(best):
                best = text
                best_source = label
    return best or "القصة غير متوفرة حالياً لهذا العنصر.", best_source or "none"


def _pick_plot_text(*sources):
    return _pick_plot_text_with_source(*sources)[0]


def _drain_cmit_queue():
    with _CMIT_LOCK:
        items = list(_CMIT_QUEUE)
        del _CMIT_QUEUE[:]
    for _f, _a, _kw in items:
        try: _f(*_a, **_kw)
        except Exception as _e:
            try: my_log("CMIT drain: {}".format(_e))
            except Exception: pass


def callInMainThread(func, *args, **kwargs):
    global _CMIT_TIMER
    with _CMIT_LOCK:
        _CMIT_QUEUE.append((func, args, kwargs))
    if _CMIT_TIMER is None:
        try:
            _CMIT_TIMER = eTimer()
            _CMIT_TIMER.callback.append(_drain_cmit_queue)
        except Exception: pass
    if _CMIT_TIMER is not None:
        try: _CMIT_TIMER.start(50, True)
        except Exception: pass
    else:
        try:
            from twisted.internet import reactor
            reactor.callFromThread(_drain_cmit_queue)
        except Exception: pass

# ─── Local HTTP Proxy (HiSilicon SSL Shield) ─────────────────────────────────
_PROXY_PORT = 19888
_PROXY_STARTED = False
_PROXY_LAST_HIT = 0
_PROXY_LAST_BYTES = 0
_PROXY_LAST_URL = ""

def start_proxy():
    global _PROXY_STARTED
    if _PROXY_STARTED: return
    try:
        def run_server():
            server = http.server.HTTPServer(('0.0.0.0', _PROXY_PORT), LocalProxyHandler)
            server.serve_forever()
        t = threading.Thread(target=run_server)
        t.daemon = True
        t.start()
        _PROXY_STARTED = True
        my_log("LocalProxy Shield: ACTIVE (Port {})".format(_PROXY_PORT))
    except Exception as e:
        my_log("start_proxy failure: {}".format(e))

class LocalProxyHandler(http.server.BaseHTTPRequestHandler):

    def do_HEAD(self):
        self._handle("HEAD")

    def do_GET(self):
        self._handle("GET")

    def _handle(self, method):
        try:
            global _PROXY_LAST_HIT, _PROXY_LAST_BYTES, _PROXY_LAST_URL
            raw = self.path[1:]
            parsed_req = urlparse(self.path)
            query = parse_qs(parsed_req.query or "")

            piped_headers = ""
            if parsed_req.path == "/stream" and query.get("url"):
                stream_url = unquote(query.get("url", [""])[0]).strip()
                explicit_referer = unquote(query.get("referer", [""])[0]).strip()
                explicit_ua = unquote(query.get("ua", [""])[0]).strip()
            else:
                explicit_referer = ""
                explicit_ua = ""
                if not raw or "://" not in raw:
                    self.send_error(400, "Bad URL")
                    return
                if "|" in raw:
                    stream_url, piped_headers = raw.split("|", 1)
                    stream_url = stream_url.strip()
                else:
                    stream_url = raw.strip()

            headers = {"User-Agent": SAFE_UA}

            if explicit_ua:
                headers["User-Agent"] = explicit_ua

            if piped_headers:
                for part in piped_headers.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        headers[k.strip()] = v.strip()

            if explicit_referer:
                headers["Referer"] = explicit_referer
            elif "Referer" not in headers:
                try:
                    parts = stream_url.split("/")
                    headers["Referer"] = parts[0] + "//" + parts[2] + "/"
                except Exception:
                    pass

            range_hdr = self.headers.get("Range") or self.headers.get("range")
            if range_hdr:
                headers["Range"] = range_hdr
                my_log("Proxy: Range={}".format(range_hdr))

            my_log("Proxy: {} {}".format(method, stream_url[:80]))
            _PROXY_LAST_HIT = time.time()
            _PROXY_LAST_BYTES = 0
            _PROXY_LAST_URL = stream_url

            req = urllib2.Request(stream_url, headers=headers)

            try:
                resp = urllib2.urlopen(req, timeout=30)
                status = resp.getcode()
            except urllib2.HTTPError as http_err:
                my_log("Proxy: Upstream HTTP {} for {}".format(http_err.code, stream_url[:60]))
                status = http_err.code
                resp = http_err
            except Exception as e:
                my_log("Proxy: Upstream connection error: {}".format(e))
                try:
                    self.send_error(502, str(e))
                except Exception:
                    pass
                return

            self.send_response(status)

            resp_hdrs = {}
            try:
                for k, v in resp.getheaders():
                    resp_hdrs[k.lower()] = v
            except Exception:
                pass

            for key in ("content-type", "content-length",
                        "content-range", "accept-ranges",
                        "last-modified", "etag"):
                if key in resp_hdrs:
                    self.send_header(key.title(), resp_hdrs[key])

            if "accept-ranges" not in resp_hdrs:
                self.send_header("Accept-Ranges", "bytes")

            self.end_headers()

            if method == "HEAD":
                return

            try:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    _PROXY_LAST_BYTES += len(chunk)
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except Exception:
                pass

        except Exception as e:
            my_log("Proxy FATAL: {}".format(e))
            try:
                self.send_error(500)
            except Exception:
                pass

    def log_message(self, *args):
        pass


# ─── Home Screen ─────────────────────────────────────────────────────────────
class ArabicPlayerHome(Screen):
    skin = """
    <screen name="ArabicPlayerHome" position="center,center" size="1920,1080"
            title="ArabicPlayer" flags="wfNoBorder">
        <ePixmap position="0,0" size="1920,1080" pixmap="{}/images/bg.png" zPosition="0" alphatest="blend" />

        <!-- ═══ Header Bar ═══ -->
        <widget name="title_bar"  position="0,0"     size="1920,120" backgroundColor="#0D1117" zPosition="1" />
        <widget name="title_text" position="45,18"   size="750,57"  font="Regular;48" foregroundColor="#00E5FF" transparent="1" zPosition="3" />
        <widget name="subtitle"   position="45,75"   size="750,36"  font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="3" />
        <widget name="status"     position="1050,24"  size="825,42"  font="Regular;28" foregroundColor="#FFD740" transparent="1" halign="right" zPosition="3" />
        <widget name="footer"     position="1050,72"  size="825,36"  font="Regular;24" foregroundColor="#58A6FF" transparent="1" halign="right" zPosition="3" />

        <!-- ═══ Menu Panel (Left) ═══ -->
        <widget name="menu_box"   position="30,142"   size="1080,810" backgroundColor="#161B22" zPosition="1" />
        <widget name="menu"       position="52,165"  size="1035,765" zPosition="2"
                scrollbarMode="showOnDemand"
                foregroundColor="#F0F6FC"
                foregroundColorSelected="#00E5FF"
                backgroundColor="#161B22"
                backgroundColorSelected="#21262D"
                font="Regular;39" itemHeight="81" transparent="1" />

        <!-- ═══ Preview Panel (Right) ═══ -->
        <widget name="preview_box" position="1140,142"  size="750,810" backgroundColor="#1C2333" zPosition="1" />
        <widget name="poster"      position="1215,172" size="600,540" zPosition="3" alphatest="blend" />
        <widget name="preview_title" position="1162,735" size="705,90" font="Regular;36" foregroundColor="#FFD740" transparent="1" zPosition="3" halign="center" />
        <widget name="preview_meta"  position="1162,832" size="705,42" font="Regular;26" foregroundColor="#00E5FF" transparent="1" zPosition="3" halign="center" />
        <widget name="preview_info" position="1162,882" size="705,54" font="Regular;22" foregroundColor="#8B949E" transparent="1" zPosition="3" halign="center" />

        <!-- ═══ Button Bar ═══ -->
        <widget name="btn_bar"    position="0,975"   size="1920,105" backgroundColor="#0D1117" zPosition="1" />
        <widget name="key_red"    position="45,990"  size="420,42" font="Regular;27" foregroundColor="#FF6B6B" transparent="1" halign="center" zPosition="3" />
        <widget name="key_green"  position="510,990" size="420,42" font="Regular;27" foregroundColor="#39D98A" transparent="1" halign="center" zPosition="3" />
        <widget name="key_yellow" position="975,990" size="420,42" font="Regular;27" foregroundColor="#FFD740" transparent="1" halign="center" zPosition="3" />
        <widget name="key_blue"   position="1440,990" size="420,42" font="Regular;27" foregroundColor="#58A6FF" transparent="1" halign="center" zPosition="3" />
    </screen>
    """

    def __init__(self, session):
        self.skin = ArabicPlayerHome.skin.format(PLUGIN_PATH)
        Screen.__init__(self, session)
        self.session = session
        self._items  = []
        self._page   = 1
        self._source = "home"
        self._site   = "egydead"
        self._m_type = "movie"
        self._last_query = ""
        self._nav_stack = []
        self._debounce_timer = eTimer()
        self._debounce_timer.callback.append(self._debounced_load_poster)
        self._pending_poster_url = None

        self["title_bar"]  = Label("")
        self["title_text"] = Label("ArabicPlayer  v{}".format(_PLUGIN_VERSION))
        self["subtitle"]   = Label("المشغل العربي الاحترافي")
        self["status"]     = Label("جاري التحميل...")
        self["footer"]     = Label("TMDb  |  المفضلة  |  السجل")
        self["menu_box"]   = Label("")
        self["preview_box"] = Label("")
        self["poster"]     = Pixmap()
        self["menu"]       = MenuList([])
        self["preview_title"] = Label("")
        self["preview_meta"] = Label("")
        self["preview_info"] = Label("")
        self["btn_bar"]    = Label("")
        self["key_red"]    = Label("أحدث أفلام")
        self["key_green"]  = Label("أحدث مسلسلات")
        self["key_yellow"] = Label("بحث")
        self["key_blue"]   = Label("الصفحة التالية")

        self.picLoad = ePicLoad()
        self.picLoad.PictureData.get().append(self._paintPoster)
        self._tmp_posters = []
        self._requested_poster_url = None
        self._poster_lock = threading.Lock()
        self.onClose.append(self._onPluginClose)

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "InfobarMenuActions"],
            {
                "ok":     self._onOk,
                "cancel": self._onBack,
                "red":    self._loadMovies,
                "green":  self._loadSeries,
                "yellow": self._onSearch,
                "blue":   self._nextPage,
                "up":     lambda: self["menu"].up(),
                "down":   lambda: self["menu"].down(),
                "left":   lambda: self["menu"].pageUp(),
                "right":  lambda: self["menu"].pageDown(),
            },
            -1
        )

        try:
            self["menu"].onSelectionChanged.append(self._refreshPreview)
        except Exception:
            pass
        self.onLayoutFinish.append(self._init)

    def _init(self):
        self._showHome()

    def _setHeader(self, title, subtitle="", status=None):
        self["title_text"].setText(_single_line_text(title, width=42, fallback="ArabicPlayer"))
        self["subtitle"].setText(_wrap_ui_text(subtitle, width=56, max_lines=2))
        if status is not None:
            self["status"].setText(status)

    def _showHome(self):
        self._source = "home"
        self._page   = 1
        self._nav_stack = []
        self._setHeader(
            "ArabicPlayer  v{}".format(_PLUGIN_VERSION),
            "المشغل العربي الاحترافي",
            "الرئيسية"
        )
        items = [
            ("━━  المصادر  ━━━━━━━━━━━━━━━━━", "separator"),
            ("EgyDead          واجهة حديثة وبوسترات", "site_egydead"),
            ("Akwam (Classic)  موقع اكوام الكلاسيكي", "site_akwam"),
            ("Akwams (Modern)  موقع اكوام الحديث", "site_akwams"),
            ("Arabseed         تصنيفات مرتبة", "site_arabseed"),
            ("Wecima           أقسام واسعة وبحث سريع", "site_wecima"),
            ("Shaheed4u        أفلام ومسلسلات حصرية", "site_shaheed"),
            ("TopCinemaa       مكتبة ضخمة", "site_topcinema"),
            ("FaselHD          دقة عالية بدون تقطيع", "site_fasel"),
            ("━━  الأدوات  ━━━━━━━━━━━━━━━━━", "separator"),
            ("البحث الشامل", "search"),
            ("المفضلة", "favorites"),
            ("السجل", "history"),
            ("الإعدادات", "settings"),
        ]
        self._items = [{"title": t, "_action": a} for t, a in items]
        self["menu"].setList([t for t, _ in items])
        self["footer"].setText("TMDb  |  {} مفضلة  |  {} سجل".format(len(_favorite_items()), len(_history_items())))
        self._refreshPreview()

    def _onOk(self):
        idx = self["menu"].getSelectedIndex()
        if idx < 0 or idx >= len(self._items):
            return
        item = self._items[idx]

        # Ignore separator items (they are not clickable)
        if item.get("_action") == "separator" or item.get("type") == "separator":
            return

        if "_action" in item:
            a = item["_action"]
            if a.startswith("site_"):
                self._site = a.replace("site_", "")
                self._showSiteCategories()
                return
            elif a == "search":
                self._onSearch()
                return
            elif a == "search_site":
                self._onSearch(item.get("_site", self._site))
                return
            elif a == "favorites":
                self._showLibrary("favorites")
                return
            elif a == "history":
                self._showLibrary("history")
                return
            elif a == "settings":
                self._openSettings()
                return

        curr_type = item.get("type", item.get("_action"))
        if curr_type == "category":
            if item.get("_m_type") in ("movie", "series"):
                self._m_type = item.get("_m_type")
            self._loadCategory(item["url"], item["title"])
            return

        if curr_type in ("movie", "series", "episode", "details"):
            self._openItem(item)

    def _onPluginClose(self):
        try:
            self.picLoad.PictureData.get().remove(self._paintPoster)
        except Exception:
            pass
        self._clearTmpPosters()

    def _onBack(self):
        if self._nav_stack:
            state = self._nav_stack.pop()
            self._source = state.get("source", "home")
            self._site = state.get("site", self._site)
            self._m_type = state.get("m_type", self._m_type)
            self._page = state.get("page", 1)
            items = state.get("items", [])
            header = state.get("header", {})
            if items:
                self._setList(items)
                self._setHeader(**header)
            else:
                self._showHome()
        elif self._source != "home":
            self._showHome()
        else:
            self.close()

    def _push_nav_state(self):
        self._nav_stack.append({
            "source": self._source,
            "site": self._site,
            "m_type": self._m_type,
            "page": self._page,
            "items": list(self._items),
            "header": {
                "title": self["title_text"].getText(),
                "subtitle": self["subtitle"].getText(),
                "status": self["status"].getText(),
            },
        })

    def _clearTmpPosters(self):
        for p in self._tmp_posters:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        self._tmp_posters = []

    def _paintPoster(self, picData=None):
        ptr = self.picLoad.getData()
        if ptr:
            self["poster"].instance.setPixmap(ptr)
            self["poster"].show()

    def _setList(self, items):
        self._items = items
        self["menu"].setList([_decorate_item_title(i, self._site) for i in items])
        self["status"].setText("{} عنصر".format(len(items)))
        self._refreshPreview()
        try:
            self._first_item_timer.stop()
        except Exception:
            pass
        self._first_item_timer = eTimer()
        self._first_item_timer.callback.append(self._refreshPreview)
        self._first_item_timer.start(700, True)

    def _refreshPreview(self):
        if not self._items:
            self["preview_title"].setText("")
            self["preview_meta"].setText("")
            self["preview_info"].setText("")
            self["poster"].hide()
            return

        idx = self["menu"].getSelectedIndex()
        if idx < 0 or idx >= len(self._items):
            idx = 0
        item = self._items[idx]
        action = item.get("_action", "")
        item_type = item.get("type", action)
        title = _strip_arabic_from_english_title(item.get("title", ""))
        site = item.get("_site", self._site)

        if action == "separator":
            self["preview_title"].setText("")
            self["preview_meta"].setText("")
            self["preview_info"].setText("")
            self["poster"].hide()
            return

        meta = []
        info_parts = []
        if action.startswith("site_"):
            site_key = action.replace("site_", "")
            meta.append("المصدر")
            info_parts.append(_site_tagline(site_key))
        elif action in ("search", "search_site", "favorites", "history", "settings"):
            meta.append("أداة")
        else:
            if site:
                meta.append(_site_label(site))
            if item.get("year"):
                meta.append(item.get("year"))
            if item.get("rating"):
                meta.append("{}/10".format(item.get("rating")))
            if item_type in _TYPE_LABELS:
                meta.append(_TYPE_LABELS.get(item_type))

        self["preview_title"].setText(_wrap_ui_text(title, width=28, max_lines=3, fallback="بدون عنوان"))
        self["preview_meta"].setText(_wrap_ui_text("  |  ".join(meta), width=36, max_lines=2))
        self["preview_info"].setText(_wrap_ui_text("  ".join(info_parts), width=36, max_lines=2) if info_parts else "")

        poster_url = item.get("poster") or item.get("image") or ""

        with self._poster_lock:
            self._requested_poster_url = poster_url

        if poster_url:
            cached = _get_cached_poster(poster_url)
            if cached:
                self._display_poster_from_file(cached)
            else:
                self._pending_poster_url = poster_url
                try:
                    self._debounce_timer.stop()
                except Exception:
                    pass
                self._debounce_timer.start(300, True)
        else:
            self["poster"].hide()

    def _debounced_load_poster(self):
        url = self._pending_poster_url
        if url:
            threading.Thread(target=self._downloadPoster, args=(url,), daemon=True).start()

    def _display_poster_from_file(self, path):
        try:
            self.picLoad.setPara((self["poster"].instance.size().width(), self["poster"].instance.size().height(), 1, 1, 0, 1, "#000000"))
            self.picLoad.startDecode(path)
        except Exception as e:
            my_log("_display_poster error: {}".format(e))

    def _downloadPoster(self, url):
        if not url: return
        with self._poster_lock:
            if url != self._requested_poster_url: return

        try:
            if url.startswith("//"): url = "https:" + url
            try:
                from urllib.parse import urlparse, quote, urlunparse
                p = list(urlparse(url))
                p[2] = quote(p[2])
                p[4] = quote(p[4])
                url = urlunparse(p)
            except Exception: pass

            cached = _get_cached_poster(url)
            if cached:
                with self._poster_lock:
                    if url != self._requested_poster_url: return
                callInMainThread(self._display_poster_from_file, cached)
                return

            cache_path = _poster_cache_path(url)
            req = urllib2.Request(url, headers={"User-Agent": SAFE_UA})
            data = urllib2.urlopen(req, timeout=7).read()

            with self._poster_lock:
                if url != self._requested_poster_url: return
                if cache_path:
                    with open(cache_path, "wb") as f:
                        f.write(data)
                    callInMainThread(self._display_poster_from_file, cache_path)
                else:
                    path = "/tmp/ap_preview_{}.jpg".format(int(time.time()))
                    with open(path, "wb") as f:
                        f.write(data)
                    self._tmp_posters.append(path)
                    callInMainThread(self._display_poster_from_file, path)
        except Exception as e:
            my_log("_downloadPoster preview error: {}".format(e))
            with self._poster_lock:
                if url == self._requested_poster_url:
                    callInMainThread(self["poster"].hide)

    def _nextPage(self):
        cat_url  = getattr(self, "_cat_url",  None)
        cat_name = getattr(self, "_cat_name", "")
        if self._source == "category" and cat_url:
            self._page += 1
            self._loadCategory(cat_url, cat_name)

    def _showSiteCategories(self):
        self._push_nav_state()
        try:
            extractor = _get_extractor(self._site)
            get_categories = getattr(extractor, "get_categories", None)
            if not get_categories:
                cats = [{"title": "لا توجد أقسام", "type": "error"}]
            elif self._site == "egydead":
                movie_cats = get_categories("movie")
                series_cats = get_categories("series")
                cats = [_site_search_item(self._site)]
                for item in movie_cats:
                    updated = dict(item)
                    updated["title"] = updated.get("title", "").replace("[فيلم] ", "").replace("[مسلسل] ", "")
                    updated["_m_type"] = "movie"
                    cats.append(updated)
                for item in series_cats:
                    updated = dict(item)
                    updated["title"] = updated.get("title", "").replace("[فيلم] ", "").replace("[مسلسل] ", "")
                    updated["_m_type"] = "series"
                    cats.append(updated)
            else:
                cats = [_site_search_item(self._site)] + (get_categories() or [])
        except Exception as e:
            my_log("_showSiteCategories error for site {}: {}".format(self._site, e))
            cats = [{"title": "فشل جلب الأقسام", "type": "error"}]

        self._source = "categories"
        self._setList(cats)
        self._setHeader(
            "تصنيفات {}".format(_site_label(self._site)),
            _site_tagline(self._site),
            "اختر القسم"
        )

    def _showCategories(self, m_type):
        self._push_nav_state()
        extractor = _get_extractor("egydead")
        get_categories = getattr(extractor, "get_categories", None)
        self._source = "categories"
        self._m_type = m_type
        cats = get_categories(m_type) if get_categories else []
        self._setList(cats)
        self._setHeader(
            "تصنيفات " + ("الأفلام" if m_type == "movie" else "المسلسلات"),
            "استعراض منظم حسب النوع داخل {}".format(_site_label("egydead")),
            "اختر التصنيف"
        )

    def _loadCategory(self, url, name):
        self._push_nav_state()
        self._source = "category"
        self._cat_url = url
        self._cat_name = name
        self["status"].setText("جاري تحميل {}...".format(name))
        self["menu"].setList(["جاري التحميل..."])
        threading.Thread(target=self._bgLoadCategory, args=(url,), daemon=True).start()

    def _bgLoadCategory(self, url):
        try:
            my_log("_bgLoadCategory started: {}, site={}, page={}".format(url, self._site, self._page))
            extractor = _get_extractor(self._site)
            get_category_items = getattr(extractor, "get_category_items", None)
            if not get_category_items:
                callInMainThread(self["status"].setText, "لا توجد نتائج")
                return
            my_log("_bgLoadCategory calling get_category_items for site: {}".format(self._site))
            items = get_category_items(url) if self._site != "egydead" else get_category_items(url, page=self._page)
            my_log("_bgLoadCategory got {} items".format(len(items) if items else 0))
            callInMainThread(self._onCategoryLoaded, items)
        except Exception as e:
            my_log("_bgLoadCategory error: {}".format(e))
            callInMainThread(self["status"].setText, "فشل: {}".format(str(e)[:60]))

    def _onCategoryLoaded(self, items):
        if not items:
            self["status"].setText("لا توجد نتائج")
            self["menu"].setList(["لا توجد نتائج"])
            return
        self._setHeader(
            "{} — صفحة {}".format(self._cat_name, self._page),
            "المصدر: {}".format(_site_label(self._site))
        )
        self._setList(_dedupe_items(items))

    def _loadMovies(self):
        self._showCategories("movie")

    def _loadSeries(self):
        self._showCategories("series")

    def _openSettings(self):
        self.session.open(ArabicPlayerSettings, self._site)

    def _showLibrary(self, kind):
        self._push_nav_state()
        self._source = kind
        if kind == "favorites":
            items = _favorite_items()
            title = "المفضلة"
            subtitle = "العناصر المحفوظة للوصول السريع"
        else:
            items = _history_items()
            title = "السجل"
            subtitle = "آخر العناصر التي تم تشغيلها"
        if not items:
            self._setHeader(title, subtitle, "لا توجد عناصر بعد")
            self["menu"].setList(["القائمة فارغة"])
            self._items = []
            return
        self._setHeader(title, subtitle)
        self._setList(items)

    def _onSearch(self, forced_scope=None):
        self.session.openWithCallback(
            self._onSearchQuery,
            ArabicPlayerSearch,
            current_site=self._site,
            default_scope=forced_scope or "all",
            query=self._last_query
        )

    def _onSearchQuery(self, result=None):
        if not result:
            return
        scope = "all"
        query = result
        if isinstance(result, tuple):
            query, scope = result
        query = (query or "").strip()
        if not query:
            return
        self._last_query = query
        self._source = "search"
        self._search_scope = scope
        self["status"].setText("بحث عن: {}...".format(query))
        self["menu"].setList(["جاري البحث..."])
        threading.Thread(
            target=self._bgSearch, args=(query, scope), daemon=True
        ).start()

    def _bgSearch(self, query, scope="all"):
        try:
            items = []
            extractors = []
            target_site = scope if scope not in ("", None, "all") else ""
            if target_site in _SEARCH_SITE_ORDER:
                extractors = [(target_site, __import__("extractors." + target_site, fromlist=["search"]))]
            else:
                for name in _SEARCH_SITE_ORDER:
                    try:
                        extractors.append((name, __import__("extractors." + name, fromlist=["search"])))
                    except Exception:
                        pass
            for site_name, module in extractors:
                search_fn = getattr(module, "search", None)
                if not callable(search_fn):
                    continue
                try:
                    for item in search_fn(query) or []:
                        item["_site"] = site_name
                        item["_m_type"] = item.get("type", "movie")
                        items.append(item)
                except Exception as e:
                    my_log("Search failed for {}: {}".format(site_name, e))
            callInMainThread(self._onSearchResults, items, query, scope)
        except Exception as e:
            my_log("_bgSearch error: {}".format(e))
            callInMainThread(self["status"].setText, "فشل البحث")

    def _onSearchResults(self, items, query, scope="all"):
        if not items:
            self["status"].setText("لا توجد نتائج لـ: {}".format(query))
            self["menu"].setList(["مفيش نتائج"])
            return
        items = _rank_search_items(items, query)
        if not items:
            self["status"].setText("لا توجد نتائج مطابقة لـ: {}".format(query))
            self["menu"].setList(["لا توجد نتائج مطابقة"])
            return
        subtitle = "بحث في {} — {} نتيجة".format(_search_scope_label(scope), len(items))
        self._setHeader(
            "نتائج: {}".format(query),
            subtitle
        )
        self._setList(items)

    def _openItem(self, item):
        self.session.open(
            ArabicPlayerDetail,
            item=item,
            site=item.get("_site", self._site),
            m_type=item.get("_m_type", self._m_type)
        )


# ─── Search Screen ────────────────────────────────────────────────────────────
class ArabicPlayerSearch(Screen):
    skin = """
    <screen name="ArabicPlayerSearch" position="center,center" size="1920,1080"
            flags="wfNoBorder">
        <ePixmap position="0,0" size="1920,1080" pixmap="{}/images/bg_search.png" zPosition="0" alphatest="blend" />
        <widget name="bg"       position="0,0"   size="1920,1080" backgroundColor="#0D1117" zPosition="1" />

        <!-- Header -->
        <widget name="title"    position="60,30" size="900,54"  font="Regular;45" foregroundColor="#00E5FF" transparent="1" zPosition="3" />
        <widget name="subtitle" position="60,90" size="1800,36" font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="3" />

        <!-- Query Box -->
        <widget name="query_box" position="60,150" size="1800,105" backgroundColor="#161B22" zPosition="2" />
        <widget name="query_label" position="90,165" size="180,27" font="Regular;24" foregroundColor="#00E5FF" transparent="1" zPosition="3" />
        <widget name="query"    position="90,198" size="1740,39" font="Regular;33" foregroundColor="#F0F6FC" transparent="1" zPosition="3" />

        <!-- Scope Box -->
        <widget name="scope_box" position="60,278" size="1800,72" backgroundColor="#1C2333" zPosition="2" />
        <widget name="scope_label" position="90,296" size="165,30" font="Regular;24" foregroundColor="#E040FB" transparent="1" zPosition="3" />
        <widget name="scope"    position="270,294" size="1560,33" font="Regular;28" foregroundColor="#F0F6FC" transparent="1" zPosition="3" />

        <!-- Suggestions -->
        <widget name="suggestions_box" position="60,372" size="1800,570" backgroundColor="#161B22" zPosition="2" />
        <widget name="suggestions_title" position="90,390" size="450,30" font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="3" />
        <widget name="suggestions" position="87,435" size="1746,480" zPosition="3"
                scrollbarMode="showOnDemand"
                foregroundColor="#F0F6FC"
                foregroundColorSelected="#00E5FF"
                backgroundColor="#161B22"
                backgroundColorSelected="#21262D"
                font="Regular;32" itemHeight="38" />

        <!-- Footer -->
        <widget name="hint"     position="60,960" size="1800,33" font="Regular;22" foregroundColor="#8B949E" transparent="1" zPosition="3" halign="center" />
        <widget name="key_red"  position="60,1002" size="420,33" font="Regular;24" foregroundColor="#FF6B6B" transparent="1" zPosition="3" halign="center" />
        <widget name="key_green" position="522,1002" size="420,33" font="Regular;24" foregroundColor="#39D98A" transparent="1" zPosition="3" halign="center" />
        <widget name="key_yellow" position="984,1002" size="420,33" font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="3" halign="center" />
        <widget name="key_blue" position="1446,1002" size="420,33" font="Regular;24" foregroundColor="#58A6FF" transparent="1" zPosition="3" halign="center" />
    </screen>
    """.format(PLUGIN_PATH)

    def __init__(self, session, current_site="egydead", default_scope="all", query=""):
        Screen.__init__(self, session)
        self._current_site = current_site
        self._query = query or ""
        self._scope = default_scope or "all"

        self["bg"] = Label("")
        self["title"] = Label("بحث احترافي")
        self["subtitle"] = Label("اكتب الاسم واختر النطاق للبحث في المصدر الحالي أو كل المصادر.")
        self["query_box"] = Label("")
        self["query_label"] = Label("نص البحث")
        self["query"] = Label("")
        self["scope_box"] = Label("")
        self["scope_label"] = Label("النطاق")
        self["scope"] = Label("")
        self["suggestions_box"] = Label("")
        self["suggestions_title"] = Label("اقتراحات سريعة")
        self["suggestions"] = MenuList([])
        self["hint"] = Label("OK يفتح الاقتراح  |  أعلى/أسفل للتنقل  |  أحمر: مسح  |  أصفر: اكتب  |  أزرق: نطاق")
        self["key_red"] = Label("مسح")
        self["key_green"] = Label("ابحث الآن")
        self["key_yellow"] = Label("اكتب")
        self["key_blue"] = Label("تبديل النطاق")
        self._suggestions = []
        self._suggestion_ticket = 0

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self._submit_or_edit,
                "cancel": self.close,
                "up": self._suggestion_up,
                "down": self._suggestion_down,
                "left": self._toggle_scope,
                "right": self._toggle_scope,
                "red": self._clear_query,
                "green": self._submit,
                "yellow": self._edit_query,
                "blue": self._toggle_scope,
            },
            -1
        )

        self.onLayoutFinish.append(self._init_search)

    def _init_search(self):
        self._refresh_suggestions()
        self._refresh()

    def _refresh(self):
        preview = self._query or "اكتب اسم فيلم أو مسلسل أو ممثل"
        self["query"].setText(_wrap_ui_text(preview, width=42, max_lines=2))
        self["scope"].setText(_search_scope_label(self._scope if self._scope else "all"))
        self._refresh_suggestion_list()

    def _refresh_suggestion_list(self):
        if not self._suggestions:
            self["suggestions_title"].setText("اقتراحات سريعة")
            self["suggestions"].setList(["لا توجد اقتراحات حالياً"])
            return
        self["suggestions_title"].setText("اقتراحات سريعة: {}".format(len(self._suggestions)))
        rows = []
        for item in self._suggestions:
            meta = []
            if item.get("source"):
                meta.append(item.get("source"))
            if item.get("kind"):
                meta.append(item.get("kind"))
            if item.get("year"):
                meta.append(item.get("year"))
            label = _single_line_text(item.get("title", ""), width=34, fallback="اقتراح")
            meta_text = " | ".join([x for x in meta if x])
            if meta_text:
                label = "{} [{}]".format(label, meta_text)
            rows.append(label)
        self["suggestions"].setList(rows)

    def _refresh_suggestions(self):
        self._suggestions = _library_search_suggestions(self._query, self._current_site, limit=6)
        self._refresh_suggestion_list()
        ticket = self._suggestion_ticket = self._suggestion_ticket + 1
        if len((self._query or "").strip()) >= 2 and _tmdb_enabled():
            threading.Thread(target=self._bg_tmdb_suggestions, args=(self._query, ticket), daemon=True).start()

    def _bg_tmdb_suggestions(self, query, ticket):
        suggestions = _tmdb_search_suggestions(query, limit=6)
        callInMainThread(self._merge_tmdb_suggestions, query, ticket, suggestions)

    def _merge_tmdb_suggestions(self, query, ticket, suggestions):
        if ticket != self._suggestion_ticket:
            return
        if (query or "").strip() != (self._query or "").strip():
            return
        seen = set(_normalize_query(item.get("query", item.get("title", ""))) for item in self._suggestions)
        for item in suggestions:
            norm = _normalize_query(item.get("query", item.get("title", "")))
            if not norm or norm in seen:
                continue
            seen.add(norm)
            self._suggestions.append(item)
        self._suggestions = self._suggestions[:8]
        self._refresh_suggestion_list()

    def _toggle_scope(self):
        self._scope = self._current_site if self._scope == "all" else "all"
        self._refresh_suggestions()
        self._refresh()

    def _clear_query(self):
        self._query = ""
        self._refresh_suggestions()
        self._refresh()

    def _edit_query(self):
        from Screens.VirtualKeyBoard import VirtualKeyBoard
        self.session.openWithCallback(
            self._onKeyboard,
            VirtualKeyBoard,
            title="ابحث عن فيلم أو مسلسل",
            text=self._query
        )

    def _onKeyboard(self, result):
        if result is None:
            return
        self._query = result.strip()
        self._refresh_suggestions()
        self._refresh()

    def _suggestion_up(self):
        if self._suggestions:
            self["suggestions"].up()

    def _suggestion_down(self):
        if self._suggestions:
            self["suggestions"].down()

    def _submit_or_edit(self):
        idx = self["suggestions"].getSelectedIndex()
        if self._suggestions and idx >= 0 and idx < len(self._suggestions):
            chosen = self._suggestions[idx]
            self.close(((chosen.get("query") or chosen.get("title") or "").strip(), self._scope or "all"))
            return
        if self._query.strip():
            self._submit()
        else:
            self._edit_query()

    def _submit(self):
        query = self._query.strip()
        if not query:
            self._edit_query()
            return
        self.close((query, self._scope or "all"))


class ArabicPlayerSettings(Screen):
    skin = """
    <screen name="ArabicPlayerSettings" position="center,center" size="1920,1080"
            flags="wfNoBorder">
        <ePixmap position="0,0" size="1920,1080" pixmap="{}/images/bg_settings.png" zPosition="0" alphatest="blend" />
        <widget name="bg"     position="0,0"   size="1920,1080" backgroundColor="#0D1117" zPosition="1" />

        <!-- Header -->
        <widget name="title"  position="60,30" size="900,57"  font="Regular;45" foregroundColor="#00E5FF" transparent="1" zPosition="3" />
        <widget name="owner"  position="60,96" size="600,36"  font="Regular;27" foregroundColor="#FFD740" transparent="1" zPosition="3" />
        <widget name="site"   position="60,138" size="1800,36" font="Regular;24" foregroundColor="#8B949E" transparent="1" zPosition="3" />

        <!-- Body -->
        <widget name="body_box" position="60,195" size="1800,720" backgroundColor="#161B22" zPosition="2" />
        <widget name="body"   position="90,218" size="1740,675" font="Regular;28" foregroundColor="#F0F6FC" transparent="1" zPosition="3" />

        <!-- Footer -->
        <widget name="hint"   position="60,939" size="1800,36" font="Regular;22" foregroundColor="#8B949E" transparent="1" zPosition="3" halign="center" />
        <widget name="key_yellow_label" position="450,987" size="450,36" font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="3" halign="center" />
        <widget name="key_blue_label"   position="990,987" size="450,36" font="Regular;24" foregroundColor="#58A6FF" transparent="1" zPosition="3" halign="center" />
    </screen>
    """.format(PLUGIN_PATH)

    def __init__(self, session, current_site):
        Screen.__init__(self, session)
        self._current_site = current_site
        self["bg"] = Label("")
        self["title"] = Label("الإعدادات وحول النسخة")
        self["owner"] = Label("")
        self["site"] = Label("")
        self["body_box"] = Label("")
        self["body"] = ScrollLabel("")
        self["hint"] = Label("OK / Back للإغلاق  |  أصفر: مفتاح TMDb  |  أزرق: حذف المفتاح")
        self["key_yellow_label"] = Label("تعديل مفتاح TMDb")
        self["key_blue_label"] = Label("حذف المفتاح")
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.close,
                "cancel": self.close,
                "up": self["body"].pageUp,
                "down": self["body"].pageDown,
                "left": self["body"].pageUp,
                "right": self["body"].pageDown,
                "yellow": self._edit_tmdb_key,
                "blue": self._clear_tmdb_key,
            },
            -1
        )
        self._refresh()

    def _refresh(self):
        self["owner"].setText("المالك: {}".format(_get_config("owner", _PLUGIN_OWNER)))
        self["site"].setText("المصدر الحالي: {}  |  {}".format(_site_label(self._current_site), _site_tagline(self._current_site)))
        api_key = (_get_config("tmdb_api_key", "") or "").strip()
        body = (
            "ArabicPlayer v{version}\n\n"
            "TMDb:\n"
            "• الحالة: {tmdb_status}\n"
            "• المفتاح الحالي: {tmdb_key}\n\n"
            "المكتبة:\n"
            "• المفضلة: {fav_count}\n"
            "• السجل: {hist_count}\n\n"
            "ما الجديد في النسخة الحالية:\n"
            "• إثراء معلومات الفيلم أو المسلسل من TMDb عند توفر المفتاح\n"
            "• دعم مفضلة وسجل محفوظين محليًا\n"
            "• واجهة إعدادات حقيقية بدل الرسالة القديمة\n"
            "• ترتيب أنظف للنتائج والسيرفرات\n\n"
            "طريقة الاستخدام:\n"
            "• اضغط الأصفر لإدخال أو تعديل مفتاح TMDb\n"
            "• اضغط الأزرق لحذف المفتاح الحالي\n"
            "• من شاشة التفاصيل استخدم الأحمر لإضافة العنصر إلى المفضلة"
        ).format(
            version=_PLUGIN_VERSION,
            tmdb_status="مفعل" if api_key else "غير مفعل",
            tmdb_key=("********" + api_key[-4:]) if api_key else "غير مضبوط",
            fav_count=len(_favorite_items()),
            hist_count=len(_history_items()),
        )
        self["body"].setText(body)

    def _edit_tmdb_key(self):
        from Screens.VirtualKeyBoard import VirtualKeyBoard
        self.session.openWithCallback(
            self._on_tmdb_key_entered,
            VirtualKeyBoard,
            title="أدخل TMDb API Key",
            text=_get_config("tmdb_api_key", "")
        )

    def _on_tmdb_key_entered(self, value):
        if value is None:
            return
        _set_config("tmdb_api_key", value.strip())
        self._refresh()

    def _clear_tmdb_key(self):
        _set_config("tmdb_api_key", "")
        self._refresh()


# ─── Detail / Episode Screen ──────────────────────────────────────────────────
class ArabicPlayerDetail(Screen):
    skin = """
    <screen name="ArabicPlayerDetail" position="center,center" size="1920,1080"
            flags="wfNoBorder">
        <ePixmap position="0,0" size="1920,1080" pixmap="{}/images/bg_detail.png" zPosition="0" alphatest="blend" />
        <widget name="bg"          position="0,0"    size="1920,1080" backgroundColor="#0D1117" zPosition="1" />

        <!-- Poster Panel -->
        <widget name="poster_box"  position="45,30"  size="420,600" backgroundColor="#1C2333" zPosition="2" />
        <widget name="poster"      position="68,52"  size="375,555" zPosition="4" alphatest="blend" />

        <!-- Info Panel -->
        <widget name="info_box"    position="495,30" size="1380,405" backgroundColor="#161B22" zPosition="2" />
        <widget name="badge"       position="525,52" size="1320,33"  font="Regular;26" foregroundColor="#E040FB" transparent="1" zPosition="4" />
        <widget name="title"       position="525,93" size="1320,90"  font="Regular;42" foregroundColor="#00E5FF" transparent="1" zPosition="4" />
        <widget name="meta"        position="525,189" size="1320,60" font="Regular;27" foregroundColor="#FFD740" transparent="1" zPosition="4" />
        <widget name="facts"       position="525,255" size="1320,42" font="Regular;24" foregroundColor="#8B949E" transparent="1" zPosition="4" />
        <widget name="source"      position="525,300" size="1320,42" font="Regular;24" foregroundColor="#58A6FF" transparent="1" zPosition="4" />
        <widget name="tmdb_note"   position="525,348" size="1320,33" font="Regular;22" foregroundColor="#39D98A" transparent="1" zPosition="4" />

        <!-- Plot Panel -->
        <widget name="plot_box"    position="495,450" size="1380,180" backgroundColor="#1C2333" zPosition="2" />
        <widget name="plot_title"  position="525,465" size="600,30"  font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="4" />
        <widget name="plot"        position="525,504" size="1320,150"  font="Regular;27" foregroundColor="#F0F6FC" transparent="1" halign="block" valign="top" zPosition="4" />

        <!-- Menu Panel -->
        <widget name="menu_box"    position="45,652" size="1830,315" backgroundColor="#161B22" zPosition="2" />
        <widget name="section"     position="75,663" size="1770,36"  font="Regular;26" foregroundColor="#FFD740" transparent="1" zPosition="4" />
        <widget name="menu"        position="72,708" size="1776,240" zPosition="4"
                scrollbarMode="showOnDemand"
                foregroundColor="#F0F6FC"
                foregroundColorSelected="#00E5FF"
                backgroundColor="#161B22"
                backgroundColorSelected="#21262D"
                font="Regular;32" itemHeight="57" />

        <!-- Footer -->
        <widget name="key_red"     position="45,990" size="420,36" font="Regular;24" foregroundColor="#FF6B6B" transparent="1" zPosition="4" />
        <widget name="key_yellow"  position="510,990" size="420,36" font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="4" />
        <widget name="status"      position="990,990" size="870,36"  font="Regular;22" foregroundColor="#8B949E" transparent="1" halign="right" zPosition="4" />
    </screen>
    """.format(PLUGIN_PATH)

    def __init__(self, session, item, site="egydead", m_type="movie"):
        Screen.__init__(self, session)
        self.session = session
        self._item   = item
        self._site   = site
        self._m_type = m_type
        self._data   = None
        self._servers = []
        self._episodes = []
        self._tmp_posters = []
        self._poster_loaded = False
        self._raw_title = ""

        self["bg"]     = Label("")
        self["poster_box"] = Label("")
        self["info_box"] = Label("")
        self["plot_box"] = Label("")
        self["menu_box"] = Label("")
        self["poster"] = Pixmap()
        self["badge"]  = Label("")
        self["title"]  = Label(item.get("title", ""))
        self["meta"]   = Label("")
        self["facts"]  = Label("")
        self["source"] = Label("")
        self["tmdb_note"] = Label("")
        self["plot_title"] = Label("القصة")
        self["plot"]   = Label("")
        self["section"] = Label("جاري التحضير...")
        self["menu"]   = MenuList([])
        self["key_red"] = Label("المفضلة")
        self["key_yellow"] = Label("تحديث TMDb")
        self["status"] = Label("جاري تحميل التفاصيل...")

        self.picLoad = ePicLoad()
        self.picLoad.PictureData.get().append(self._paintPoster)

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok":     self._onOk,
                "cancel": self._onCancel,
                "red":    self._toggleFavorite,
                "yellow": self._refreshTMDb,
                "up":     lambda: self["menu"].up(),
                "down":   lambda: self["menu"].down(),
                "left":   lambda: self["menu"].pageUp(),
                "right":  lambda: self["menu"].pageDown(),
            },
            -1
        )

        self.onLayoutFinish.append(self._load)
        self.onExecBegin.append(self._refreshPoster)

    def _load(self):
        threading.Thread(target=self._bgLoad, args=(self._site, self._item["url"], self._m_type), daemon=True).start()

    def _bgLoad(self, site, url, m_type):
        _done = [False]
        def _watchdog():
            if not _done[0]:
                my_log("_bgLoad watchdog: timeout for {}".format(url[:60]))
                callInMainThread(self["status"].setText, u"Timeout — please try again")
        _wt = threading.Timer(30, _watchdog)
        _wt.daemon = True
        _wt.start()
        try:
            from extractors.base import log
            log("Detail _bgLoad: START site={}, m_type={}".format(site, m_type))
            extractor = _get_extractor(site)
            get_page = getattr(extractor, "get_page", None)
            if not get_page:
                callInMainThread(self["status"].setText, u"لا توجد بيانات")
                return
            if site == "egydead":
                data = get_page(url, m_type=m_type)
            else:
                data = get_page(url)
            merged_seed = dict(self._item or {})
            merged_seed.update(data or {})
            data = _merge_tmdb_data(merged_seed)
            _done[0] = True
            callInMainThread(self._onLoaded, data)
        except Exception as e:
            _done[0] = True
            from extractors.base import log
            log("_bgLoad error: {} -- trying TMDb fallback".format(e))
            try:
                fallback = _merge_tmdb_data(dict(self._item or {}))
                if fallback and (fallback.get("plot") or fallback.get("poster")):
                    callInMainThread(self._onLoaded, fallback)
                else:
                    callInMainThread(self["status"].setText,
                        u"فشل التحميل — {}".format(str(e)[:40]))
            except Exception as e2:
                log("TMDb fallback failed: {}".format(e2))
                callInMainThread(self["status"].setText,
                    u"فشل التحميل — {}".format(str(e)[:40]))
        finally:
            _wt.cancel()

    def _onCancel(self):
        try:
            self.picLoad.PictureData.get().remove(self._paintPoster)
        except Exception:
            pass
        for p in self._tmp_posters:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        self.close()

    def _paintPoster(self, picData=None):
        ptr = self.picLoad.getData()
        if ptr:
            self["poster"].instance.setPixmap(ptr)
            self["poster"].show()
            self._poster_loaded = True

    def _onLoaded(self, data):
        if not data:
            self["status"].setText("تعذر تحميل الصفحة")
            return

        self._data = data
        current_title = _strip_arabic_from_english_title(
            data.get("title") or self._item.get("title", ""))
        self._raw_title = re.sub(r"\s+", " ", current_title).strip()
        self["title"].setText(_wrap_ui_text(current_title, width=30, max_lines=2, fallback="بدون عنوان"))

        meta = []
        if data.get("year"):   meta.append(data["year"])
        if data.get("rating"): meta.append("{}/10".format(data["rating"]))
        if data.get("type"):   meta.append(_TYPE_LABELS.get(data["type"], "عنصر"))
        if data.get("genres"): meta.append(data["genres"])
        self["meta"].setText(_wrap_ui_text("   ".join(meta), width=58, max_lines=2))
        self["badge"].setText("{}  •  {}".format(_site_label(self._site), _TYPE_LABELS.get(data.get("type"), "عنصر")))
        facts = [
            "المفضلة: {}  |  النسخة: {}  |  الوصف: {}".format(
                "محفوظ" if _is_favorite(self._item.get("url")) else "غير محفوظ",
                _PLUGIN_VERSION,
                "موجود" if _pick_plot_text(data, self._item) != "القصة غير متوفرة حالياً لهذا العنصر." else "غير متوفر"
            ),
        ]
        self["facts"].setText(_single_line_text("".join(facts), width=62))
        counts = []
        has_episodes = bool(data.get("items"))
        is_series_item = (
            data.get("type") in ("series", "show")
            or self._item.get("type") in ("series", "show")
            or has_episodes
        )
        if is_series_item:
            counts.append("الحلقات: {}".format(len([e for e in data.get("items", []) if e.get("type") == "episode"])))
        else:
            counts.append("السيرفرات: {}".format(len([s for s in data.get("servers", []) if s.get("url")])))
        if data.get("year"):
            counts.append("السنة: {}".format(data.get("year")))
        self["source"].setText(_wrap_ui_text("المصدر: {}  |  {}".format(_site_label(self._site), "  |  ".join(counts)), width=58, max_lines=2))
        self["tmdb_note"].setText("TMDb: تم تعزيز البيانات والبوستر" if data.get("_tmdb") else "TMDb: لا توجد بيانات إضافية حالياً")
        if is_series_item:
            plot_label = "قصة المسلسل"
        else:
            plot_label = "قصة الفيلم"
        if current_title:
            plot_label = "{}: {}".format(plot_label, current_title[:32])
        self["plot_title"].setText(_single_line_text(plot_label, width=46, fallback="القصة"))

        plot_text, plot_source = _pick_plot_text_with_source(data, self._item)
        plot_text = re.sub(r"^\[.*?\]\s*|^المصدر:\s*.*?\|\s*", "", plot_text)
        _MID_SITES = (
            "EgyDead", "Wecima", "Akoam", "ArabSeed",
            "TopCinema", "TopCinemaa", "FaselHD", "Shaheed", "Shaheed4u",
        )
        for _ms in _MID_SITES:
            plot_text = re.sub(
                r"\s*[|\-]\s*" + re.escape(_ms) + r"[^\u0600-\u06ff\n]{0,25}",
                " ", plot_text, flags=re.I)
            plot_text = re.sub(
                r"\u0639\u0644\u0649\s+\u0645\u0648\u0642\u0639\s+" + re.escape(_ms)
                + r"[^\u0600-\u06ff\n]{0,30}",
                " ", plot_text, flags=re.I)
        plot_text = re.sub(r"  +", " ", plot_text).strip()
        my_log("Detail plot source: {} | len={}".format(plot_source, len(plot_text)))

        _pt = (plot_text or "").strip()
        if len(_pt) > 500:
            _pt = _pt[:500].rsplit(" ", 1)[0] + "…"
        # FIX #2: use correct U+200F RIGHT-TO-LEFT MARK (not embedding chars U+202B/202C)
        _ar_count = sum(1 for _c in _pt[:80] if "\u0600" <= _c <= "\u06ff")
        if _ar_count > int(len(_pt[:80]) * 0.3):
            _pt = "\u200f" + _pt
        self["plot"].setText(_pt)

        self._servers = _sort_servers([s for s in data.get("servers", []) if s.get("url")])
        self._episodes = [e for e in data.get("items", []) if e.get("type") == "episode"]

        my_log("Detail _onLoaded: servers={}, items={}".format(len(self._servers), len(self._episodes)))

        is_series = (
            data.get("type") in ("series", "show")
            or self._item.get("type") in ("series", "show")
            or bool(self._episodes)
        )

        if is_series:
            if self._episodes:
                self["section"].setText(_single_line_text("الحلقات المتاحة: {}  |  اختر الحلقة المطلوبة".format(len(self._episodes)), width=90))
                self["menu"].setList(["{}. {}".format(i + 1, _single_line_text(ep.get("title", "Episode"), width=58, fallback="حلقة")) for i, ep in enumerate(self._episodes)])
                self["status"].setText(self._status_hint("اختار حلقة — OK"))
            else:
                self["section"].setText("الحلقات المتاحة: 0")
                self["menu"].setList(["لا توجد حلقات متاحة حالياً"])
                self["status"].setText("لا توجد حلقات")
        else:
            if self._servers:
                self["section"].setText(_single_line_text("السيرفرات المتاحة: {}  |  اختر الجودة أو السيرفر".format(len(self._servers)), width=90))
                self["menu"].setList(["{}. {}".format(i + 1, _single_line_text(s.get("name", "Server"), width=58, fallback="Server")) for i, s in enumerate(self._servers)])
                self["status"].setText(self._status_hint("اختار سيرفر — OK"))
            else:
                self["section"].setText("السيرفرات المتاحة: 0")
                self["menu"].setList(["لا توجد سيرفرات متاحة"])
                self["status"].setText("لا توجد سيرفرات")

        poster_url = data.get("poster") or self._item.get("poster", "")
        if poster_url:
            threading.Thread(
                target=self._downloadPoster, args=(poster_url,), daemon=True
            ).start()

    def _status_hint(self, prefix):
        fav_state = "محفوظ" if _is_favorite(self._item.get("url")) else "غير محفوظ"
        tmdb_state = "TMDb مفعل" if _tmdb_enabled() else "TMDb غير مفعل"
        return "{}  |  {}  |  {}".format(prefix, fav_state, tmdb_state)

    def _refreshPoster(self):
        if getattr(self, "_poster_loaded", False):
            try:
                self["poster"].show()
            except Exception:
                pass
            return
        poster_url = None
        if self._data and self._data.get("poster"):
            poster_url = self._data["poster"]
        elif self._item.get("poster"):
            poster_url = self._item["poster"]
        if poster_url:
            self._downloadPoster(poster_url)
        else:
            callInMainThread(self["poster"].hide)

    def _downloadPoster(self, url):
        try:
            if not url: return
            if url.startswith("//"): url = "https:" + url

            import urllib.request as urllib2
            try:
                from urllib.parse import urlparse, quote, urlunparse
                p = list(urlparse(url))
                p[2] = quote(p[2])
                p[4] = quote(p[4])
                url = urlunparse(p)
            except Exception: pass

            cached = _get_cached_poster(url)
            if cached:
                callInMainThread(self.picLoad.setPara, (self["poster"].instance.size().width(), self["poster"].instance.size().height(), 1, 1, 0, 1, "#000000"))
                callInMainThread(self.picLoad.startDecode, cached)
                return

            cache_path = _poster_cache_path(url)
            req = urllib2.Request(url, headers={"User-Agent": SAFE_UA})
            data = urllib2.urlopen(req, timeout=10).read()

            save_path = cache_path or "/tmp/ap_detail_{}.jpg".format(int(time.time()))
            with open(save_path, "wb") as f:
                f.write(data)
            if not cache_path:
                self._tmp_posters.append(save_path)
            callInMainThread(self.picLoad.setPara, (self["poster"].instance.size().width(), self["poster"].instance.size().height(), 1, 1, 0, 1, "#000000"))
            callInMainThread(self.picLoad.startDecode, save_path)
        except Exception as e:
            my_log("_downloadPoster error: {} (URL: {})".format(e, url))

    def _onOk(self):
        idx = self["menu"].getSelectedIndex()
        if idx < 0:
            return

        is_series = bool(
            self._data and (
                self._data.get("type") in ("series", "show")
                or self._item.get("type") in ("series", "show")
                or self._episodes
            )
        )

        if is_series:
            if idx >= len(self._episodes):
                return
            ep = self._episodes[idx]
            self.session.open(ArabicPlayerDetail, ep, self._site, "episode")
        else:
            if idx >= len(self._servers):
                return
            server = self._servers[idx]
            self["status"].setText("Extracting stream...")
            self["status"].show()
            threading.Thread(target=self._bgExtract, args=(server,), daemon=True).start()

    def _toggleFavorite(self):
        base = self._data or self._item
        entry = _entry_from_item(
            dict(self._item, **(base or {})),
            self._site,
            self._m_type,
            {"type": (base or {}).get("type", self._item.get("type", self._m_type))}
        )
        added = _toggle_favorite_entry(entry)
        self["status"].setText("تمت الإضافة إلى المفضلة" if added else "تم الحذف من المفضلة")
        if self._data:
            self._onLoaded(self._data)

    def _refreshTMDb(self):
        if not _tmdb_enabled():
            self["status"].setText("أضف TMDb API Key من الإعدادات أولاً")
            return
        self["status"].setText("جاري تحديث البيانات من TMDb...")
        threading.Thread(target=self._bgRefreshTMDb, daemon=True).start()

    def _bgRefreshTMDb(self):
        try:
            merged = _merge_tmdb_data(self._data or self._item)
            callInMainThread(self._onLoaded, merged)
        except Exception as e:
            my_log("TMDb refresh failed: {}".format(e))
            callInMainThread(self["status"].setText, "فشل تحديث TMDb")

    def _bgExtract(self, server):
        try:
            from extractors.base import log
            log("Detail _bgExtract: START extracting for server={}".format(server.get("name", "Unknown")))

            extract_fn = None
            try:
                extractor = _get_extractor(self._site)
                extract_fn = getattr(extractor, "extract_stream", None)
            except Exception:
                extract_fn = None

            if extract_fn is None:
                from extractors.base import extract_stream as extract_fn

            url, qual, final_ref = extract_fn(server["url"])

            if url:
                log("Detail _bgExtract: SUCCESS! URL: {}".format(url))
                callInMainThread(self._onStreamFound, url, qual, final_ref, server)
            else:
                log("Detail _bgExtract: FAILED to resolve stream")
                callInMainThread(self["status"].setText, "فشل استخراج الرابط — جرب سيرفر تاني")
        except Exception as e:
            log("Detail _bgExtract CRITICAL ERROR: {}".format(e))
            callInMainThread(self["status"].setText, "خطأ في النظام: {}".format(str(e)[:30]))

    def _onStreamFound(self, stream_url, quality, final_ref, server):
        if not stream_url:
            self["status"].setText("{} — غير متاح، جرب سيرفر آخر".format(server["name"]))
            return
        my_log("Stream found: {} [{}]".format(stream_url, quality))
        history_entry = _entry_from_item(
            dict(self._item, **(self._data or {})),
            self._site,
            self._m_type,
            {
                "server_name": server.get("name", ""),
                "quality": quality or "",
                "last_stream_url": stream_url,
            }
        )
        _upsert_library_item("history", history_entry, limit=120)

        # FIX #3: removed unused _quality_tag variable
        # Use raw single-line title
        title = getattr(self, "_raw_title", None) or \
                re.sub(r"\s+", " ", self["title"].getText()).strip()

        try:
            raw_url = stream_url.strip()
            if "|" in raw_url:
                main_url, old_params = raw_url.split("|", 1)
            else:
                main_url, old_params = raw_url, ""

            lower_main_url = main_url.lower()
            is_media_url = any(marker in lower_main_url for marker in (
                ".m3u8", ".mp4", ".mkv", ".mp3", ".ts", ".avi",
                "master.txt", "/hls", "/stream", "/playlist"
            ))
            is_embed_page = any(marker in lower_main_url for marker in (
                "/embed-", "/embed/", "/e/", "/watch/"
            ))
            if is_embed_page and not is_media_url:
                self["status"].setText("الرابط صفحة تشغيل وليس ملف فيديو — جرب سيرفر آخر")
                return

            headers = {"User-Agent": SAFE_UA}

            if final_ref:
                headers["Referer"] = final_ref

            if old_params:
                for p in old_params.split("&"):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        if k not in headers: headers[k] = v

            header_str = "&".join(["{}={}".format(k, v) for k, v in headers.items()])
            pure_url = main_url.split("|")[0].strip()
            url = pure_url + "#" + header_str if header_str else pure_url

            _item_url = self._item.get("url", "")
            _saved_pos = _get_saved_position(_item_url)
            if _saved_pos > 30:
                if _saved_pos >= 3600:
                    _hours_r = _saved_pos // 3600
                    _mins_r = (_saved_pos % 3600) // 60
                    _secs_r = _saved_pos % 60
                    resume_text = "Resume from {:02d}:{:02d}:{:02d}?".format(_hours_r, _mins_r, _secs_r)
                else:
                    _mins_r = _saved_pos // 60
                    _secs_r = _saved_pos % 60
                    resume_text = "Resume from {}:{:02d}?".format(_mins_r, _secs_r)

                def _on_resume(_ans, _u=url, _t=title, _iu=_item_url, _sp=_saved_pos):
                    if not _ans:
                        _save_position(_iu, 0)
                    _play(self.session, _u, _t, resume_pos=_sp if _ans else 0, item_url=_iu)
                self["status"].setText("جاري فتح المشغل...")
                self.session.openWithCallback(
                    _on_resume, MessageBox,
                    resume_text,
                    MessageBox.TYPE_YESNO, timeout=8, default=True)
            else:
                self["status"].setText("Opening player...")
                _play(self.session, url, title, resume_pos=0, item_url=_item_url)
            self["status"].hide()

        except Exception as e:
            my_log("Error opening player: {}".format(e))
            self["status"].setText("خطأ في المشغل: {}".format(str(e)[:60]))


from Screens.InfoBar import InfoBar

def _build_remote_play_candidates(url):
    url = str(url).strip()
    plain_url = url.split("#", 1)[0].strip()
    headers = {}
    if "#" in url:
        for part in url.split("#", 1)[1].split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                headers[key] = value
    candidates = []
    seen = set()

    def add_candidate(p_type, svc_url, label, uses_proxy=False):
        key = (p_type, svc_url)
        if not svc_url or key in seen:
            return
        seen.add(key)
        candidates.append((p_type, svc_url, label, uses_proxy))

    if plain_url.startswith("https://") or plain_url.startswith("http://"):
        proxy_params = {"url": plain_url}
        if headers.get("Referer"):
            proxy_params["referer"] = headers["Referer"]
        if headers.get("User-Agent"):
            proxy_params["ua"] = headers["User-Agent"]
        proxied = "http://127.0.0.1:{}/stream?{}".format(_PROXY_PORT, urlencode(proxy_params))
        start_proxy()
        legacy_raw = url.replace("#", "|") if "#" in url else url
        legacy_proxied = "http://127.0.0.1:{}/{}".format(_PROXY_PORT, legacy_raw)
    else:
        proxied = ""
        legacy_proxied = ""

    is_hls = any(x in plain_url.lower() for x in (".m3u8", "master.txt", "/hls", "/playlist"))

    if is_hls:
        add_candidate(4097, plain_url, "4097 مباشر HLS")
        if proxied:
            add_candidate(4097, proxied, "4097 + proxy HLS", True)
        add_candidate(4097, url, "4097 + headers HLS")
        add_candidate(8193, plain_url, "8193 مباشر")
        if proxied:
            add_candidate(8193, proxied, "8193 + proxy", True)
    else:
        if proxied:
            add_candidate(5001, proxied, "5001 + proxy", True)
        add_candidate(5001, plain_url, "5001 مباشر")
        add_candidate(8193, plain_url, "8193 مباشر")
        if proxied:
            add_candidate(8193, proxied, "8193 + proxy", True)
        add_candidate(4097, plain_url, "4097 مباشر")
        if proxied:
            add_candidate(4097, proxied, "4097 + proxy", True)
        add_candidate(4097, url, "4097 + headers")
    if legacy_proxied:
        add_candidate(4097, legacy_proxied, "4097 + proxy قديم", True)

    if os.path.exists("/usr/bin/exteplayer3"):
        if plain_url.startswith("http://") or plain_url.startswith("https://"):
            add_candidate(5002, plain_url, "5002 مباشر")
            if proxied:
                add_candidate(5002, proxied, "5002 + proxy", True)
        add_candidate(5002, url, "5002 + headers")

    return candidates


def _copy_service_ref(sref):
    if not sref:
        return None
    try:
        return eServiceReference(sref.toString())
    except Exception:
        try:
            return eServiceReference(str(sref.toString()))
        except Exception:
            return sref


def _capture_previous_service(session):
    try:
        return _copy_service_ref(session.nav.getCurrentlyPlayingServiceReference())
    except Exception as e:
        my_log("Capture previous service failed: {}".format(e))
        return None


def _restore_previous_service(session, previous_service):
    if not previous_service:
        return
    try:
        session.nav.stopService()
    except Exception:
        pass
    try:
        session.nav.playService(previous_service)
        my_log("Previous service restored")
    except Exception as e:
        my_log("Restore previous service failed: {}".format(e))


# ─── Simple Player ────────────────────────────────────────────────────────────
class ArabicPlayerSimplePlayer(Screen):
    skin = """
    <screen name="ArabicPlayerSimplePlayer" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="transparent">

        <widget name="osd_shadow"   position="148,856" size="1624,230" backgroundColor="#000000" zPosition="9" />
        <widget name="overlay_bg"   position="160,860" size="1600,210" backgroundColor="#0A0E14" zPosition="10" />
        <widget name="osd_topline"  position="160,860" size="1600,3" backgroundColor="#00E5FF" zPosition="11" />
        <widget name="osd_titlebar" position="160,860" size="1600,52" backgroundColor="#0D1520" zPosition="11" />
        <widget name="osd_title"    position="180,868" size="1180,38" font="Regular;30" foregroundColor="#00E5FF" transparent="1" zPosition="12" halign="left" />
        <widget name="osd_durtext"  position="1380,868" size="360,38" font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="12" halign="right" />
        <widget name="prog_bar"     position="160,906" size="1600,30" font="Regular;22" foregroundColor="#00B4D8" transparent="1" zPosition="12" halign="left" />
        <widget name="osd_elapsed"  position="180,938" size="320,44" font="Regular;36" foregroundColor="#FFD740" transparent="1" zPosition="12" />
        <widget name="status"       position="640,938" size="640,44" font="Regular;36" foregroundColor="#39D98A" transparent="1" zPosition="12" halign="center" />
        <widget name="osd_hints"    position="1220,938" size="520,44" font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="12" halign="right" />
        <widget name="osd_divider"  position="160,982" size="1600,2" backgroundColor="#1C2333" zPosition="11" />
        <widget name="osd_keybar"   position="160,984" size="1600,46" backgroundColor="#0D1520" zPosition="11" />
        <widget name="osd_keys"     position="180,992" size="1560,34" font="Regular;24" foregroundColor="#484F58" transparent="1" zPosition="12" halign="center" />
        <widget name="osd_botline"  position="160,1027" size="1600,3" backgroundColor="#0A2040" zPosition="11" />
    </screen>
    """

    def __init__(self, session, title, candidates, previous_service=None, resume_pos=0, item_url=""):
        Screen.__init__(self, session)
        self["overlay_bg"]   = Label("")
        self["status"]       = Label("جاري التشغيل...")
        self["osd_shadow"]   = Label("")
        self["osd_titlebar"] = Label("")
        self["osd_title"]    = Label("")
        self["osd_durtext"]  = Label("")
        self["osd_topline"]  = Label("")
        self["prog_bar"]     = Label("")
        self["osd_elapsed"]  = Label("")
        self["osd_hints"]    = Label("")
        self["osd_divider"]  = Label("")
        self["osd_keybar"]   = Label("")
        self["osd_keys"]     = Label("")
        self["osd_botline"]  = Label("")
        _raw = (title or "").strip()
        _qtag_m = re.search(r'\s*(\[\d+p\])\s*$', _raw)
        _qtag = _qtag_m.group(1) if _qtag_m else ""
        _bare = _raw[:_qtag_m.start()].strip() if _qtag_m else _raw
        if len(_bare) > 34:
            _bare = _bare[:32].rstrip() + u"\u2026"
        self.title = (_bare + " " + _qtag).strip() if _qtag else _bare
        self.candidates = candidates or []
        self.previous_service = _copy_service_ref(previous_service)
        self.sref = None
        self._play_confirmed = False
        self._candidate_idx = -1
        self._candidate_start_ts = 0
        self._candidate_uses_proxy = False
        self._candidate_label = ""
        self._handoff = False
        self._restored_previous = False
        self._resume_pos = int(resume_pos or 0)
        self._item_url  = item_url or ""
        self._seek_timer = eTimer()
        self._seek_timer.callback.append(self.__doSeek)
        self._seek_retry_count = 0
        self._seek_verify_timer = eTimer()
        self._seek_verify_timer.callback.append(self.__verifySeek)
        self._hide_timer = eTimer()
        self._hide_timer.callback.append(self.__hideOSD)
        self._osd_update_timer = eTimer()
        self._osd_update_timer.callback.append(self.__updateOSD)
        self._osd_visible = False
        self._total_secs  = 0
        self._osd_auto_hide_secs = 4
        self._paused = False
        self._paused_elapsed = 0
        self._force_confirmation_timer = eTimer()
        self._force_confirmation_timer.callback.append(self.__forceConfirm)

        self["actions"] = ActionMap(
            ["OkCancelActions", "MediaPlayerActions", "InfobarSeekActions", "DirectionActions", "ColorActions"],
            {
                "cancel":           self.__onExit,
                "stop":             self.__onExit,
                "ok":               self.__togglePause,
                "playpauseService": self.__togglePause,
                "right":            lambda: self.__seek(+10),
                "left":             lambda: self.__seek(-10),
                "seekFwd":          lambda: self.__seek(+60),
                "seekBack":         lambda: self.__seek(-60),
                "green":            self.__onRestart,
            },
            -1
        )
        self._retry_timer = eTimer()
        self._retry_timer.callback.append(self.__onTimeout)
        eventmap = {
            iPlayableService.evTuneFailed: self.__onFailed,
            iPlayableService.evEOF: self.__onFailed,
        }
        ev_video = getattr(iPlayableService, "evVideoSizeChanged", None)
        if ev_video is not None:
            eventmap[ev_video] = self.__onConfirmed
        self._events = ServiceEventTracker(screen=self, eventmap=eventmap)
        self.onLayoutFinish.append(self.__initOSD)
        self.onLayoutFinish.append(self.__playNext)
        self.onClose.append(self.__stop)

    _OSD_WIDGETS = [
        "osd_shadow","overlay_bg","osd_topline","osd_botline",
        "osd_titlebar","osd_title","osd_durtext",
        "prog_bar","osd_elapsed",
        "status","osd_hints","osd_divider",
        "osd_keybar","osd_keys",
    ]

    def __initOSD(self):
        for w in self._OSD_WIDGETS:
            try: self[w].hide()
            except: pass

    def __hideOSD(self):
        self._osd_visible = False
        try: self._osd_update_timer.stop()
        except: pass
        for w in self._OSD_WIDGETS:
            try: self[w].hide()
            except: pass

    def __showOSD(self, auto_hide=True):
        self._osd_visible = True
        for w in self._OSD_WIDGETS:
            try: self[w].show()
            except: pass
        self.__updateOSD()
        try:
            self._osd_update_timer.start(1000, False)
        except: pass
        if auto_hide:
            try:
                self._hide_timer.stop()
                self._hide_timer.start(self._osd_auto_hide_secs * 1000, True)
            except: pass

    def __updateOSD(self):
        if not self._osd_visible:
            try: self._osd_update_timer.stop()
            except: pass
            return
        try:
            if self._paused:
                elapsed = self._paused_elapsed
            else:
                wall = _GLOBAL_PLAY_START_WALL
                base = _GLOBAL_PLAY_START_POS
                if wall and base >= 0:
                    elapsed = max(0, int((time.time() - wall) + base))
                else:
                    elapsed = 0
            he = elapsed // 3600; me = (elapsed % 3600) // 60; se = elapsed % 60
            self["osd_elapsed"].setText("{:02d}:{:02d}:{:02d}".format(he, me, se))
            total = self._total_secs
            if not total:
                try:
                    svc = self.session.nav.getCurrentService()
                    seek = svc and svc.seek()
                    if seek:
                        r = seek.getLength()
                        if r and r[0] == 0 and r[1] > 0:
                            total = r[1] // 90000
                            self._total_secs = total
                except: pass
            if total > 0:
                rem = max(0, total - elapsed)
                pct = min(1.0, float(elapsed) / float(total))
                hr = rem // 3600
                mr = (rem % 3600) // 60
                sr = rem % 60
                ht = total // 3600
                mt = (total % 3600) // 60
                st = total % 60
                self["osd_durtext"].setText("-{:02d}:{:02d}:{:02d}  {:02d}:{:02d}:{:02d}".format(hr, mr, sr, ht, mt, st))
                BAR_W = 96
                filled = max(0, min(BAR_W, int(pct * BAR_W)))
                bar = u"█" * filled + u"░" * (BAR_W - filled)
                self["prog_bar"].setText(u"{} {:.1f}%".format(bar, pct * 100))
            else:
                self["osd_durtext"].setText("")
                self["prog_bar"].setText("")
            self["osd_keys"].setText("OK=Pause   << -10s   +10s >>   <<< -60s   +60s >>>   Green=إعادة+استئناف   Stop=حفظ&خروج")
        except Exception as e:
            my_log("updateOSD error: {}".format(e))

    def __forceConfirm(self):
        if not self._play_confirmed:
            my_log("Force confirm (unconditional)")
            self.__onConfirmed()

    def __playNext(self):
        global _PROXY_LAST_HIT, _PROXY_LAST_BYTES
        self._candidate_idx += 1
        if self._candidate_idx >= len(self.candidates):
            self["status"].setText("تعذر تشغيل الرابط على كل المحاولات")
            return

        p_type, svc_url, label, uses_proxy = self.candidates[self._candidate_idx]
        self._play_confirmed = False
        self._candidate_start_ts = time.time()
        self._candidate_uses_proxy = uses_proxy
        self._candidate_label = label
        if uses_proxy:
            _PROXY_LAST_HIT = 0
            _PROXY_LAST_BYTES = 0
        self.sref = eServiceReference(p_type, 0, svc_url)
        if sys.version_info[0] == 3:
            self.sref.setName(str(self.title))
        else:
            self.sref.setName(self.title.encode("utf-8", "ignore"))

        self["status"].setText("جاري التشغيل... {}".format(label))
        my_log("Play attempt: {}".format(label))
        try:
            self.session.nav.stopService()
        except: pass
        try:
            self.session.nav.playService(self.sref)
            self._retry_timer.start(12000, True)
            self._force_confirmation_timer.start(3000, True)
        except Exception as e:
            my_log("SimplePlayer fallback error: {}".format(e))
            self.__playNext()

    def __onConfirmed(self):
        if self._play_confirmed:
            return
        self._play_confirmed = True
        try:
            self._retry_timer.stop()
            self._force_confirmation_timer.stop()
        except: pass
        my_log("Play confirmed: {}".format(self._candidate_label))
        _start_pos_tracker(self.session, self._item_url, start_pos=0)
        if self._resume_pos > 30:
            self._seek_retry_count = 0
            self._seek_timer.start(6000, True)
        self["osd_title"].setText(self.title)
        self["status"].setText(u"▶ Playing")
        self._total_secs = 0
        self.__showOSD(True)

    def __togglePause(self):
        try:
            svc = self.session.nav.getCurrentService()
            if not svc:
                self.__showOSD(True); return
            p = svc.pause()
            if not p:
                self.__showOSD(True); return
            if self._paused:
                p.unpause()
                self._paused = False
                global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
                _GLOBAL_PLAY_START_POS = self._paused_elapsed
                _GLOBAL_PLAY_START_WALL = time.time()
                self["status"].setText(u"▶ Playing")
            else:
                wall = _GLOBAL_PLAY_START_WALL
                base = _GLOBAL_PLAY_START_POS
                if wall:
                    elapsed = int((time.time() - wall) + base)
                else:
                    elapsed = 0
                self._paused_elapsed = max(0, elapsed)
                p.pause()
                self._paused = True
                self["status"].setText(u"⏸ Paused")
            self.__showOSD(True)
        except Exception as e:
            my_log("togglePause error: {}".format(e))
            self.__showOSD(True)

    def __seek(self, delta_secs):
        try:
            svc = self.session.nav.getCurrentService()
            if not svc: return
            sk = svc.seek()
            if not sk: return
            global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
            global _GLOBAL_LAST_SEEK_TARGET
            _wall = _GLOBAL_PLAY_START_WALL
            _base = _GLOBAL_PLAY_START_POS
            if _wall:
                elapsed = time.time() - _wall
            else:
                elapsed = 0
            current_est = int(_base + elapsed)
            target = max(0, current_est + int(delta_secs))
            _tot = self._total_secs
            if _tot > 0:
                target = min(target, _tot - 3)
            sk.seekTo(target * 90000)
            _GLOBAL_LAST_SEEK_TARGET = target
            _GLOBAL_PLAY_START_POS = max(0, target - 2)
            _GLOBAL_PLAY_START_WALL = time.time()
            if self._paused:
                self._paused_elapsed = target
            self._total_secs = 0
            _th = target // 3600; _tm = (target % 3600) // 60; _ts = target % 60
            _arr = u"➡" if delta_secs > 0 else u"⬅"
            self["status"].setText(u"{} {:02d}:{:02d}:{:02d}".format(_arr, _th, _tm, _ts))
            self.__showOSD(True)
            self._hide_timer.start(2500, True)
        except Exception as e:
            my_log("seek error: {}".format(e))

    def __onRestart(self):
        my_log("Restart+Resume requested by green button")
        if self._item_url:
            try:
                if self._paused:
                    secs = self._paused_elapsed
                else:
                    wall = _GLOBAL_PLAY_START_WALL
                    base = _GLOBAL_PLAY_START_POS
                    secs = int((time.time() - wall) + base) if wall else 0
                if secs > 30:
                    _save_position(self._item_url, secs)
                    self._resume_pos = secs
                    my_log("Restart: saved pos={}s, will re-seek after restart".format(secs))
            except Exception as e:
                my_log("Restart pos-save error: {}".format(e))
        try:
            self._seek_timer.stop()
            self._seek_verify_timer.stop()
        except: pass
        self._play_confirmed = False
        self._seek_retry_count = 0
        try:
            self.session.nav.stopService()
        except: pass
        self._candidate_idx = -1
        self["status"].setText(u"إعادة التشغيل + استئناف من {}:{:02d}...".format(
            self._resume_pos // 60, self._resume_pos % 60) if self._resume_pos > 30 else u"إعادة التشغيل...")
        self.__showOSD(True)
        restart_timer = eTimer()
        restart_timer.callback.append(self.__playNext)
        restart_timer.start(500, True)

    def __onExit(self):
        try:
            if self._item_url:
                if self._paused:
                    secs = self._paused_elapsed
                else:
                    wall = _GLOBAL_PLAY_START_WALL
                    base = _GLOBAL_PLAY_START_POS
                    if wall:
                        secs = int((time.time() - wall) + base)
                    else:
                        secs = 0
                _tot = self._total_secs
                if _tot > 0:
                    secs = min(secs, _tot - 5)
                secs = max(0, secs)
                if secs > 30:
                    _save_position(self._item_url, secs)
                    my_log("Exit save: {}s".format(secs))
        except Exception as e:
            my_log("Exit save error: {}".format(e))
        try:
            self.session.nav.stopService()
        except: pass
        _stop_pos_tracker()
        _restore_previous_service(self.session, self.previous_service)
        self.close()

    def __stop(self):
        self.__hideOSD()
        for t in ("_seek_timer","_seek_verify_timer","_retry_timer","_hide_timer","_osd_update_timer","_force_confirmation_timer"):
            try: getattr(self, t).stop()
            except: pass

    def __onFailed(self):
        if self._play_confirmed:
            return
        try:
            self._retry_timer.stop()
            self._force_confirmation_timer.stop()
        except: pass
        my_log("Play failed event: {}".format(self._candidate_label))
        self.__playNext()

    def __onTimeout(self):
        global _PROXY_LAST_HIT, _PROXY_LAST_BYTES
        if self._play_confirmed:
            return
        if self._candidate_uses_proxy and _PROXY_LAST_HIT >= self._candidate_start_ts and _PROXY_LAST_BYTES > 0:
            my_log("Play proxy confirmed by traffic: {} bytes".format(_PROXY_LAST_BYTES))
            self.__onConfirmed()
            return
        my_log("Play timeout: {}".format(self._candidate_label))
        self.__playNext()

    def __doSeek(self):
        if not self._resume_pos or self._resume_pos <= 30:
            my_log("Seek skipped: resume_pos={}".format(self._resume_pos))
            return
        try:
            svc = self.session.nav.getCurrentService()
            seek = svc and svc.seek()
            if not seek:
                self._seek_retry_count += 1
                if self._seek_retry_count <= 3:
                    my_log("doSeek: no seek interface, retry {}/3 in 4s".format(self._seek_retry_count))
                    self._seek_timer.start(4000, True)
                else:
                    my_log("doSeek: giving up after 3 retries")
                return

            seek.seekTo(self._resume_pos * 90000)
            my_log("Resume seekTo: {}s (attempt {})".format(self._resume_pos, self._seek_retry_count + 1))
            self._total_secs = 0

            self._seek_verify_timer.start(4000, True)

            if self._osd_visible:
                self.__updateOSD()
        except Exception as e:
            my_log("doSeek failed: {} — retry {}/3".format(e, self._seek_retry_count))
            self._seek_retry_count += 1
            if self._seek_retry_count <= 3:
                self._seek_timer.start(4000, True)

    def __verifySeek(self):
        if not self._resume_pos or self._resume_pos <= 30:
            return
        global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS, _GLOBAL_LAST_SEEK_TARGET
        try:
            svc = self.session.nav.getCurrentService()
            seek = svc and svc.seek()
            actual_pos = -1

            if seek:
                try:
                    r = seek.getPlayPosition()
                    if r and r[0] == 0 and r[1] > 0:
                        actual_pos = int(r[1] // 90000)
                except Exception:
                    pass

            if actual_pos >= 0:
                if actual_pos >= max(0, self._resume_pos - 60):
                    _GLOBAL_PLAY_START_POS = actual_pos
                    _GLOBAL_PLAY_START_WALL = time.time()
                    _GLOBAL_LAST_SEEK_TARGET = actual_pos
                    if self._paused:
                        self._paused_elapsed = actual_pos
                    my_log("verifySeek OK via PTS: actual={}s target={}s".format(
                        actual_pos, self._resume_pos))
                else:
                    if seek and self._seek_retry_count <= 3:
                        self._seek_retry_count += 1
                        seek.seekTo(self._resume_pos * 90000)
                        my_log("verifySeek double-tap {}/3: actual={}s target={}s".format(
                            self._seek_retry_count, actual_pos, self._resume_pos))
                        self._seek_verify_timer.start(3000, True)
                    else:
                        _GLOBAL_PLAY_START_POS = max(0, self._resume_pos - 2)
                        _GLOBAL_PLAY_START_WALL = time.time()
                        my_log("verifySeek giving up, setting display to target {}s".format(
                            self._resume_pos))
            else:
                if self._seek_retry_count <= 2:
                    if seek:
                        seek.seekTo(self._resume_pos * 90000)
                    self._seek_retry_count += 1
                    _GLOBAL_PLAY_START_POS = max(0, self._resume_pos - 2)
                    _GLOBAL_PLAY_START_WALL = time.time()
                    _GLOBAL_LAST_SEEK_TARGET = self._resume_pos
                    if self._paused:
                        self._paused_elapsed = self._resume_pos
                    my_log("verifySeek double-tap {}/3 (no PTS), target={}s".format(
                        self._seek_retry_count, self._resume_pos))
                    self._seek_verify_timer.start(3000, True)
                else:
                    my_log("verifySeek: max retries reached, target={}s".format(self._resume_pos))
        except Exception as e:
            my_log("verifySeek error: {}".format(e))

    def __restorePrevious(self):
        if self._restored_previous:
            return
        self._restored_previous = True
        _restore_previous_service(self.session, self.previous_service)


# ─── Global play function ─────────────────────────────────────────────────────
def _play(session, url, title, resume_pos=0, item_url=""):
    try:
        svc_url = str(url).strip()
        is_remote = svc_url.startswith("http://") or svc_url.startswith("https://")
        previous_service = _capture_previous_service(session)

        if is_remote:
            session.open(ArabicPlayerSimplePlayer, title, _build_remote_play_candidates(svc_url), previous_service, resume_pos=resume_pos, item_url=item_url)
            return

        sref = eServiceReference(4097, 0, svc_url)
        if sys.version_info[0] == 3:
            sref.setName(str(title))
        else:
            sref.setName(title.encode("utf-8", "ignore"))

        try:
            from Screens.InfoBar import MoviePlayer
            callback = lambda *args: _restore_previous_service(session, previous_service)
            try:
                if is_remote:
                    session.openWithCallback(callback, MoviePlayer, sref, streamMode=True, askBeforeLeaving=False)
                else:
                    session.openWithCallback(callback, MoviePlayer, sref, askBeforeLeaving=False)
            except TypeError:
                session.openWithCallback(callback, MoviePlayer, sref)
        except Exception as e:
            my_log("[PLAY_INFOBAR_FALLBACK] " + str(e))
            session.open(ArabicPlayerSimplePlayer, title, _build_remote_play_candidates(svc_url), previous_service)
    except Exception as e:
        my_log("[PLAY_ERROR] " + str(e))

# ─── Splash Screen ───────────────────────────────────────────────────────────
class ArabicPlayerSplash(Screen):
    skin = """
    <screen name="ArabicPlayerSplash" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#000000">
        <widget name="splash_pic" position="0,0" size="1920,1080" zPosition="1" alphatest="blend" />
    </screen>
    """

    def __init__(self, session):
        self.skin = ArabicPlayerSplash.skin.format(PLUGIN_PATH)
        Screen.__init__(self, session)
        self["splash_pic"] = Pixmap()
        self._timer = eTimer()
        self._timer.callback.append(self._onFinish)

        self.picLoad = ePicLoad()
        self.picLoad.PictureData.get().append(self._paintSplash)

        self.onLayoutFinish.append(self._start)

    def _start(self):
        splash_path = os.path.join(PLUGIN_PATH, "images", "splash.png")
        if os.path.exists(splash_path):
            self.picLoad.setPara((1920, 1080, 1, 1, 0, 1, "#000000"))
            self.picLoad.startDecode(splash_path)
        self._timer.start(2500, True)

    def _paintSplash(self, picData=None):
        ptr = self.picLoad.getData()
        if ptr:
            self["splash_pic"].instance.setPixmap(ptr)
            self["splash_pic"].show()

    def _onFinish(self):
        self._timer.stop()
        try:
            self.picLoad.PictureData.get().remove(self._paintSplash)
        except Exception:
            pass
        self.session.open(ArabicPlayerHome)
        self.close()


# ─── Plugin Entry Points ──────────────────────────────────────────────────────
def main(session, **kwargs):
    session.open(ArabicPlayerSplash)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name        = _PLUGIN_NAME,
            description = "تشغيل أفلام ومسلسلات من مواقع عربية",
            where       = PluginDescriptor.WHERE_PLUGINMENU,
            icon        = "plugin.png",
            fnc         = main
        ),
        PluginDescriptor(
            name        = _PLUGIN_NAME,
            description = "تشغيل أفلام ومسلسلات من مواقع عربية",
            where       = PluginDescriptor.WHERE_EXTENSIONSMENU,
            fnc         = main
        ),
    ]
`````

## File: README.md
`````markdown
# 🎬 ArabicPlayer Plugin (Enigma2)
![ArabicPlayer Logo](plugin.png)

تطبيق **ArabicPlayer** هو بلاجن مخصص لأجهزة الاستقبال العاملة بنظام **Enigma2** (مثل Novaler 4K Pro, Dreambox, Vu+ وغيرها)، يتيح لك مشاهدة أحدث الأفلام والمسلسلات العربية والأجنبية المترجمة مباشرة من أشهر المواقع العربية بجودة عالية وبدون تقطيع.

---

## 🌟 المميزات (Premium Version)
*   **تصميم عصري "Neon Mode"**: واجهة مستخدم جديدة كلياً مع شعار وخلفية "Splash Screen" احترافية.
*   **دعم شامل لأشهر المواقع**:
    *   ✅ **TopCinema**: تم إصلاح استخراج السيرفرات وتجاوز مشاكل "صالة العرض".
    *   ✅ **FaselHD**: استعادة كافة الأقسام (أفلام، مسلسلات، أنمي) مع دعم السيرفرات المشفّرة.
    *   ✅ **Wecima**: بحث سريع وروابط مباشرة.
    *   ✅ **EgyDead**: مكتبة ضخمة وبوسترات بوضوح عالٍ.
    *   ✅ **Akoam & ArabSeed**: محتوى متجدد وتصنيفات مرتبة.
*   **تجاوز الحماية**: محاكاة كاملة للمتصفح لتجاوز حماية الـ WAF و Cloudflare.
*   **دعم TMDB**: جلب معلومات الأفلام والبوسترات المفقودة تلقائياً.

---

## 📸 معاينة الواجهة الجديدة (Splash Screen)
![Splash Screen](images/splash.png)

---

## 🚀 طريقة التثبيت
يمكنك تثبيت البلاجن مباشرة عبر **التلنت (Telnet)** باستخدام هذا الأمر:
```bash
wget -q "--no-check-certificate" https://raw.githubusercontent.com/asdrere123-alt/ArabicPlayer/main/installer.sh -O - | /bin/sh
```

أو يدوياً:
1. قم بتحميل الملفات ووضعها في المسار:
   `/usr/lib/enigma2/python/Plugins/Extensions/ArabicPlayer`
2. قم بعمل **Restart Enigma2**.
3. استمتع بالمشاهدة!

---

## 👨‍💻 المطور
*   **الإصدار**: 1.3.1 (Modern UI)
*   **بواسطة**: أحمد إبراهيم

---

> [!TIP]
> جميع الحقوق محفوظة للمواقع الأصلية، هذا البلاجن هو وسيلة لتسهيل الوصول للمحتوى على أجهزة الإنيجما 2 فقط.
`````

## File: repomix-output-westy4ever-Arabic-player-mod.md
`````markdown
# Directory Structure
```
extractors/
  __init__.py
  akoam.py
  arablionztv.py
  arabseed.py
  base.py
  egydead.py
  fasel.py
  shaheed.py
  topcinema.py
  wecima.py
images/
  bg_detail.png
  bg_search.png
  bg_settings.png
  bg.png
  playback_a_ff.png
  playback_a_pause.png
  playback_a_play.png
  playback_a_rew.png
  playback_banner_sd.png
  playback_banner.png
  playback_buff_progress.png
  playback_cbuff_progress.png
  playback_ffmpeg_logo.png
  playback_gstreamer_logo.png
  playback_loop_off.png
  playback_loop_on.png
  playback_pointer.png
  playback_progress.png
  playerclock.xml
  playerskin.xml
  settings.json
  splash.png
  sub_synchro.png
plugin.png
plugin.py
README.md
```

# Files

## File: extractors/__init__.py
````python
# ArabicPlayer Extractors Package
````

## File: extractors/akoam.py
````python
# -*- coding: utf-8 -*-
import re
from urllib.parse import urljoin
from .base import fetch, log

# Updated to work with both akwams.com.co and akwam.com.co
# (with or without trailing slash)
MAIN_URL = "https://akwam.com.co/one/"


def _clean_title(title):
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("تحميل", "")
        .strip()
    )


def _extract_items_from_homepage(html):
    """
    Extract movies/series/anime from the new akwam.com.co homepage structure.
    Pattern matches: div with class="item" or similar, containing an <a> with poster image.
    """
    items = []
    seen = set()
    
    # Primary pattern for akwam.com.co
    patterns = [
        # Format: <div class="item"> <a href="URL" class="movie"> <img data-src="POSTER" alt="TITLE">
        r'<div class="item">\s*<a href="([^"]+)" class="movie">\s*<img[^>]+data-src="([^"]+)"[^>]+alt="([^"]+)"',
        # Fallback: simpler pattern
        r'<a href="(/[^"]+)" class="movie">\s*<img[^>]+(?:data-src|src)="([^"]+)"[^>]+alt="([^"]+)"',
        # Another variant
        r'<div[^>]*class="[^"]*item[^"]*"[^>]*>.*?<a href="([^"]+)".*?<img[^>]+(?:data-src|src)="([^"]+)"[^>]+alt="([^"]+)"',
    ]
    
    for pattern in patterns:
        for match in re.findall(pattern, html or "", re.S):
            link, img, title = match
            if link in seen or not link.startswith("/"):
                continue
            seen.add(link)
            
            # Determine type from URL or context
            if "/series/" in link or "/مسلسل" in link or "series" in title.lower():
                item_type = "series"
            elif "/anime/" in link or "/انمي" in link:
                item_type = "anime"
            else:
                item_type = "movie"
            
            # Build full URL
            full_url = urljoin(MAIN_URL, link)
            
            items.append({
                "title": _clean_title(title),
                "url": full_url,
                "poster": img,
                "type": item_type,
                "_action": "details",
            })
    
    return items


def get_categories():
    """Return main category links (Movies, Series, Anime)"""
    # The new site uses query parameters for filtering
    return [
        {"title": "🎬 Movies",    "url": urljoin(MAIN_URL, "?filter=movies"), "type": "category", "_action": "category"},
        {"title": "📺 TV Series", "url": urljoin(MAIN_URL, "?filter=series"), "type": "category", "_action": "category"},
        {"title": "🍥 Anime",     "url": urljoin(MAIN_URL, "?filter=anime"),  "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    """
    Fetch items from a category page (movies, series, anime, or search results)
    """
    html, _ = fetch(url, referer=MAIN_URL)
    if not html:
        return []

    items = _extract_items_from_homepage(html)
    seen_urls = {item["url"] for item in items}
    
    # Pagination - look for next page link
    next_patterns = [
        r'<a href="([^"]+)"[^>]*class="[^"]*next[^"]*"[^>]*>',
        r'<link[^>]*rel=["\']next["\'][^>]*href=["\']([^"\']+)["\']',
        r'<a[^>]*>\s*التالي\s*</a>\s*<a href="([^"]+)"',
    ]
    
    for pattern in next_patterns:
        next_match = re.search(pattern, html, re.I)
        if next_match:
            next_url = next_match.group(1).replace("&amp;", "&")
            if not next_url.startswith("http"):
                next_url = urljoin(MAIN_URL, next_url)
            if next_url not in seen_urls:
                items.append({
                    "title": "➡️ Next Page",
                    "url": next_url,
                    "type": "category",
                    "_action": "category",
                })
            break
    
    return items


def _quote_url(url):
    from urllib.parse import quote
    return quote(url, safe=":/%?=&")


def get_page(url):
    """
    Extract details (title, poster, plot, episodes, servers) from a movie/series/episode page
    """
    url = _quote_url(url)
    html, final_url = fetch(url, referer=MAIN_URL)
    
    result = {
        "url": url,
        "title": "",
        "poster": "",
        "plot": "",
        "servers": [],
        "items": [],
        "type": "movie",
    }
    
    if not html:
        return result

    # Extract title
    title_patterns = [
        r'<h1[^>]*>(.*?)</h1>',
        r'<div[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</div>',
        r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"',
    ]
    for pattern in title_patterns:
        m = re.search(pattern, html, re.S | re.I)
        if m:
            result["title"] = _clean_title(m.group(1))
            break

    # Extract poster
    poster_patterns = [
        r'<img[^>]+class="[^"]*img-fluid[^"]*"[^>]+src="([^"]+)"',
        r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"',
        r'<div[^>]*class="[^"]*poster[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"',
        r'<img[^>]+data-src="([^"]+)"[^>]+alt="[^"]*poster',
    ]
    for pattern in poster_patterns:
        m = re.search(pattern, html, re.I)
        if m:
            result["poster"] = m.group(1).replace("&amp;", "&")
            break

    # Extract plot/summary
    plot_patterns = [
        r'<p[^>]+class="[^"]*plot[^"]*"[^>]*>(.*?)</p>',
        r'<div[^>]*class="[^"]*summary[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="[^"]*description[^"]*"[^>]*>(.*?)</div>',
        r'القصة\s*:?\s*</?(?:strong|span|div)?[^>]*>\s*(.*?)(?:</|$)',
    ]
    for pattern in plot_patterns:
        m = re.search(pattern, html, re.S | re.I)
        if m:
            result["plot"] = _clean_title(re.sub(r'<[^>]+>', '', m.group(1)))
            break

    # Check if this is a series page (has episodes)
    is_series = (
        "/series/" in (final_url or url) or
        "/مسلسل" in result["title"] or
        "مسلسل" in result["title"] or
        ("الحلقة" in html and ("episode" in html.lower() or "حلقة" in html))
    ) and "/episode/" not in (final_url or url)

    if is_series:
        result["type"] = "series"
        seen_eps = set()
        
        # Episode extraction patterns for akwam.com.co
        episode_patterns = [
            # Pattern: <a href="/series/.../episode/1"> <div class="episode-number">1</div>
            r'<a[^>]+href="([^"]+/(?:episode|حلقة)/[^"]+)"[^>]*>.*?(?:<div[^>]*class="[^"]*episode[^"]*"[^>]*>(.*?)</div>|<span[^>]*>(?:Episode|حلقة)\s*(\d+))',
            # Simple pattern for episode links
            r'<a[^>]+href="([^"]*episode[^"]*)"[^>]*>(.*?)</a>',
            # Any link containing /episode/ or /حلقة/
            r'href="([^"]*(?:/episode/|/حلقة/)[^"]*)"',
        ]
        
        for pattern in episode_patterns:
            for match in re.findall(pattern, html, re.S | re.I):
                if isinstance(match, tuple):
                    ep_url = match[0]
                    ep_title = match[1] if len(match) > 1 else ""
                else:
                    ep_url = match
                    ep_title = ""
                
                full_url = urljoin(final_url or url, ep_url).replace("&amp;", "&")
                if full_url in seen_eps:
                    continue
                seen_eps.add(full_url)
                
                if not ep_title or ep_title.strip() == "":
                    ep_num = len(result["items"]) + 1
                    ep_title = f"Episode {ep_num}"
                else:
                    ep_title = _clean_title(ep_title)
                
                result["items"].append({
                    "title": ep_title,
                    "url": full_url,
                    "type": "episode",
                    "_action": "details",
                })
        
        # Sort episodes by number if possible
        def extract_ep_num(item):
            match = re.search(r'(\d+)', item["title"])
            return int(match.group(1)) if match else 999
        result["items"].sort(key=extract_ep_num)
        
        return result

    # For movies or episode pages, extract watch/download servers
    watch_links = []
    
    # Find watch/download links
    link_patterns = [
        r'href="(https?://(?:go\.)?akwam(?:s)?\.com\.co/(?:watch|download|episode)/[^"]+)"',
        r'href="(/watch/[^"]+)"',
        r'href="(/download/[^"]+)"',
        r'<a[^>]+class="[^"]*btn[^"]*watch[^"]*"[^>]+href="([^"]+)"',
        r'<a[^>]+href="([^"]+)"[^>]*>(?:مشاهدة|تحميل|Watch|Download)',
    ]
    
    for pattern in link_patterns:
        for link in re.findall(pattern, html, re.I):
            if link.startswith("/"):
                link = urljoin(MAIN_URL, link)
            link = link.replace("&amp;", "&").strip()
            if link not in watch_links:
                watch_links.append(link)
    
    # Build server entries
    watch_count = 1
    download_count = 1
    for link in watch_links:
        if "/watch/" in link or "/episode/" in link:
            result["servers"].append({
                "name": f"🎬 Watch {watch_count}",
                "url": link,
                "type": "direct"
            })
            watch_count += 1
        elif "/download/" in link:
            result["servers"].append({
                "name": f"⬇️ Download {download_count}",
                "url": link,
                "type": "direct"
            })
            download_count += 1
        else:
            result["servers"].append({
                "name": f"🌐 Server {len(result['servers']) + 1}",
                "url": link,
                "type": "direct"
            })
    
    return result


def extract_stream(url):
    """
    Extract direct video stream URL from a watch page.
    Handles go.akwam shortener and extracts m3u8/mp4 sources.
    """
    url = (url or "").replace("&amp;", "&").strip()

    # Resolve go.akwam.sv or go.akwams.com.co shortener
    if "go.akwam" in url or "go.akwams" in url:
        html, final_url = fetch(url, referer=MAIN_URL)
        if html:
            resolved = re.search(r'https?://akwam(?:s)?\.com\.co/(?:watch|episode)/[^\s\'"<>]+', html, re.I)
            if resolved:
                url = resolved.group(0).replace("&amp;", "&")
            elif final_url and ("akwam" in final_url or "akwams" in final_url):
                url = final_url

    # Handle akwam watch pages
    if "akwam.com.co/watch/" in url or "akwams.com.co/watch/" in url or \
       "akwam.com.co/episode/" in url or "akwams.com.co/episode/" in url:
        html, final_url = fetch(url, referer=MAIN_URL)
        if html:
            # Try multiple patterns to find video source
            patterns = [
                r'<source[^>]+src="([^"]+)"[^>]*type="video/mp4"',
                r'<source[^>]+src="([^"]+(?:m3u8|mp4)[^"]*)"',
                r'"file"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
                r'"videoUrl"\s*:\s*"([^"]+)"',
                r'data-video-url=["\']([^"\']+)["\']',
                r'src:\s*["\']([^"\']+\.(?:m3u8|mp4))',
                r'<video[^>]+src="([^"]+)"',
                r'<iframe[^>]+src="([^"]+)"',
            ]
            
            for pattern in patterns:
                m = re.search(pattern, html, re.I)
                if m:
                    video_url = m.group(1).replace("\\u0026", "&").replace("&amp;", "&")
                    # If it's an iframe, resolve it recursively
                    if "iframe" in pattern or video_url.startswith("http") and "iframe" not in pattern.lower():
                        # Could be an embedded player
                        from .base import resolve_iframe_chain
                        resolved_stream, _ = resolve_iframe_chain(video_url, referer=url)
                        if resolved_stream:
                            return resolved_stream, None, MAIN_URL
                    if video_url.startswith("http") and (".m3u8" in video_url or ".mp4" in video_url):
                        return video_url, None, MAIN_URL

    # Fallback to base extractor which handles all major video hosts
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
````

## File: extractors/arablionztv.py
````python
# -*- coding: utf-8 -*-
"""
Plugin for arablionztv.xyz
FIX: Replaced f-strings with .format() for Python 2/3.5 compatibility.
FIX: Improved card/episode regex to match modern layouts.
FIX: get_page() now catches data-src/data-lazy-src iframe patterns.
"""

import re
from urllib.parse import urljoin
from .base import fetch, extract_stream as base_extract_stream

MAIN_URL = "https://arablionztv.xyz/"


def _clean_title(title):
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("تحميل", "")
        .replace("فيلم", "")
        .replace("مسلسل", "")
        .strip()
    )


def _full_url(path):
    if not path:
        return ""
    path = path.strip()
    if path.startswith("http"):
        return path
    if path.startswith("//"):
        return "https:" + path
    return urljoin(MAIN_URL, path)


def _extract_boxes(html):
    """
    FIX: Reworked to use a more general card-finding strategy that works
    across common WordPress / custom CMS layouts.
    Returns list of (link, img, title) tuples.
    """
    results = []
    seen = set()

    # Strategy 1: article or post-type containers
    for container in re.findall(
        r'<(?:article|div)[^>]+class="[^"]*(?:item|post|movie|entry)[^"]*"[^>]*>(.*?)</(?:article|div)>',
        html or "", re.S | re.I
    ):
        link_m  = re.search(r'href=["\']([^"\']+)["\']', container)
        title_m = (
            re.search(r'title=["\']([^"\']+)["\']', container) or
            re.search(r'alt=["\']([^"\']+)["\']', container) or
            re.search(r'<h[1-4][^>]*>([^<]+)</h[1-4]>', container, re.I)
        )
        img_m   = re.search(r'(?:data-src|data-lazy-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', container, re.I)

        if link_m and title_m:
            link  = _full_url(link_m.group(1))
            title = _clean_title(title_m.group(1))
            img   = _full_url(img_m.group(1)) if img_m else ""
            if link and link not in seen:
                seen.add(link)
                results.append((link, img, title))

    if results:
        return results

    # Strategy 2: plain <a href> + <img> pattern (broad fallback)
    for m in re.finditer(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*'
        r'(?:[^<]*<[^>]+>[^<]*)*?'
        r'<img[^>]+(?:data-src|data-lazy-src|src)=["\']([^"\']+)["\'][^>]+alt=["\']([^"\']+)["\']',
        html or "", re.S | re.I
    ):
        link  = _full_url(m.group(1))
        img   = _full_url(m.group(2))
        title = _clean_title(m.group(3))
        if link and link not in seen:
            seen.add(link)
            results.append((link, img, title))

    return results


def _extract_episodes(html, base_url):
    episodes = []
    seen = set()

    # Pattern: links containing episode/حلقة with a number
    for m in re.finditer(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(?:[^<]*<[^>]*>)*?'
        r'(?:حلقة|Episode|EP)\s*(\d+)',
        html or "", re.I | re.S
    ):
        url    = _full_url(m.group(1).replace("&amp;", "&"))
        ep_num = m.group(2)
        if url in seen:
            continue
        seen.add(url)
        episodes.append({
            "title":    "حلقة {}".format(ep_num),
            "url":      url,
            "type":     "episode",
            "_action":  "details",
        })
        if len(episodes) >= 100:
            return episodes

    # Fallback: any link containing episode/season in URL
    if not episodes:
        for link in re.findall(r'href=["\']([^"\']*(?:episode|season|ep)[^"\']*)["\']', html, re.I):
            url = _full_url(link.replace("&amp;", "&"))
            if url in seen or "category" in url:
                continue
            seen.add(url)
            episodes.append({
                "title":   "حلقة",
                "url":     url,
                "type":    "episode",
                "_action": "details",
            })
    return episodes


def get_categories():
    return [
        {"title": "🎬 أفلام إنجليزية",  "url": urljoin(MAIN_URL, "category/movies/english-movies/"), "type": "category", "_action": "category"},
        {"title": "🎬 أفلام عربية",     "url": urljoin(MAIN_URL, "category/movies/arabic-movies/"),  "type": "category", "_action": "category"},
        {"title": "🎬 كارتون",          "url": urljoin(MAIN_URL, "category/movies/cartoon/"),        "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات إنجليزية","url": urljoin(MAIN_URL, "category/series/english-series/"),"type": "category", "_action": "category"},
        {"title": "📺 مسلسلات عربية",   "url": urljoin(MAIN_URL, "category/series/arabic-series/"),  "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات تركية",   "url": urljoin(MAIN_URL, "category/series/turkish-series/"), "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        return []

    items = []
    seen  = set()

    for link, img, title in _extract_boxes(html):
        if link in seen:
            continue
        seen.add(link)
        low = link.lower() + " " + title.lower()
        is_series = "/series/" in low or "مسلسل" in low
        items.append({
            "title":   title,
            "url":     link,
            "poster":  img,
            "type":    "series" if is_series else "movie",
            "_action": "details",
        })

    # Pagination
    next_m = (
        re.search(r'<a[^>]+class="next"[^>]+href=["\']([^"\']+)["\']', html, re.I) or
        re.search(r'<link[^>]+rel="next"[^>]+href=["\']([^"\']+)["\']', html, re.I)
    )
    if next_m:
        items.append({
            "title":   "➡️ الصفحة التالية",
            "url":     next_m.group(1).replace("&amp;", "&"),
            "type":    "category",
            "_action": "category",
        })

    return items


def get_page(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    result = {
        "url":     url,
        "title":   "",
        "poster":  "",
        "plot":    "",
        "servers": [],
        "items":   [],
        "type":    "movie",
    }
    if not html:
        return result

    # Title
    title_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
    if title_m:
        result["title"] = _clean_title(title_m.group(1))

    # Poster
    poster_m = (
        re.search(r'<img[^>]+class="[^"]*(?:poster|cover|img-fluid)[^"]*"[^>]+src=["\']([^"\']+)["\']', html, re.I) or
        re.search(r'<meta[^>]+property="og:image"[^>]+content=["\']([^"\']+)["\']', html, re.I)
    )
    if poster_m:
        result["poster"] = poster_m.group(1).replace("&amp;", "&")

    # Plot
    plot_m = (
        re.search(r'<div[^>]*class="[^"]*(?:description|summary|plot)[^"]*"[^>]*>(.*?)</div>', html, re.S | re.I) or
        re.search(r'<p[^>]*class="[^"]*desc[^"]*"[^>]*>(.*?)</p>', html, re.S | re.I)
    )
    if plot_m:
        result["plot"] = re.sub(r'<[^>]+>', ' ', plot_m.group(1)).strip()

    # Series check
    is_series = "/series/" in (final_url or url) or "مسلسل" in result["title"]
    if is_series:
        result["type"]  = "series"
        result["items"] = _extract_episodes(html, final_url or url)
        return result

    # Servers — FIX: added data-src and data-lazy-src to iframe search
    seen_servers = set()
    for m in re.finditer(
        r'<iframe[^>]+(?:src|data-src|data-lazy-src)=["\']([^"\']+)["\']',
        html, re.I
    ):
        iframe_url = m.group(1).strip()
        if iframe_url.startswith("//"):
            iframe_url = "https:" + iframe_url
        if not iframe_url.startswith("http") or iframe_url in seen_servers:
            continue
        seen_servers.add(iframe_url)
        result["servers"].append({
            "name":  "سيرفر {}".format(len(result["servers"]) + 1),
            "url":   iframe_url,
            "type":  "direct",
        })

    # Direct video host links
    for m in re.finditer(
        r'href=["\']'
        r'(https?://(?:streamtape|dood|mixdrop|uqload|voe|vidbom|upstream|'
        r'streamwish|filemoon|lulustream|ok\.ru)[^"\']+)'
        r'["\']',
        html, re.I
    ):
        link = m.group(1)
        if link not in seen_servers:
            seen_servers.add(link)
            result["servers"].append({
                "name":  "مشاهدة {}".format(len(result["servers"]) + 1),
                "url":   link,
                "type":  "direct",
            })

    # Direct media URL fallback
    if not result["servers"]:
        for pat in (
            r'file\s*:\s*["\']([^"\']+)["\']',
            r'src\s*:\s*["\']([^"\']+)["\']',
            r'data-video=["\']([^"\']+)["\']',
        ):
            m = re.search(pat, html, re.I)
            if m:
                result["servers"].append({
                    "name":  "مشاهدة",
                    "url":   m.group(1),
                    "type":  "direct",
                })
                break

    return result


def extract_stream(url):
    if url.startswith("http") and any(x in url.lower() for x in (".m3u8", ".mp4", ".mkv")):
        return url, None, MAIN_URL
    return base_extract_stream(url)
````

## File: extractors/arabseed.py
````python
# -*- coding: utf-8 -*-
import base64
import json
import re
from .base import fetch, log, urljoin

MAIN_URL     = "https://asd.pics/"
QUALITY_ORDER = {"1080": 0, "720": 1, "480": 2}
BLOCKED_HOSTS = ("vidara.to", "bysezejataos.com")


def _clean_title(title):
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("فيلم", "")
        .strip()
    )


def _extract_first(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text or "", re.S)
        if match:
            return match.group(1).strip()
    return ""


def _decode_hidden_url(url):
    url = (url or "").replace("\\/", "/").replace("&amp;", "&").strip()
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith("http"):
        url = urljoin(MAIN_URL, url)
    for key in ("url", "id"):
        marker = key + "="
        if marker not in url:
            continue
        raw = url.split(marker, 1)[1].split("&", 1)[0]
        try:
            raw += "=" * ((4 - len(raw) % 4) % 4)
            decoded = base64.b64decode(raw).decode("utf-8")
            if decoded.startswith("http"):
                return decoded
        except Exception:
            pass
    return url


def _server_priority(server_url):
    lowered = server_url.lower()
    if "reviewrate" in lowered or "reviewtech" in lowered:
        return 0
    if "vidmoly" in lowered:
        return 1
    return 9


def _server_name(server_url, label_hint=""):
    lowered = (server_url or "").lower()
    if "reviewrate" in lowered or "reviewtech" in lowered:
        return "عرب سيد"
    if "vidmoly" in lowered:
        return "VidMoly"
    if label_hint:
        return label_hint.strip()
    domain_match = re.search(r'https?://([^/]+)', server_url or "")
    return domain_match.group(1) if domain_match else "Server"


def _collect_ajax_servers(watch_html, watch_url):
    token = _extract_first(
        [
            r"csrf__token['\"]?\s*[:=]\s*['\"]([^'\"]+)",
            r"csrf_token['\"]?\s*[:=]\s*['\"]([^'\"]+)",
        ],
        watch_html,
    )
    post_id = _extract_first(
        [
            r"psot_id['\"]?\s*[:=]\s*['\"](\d+)",
            r"post_id['\"]?\s*[:=]\s*['\"](\d+)",
        ],
        watch_html,
    )
    home_url = _extract_first([r"main__obj\s*=\s*\{'home__url':\s*'([^']+)'"], watch_html) or MAIN_URL
    if not token or not post_id:
        log("ArabSeed: Missing AJAX token/post_id")
        return []

    quality_url     = urljoin(home_url, "get__quality__servers/")
    watch_server_url = urljoin(home_url, "get__watch__server/")
    results = []
    seen    = set()

    for quality in ("1080", "720", "480"):
        body, _ = fetch(
            quality_url,
            post_data={"post_id": post_id, "quality": quality, "csrf_token": token},
            referer=watch_url,
        )
        if not body:
            continue
        try:
            data = json.loads(body)
        except Exception:
            log("ArabSeed: Failed to decode quality JSON for {}p".format(quality))
            continue
        if data.get("type") != "success":
            continue

        # Direct server in response
        direct_server = _decode_hidden_url(data.get("server", ""))
        if direct_server.startswith("http") and not any(h in direct_server for h in BLOCKED_HOSTS):
            key = (quality, direct_server)
            if key not in seen:
                seen.add(key)
                results.append({
                    "quality": quality,
                    "url":     direct_server,
                    "name":    _server_name(direct_server, "سيرفر عرب سيد"),
                })

        # Server list rows
        server_rows = re.findall(
            r'<li[^>]+data-post="([^"]+)"[^>]+data-server="([^"]+)"[^>]+data-qu="([^"]+)"[^>]*>.*?<span>([^<]+)</span>',
            data.get("html", ""),
            re.S,
        )
        for row_post_id, server_id, row_quality, label in server_rows:
            watch_body, _ = fetch(
                watch_server_url,
                post_data={
                    "post_id":   row_post_id,
                    "quality":   row_quality,
                    "server":    server_id,
                    "csrf_token": token,
                },
                referer=watch_url,
            )
            if not watch_body:
                continue
            try:
                watch_data = json.loads(watch_body)
            except Exception:
                continue
            if watch_data.get("type") != "success" or not watch_data.get("server"):
                continue

            server_url_decoded = _decode_hidden_url(watch_data.get("server", ""))
            if not server_url_decoded.startswith("http"):
                continue
            if any(h in server_url_decoded for h in BLOCKED_HOSTS):
                continue

            key = (row_quality, server_url_decoded)
            if key in seen:
                continue
            seen.add(key)
            results.append({
                "quality": row_quality,
                "url":     server_url_decoded,
                "name":    _server_name(server_url_decoded, label),
            })

    # FIX: if AJAX returned nothing at all, log clearly rather than silent empty
    if not results:
        log("ArabSeed: AJAX returned 0 servers for watch_url={}".format(watch_url))

    results.sort(key=lambda item: (
        QUALITY_ORDER.get(item["quality"], 9),
        _server_priority(item["url"]),
        item["name"],
    ))
    return results


def get_categories():
    return [
        {"title": "🌍 أفلام أجنبي",    "url": urljoin(MAIN_URL, "category/foreign-movies-12/"),  "type": "category", "_action": "category"},
        {"title": "🇪🇬 أفلام عربي",   "url": urljoin(MAIN_URL, "category/arabic-movies-12/"),   "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أجنبي",  "url": urljoin(MAIN_URL, "category/foreign-series-5/"),   "type": "category", "_action": "category"},
        {"title": "🇸🇦 مسلسلات عربي", "url": urljoin(MAIN_URL, "category/arabic-series-10/"),   "type": "category", "_action": "category"},
        {"title": "🎭 مسلسلات انمي",   "url": urljoin(MAIN_URL, "category/anime-series-1/"),     "type": "category", "_action": "category"},
        {"title": "🎮 عروض مصارعة",    "url": urljoin(MAIN_URL, "category/wwe-shows-1/"),        "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, _ = fetch(url, referer=MAIN_URL)
    if not html:
        return []

    items = []
    seen  = set()

    # FIX: try structured blocks first, then broader fallback
    blocks = re.findall(
        r'<div[^>]+class=["\'](?:recent--block|post--block|item)[^>]*>(.*?)</div>',
        html, re.S | re.IGNORECASE
    )
    if not blocks:
        blocks = re.findall(
            r'(<a[^>]+href=["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\'][^>]*>.*?</a>)',
            html, re.S | re.IGNORECASE
        )

    for block in blocks:
        m = (
            re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]+title=["\']([^"\']+)["\'][^>]*>', block, re.S) or
            re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?<img[^>]+alt=["\']([^"\']+)["\']', block, re.S)
        )
        if m:
            link, title = m.groups()
            img_m = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', block)
            img   = img_m.group(1) if img_m else ""
            if link in seen or "/category/" in link:
                continue
            seen.add(link)
            title     = _clean_title(title)
            item_type = "series" if ("/series-" in link or "مسلسل" in title) else "movie"
            items.append({"title": title, "url": link, "poster": img, "type": item_type, "_action": "details"})

    # Broad fallback if nothing found yet
    if not items:
        regex = r'<a[^>]+href=["\']([^"\']+)["\'][^>]+title=["\']([^"\']+)["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']'
        for link, title, img in re.findall(regex, html, re.S | re.IGNORECASE):
            if link in seen or "/category/" in link:
                continue
            seen.add(link)
            item_type = "series" if ("/series-" in link or "مسلسل" in title) else "movie"
            items.append({"title": title.strip(), "url": link, "poster": img, "type": item_type, "_action": "details"})

    next_page = re.search(r'href="([^"]+/page/\d+/)"', html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page.group(1), "type": "category", "_action": "category"})
    return items


def get_page(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        return {"title": "Error", "servers": []}

    result = {
        "url":     final_url or url,
        "title":   "",
        "plot":    "",
        "poster":  "",
        "rating":  "",
        "year":    "",
        "servers": [],
        "items":   [],
    }

    title_match = (
        re.search(r'og:title[^>]+content="([^"]+)"', html) or
        re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    )
    if title_match:
        result["title"] = _clean_title(title_match.group(1).split("-")[0])

    poster_match = re.search(r'og:image"[^>]+content="([^"]+)"', html)
    if poster_match:
        result["poster"] = poster_match.group(1)

    plot_match = re.search(r'name="description"[^>]+content="([^"]+)"', html)
    if plot_match:
        result["plot"] = plot_match.group(1)

    is_series = (
        any(m in (final_url or url) for m in ("/series-", "/season-", "/episode-"))
        or "مسلسل" in result["title"]
    )

    # Determine watch URL
    watch_url   = (final_url or url).rstrip("/") + "/watch/"
    watch_match = re.search(r'href="([^"]+/watch/)"', html)
    if watch_match:
        watch_url = watch_match.group(1)

    watch_html, watch_final = fetch(watch_url, referer=final_url or url)
    if not watch_html:
        watch_html, watch_final = html, (final_url or url)

    for server in _collect_ajax_servers(watch_html, watch_final or watch_url):
        result["servers"].append({
            "name": "[{}p] {}".format(server["quality"], server["name"]),
            "url":  server["url"],
            "type": "direct",
        })

    if is_series:
        seen_eps   = set()
        blocks_html = (
            " ".join(re.findall(
                r'<div[^>]+class=["\'](?:Blocks-Episodes|Episode--List|seasons--episodes|'
                r'Blocks-Container|List--Episodes|List--Seasons|episodes)[^>]*>(.*?)</section>',
                html, re.S | re.I
            )) or html
        )
        for ep_url, ep_title in re.findall(
            r'<a[^>]+href="(https?://[^/]+/[^"]+)"[^>]+title="([^"]+)"',
            blocks_html, re.S
        ):
            if ("الحلقة" not in ep_title and "حلقة" not in ep_title) or ep_url in seen_eps:
                continue
            if not any(x in ep_url for x in ("series-", "-season", "episode")):
                continue
            seen_eps.add(ep_url)
            result["items"].append({
                "title":   ep_title.strip(),
                "url":     ep_url,
                "type":    "episode",
                "_action": "details",
            })

    # Data-link fallback if AJAX produced nothing
    if not result["servers"]:
        for fallback in re.findall(r'data-(?:link|url|iframe|src|href)="([^"]+)"', watch_html or "", re.S):
            fallback = _decode_hidden_url(fallback)
            if not fallback.startswith("http"):
                continue
            if any(h in fallback for h in BLOCKED_HOSTS):
                continue
            if fallback not in [s["url"] for s in result["servers"]]:
                result["servers"].append({"name": "Fallback", "url": fallback, "type": "direct"})

    return result


def extract_stream(url):
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
````

## File: extractors/base.py
````python
# -*- coding: utf-8 -*-
"""
Base extractor — common utilities + video host resolvers
Improvements over previous version:
  - Fixed egydead referer (tv8.egydead.live instead of stale x7k9f.sbs)
  - fetch() retry on transient failures (503 / timeout)
  - New resolvers: ok.ru, filemoon, streamwish family, lulustream, vidguard
  - Improved: streamtape (3 fallback patterns), doodstream (15+ domains),
               voe (base64 + newer layout), resolve_iframe_chain (meta-refresh,
               JS location, data-src)
  - _best_media_url: richer source patterns (jwplayer, sources[], clappr)
  - Unicode URL support for Arabic characters
"""

import re
import json
import time
import random
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor, HTTPSHandler
from urllib.parse import urljoin, urlparse, unquote, urlencode, quote_plus
from urllib.error import URLError, HTTPError
import http.cookiejar as cookiejar
import ssl
import gzip
import zlib
import io
import sys

try:
    import brotli
except Exception:
    brotli = None

UA      = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 30
ACCEPT_ENCODING = "gzip, deflate, br" if brotli is not None else "gzip, deflate"

_opener = None


def log(msg):
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = "[{}] {}\n".format(ts, msg)
        with open("/tmp/arabicplayer.log", "a") as f:
            f.write(line)
        print("[ArabicPlayer] {}".format(msg))
    except Exception:
        pass


def _get_opener():
    global _opener
    if _opener:
        return _opener
    cj = cookiejar.CookieJar()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    except AttributeError:
        ctx = ssl._create_unverified_context()
    _opener = build_opener(HTTPCookieProcessor(cj), HTTPSHandler(context=ctx))
    return _opener


def _decode_response_body(raw, info):
    ce = info.get("Content-Encoding", "").lower()
    if "gzip" in ce:
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    elif "deflate" in ce:
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except Exception:
            raw = zlib.decompress(raw)
    elif "br" in ce and brotli is not None:
        raw = brotli.decompress(raw)
    charset = "utf-8"
    ctype = info.get("Content-Type", "").lower()
    if "charset=" in ctype:
        charset = ctype.split("charset=")[-1].split(";")[0].strip()
    try:
        return raw.decode(charset)
    except Exception:
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return raw.decode("latin-1", errors="ignore")


def _encode_unicode_url(url):
    """Encode Unicode characters in URL to percent-encoded format."""
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


def fetch(url, referer=None, extra_headers=None, post_data=None):
    """
    Robust fetch with:
    - Smart per-domain referer defaults
    - Auto retry on transient errors (503, timeout, connection reset)
    - Brotli / gzip / deflate decompression
    - Cookie jar (shared session)
    - Unicode URL support (properly encodes Arabic/etc. characters)
    """
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            opener = _get_opener()
            
            # Handle Unicode URLs - encode to percent-encoded format
            encoded_url = _encode_unicode_url(url)
            
            parsed = urlparse(encoded_url)
            domain = parsed.netloc.lower()

            if not referer:
                # ── per-domain referer defaults ───────────────────────────
                if "tv8.egydead" in domain or "egydead" in domain:
                    referer = "https://tv8.egydead.live/"
                elif "wecima" in domain or "mycima" in domain:
                    referer = "https://wecima.click/"
                elif "fasel" in domain:
                    referer = "https://www.faselhd.cam/"
                elif "topcinema" in domain:
                    referer = "https://topcinemaa.com/"
                elif "shaheed" in domain:
                    referer = "https://shaheeid4u.net/"
                elif "streamwish" in domain or "wishfast" in domain:
                    referer = "https://streamwish.to/"
                elif "filemoon" in domain:
                    referer = "https://filemoon.sx/"
                elif "lulustream" in domain:
                    referer = "https://lulustream.com/"
                elif "ok.ru" in domain:
                    referer = "https://ok.ru/"
                elif "vidguard" in domain or "vgfplay" in domain:
                    referer = "https://vidguard.to/"
                elif "filelion" in domain or "vidhide" in domain or "streamhide" in domain:
                    referer = "https://filelions.to/"
                else:
                    referer = "{}://{}/".format(parsed.scheme, domain)

            headers = {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "ar,en-US,en;q=0.9",
                "Accept-Encoding": ACCEPT_ENCODING,
                "Connection": "keep-alive",
                "Referer": referer,
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
            if any(x in encoded_url.lower() for x in ["ajax", "get__watch", "api/", ".json"]):
                headers.update({
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                })
            if extra_headers:
                headers.update(extra_headers)

            data = post_data
            if data and isinstance(data, dict):
                data = urlencode(data).encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            elif data and isinstance(data, (str, bytes)):
                if isinstance(data, str):
                    data = data.encode("utf-8")

            log("Fetching (attempt {}): {}".format(attempt + 1, encoded_url))
            req = Request(encoded_url, headers=headers, data=data)

            with opener.open(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
                final_url = resp.geturl()
                info = resp.info()

                if any(x in final_url.lower() for x in ("alliance4creativity.com", "watch-it-legally")):
                    log("!!! ACE Redirect detected for {} !!!".format(encoded_url))
                    return None, final_url

                html = _decode_response_body(raw, info)
                log("Fetch OK: {} ({} bytes)".format(final_url, len(html)))
                return html, final_url

        except HTTPError as e:
            # Retry on 503 / 429
            if attempt < max_retries and e.code in (503, 429, 502):
                log("Fetch HTTPError {}, retrying in 2s: {}".format(e.code, url))
                time.sleep(2)
                continue
            try:
                raw = e.read()
                html = _decode_response_body(raw, e.info()) if raw else ""
                log("Fetch HTTPError: {} → {} {} ({} bytes)".format(url, e.code, e.reason, len(html)))
            except Exception:
                log("Fetch HTTPError: {} → {} {}".format(url, getattr(e, "code", "?"), getattr(e, "reason", e)))
            return None, url

        except URLError as e:
            if attempt < max_retries:
                log("Fetch URLError (retry {}): {} → {}".format(attempt + 1, url, e))
                global _opener
                _opener = None           # reset opener on network error
                time.sleep(1.5)
                continue
            log("Fetch URLError: {} → {}".format(url, e))
            _opener = None
            return None, url

        except UnicodeEncodeError as e:
            # Handle Unicode encoding errors specifically
            log("Fetch UnicodeEncodeError: {} → {}".format(url, e))
            # Try with manual encoding
            try:
                # Fallback: try to encode the URL explicitly
                encoded_url = url.encode('utf-8').decode('ascii', errors='ignore')
                if encoded_url != url:
                    log("Retrying with encoded URL: {}".format(encoded_url))
                    return fetch(encoded_url, referer, extra_headers, post_data)
            except Exception:
                pass
            return None, url

        except Exception as e:
            if attempt < max_retries:
                log("Fetch Error (retry {}): {} → {}".format(attempt + 1, url, e))
                time.sleep(1)
                continue
            log("Fetch Error: {} → {}".format(url, e))
            return None, url

    return None, url


# ─── HTML helpers ─────────────────────────────────────────────────────────────

def extract_iframes(html, base_url=""):
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    result = []
    for src in iframes:
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/") and base_url:
            p = urlparse(base_url)
            src = "{}://{}{}".format(p.scheme, p.netloc, src)
        if src.startswith("http"):
            result.append(src)
    return result


def find_m3u8(html):
    if not html:
        return None
    patterns = [
        r'["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'hls\.loadSource\(["\']([^"\']+)["\']',
        r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'data-(?:url|src)=["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'hlsManifestUrl["\']?\s*:\s*["\']([^"\']+)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").replace("\\u0026", "&").strip()
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith("http") and ".m3u8" in url:
                return url
    return None


def find_mp4(html):
    if not html:
        return None
    patterns = [
        r'["\']([^"\']+\.mp4[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
        r'data-(?:url|src)=["\']([^"\']+\.mp4[^"\']*)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").strip()
            if url.startswith("//"):
                url = "https:" + url
            if url.startswith("http") and ".mp4" in url:
                return url
    return None


def _best_media_url(text):
    """
    Pick the highest-quality video URL visible in plain or unpacked JS.
    Covers: direct URLs, JWPlayer setup, sources[], Clappr, HLS manifests.
    """
    if not text:
        return None
    candidates = []
    seen = set()

    def score(url):
        lowered = url.lower()
        if "2160" in lowered or "4k" in lowered:   return 5000
        if "1080" in lowered or "fhd" in lowered:  return 4000
        if "720" in lowered  or "hd" in lowered:   return 3000
        if "480" in lowered:                        return 2000
        if "360" in lowered:                        return 1000
        if "240" in lowered or "sd" in lowered:     return 500
        if ".m3u8" in lowered:                      return 3500
        return 100

    patterns = [
        # JWPlayer / sources array
        r'sources\s*:\s*\[{[^}]*file\s*:\s*["\']([^"\']+)["\']',
        r'"file"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        r"'file'\s*:\s*'([^']+(?:m3u8|mp4)[^']*)'",
        # Clappr / hls.js
        r'"source"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        r"'source'\s*:\s*'([^']+(?:m3u8|mp4)[^']*)'",
        r'"src"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        # Direct URLs
        r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
        r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)',
        # hlsManifestUrl (ok.ru, etc.)
        r'hlsManifestUrl["\']?\s*:\s*["\']([^"\']+)["\']',
        # playlist / stream
        r'"(?:playlist|stream|hls|hls2|master)"\s*:\s*"([^"]+)"',
        r"'(?:playlist|stream|hls|hls2|master)'\s*:\s*'([^']+)'",
    ]
    for pat in patterns:
        for match in re.findall(pat, text, re.I):
            url = match.replace("\\/", "/").replace("&amp;", "&").replace("\\u0026", "&").strip()
            if url.startswith("//"):
                url = "https:" + url
            if not url.startswith("http"):
                continue
            if url in seen:
                continue
            seen.add(url)
            candidates.append((score(url), url))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# ─── Packer / obfuscation ─────────────────────────────────────────────────────

def _extract_packer_blocks(html):
    blocks = []
    marker = "eval(function(p,a,c,k,e,d){"
    tail   = ".split('|')))"
    pos = 0
    while True:
        start = (html or "").find(marker, pos)
        if start == -1:
            break
        end = (html or "").find(tail, start)
        if end == -1:
            break
        blocks.append(html[start : end + len(tail)])
        pos = end + len(tail)
    return blocks


def decode_packer(packed):
    try:
        def read_js_string(text, start_idx):
            quote = text[start_idx]
            i = start_idx + 1
            out = []
            while i < len(text):
                ch = text[i]
                if ch == "\\" and i + 1 < len(text):
                    out.append(text[i + 1])
                    i += 2
                    continue
                if ch == quote:
                    return "".join(out), i + 1
                out.append(ch)
                i += 1
            return "", -1

        start = packed.find("}(")
        if start == -1:
            return ""
        idx = start + 2
        while idx < len(packed) and packed[idx] in " \t\r\n":
            idx += 1
        if idx >= len(packed) or packed[idx] not in ("'", '"'):
            return ""

        p, idx = read_js_string(packed, idx)
        if idx == -1:
            return ""

        nums = re.match(r"\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*", packed[idx:], re.S)
        if not nums:
            return ""
        a, c = nums.group(1), nums.group(2)
        idx += nums.end()
        if idx >= len(packed) or packed[idx] not in ("'", '"'):
            return ""

        k, idx = read_js_string(packed, idx)
        if idx == -1:
            return ""

        a, c = int(a), int(c)
        k = k.split("|")

        def e(c_val):
            result = ""
            while True:
                result = "0123456789abcdefghijklmnopqrstuvwxyz"[c_val % a] + result
                c_val //= a
                if c_val == 0:
                    break
            return result

        d = {e(i): k[i] or e(i) for i in range(c)}
        return re.sub(r'\b(\w+)\b', lambda x: d.get(x.group(1), x.group(1)), p)
    except Exception:
        return ""


def find_packed_links(html):
    for ev in _extract_packer_blocks(html):
        dec = decode_packer(ev)
        if dec:
            res = find_m3u8(dec) or find_mp4(dec)
            if res:
                return res
    # fallback broader eval pattern
    for ev in re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S):
        dec = decode_packer(ev)
        if dec:
            res = find_m3u8(dec) or find_mp4(dec)
            if res:
                return res
    return None


def _unpack_all(html):
    """Return list of (original_html + all unpacked JS blocks) for thorough scanning."""
    texts = [html]
    for block in _extract_packer_blocks(html):
        dec = decode_packer(block)
        if dec:
            texts.append(dec)
    return texts


# ─── Video Host Resolvers ─────────────────────────────────────────────────────

def resolve_streamtape(url):
    """streamtape.com — tries 3 extraction patterns as the site changes often."""
    try:
        html, _ = fetch(url, referer="https://streamtape.com/")
        if not html:
            return None

        # Pattern 1: robotlink innerHTML concat (classic)
        m = re.search(r"robotlink\)\.innerHTML\s*=\s*'([^']+)'\s*\+\s*'([^']+)'", html)
        if m:
            link = m.group(1) + m.group(2)
            if not link.startswith("http"):
                link = "https:" + link
            return link.replace("//streamtape.com", "https://streamtape.com")

        # Pattern 2: single innerHTML assignment
        m = re.search(r"robotlink\)\.innerHTML\s*=\s*['\"]([^'\"]+)['\"]", html)
        if m:
            link = m.group(1)
            return ("https:" + link) if link.startswith("//") else link

        # Pattern 3: /get_video?... inside JS
        m = re.search(r'(/get_video\?[^"\'&\s]+)', html)
        if m:
            return "https://streamtape.com" + m.group(1)

        # Pattern 4: direct mp4 URL
        return find_mp4(html)
    except Exception:
        pass
    return None


def resolve_doodstream(url):
    """dood.* / doodstream / dsv* / d0o0d and 20+ domain variants."""
    DOOD_DOMAINS = [
        "dood.re", "dood.to", "dood.so", "dood.pm", "dood.ws",
        "dood.watch", "dood.sh", "dood.la", "dood.li", "dood.cx",
        "dood.xyz", "dood.wf", "d0o0d.com", "dsvplay.com",
        "doods.pro", "ds2play.com", "dooood.com", "doodstream.com",
    ]
    try:
        # Normalise to a working domain
        working_html = None
        working_url  = url
        for dom in DOOD_DOMAINS:
            candidate = re.sub(r'dood\.[a-z]+|dsvplay\.[a-z]+|d0o0d\.[a-z]+|doodstream\.[a-z]+', dom, url)
            html, final = fetch(candidate, referer=candidate)
            if html and "pass_md5" in html:
                working_html = html
                working_url  = candidate
                break
        if not working_html:
            working_html, _ = fetch(url, referer=url)
        if not working_html:
            return None

        m = re.search(r'\$\.get\(["\'](/pass_md5/[^"\']+)["\']', working_html)
        if not m:
            m = re.search(r'pass_md5/([^"\'.\s&]+)', working_html)
            if m:
                pass_path = "/pass_md5/" + m.group(1)
            else:
                return None
        else:
            pass_path = m.group(1)

        # Extract base domain from working URL
        parsed = urlparse(working_url)
        dood_base = "{}://{}".format(parsed.scheme, parsed.netloc)

        token_html, _ = fetch(dood_base + pass_path, referer=working_url)
        if not token_html:
            return None

        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        rand = "".join(random.choice(chars) for _ in range(10))
        token = pass_path.split("/")[-1]
        return "{}{}&token={}&expiry={}".format(
            token_html.strip(), rand, token, int(time.time() * 1000)
        )
    except Exception:
        pass
    return None


def resolve_vidbom(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    except Exception:
        pass
    return None


def resolve_uqload(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        m = re.search(r'sources:\s*\["([^"]+)"\]', html)
        if m:
            return m.group(1)
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_govid(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_upstream(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_mixdrop(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        # Direct MDCore pattern
        m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', html)
        if m:
            link = m.group(1)
            return ("https:" + link) if link.startswith("//") else link
        # Packed JS
        for txt in _unpack_all(html):
            m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', txt)
            if m:
                link = m.group(1)
                return ("https:" + link) if link.startswith("//") else link
    except Exception:
        pass
    return None


def resolve_voe(url):
    """voe.sx — handles multiple obfuscation layers including base64 and newer layouts."""
    try:
        html, final = fetch(url, referer="https://voe.sx/")
        if not html:
            return None

        # Layer 1: direct hls / sources patterns
        for pat in [
            r"'hls'\s*:\s*'([^']+)'",
            r'"hls"\s*:\s*"([^"]+)"',
            r"sources\s*=\s*\[{[^}]*file\s*:\s*'([^']+)'",
            r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        ]:
            m = re.search(pat, html, re.I)
            if m:
                return m.group(1).replace("\\/", "/")

        # Layer 2: base64 atob() blobs
        import base64
        for enc in re.finditer(r'atob\([\'"]([A-Za-z0-9+/=]+)[\'"]\)', html):
            try:
                dec = base64.b64decode(enc.group(1) + "==").decode("utf-8", errors="ignore")
                mm = re.search(r'(https?://[^\s\'"<>]+\.m3u8[^\s\'"<>]*)', dec)
                if mm:
                    return mm.group(1)
            except Exception:
                pass

        # Layer 3: packed JS
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_streamruby(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        res = find_m3u8(html) or find_mp4(html)
        if res:
            return res
        for txt in _unpack_all(html):
            res = find_m3u8(txt) or find_mp4(txt)
            if res:
                return res
    except Exception:
        pass
    return None


def resolve_hgcloud(url):
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_vidtube(url):
    """vidtube.one — JWPlayer behind packer, optional domain restriction bypass."""
    try:
        html, _ = fetch(url, referer="https://topcinema.fan/")
        if not html or "restricted for this domain" in html.lower():
            html, _ = fetch(url, referer="https://topcinema.fan/")
        if not html:
            return None
        best = _best_media_url(html)
        if best:
            return best
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best
    except Exception:
        pass
    return None


# ── NEW resolvers ──────────────────────────────────────────────────────────────

def resolve_streamwish(url):
    """
    StreamWish / WishFast / Filelions / VidHide / StreamHide / DHTpre —
    all run the same JWPlayer-based platform.
    """
    try:
        html, _ = fetch(url, referer=url)
        if not html:
            return None

        # Try direct patterns first (fastest)
        best = _best_media_url(html)
        if best:
            return best

        # Packed JS (all these sites heavily pack their JS)
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_filemoon(url):
    """
    Filemoon.sx / .to / .nl / .wf — packed JS containing JWPlayer setup.
    Uses parserBYSE in e2iplayer (= packed → JWPlayer sources).
    """
    try:
        html, _ = fetch(url, referer="https://filemoon.sx/")
        if not html:
            return None

        # Direct scan first
        best = _best_media_url(html)
        if best:
            return best

        # Unpack all eval blocks
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        # base64 blobs
        import base64
        for b64 in re.findall(r'atob\(["\']([A-Za-z0-9+/=]{40,})["\']\)', html, re.I):
            try:
                dec = base64.b64decode(b64 + "==").decode("utf-8", "ignore")
                best = _best_media_url(dec)
                if best:
                    return best
            except Exception:
                pass

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_lulustream(url):
    """
    LuluStream — JWPlayer based, similar to streamwish family.
    Requires Referer: https://1fo1ndyf09qz.tnmr.org (confirmed from e2iplayer).
    """
    try:
        html, _ = fetch(url, referer="https://1fo1ndyf09qz.tnmr.org",
                        extra_headers={"Origin": "https://lulustream.com"})
        if not html:
            html, _ = fetch(url, referer="https://lulustream.com/")
        if not html:
            return None

        best = _best_media_url(html)
        if best:
            return best

        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_okru(url):
    """
    ok.ru — uses the /dk/video.playJSON API (confirmed from e2iplayer parserOKRU).
    Extracts HLS manifest URL.
    """
    try:
        # Normalise URL → extract video ID
        m = re.search(r'ok\.ru/(?:video(?:embed)?/|videoembed/)(\d+)', url)
        if not m:
            m = re.search(r'/(\d{10,})', url)
        if not m:
            return None
        video_id = m.group(1)

        # API endpoint (same as e2iplayer parserOKRU)
        api_url = "https://ok.ru/dk/video.playJSON?movieId={}".format(video_id)
        mobile_ua = ("Mozilla/5.0 (iPad; U; CPU OS 3_2 like Mac OS X; en-us) "
                     "AppleWebKit/531.21.10 (KHTML, like Gecko) "
                     "Version/4.0.4 Mobile/7B334b Safari/531.21.10")
        body, _ = fetch(api_url,
                        referer=url,
                        extra_headers={
                            "User-Agent": mobile_ua,
                            "Accept": "application/json",
                        })
        if body:
            try:
                data = json.loads(body)
                hls = data.get("hlsManifestUrl", "")
                if hls:
                    return hls.replace("\\u0026", "&").replace("\\/", "/")
                # Fallback: videos array
                for vid in (data.get("videos") or []):
                    u = vid.get("url") or ""
                    if u.startswith("http"):
                        return u.replace("\\u0026", "&").replace("\\/", "/")
            except Exception:
                pass

        # Fallback: scrape embed page
        embed_url = "https://ok.ru/videoembed/{}".format(video_id)
        html, _ = fetch(embed_url, referer="https://ok.ru/",
                        extra_headers={"User-Agent": mobile_ua})
        if html:
            best = _best_media_url(html)
            if best:
                return best
            m2 = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+)"', html)
            if m2:
                return m2.group(1).replace("\\u0026", "&").replace("\\/", "/")
    except Exception:
        pass
    return None


def resolve_vidguard(url):
    """
    VidGuard / vgfplay — obfuscated JS, exposes stream_url or packed m3u8.
    """
    try:
        html, _ = fetch(url, referer="https://vidguard.to/")
        if not html:
            return None

        # Common direct patterns
        for pat in [
            r'stream_url\s*=\s*["\']([^"\']+)["\']',
            r'"(?:file|src|url)"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r"'(?:file|src|url)'\s*:\s*'([^']+\.m3u8[^']*)'",
        ]:
            m = re.search(pat, html, re.I)
            if m:
                u = m.group(1).replace("\\/", "/").replace("\\u0026", "&")
                return u

        # Packed JS
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best

        # base64 decode attempts
        import base64
        for b64 in re.findall(r'atob\(["\']([A-Za-z0-9+/=]{40,})["\']\)', html, re.I):
            try:
                dec = base64.b64decode(b64 + "==").decode("utf-8", "ignore")
                best = _best_media_url(dec)
                if best:
                    return best
            except Exception:
                pass

        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


# ─── Host dispatcher ──────────────────────────────────────────────────────────

HOST_RESOLVERS = {
    # Existing
    "streamtape":  resolve_streamtape,
    "dood":        resolve_doodstream,
    "dsvplay":     resolve_doodstream,
    "d0o0d":       resolve_doodstream,
    "doods":       resolve_doodstream,
    "ds2play":     resolve_doodstream,
    "dooood":      resolve_doodstream,
    "vidbom":      resolve_vidbom,
    "vidshare":    resolve_vidbom,
    "uqload":      resolve_uqload,
    "govid":       resolve_govid,
    "upstream":    resolve_upstream,
    "mixdrop":     resolve_mixdrop,
    "voe":         resolve_voe,
    "streamruby":  resolve_streamruby,
    "hgcloud":     resolve_hgcloud,
    "masukestin":  resolve_hgcloud,
    "vidtube":     resolve_vidtube,
    # New
    "streamwish":  resolve_streamwish,
    "wishfast":    resolve_streamwish,
    "filelion":    resolve_streamwish,   # filelions.to
    "filelions":   resolve_streamwish,
    "vidhide":     resolve_streamwish,
    "streamhide":  resolve_streamwish,
    "dhtpre":      resolve_streamwish,
    "embedrise":   resolve_streamwish,
    "hglamioz":    resolve_streamwish,
    "filemoon":    resolve_filemoon,
    "lulustream":  resolve_lulustream,
    "ok.ru":       resolve_okru,
    "okru":        resolve_okru,
    "vidguard":    resolve_vidguard,
    "vgfplay":     resolve_vidguard,
}


def resolve_generic_embed(url):
    """Generic resolver — m3u8/mp4 scan → packer unpack → iframe follow."""
    try:
        html, final = fetch(url, referer=url)
        if not html:
            return None
        best = _best_media_url(html)
        if best:
            return best
        for txt in _unpack_all(html):
            best = _best_media_url(txt)
            if best:
                return best
        # Follow one level of iframes
        for iframe_url in extract_iframes(html, final or url)[:3]:
            h2, _ = fetch(iframe_url, referer=url)
            if h2:
                best = _best_media_url(h2)
                if best:
                    return best
    except Exception:
        pass
    return None


# ─── Multi-provider premium resolvers (TMDB-based) ───────────────────────────

def _get_stream_moviesapi(tmdb_id, m_type, season=None, episode=None):
    url = ("https://moviesapi.club/api/v1/movies/{}".format(tmdb_id) if m_type == "movie"
           else "https://moviesapi.club/api/v1/tv/{}/{}/{}".format(tmdb_id, season or 1, episode or 1))
    body, _ = fetch(url, extra_headers={"Accept": "application/json"})
    if not body:
        return None
    try:
        data = json.loads(body)
        for src in (data.get("sources") or []):
            f = src.get("file") or src.get("url") or ""
            if ".m3u8" in f:
                return f
        for src in (data.get("sources") or []):
            f = src.get("file") or src.get("url") or ""
            if f.startswith("http"):
                return f
    except Exception:
        pass
    return find_m3u8(body) or find_mp4(body)


def _get_stream_vidsrc(tmdb_id, m_type, season=None, episode=None):
    url = ("https://vidsrc.me/embed/movie/{}".format(tmdb_id) if m_type == "movie"
           else "https://vidsrc.me/embed/tv/{}/{}/{}".format(tmdb_id, season or 1, episode or 1))
    html, _ = fetch(url, referer="https://vidsrc.me/")
    if not html:
        return None
    m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    if m:
        iframe_url = m.group(1)
        if iframe_url.startswith("//"):
            iframe_url = "https:" + iframe_url
        h2, _ = fetch(iframe_url, referer=url)
        if h2:
            return find_m3u8(h2) or find_mp4(h2)
    return find_m3u8(html) or find_mp4(html)


def _get_stream_autoembed(tmdb_id, m_type, season=None, episode=None):
    url = ("https://autoembed.cc/movie/tmdb-{}".format(tmdb_id) if m_type == "movie"
           else "https://autoembed.cc/tv/tmdb-{}-{}-{}".format(tmdb_id, season or 1, episode or 1))
    html, _ = fetch(url)
    if not html:
        return None
    return find_m3u8(html) or find_mp4(html)


_PREMIUM_METHODS = {
    "moviesapi": _get_stream_moviesapi,
    "vidsrc":    _get_stream_vidsrc,
    "autoembed": _get_stream_autoembed,
}


def get_premium_servers(m_type, tmdb_id, season=None, episode=None):
    suffix = ":{}:{}".format(season, episode) if (season and episode) else ""
    return [
        {"name": "Premium: AutoEmbed 🚀", "url": "autoembed://{}:{}{}".format(m_type, tmdb_id, suffix)},
        {"name": "Premium: VidSrc 🔥",    "url": "vidsrc://{}:{}{}".format(m_type, tmdb_id, suffix)},
    ]


# ─── Main host dispatcher ─────────────────────────────────────────────────────

def resolve_host(url, referer=None):
    """Detect host from domain and dispatch to the right resolver."""
    # Premium protocol shortcuts  (autoembed://, vidsrc://, etc.)
    m = re.match(r'(\w+)://(movie|series|tv|episode):(\d+)(?::(\d+):(\d+))?', url)
    if m:
        method_name, m_type, tmdb_id, season, episode = m.groups()
        m_type = "movie" if m_type in ("movie", "film") else "series"
        if method_name in _PREMIUM_METHODS:
            return _PREMIUM_METHODS[method_name](tmdb_id, m_type, season, episode)
        if method_name == "auto":
            for func in _PREMIUM_METHODS.values():
                try:
                    res = func(tmdb_id, m_type, season, episode)
                    if res:
                        return res
                except Exception:
                    pass
        return None

    domain = urlparse(url).netloc.lower()
    log("resolve_host: domain={} url={}".format(domain, url[:80]))

    # Exact-key match first, then substring scan
    for key, resolver in HOST_RESOLVERS.items():
        if key in domain:
            log("Using resolver: {}".format(key))
            result = resolver(url)
            if result:
                return result
            log("Resolver {} returned nothing, trying generic".format(key))
            break

    log("Generic fallback for: {}".format(domain))
    return resolve_generic_embed(url)


# ─── iframe chain resolver ────────────────────────────────────────────────────

def resolve_iframe_chain(url, referer=None, depth=0, max_depth=8):
    """
    Follow iframes / meta-refresh / JS location redirects recursively.
    Returns (stream_url, domain) or (None, "").
    """
    if depth > max_depth:
        return None, ""

    html, final_url = fetch(url, referer=referer)
    if not html:
        return None, ""

    active_url = final_url or url
    domain = urlparse(active_url).netloc.lower()

    # 1. Direct media URL in page
    stream = find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    if stream:
        return stream, domain

    # 2. Meta-refresh redirect
    m = re.search(
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+\s*;\s*url=([^"\']+)["\']',
        html, re.I
    )
    if m:
        new_url = m.group(1).strip()
        if new_url.startswith("//"):
            new_url = "https:" + new_url
        elif not new_url.startswith("http"):
            new_url = urljoin(active_url, new_url)
        if new_url != active_url:
            return resolve_iframe_chain(new_url, referer=active_url, depth=depth + 1, max_depth=max_depth)

    # 3. JS window.location redirect
    m = re.search(r'(?:window\.location(?:\.href)?\s*=|location\.replace\()\s*["\']([^"\']+)["\']', html, re.I)
    if m:
        new_url = m.group(1).strip()
        if new_url.startswith("//"):
            new_url = "https:" + new_url
        elif not new_url.startswith("http"):
            new_url = urljoin(active_url, new_url)
        if new_url != active_url and "://" in new_url:
            return resolve_iframe_chain(new_url, referer=active_url, depth=depth + 1, max_depth=max_depth)

    # 4. iframes (src, data-src, data-url, data-lazy-src)
    iframe_srcs = re.findall(
        r'<(?:iframe|embed|frame)[^>]+(?:src|data-src|data-url|data-lazy-src)=["\']([^"\']+)["\']',
        html, re.I
    )
    for src in iframe_srcs:
        if src.startswith("//"):
            src = "https:" + src
        elif not src.startswith("http"):
            p = urlparse(active_url)
            if src.startswith("/"):
                src = "{}://{}{}".format(p.scheme, p.netloc, src)
            else:
                continue

        if any(x in src.lower() for x in ("facebook.com", "twitter.com", "googletag", "doubleclick", "analytics")):
            continue

        # Check if this is a known host — resolve directly rather than fetching page
        src_domain = urlparse(src).netloc.lower()
        for key, resolver in HOST_RESOLVERS.items():
            if key in src_domain:
                result = resolver(src)
                if result:
                    return result, src_domain
                break

        res, h = resolve_iframe_chain(src, referer=active_url, depth=depth + 1, max_depth=max_depth)
        if res:
            return res, h

    return None, ""


# ─── Main extract_stream entry point ─────────────────────────────────────────

def extract_stream(url):
    """
    Standard entry point used by all extractors.
    Returns (stream_url, quality_label, referer).
    """
    log("--- extract_stream START: {} ---".format(url))
    raw_url = (url or "").strip()
    if not raw_url:
        return None, "", url

    # Split piped headers (url|Referer=xxx&User-Agent=yyy)
    piped_headers = {}
    main_url = raw_url
    if "|" in raw_url:
        main_url, raw_hdrs = raw_url.split("|", 1)
        for part in raw_hdrs.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                piped_headers[k.strip()] = v.strip()

    lower = main_url.lower()

    # Fast path: already a direct media URL
    if main_url.startswith("http") and any(ext in lower for ext in (".m3u8", ".mp4", ".mkv", ".mp3")):
        ref = piped_headers.get("Referer") or "{}://{}/".format(*urlparse(main_url)[:2])
        q = ("1080p" if "1080" in lower else "720p" if "720" in lower else "HD")
        log("extract_stream DIRECT: {}".format(main_url))
        return raw_url, q, ref

    _, final_ref = fetch(main_url, referer=piped_headers.get("Referer"))

    stream = resolve_host(main_url, referer=piped_headers.get("Referer"))
    if not stream:
        log("resolve_host failed, trying iframe chain")
        stream, _ = resolve_iframe_chain(main_url, referer=piped_headers.get("Referer"))

    if stream:
        q = ("1080p" if "1080" in stream else "720p" if "720" in stream else "HD")
        log("extract_stream SUCCESS: {}".format(stream[:120]))
        return stream, q, final_ref or main_url

    log("extract_stream FAILED for: {}".format(main_url))
    return None, "", final_ref or main_url
````

## File: extractors/egydead.py
````python
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
````

## File: extractors/fasel.py
````python
# -*- coding: utf-8 -*-
import sys
import re
import time
from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse
    from html import unescape as html_unescape
else:
    from urllib import quote_plus
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

DOMAINS = [
    "https://faselhd.fit/",
    "https://www.faselhd.cam",
    "https://faselhd.pro",
    "https://faselhd.cc",
]

# FIX: removed "telegram" — it was blocking legitimate pages that link to Telegram
BLOCKED_MARKERS = ("alliance4creativity", "watch-it-legally", "just a moment", "cf-chl")

_ACTIVE_URL = None
_ACTIVE_BASE_FETCH_TIME = 0


def _get_base():
    global _ACTIVE_URL
    for domain in DOMAINS:
        log("FaselHD: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        if html and not any(m in (final_url or "").lower() for m in BLOCKED_MARKERS):
            log("FaselHD: using {}".format(domain))
            _ACTIVE_URL = domain.rstrip("/")
            return _ACTIVE_URL
    _ACTIVE_URL = DOMAINS[0].rstrip("/")
    return _ACTIVE_URL


def _base():
    global _ACTIVE_URL, _ACTIVE_BASE_FETCH_TIME
    if not _ACTIVE_URL or (time.time() - _ACTIVE_BASE_FETCH_TIME) > 3600:
        _ACTIVE_URL = _get_base()
        _ACTIVE_BASE_FETCH_TIME = time.time()
    return _ACTIVE_URL


def _normalize_url(url):
    if not url:
        return ""
    url = html_unescape(url.strip())
    if url.startswith("//"):
        return "https:" + url
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
        {"title": "🎬 افلام اجنبي",      "url": base + "/category/افلام-اجنبي",      "type": "category", "_action": "category"},
        {"title": "🎬 افلام عربي",       "url": base + "/category/افلام-عربي",       "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات اجنبي",    "url": base + "/category/مسلسلات-اجنبي",    "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات عربي",     "url": base + "/category/مسلسلات-عربي",     "type": "category", "_action": "category"},
        {"title": "🎌 انمي",             "url": base + "/category/انمي",             "type": "category", "_action": "category"},
    ]
    if not html:
        return fallback
    seen = set()
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html):
        url = m.group(1)
        title = m.group(2).strip()
        if "/category/" in url and title and len(title) < 30 and url not in seen:
            seen.add(url)
            emoji = "🎬" if "فيلم" in title or "افلام" in title else ("📺" if "مسلسل" in title else "📁")
            categories.append({
                "title": "{} {}".format(emoji, title),
                "url": _normalize_url(url),
                "type": "category",
                "_action": "category",
            })
    if categories:
        return categories
    return fallback


def _extract_items(html):
    items = []
    pattern = (
        r'<div[^>]*class="[^"]*grid-card[^"]*"[^>]*>.*?'
        r'<a[^>]+href="([^"]+)".*?'
        r'<img[^>]*class="[^"]*thumb-img[^"]*"[^>]*src="([^"]+)".*?'
        r'<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>'
    )
    matches = re.findall(pattern, html, re.DOTALL | re.I)
    if not matches:
        pattern = (
            r'<div[^>]*class="[^"]*post[^"]*"[^>]*>.*?'
            r'<a href="([^"]+)".*?'
            r'<img[^>]*(?:src|data-src)="([^"]+)".*?'
            r'<h[23][^>]*>([^<]+)</h[23]>'
        )
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
            "_action": "details",
        })
    return items


def get_category_items(url):
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        return []
    # Handle meta-refresh (some category pages use it)
    refresh = re.search(
        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;url=([^"\']+)["\']',
        html, re.I
    )
    if refresh:
        new_url = _normalize_url(refresh.group(1))
        log("FaselHD: meta-refresh to {}".format(new_url))
        return get_category_items(new_url)

    items = _extract_items(html)

    # Pagination
    next_match = (
        re.search(r'<a[^>]+href="([^"]+)"[^>]*>(?:التالي|Next)</a>', html, re.I) or
        re.search(r'<li[^>]*class="next"[^>]*>.*?<a href="([^"]+)"', html, re.I)
    )
    if next_match:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": _normalize_url(next_match.group(1)),
            "type": "category",
            "_action": "category",
        })
    return items


def search(query, page=1):
    base = _base()
    url = base + "/?s=" + quote_plus(query)
    html, _ = fetch(url, referer=base)
    return _extract_items(html) if html else []


def get_page(url):
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        return {"title": "Error", "servers": [], "items": [], "_action": "details"}

    title_m = re.search(r'<title>(.*?)</title>', html)
    title = _clean_title(title_m.group(1)) if title_m else "FaselHD"

    poster_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(poster_m.group(1)) if poster_m else ""

    plot_m = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html)
    plot = _clean_title(plot_m.group(1)) if plot_m else ""

    servers  = []
    episodes = []
    item_type = "movie"

    if "/series/" in url or "مسلسل" in title:
        item_type = "series"
        # Episodes
        for ep_url, ep_num in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?الحلقة\s*(\d+)', html, re.I):
            episodes.append({
                "title": "الحلقة {}".format(ep_num),
                "url": _normalize_url(ep_url),
                "type": "episode",
                "_action": "details",
            })
        if not episodes:
            for s_url, s_num in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?الموسم\s*(\d+)', html, re.I):
                episodes.append({
                    "title": "الموسم {}".format(s_num),
                    "url": _normalize_url(s_url),
                    "type": "category",
                    "_action": "category",
                })

    # Servers: look for known embed URLs
    seen_servers = set()
    # FIX: broadened to catch streamwish, filemoon, dood, voe etc. not just govid
    hoster_pattern = re.compile(
        r'href=["\']'
        r'(https?://(?:govid\.live|streamtape|dood\.|mixdrop|voe\.sx|'
        r'streamwish|filemoon|lulustream|vidbom|vidshare|upstream)[^"\']+)'
        r'["\']',
        re.I,
    )
    for m in hoster_pattern.finditer(html):
        hurl = m.group(1)
        if hurl not in seen_servers:
            seen_servers.add(hurl)
            servers.append({"name": "فاصل - سيرفر", "url": hurl, "_action": "details"})

    # iframes as fallback
    if not servers:
        for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
            iframe_url = _normalize_url(m.group(1))
            if iframe_url and iframe_url not in seen_servers:
                seen_servers.add(iframe_url)
                servers.append({"name": "بلاير", "url": iframe_url, "type": "direct"})

    return {
        "url":     final_url or url,
        "title":   title,
        "plot":    plot,
        "poster":  poster,
        "servers": servers,
        "items":   episodes,
        "type":    item_type,
    }


def extract_stream(url):
    """
    FIX: Replaced the fragile follow_chain() loop with a clean chain that:
    - Has a hard media-URL guard (won't follow non-video links endlessly)
    - Delegates known hosts to base resolvers
    - Falls back to resolve_iframe_chain for unknown pages
    """
    log("FaselHD extract_stream: {}".format(url))
    referer = _base()

    from .base import resolve_iframe_chain, resolve_host, find_m3u8, find_mp4

    # Step 1: if the URL itself is a known host, resolve directly
    stream = resolve_host(url, referer=referer)
    if stream:
        q = "HD" if "720" in stream else ("FHD" if "1080" in stream else "Auto")
        return stream, q, referer

    # Step 2: fetch the page and look for a media URL or iframe chain
    html, final_url = fetch(url, referer=referer)
    if html:
        # Direct media in page
        direct = find_m3u8(html) or find_mp4(html)
        if direct:
            return direct, "Auto", referer

        # iframes
        stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=8)
        if stream:
            return stream, "Auto", referer

    # Step 3: base fallback
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
````

## File: extractors/shaheed.py
````python
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
VALID_HOST_MARKERS   = ("shahid4u.guru", "shahieed4u.net", "shaheeid4u.net")
BLOCKED_HOST_MARKERS = ("alliance4creativity.com",)
MAIN_URL   = None
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
    if any(m in host for m in BLOCKED_HOST_MARKERS):
        return False
    return any(m in host for m in VALID_HOST_MARKERS)


def _is_blocked_page(html, final_url=""):
    text  = (html or "").lower()
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
    """
    FIX: No longer rejects pages when the final URL domain doesn't match
    VALID_HOST_MARKERS — CDN / image / video URLs are fetched by other means.
    Only rejects confirmed ACE/Cloudflare walls.
    """
    ref = referer or _get_base()
    h, final_url = fetch(url, referer=ref)
    if _is_blocked_page(h, final_url):
        return "", ""
    return h, final_url or url


def get_categories():
    base = _get_base().rstrip("/")
    html, _ = _fetch_live(base)
    categories = []
    seen_urls = set()
    if html:
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', html):
            url   = m.group(1)
            title = m.group(2).strip()
            if "/category/" in url and title and len(title) < 30 and url not in seen_urls:
                seen_urls.add(url)
                emoji = "🎬" if "فيلم" in title or "افلام" in title else ("📺" if "مسلسل" in title else "📁")
                categories.append({
                    "title": "{} {}".format(emoji, title),
                    "url":   _normalize_url(url),
                    "type":  "category",
                    "_action": "category",
                })
    if not categories:
        categories = [
            {"title": "🎬 افلام اجنبي",    "url": base + "/category/افلام-اجنبي",    "type": "category", "_action": "category"},
            {"title": "🎬 افلام عربي",     "url": base + "/category/افلام-عربي",     "type": "category", "_action": "category"},
            {"title": "📺 مسلسلات اجنبي",  "url": base + "/category/مسلسلات-اجنبي",  "type": "category", "_action": "category"},
            {"title": "📺 مسلسلات عربي",   "url": base + "/category/مسلسلات-عربي",   "type": "category", "_action": "category"},
        ]
    return categories


def _extract_cards(html):
    items = []
    # JSON-LD first (most reliable)
    ld_m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    if ld_m:
        try:
            data = json.loads(ld_m.group(1))
            if data.get("@type") == "ItemList":
                for entry in data.get("itemListElement", []):
                    item = entry.get("item", {})
                    if item.get("@type") in ("Movie", "TVSeries"):
                        title  = item.get("name", "")
                        url    = item.get("url", "")
                        poster = item.get("image", "")
                        if title and url:
                            items.append({
                                "title":   html_unescape(title),
                                "url":     _normalize_url(url),
                                "poster":  _normalize_url(poster),
                                "type":    "movie" if item.get("@type") == "Movie" else "series",
                                "_action": "details",
                            })
                if items:
                    return items
        except Exception:
            pass

    # HTML fallbacks
    for pattern in (
        r'<div[^>]*class="[^"]*post[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)".*?<img[^>]+src="([^"]+)".*?<h[23][^>]*>([^<]+)</h[23]>',
        r'<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)".*?<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>',
    ):
        matches = re.findall(pattern, html, re.DOTALL | re.I)
        if matches:
            for url, poster, title in matches:
                title = title.strip()
                if title and url:
                    items.append({
                        "title":   html_unescape(title),
                        "url":     _normalize_url(url),
                        "poster":  _normalize_url(poster),
                        "type":    "movie",
                        "_action": "details",
                    })
            break
    return items


def get_category_items(url):
    html, _ = _fetch_live(url)
    if not html:
        return []
    items = _extract_cards(html)
    log("Shaheed: {} -> {} items".format(url, len(items)))
    next_m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(?:التالي|Next)</a>', html, re.I)
    if next_m:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url":   _normalize_url(next_m.group(1)),
            "type":  "category",
            "_action": "category",
        })
    return items


def search(query, page=1):
    base = _get_base()
    url  = base + "/search?s=" + quote_plus(query) + "&page=" + str(page)
    html, _ = _fetch_live(url)
    return _extract_cards(html) if html else []


def get_page(url):
    html, final_url = _fetch_live(url)
    if not html:
        return {"title": "Error", "servers": [], "items": [], "type": "movie"}

    title_m = re.search(r'<title>(.*?)</title>', html)
    title   = html_unescape(title_m.group(1)) if title_m else ""

    poster_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster   = _normalize_url(poster_m.group(1)) if poster_m else ""

    plot = ""
    plot_m = re.search(r'class=["\']description["\'][^>]*>(.*?)</p>', html, re.S)
    if plot_m:
        plot = re.sub(r'<[^>]+>', ' ', plot_m.group(1)).strip()
        plot = html_unescape(plot)

    servers  = []
    episodes = []

    if "/series/" in (final_url or url) or "مسلسل" in title:
        for ep_url, ep_num in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?الحلقة\s*(\d+)', html, re.I):
            episodes.append({
                "title":   "الحلقة {}".format(ep_num),
                "url":     _normalize_url(ep_url),
                "type":    "episode",
                "_action": "details",
            })
        if not episodes:
            for s_url, s_num in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>.*?الموسم\s*(\d+)', html, re.I):
                episodes.append({
                    "title":   "الموسم {}".format(s_num),
                    "url":     _normalize_url(s_url),
                    "type":    "category",
                    "_action": "category",
                })

    # Watch page servers
    watch_m = re.search(r'href=["\']([^"\']+/watch/[^"\']+)["\']', html)
    if watch_m:
        watch_url = _normalize_url(watch_m.group(1))
        wh, _ = _fetch_live(watch_url, referer=final_url or url)
        if wh:
            # FIX: improved server JSON parsing — handles both let/var and inline arrays
            servers = _parse_watch_servers(wh, final_url or url)

    return {
        "url":     final_url or url,
        "title":   title,
        "plot":    plot,
        "poster":  poster,
        "servers": servers,
        "items":   episodes,
        "type":    "series" if episodes else "movie",
    }


def _parse_watch_servers(html, base_url):
    """
    FIX: More robust server parsing — tries JSON array, then iframe fallback.
    No longer crashes silently on schema changes.
    """
    servers = []
    seen = set()
    site_root = _site_root(base_url)

    # Pattern 1: servers JSON variable
    for pat in (
        r"let\s+servers\s*=\s*JSON\.parse\(['\"](.+?)['\"]\)",
        r"var\s+servers\s*=\s*(\[.*?\])",
        r"servers\s*=\s*(\[.*?\])",
    ):
        m = re.search(pat, html, re.S | re.I)
        if m:
            try:
                raw = m.group(1).replace("\\'", "'").replace('\\"', '"')
                # JSON.parse input uses single-quote escaping sometimes
                if raw.startswith("["):
                    srv_data = json.loads(raw)
                else:
                    srv_data = json.loads(raw.replace("'", '"'))
                for s in srv_data:
                    if s.get("url"):
                        u = s["url"] + "|Referer=" + site_root
                        if u not in seen:
                            seen.add(u)
                            servers.append({"name": s.get("name", "Server"), "url": u, "type": "direct"})
                if servers:
                    return servers
            except Exception as exc:
                log("Shaheed: server JSON parse failed: {}".format(exc))

    # Pattern 2: iframes
    for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
        u = _normalize_url(m.group(1))
        if u and u not in seen:
            seen.add(u)
            servers.append({"name": "Stream", "url": u + "|Referer=" + site_root, "type": "direct"})

    return servers


def extract_stream(url):
    log("Shaheed extract_stream: {}".format(url))
    referer = _get_base()
    if "|" in url:
        parts = url.split("|", 1)
        url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()

    # FIX: increased max_depth to 10 for deeper iframe chains
    from .base import resolve_iframe_chain
    stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=10)
    if stream:
        return stream, None, referer

    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
````

## File: extractors/topcinema.py
````python
# -*- coding: utf-8 -*-
import sys
import re
from .base import fetch, urljoin, log, resolve_iframe_chain

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse, urlunparse, quote, urlencode
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, quote, urlencode
    from urlparse import urlparse, urlunparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

DOMAINS = ["https://topcinemaa.com"]
MAIN_URL = DOMAINS[0]

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
    return [
        {"title": "🎬 المضاف حديثا", "url": MAIN_URL + "/recent/", "type": "category", "_action": "category"},
        {"title": "🎬 أفلام أجنبية", "url": MAIN_URL + "/category/%D8%A7%D9%81%D9%84%D8%A7%D9%85-%D8%A7%D8%AC%D9%86%D8%A8%D9%8A-8/", "type": "category", "_action": "category"},
        {"title": "🎬 أفلام أنمي", "url": MAIN_URL + "/category/%D8%A7%D9%81%D9%84%D8%A7%D9%85-%D8%A7%D9%86%D9%85%D9%8A-2/", "type": "category", "_action": "category"},
        {"title": "🎬 أفلام أسيوية", "url": MAIN_URL + "/category/%D8%A7%D9%81%D9%84%D8%A7%D9%85-%D8%A7%D8%B3%D9%8A%D9%88%D9%8A/", "type": "category", "_action": "category"},
        {"title": "🎬 أفلام نتفليكس", "url": MAIN_URL + "/netflix-movies/", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أجنبية", "url": MAIN_URL + "/category/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%A7%D8%AC%D9%86%D8%A8%D9%8A/", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أسيوية", "url": MAIN_URL + "/category/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%A7%D8%B3%D9%8A%D9%88%D9%8A%D8%A9/", "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أنمي", "url": MAIN_URL + "/category/%D9%85%D8%B3%D9%84%D8%B3%D9%84%D8%A7%D8%AA-%D8%A7%D9%86%D9%85%D9%8A/", "type": "category", "_action": "category"},
    ]

def _extract_blocks(html):
    items = []
    # Match any <a> that has a class with 'block' and contains an <img> with src/data-src
    # Using a more permissive regex that doesn't strictly depend on attribute order
    blocks = re.findall(r'(<a[^>]+href=["\'][^"\']+["\'][^>]*title=["\'][^"\']+["\'][^>]*class=["\'][^"\']*block[^"\']*["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\']([^"\']+)["\'][^>]*>)', html, re.DOTALL | re.IGNORECASE)
    
    if not blocks:
        # Final fallback for older pattern
        blocks = re.findall(r'(<a[^>]+href=["\'][^"\']+["\'][^>]*title=["\'][^"\']+["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\']([^"\']+)["\'][^>]*>)', html, re.DOTALL | re.IGNORECASE)

    for block_html, img in blocks:
        link_m = re.search(r'href=["\']([^"\']+)["\']', block_html)
        title_m = re.search(r'title=["\']([^"\']+)["\']', block_html)
        
        if link_m and title_m:
            link = _normalize_url(link_m.group(1))
            title = _clean_title(title_m.group(1))
            if not img or img.strip() in ("", "http:", "https:"):
                for _ipat in [
                    r'data-lazy=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)["\']',
                    r'data-original=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)["\']',
                    r'data-bg=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)["\']',
                    r'background(?:-image)?:\s*url\(["\']?([^"\')\s]+)',
                ]:
                    _im = re.search(_ipat, block_html, re.I)
                    if _im:
                        img = _im.group(1).strip("'\" ")
                        break
            img = _normalize_url(img)

            item_type = "movie"
            if "مسلسل" in title or "حلقة" in title or "انمي" in title:
                item_type = "series"

            items.append({
                "title": title,
                "url": link,
                "poster": img,
                "type": item_type,
                "_action": "details"
            })
    return items

def get_category_items(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html:
        log("TopCinema: fetch returned no content for {}".format(url))
        return []
    items = _extract_blocks(html)

    # Next page pagination
    next_page_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*class=["\']next page-numbers["\']', html)
    if next_page_match:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": _normalize_url(next_page_match.group(1)),
            "type": "category",
            "_action": "category"
        })
        
    return items

def search(query, page=1):
    items = []
    url = MAIN_URL + "/search/?query=" + quote_plus(query) + "&type=all"
    html, final_url = fetch(url, referer=MAIN_URL)
    items = _extract_blocks(html)
    return items

def get_page(url):
    html, final_url = fetch(url, referer=MAIN_URL)

    title_m = re.search(r'<title>(.*?)</title>', html, re.I | re.S)
    title = _clean_title(title_m.group(1)) if title_m else "Unknown Title"

    poster_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    poster = _normalize_url(poster_m.group(1)) if poster_m else ""

    plot_m = re.search(r'class=["\']description["\'][^>]*>(.*?)</', html, re.S | re.I)
    plot = _clean_title(re.sub(r'<[^>]+>', '', plot_m.group(1))) if plot_m else ""

    servers = []
    episodes = []
    item_type = "movie"

    watch_page_html = html or ""
    movie_url = final_url
    watch_url = ""

    watch_url_m = re.search(
        r'<a[^>]+class=["\'][^"\']*watch[^"\']*["\'][^>]+href=["\']([^"\']+/watch/?)[\"\']',
        html,
        re.I
    )
    if watch_url_m:
        watch_url = _normalize_url(watch_url_m.group(1))
        watch_page_html, _ = fetch(watch_url, referer=final_url)
        watch_page_html = watch_page_html or ""
        final_url = watch_url

    post_id = ""
    for pat in [
        r'data-id=["\'](\d+)["\']',
        r'\?p=(\d+)',
        r'postid["\']?\s*[:=]\s*["\']?(\d+)["\']?',
        r'post_id["\']?\s*[:=]\s*["\']?(\d+)["\']?'
    ]:
        m = re.search(pat, watch_page_html, re.I)
        if m:
            post_id = m.group(1)
            break

    def _server_name_ok(name):
        if not name:
            return False
        n = _clean_title(name).strip()
        if not n:
            return False
        bad_exact = [u"صالة العرض", u"صالة", u"Gallery", u"السيرفرات", u"مشاهدة", u"watch"]
        if n in bad_exact:
            return False
        # reject section titles / headings
        low = n.lower()
        for bad in ["gallery", "watch servers", "servers"]:
            if low == bad:
                return False
        return True

    server_candidates = []

    # 1) الشكل الصحيح: لازم نمسك الـ li كامل لأن data-id/data-server بيبقوا على العنصر نفسه
    old_matches = re.findall(
        r'<li[^>]*class=["\'][^"\']*server--item[^"\']*["\'][^>]*data-id=["\'](\d+)["\'][^>]*data-server=["\'](\d+)["\'][^>]*>(.*?)</li>',
        watch_page_html,
        re.I | re.S
    )
    for pid, idx, inner in old_matches:
        name = re.sub(r'<[^>]+>', ' ', inner)
        name = _clean_title(re.sub(r'\s+', ' ', name)).strip()
        if _server_name_ok(name):
            server_candidates.append((pid, idx, name))

    # 2) fallback: data-server موجود على أي عنصر
    if not server_candidates:
        generic_matches = re.findall(
            r'<(?:li|a|button|div)[^>]*data-id=["\'](\d+)["\'][^>]*data-server=["\'](\d+)["\'][^>]*>(.*?)</(?:li|a|button|div)>',
            watch_page_html,
            re.I | re.S
        )
        for pid, idx, inner in generic_matches:
            name = re.sub(r'<[^>]+>', ' ', inner)
            name = _clean_title(re.sub(r'\s+', ' ', name)).strip()
            if _server_name_ok(name):
                server_candidates.append((pid, idx, name))

    # 3) fallback بالأسماء المعروفة فقط
    if not server_candidates and post_id:
        visible_servers = [
            "متعدد الجودات",
            "UpDown",
            "StreamWish",
            "Doodstream",
            "Filelions",
            "Streamtape",
            "LuluStream",
            "Filemoon",
            "Mixdrop",
            "VidGuard",
            "Okru"
        ]
        found_names = []
        for srv in visible_servers:
            if re.search(re.escape(srv), watch_page_html, re.I):
                found_names.append(srv)
        for i, srv_name in enumerate(found_names, 1):
            server_candidates.append((post_id, str(i), srv_name))

    log("TopCinema FIX: post_id={} servers_found={}".format(post_id, repr(server_candidates[:10])))

    seen = set()
    ajax_endpoint = MAIN_URL + "/wp-content/themes/movies2023/Ajaxat/Single/Server.php"

    for pid, idx, name in server_candidates:
        if not pid or not idx:
            continue
        clean_name = _clean_title(name or "").strip()
        if not _server_name_ok(clean_name):
            continue
        key = (pid, idx)
        if key in seen:
            continue
        seen.add(key)

        s_url = "topcinema_server|{}|{}|{}|{}".format(
            ajax_endpoint, pid, idx, watch_url or movie_url
        )
        servers.append({
            "name": "توب سينما " + clean_name,
            "url": s_url,
        })

    # حلقات: شغّلها فقط لو واضح إنه مسلسل، عشان الفيلم ما يتحسبش item واحد بالغلط
    is_series_like = (
        ("مسلسل" in title) or
        ("الحلقة" in watch_page_html) or
        ("episodes" in watch_page_html.lower()) or
        ("season" in watch_page_html.lower())
    )

    if is_series_like:
        episodes_patterns = [
            r'<div[^>]+class=[\"\'][^\"]*(?:episodes|series-episodes|season-episodes|ep_list|episodes-list|series-list|all-episodes)[^\"]*[\"\'][^>]*>(.*?)</div>',
            r'<ul[^>]*class=[\"\'][^\"]*(?:episodes|series-episodes|list-episodes|ep_list)[^\"]*[\"\'][^>]*>(.*?)</ul>',
            r'<section[^>]*class=[\"\'][^\"]*(?:episodes|series)[^\"]*[\"\'][^>]*>(.*?)</section>',
            r'<div[^>]+id=[\"\'][^\"]*(?:episodes|episodes-list|episodes-all)[^\"]*[\"\'][^>]*>(.*?)</div>'
        ]

        eps_html = ""
        for pat in episodes_patterns:
            matches = re.findall(pat, watch_page_html, re.S | re.I)
            if matches:
                eps_html = "".join(matches)
                break

        if not eps_html:
            eps_html = watch_page_html

        eps_matches = re.findall(
            r'<a[^>]+href=["\']([^"\']+/(?:watch|episode)[^"\']*)["\'][^>]*>(.*?)</a>',
            eps_html,
            re.DOTALL | re.I
        )
        seen_eps = set()
        for e_link, e_inner in eps_matches:
            full_link = _normalize_url(e_link)
            if not full_link or full_link == watch_url:
                continue
            if full_link in seen_eps:
                continue
            seen_eps.add(full_link)

            e_text = re.sub(r'<[^>]+>', '', e_inner).strip()
            e_num_m = re.search(r'الحلقة\s*(\d+)', e_text)
            if not e_num_m:
                e_num_m = re.search(r'(\d+)', e_text)

            e_num = e_num_m.group(1).strip() if e_num_m else (e_text[:30] if e_text else "Episode")
            episodes.append({
                "title": "حلقة " + e_num if e_num.isdigit() else e_num,
                "url": full_link,
                "type": "episode",
                "_action": "item"
            })

    if episodes:
        item_type = "series"

    return {
        "url": final_url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "servers": servers,
        "items": episodes,
        "type": item_type
    }

def extract_stream(url):
    log("TopCinema: resolving {}".format(url))
    if url.startswith("topcinema_server|"):
        parts = url.split("|")
        ajax_url = parts[1]
        post_id = parts[2]
        server_index = parts[3]
        referer_url = parts[4] if len(parts) > 4 else MAIN_URL
        
        postdata = {
            "id": post_id,
            "i": server_index
        }
        
        html, _ = fetch(ajax_url, referer=referer_url, extra_headers={"X-Requested-With": "XMLHttpRequest"}, post_data=postdata)
        
        v_url = ""
        ifr_m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
        if ifr_m:
            v_url = _normalize_url(ifr_m.group(1))
            log("TopCinema: Found iframe '{}'".format(v_url))
            resolved = resolve_iframe_chain(v_url, referer=MAIN_URL)
            if resolved:
                if isinstance(resolved, tuple):
                    return resolved[0], None, (resolved[1] if len(resolved)>1 and resolved[1] else MAIN_URL)
                return resolved, None, MAIN_URL
            return v_url, None, MAIN_URL
            
    return url, None, MAIN_URL
````

## File: extractors/wecima.py
````python
# -*- coding: utf-8 -*-
import re
import sys

from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse
    from html import unescape as html_unescape
else:
    from urllib import quote_plus
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

# FIX: expanded domain list — wecima.rent was dead, added .click / .show / .video
DOMAINS = [
    "https://wecima.click/",
    "https://wecima.show/",
    "https://wecima.video/",
    "https://wecima.rent/",
    "https://wecima.date/",
    "https://www.wecima.site/",
]
VALID_HOST_MARKERS = (
    "wecima.click", "wecima.show", "wecima.video",
    "wecima.rent",  "wecima.date",  "wecima.site",
)
BLOCKED_HOST_MARKERS = ("alliance4creativity.com",)
MAIN_URL = None
_HOME_HTML = None

_CATEGORY_FALLBACKS = {
    "افلام اجنبي":    "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/",
    "افلام عربي":     "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%b9%d8%b1%d8%a8%d9%8a/",
    "مسلسلات اجنبي":  "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/",
    "مسلسلات عربية":  "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b9%d8%b1%d8%a8%d9%8a%d8%a9/",
    "مسلسلات انمي":   "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d9%86%d9%85%d9%8a/",
    "تريندج":         "/",
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
    if any(m in host for m in BLOCKED_HOST_MARKERS):
        return False
    return any(m in host for m in VALID_HOST_MARKERS)


def _is_blocked_page(html, final_url=""):
    """
    FIX: Loosened check — only block on confirmed ACE/Cloudflare walls.
    No longer rejects pages merely because domain changed (CDN redirects are normal).
    """
    text = (html or "").lower()
    final = (final_url or "").lower()
    if not text:
        return True
    if "just a moment" in text and "cf-chl" in text:
        return True
    if "enable javascript and cookies to continue" in text:
        return True
    if "watch it legally" in text or "alliance for creativity" in text:
        return True
    if any(m in final for m in BLOCKED_HOST_MARKERS):
        return True
    return False


def _looks_like_wecima_page(html):
    text = html or ""
    return (
        "Grid--WecimaPosts" in text
        or "NavigationMenu" in text
        or "Thumb--GridItem" in text
        or "WECIMA" in text
        or "وي سيما" in text
        or "wecima" in text.lower()
    )


def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)


def _get_base():
    global MAIN_URL, _HOME_HTML
    if MAIN_URL:
        return MAIN_URL
    for domain in DOMAINS:
        log("Wecima: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked {}".format(final_url))
            continue
        if html and _looks_like_wecima_page(html):
            MAIN_URL = _site_root(final_url)
            _HOME_HTML = html
            log("Wecima: selected base {}".format(MAIN_URL))
            return MAIN_URL
    MAIN_URL = DOMAINS[0]
    log("Wecima: fallback base {}".format(MAIN_URL))
    return MAIN_URL


def _search_url():
    return _get_base().rstrip("/") + "/?s="


def _normalize_url(url):
    if not url:
        return ""
    url = url.strip()
    try:
        url = url.encode("utf-8").decode("unicode_escape") if "\\u" in url else url
    except Exception:
        pass
    url = url.replace("\\u0026", "&").replace("&amp;", "&").replace("\\/", "/")
    url = html_unescape(url)
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(_get_base(), url)
    if any(m in _host(url) for m in BLOCKED_HOST_MARKERS):
        return ""
    if _is_valid_site_url(url):
        base_parts = urlparse(_get_base())
        parts = urlparse(url)
        if parts.netloc != base_parts.netloc and "wecima" in parts.netloc:
            clean = "{}://{}{}".format(base_parts.scheme, base_parts.netloc, parts.path or "/")
            if parts.query:
                clean += "?" + parts.query
            return clean
    return url


def _candidate_urls(url):
    normalized = _normalize_url(url)
    if not normalized:
        return []
    parts = urlparse(normalized)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    urls = []
    seen = set()
    seeds = []
    if MAIN_URL:
        seeds.append(MAIN_URL)
    seeds.extend(DOMAINS)
    if normalized.startswith("http"):
        seeds.insert(0, _site_root(normalized))
    for domain in seeds:
        if not domain:
            continue
        base = domain if domain.endswith("/") else domain + "/"
        candidate = urljoin(base, path.lstrip("/"))
        if candidate in seen:
            continue
        seen.add(candidate)
        urls.append(candidate)
    if normalized not in seen:
        urls.insert(0, normalized)
    return urls


def _fetch_live(url, referer=None):
    for candidate in _candidate_urls(url):
        log("Wecima: fetching {}".format(candidate))
        html, final_url = fetch(candidate, referer=referer or _get_base())
        final_url = final_url or candidate
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked {}".format(final_url))
            continue
        if html and _looks_like_wecima_page(html):
            log("Wecima: success {}".format(final_url))
            return html, final_url
        if html:
            log("Wecima: page shape mismatch {}".format(final_url))
    log("Wecima: fetch failed for {}".format(url))
    return "", ""


def _clean_html(text):
    text = html_unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title):
    title = _clean_html(title)
    for token in (
        "مشاهدة فيلم", "مشاهدة مسلسل", "مشاهدة",
        "فيلم", "مسلسل", "اون لاين", "أون لاين",
        "مترجم", "مترجمة", "مدبلج", "مدبلجة",
    ):
        title = title.replace(token, "")
    return re.sub(r"\s+", " ", title).strip(" -|")


def _home_html():
    global _HOME_HTML
    if _HOME_HTML:
        return _HOME_HTML
    base = _get_base()
    html, final_url = _fetch_live(base, referer=base)
    _HOME_HTML = html if not _is_blocked_page(html, final_url) else ""
    return _HOME_HTML


def _guess_type(title, url):
    text = "{} {}".format(title or "", url or "").lower()
    if any(t in text for t in ("/episode/", "الحلقة", "حلقة")):
        return "episode"
    if any(t in text for t in ("/series", "/season", "مسلسل", "series-")):
        return "series"
    return "movie"


def _grid_blocks(html):
    blocks = []
    for block in re.split(r'(?=<div[^>]+class="GridItem")', html or "", flags=re.I):
        if 'class="GridItem"' not in block:
            continue
        end_match = re.search(
            r'<ul[^>]+class="PostItemStats"[^>]*>.*?</ul>\s*</div>',
            block, re.S | re.I,
        )
        blocks.append(block[: end_match.end()] if end_match else block[:2500])
    return blocks


def _extract_cards(html):
    cards = []
    seen = set()
    for block in _grid_blocks(html):
        href_match = re.search(r'<a[^>]+href="([^"]+)"', block, re.I)
        if not href_match:
            continue
        url = _normalize_url(href_match.group(1))
        if not url or url in seen:
            continue
        lowered = url.lower()
        if any(t in lowered for t in ("/category/", "/tag/", "/page/", "/filtering", "/feed/")):
            continue

        title_match = (
            re.search(r'title="([^"]+)"', block, re.I)
            or re.search(r'<strong[^>]+class="hasyear"[^>]*>(.*?)</strong>', block, re.S | re.I)
            or re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S | re.I)
        )
        title = _clean_title(title_match.group(1) if title_match else "")
        if not title:
            continue

        poster = ""
        m = re.search(r'data-lazy-style="[^"]*url\(([^)]+)\)"', block, re.I)
        if m:
            poster = m.group(1).strip("'\" ")
        if not poster:
            m = re.search(r'(?:data-src|src)="([^"]+)"', block, re.I)
            if m:
                poster = m.group(1).strip()

        year = ""
        m = re.search(r'<span[^>]+class="year"[^>]*>\(\s*(\d{4})', block, re.I)
        if m:
            year = m.group(1)

        seen.add(url)
        cards.append({
            "title": title,
            "url": url,
            "poster": _normalize_url(poster) if poster else "",
            "plot": year,
            "type": _guess_type(title, url),
            "_action": "details",
        })
    log("Wecima: extracted {} cards".format(len(cards)))
    return cards


def _extract_next_page(html):
    for pat in (
        r'<a[^>]+class="[^"]*next[^"]*page-numbers[^"]*"[^>]+href="([^"]+)"',
        r'<a[^>]+rel="next"[^>]+href="([^"]+)"',
    ):
        m = re.search(pat, html or "", re.I)
        if m:
            return _normalize_url(m.group(1))
    return ""


def _category_from_home(label, fallback):
    html = _home_html()
    for pattern in (
        r'<a[^>]+href="([^"]+)"[^>]*>\s*' + re.escape(label) + r'\s*</a>',
        r'<a[^>]+href="([^"]+)"[^>]*>\s*<span[^>]*>\s*' + re.escape(label) + r'\s*</span>',
    ):
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            url = _normalize_url(m.group(1))
            if url:
                return url
    return _normalize_url(urljoin(_get_base(), _CATEGORY_FALLBACKS.get(label, "/")))


def _extract_servers(html):
    servers = []
    seen = set()

    # Method 1: <ul id="watch"> with data-watch
    watch_list = re.search(r'<ul[^>]+id="watch"[^>]*>(.*?)</ul>', html or "", re.S | re.I)
    if watch_list:
        for idx, m in enumerate(re.finditer(
            r'<li[^>]+data-watch="([^"]+)"[^>]*>(.*?)</li>',
            watch_list.group(1), re.S | re.I
        )):
            server_url = html_unescape(m.group(1)).strip()
            if not server_url or server_url in seen:
                continue
            seen.add(server_url)
            name = _clean_html(m.group(2)) or "Server {}".format(idx + 1)
            servers.append({"name": name, "url": server_url, "type": "direct"})
    if servers:
        return servers

    # Method 2: class containing server/watch/player
    for m in re.finditer(
        r'<(?:a|div|li|button)[^>]+(?:class|id)="[^"]*(?:server|watch|player)[^"]*"[^>]*>.*?href="([^"]+)"',
        html or "", re.S | re.I
    ):
        url = _normalize_url(m.group(1))
        if url and url not in seen and "://" in url:
            seen.add(url)
            servers.append({"name": "Server {}".format(len(servers) + 1), "url": url, "type": "direct"})

    # Method 3: iframes with embed/player/stream
    if not servers:
        for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', html or "", re.I):
            url = _normalize_url(m.group(1))
            if url and url not in seen and "://" in url:
                if any(k in url for k in ["embed", "player", "watch", "stream", "video"]):
                    seen.add(url)
                    servers.append({"name": "Player {}".format(len(servers) + 1), "url": url, "type": "direct"})

    if not servers:
        log("Wecima: no watch server list found")
    return servers


def _extract_episode_cards(html):
    episodes = []
    seen = set()
    for card in _extract_cards(html):
        title = card.get("title") or ""
        url = card.get("url") or ""
        if "الحلقة" not in title and "حلقة" not in title and "/episode/" not in url.lower():
            continue
        if url in seen:
            continue
        seen.add(url)
        episodes.append({
            "title": title or "حلقة",
            "url": url,
            "type": "episode",
            "_action": "details",
        })
    return episodes


def _detail_title(html):
    for pattern in (
        r'<h1[^>]+itemprop="name"[^>]*>(.*?)</h1>',
        r'<h1[^>]*>(.*?)</h1>',
        r'property="og:title"[^>]+content="([^"]+)"',
        r'content="([^"]+)"[^>]+property="og:title"',
    ):
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            title = _clean_title(m.group(1))
            if title:
                return title
    return ""


def _detail_plot(html):
    for pattern in (
        r'<span[^>]+itemprop="description"[^>]*>(.*?)</span>',
        r'<meta[^>]+itemprop="description"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+itemprop="description"',
        r'property="og:description"[^>]+content="([^"]+)"',
        r'content="([^"]+)"[^>]+property="og:description"',
        r'name="description"[^>]+content="([^"]+)"',
    ):
        m = re.search(pattern, html or "", re.S | re.I)
        if m:
            text = _clean_html(m.group(1))
            if text and "موقع وي سيما" not in text and "مشاهدة احدث الافلام" not in text:
                return text
    return ""


def _detail_poster(html):
    for pattern in (
        r'<wecima[^>]+style="[^"]*--img:url\(([^)]+)\)',
        r'property="og:image"[^>]+content="([^"]+)"',
        r'content="([^"]+)"[^>]+property="og:image"',
        r'(?:data-src|src)="([^"]+)"[^>]+itemprop="image"',
    ):
        m = re.search(pattern, html or "", re.I)
        if m:
            poster = m.group(1).strip("'\" ")
            if poster:
                return _normalize_url(poster) or poster
    return ""


def _detail_year(title, html):
    m = re.search(r'\b(19\d{2}|20\d{2}|21\d{2})\b', title or "")
    if m:
        return m.group(1)
    for pat in (r'datePublished[^>]*?(\d{4})', r'"datePublished"\s*:\s*"(\d{4})'):
        m = re.search(pat, html or "", re.I)
        if m:
            return m.group(1)
    return ""


def _detail_rating(html):
    m = re.search(r'"ratingValue"\s*:\s*"?(\\?\d+(?:\.\d+)?)', html or "", re.I)
    if m:
        return m.group(1).replace("\\", "")
    m = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', html or "", re.I)
    if m:
        return m.group(1)
    return ""


def get_categories(mtype="movie"):
    return [
        {"title": "أفلام أجنبية",   "url": _category_from_home("افلام اجنبي",   _CATEGORY_FALLBACKS["افلام اجنبي"]),   "type": "category", "_action": "category"},
        {"title": "أفلام عربية",    "url": _category_from_home("افلام عربي",    _CATEGORY_FALLBACKS["افلام عربي"]),    "type": "category", "_action": "category"},
        {"title": "مسلسلات أجنبية", "url": _category_from_home("مسلسلات اجنبي", _CATEGORY_FALLBACKS["مسلسلات اجنبي"]), "type": "category", "_action": "category"},
        {"title": "مسلسلات عربية",  "url": _category_from_home("مسلسلات عربية", _CATEGORY_FALLBACKS["مسلسلات عربية"]), "type": "category", "_action": "category"},
        {"title": "كارتون وانمي",   "url": _category_from_home("مسلسلات انمي",  _CATEGORY_FALLBACKS["مسلسلات انمي"]),  "type": "category", "_action": "category"},
        {"title": "ترند",           "url": _category_from_home("تريندج",        _CATEGORY_FALLBACKS["تريندج"]),        "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    base = _get_base()
    html, final_url = _fetch_live(url, referer=base)
    if _is_blocked_page(html, final_url):
        log("Wecima: category blocked {}".format(url))
        return []
    items = _extract_cards(html)
    if not items:
        alt_html, alt_url = _fetch_live((final_url or url).rstrip("/") + "/page/1/", referer=base)
        if not _is_blocked_page(alt_html, alt_url):
            html = alt_html
            items = _extract_cards(alt_html)
    log("Wecima: {} -> {} items".format(url, len(items)))
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def search(query, page=1):
    base = _get_base()
    items = []
    html = ""
    for search_url in [
        _search_url() + quote_plus(query),
        urljoin(base, "search/") + quote_plus(query),
    ]:
        html, final_url = _fetch_live(search_url, referer=base)
        if _is_blocked_page(html, final_url):
            continue
        items = _extract_cards(html)
        if items:
            break
    log("Wecima: search '{}' -> {} items".format(query, len(items)))
    if not html and not items:
        return []
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def get_page(url, m_type=None):
    base = _get_base()
    html, final_url = _fetch_live(url, referer=base)
    if _is_blocked_page(html, final_url) or not html:
        log("Wecima: detail failed {}".format(url))
        return {"title": "Error", "servers": [], "items": [], "type": m_type or "movie"}

    title  = _detail_title(html)
    poster = _detail_poster(html)
    plot   = _detail_plot(html)
    year   = _detail_year(title, html)
    rating = _detail_rating(html)

    servers  = _extract_servers(html)
    episodes = [] if servers else _extract_episode_cards(html)
    log("Wecima: detail {} -> servers={}, episodes={}".format(url, len(servers), len(episodes)))

    item_type = m_type or _guess_type(title, final_url or url)
    if episodes:
        item_type = "series"
    elif servers and any(t in (title or "") for t in ("الحلقة", "حلقة")):
        item_type = "episode"

    return {
        "url":     final_url or url,
        "title":   title,
        "plot":    plot,
        "poster":  poster,
        "rating":  rating,
        "year":    year,
        "servers": servers,
        "items":   episodes,
        "type":    item_type,
    }


def extract_stream(url):
    """
    FIX: Removed the brittle akhbarworld/mycimafsd branch.
    All resolution now delegates to the unified base extractor which
    handles all known video hosts including the ones Wecima uses.
    """
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
````

## File: images/playerclock.xml
````xml
<widget name="clockTime" noWrap="1" position="35,6" size="500,40" zPosition="3" transparent="1" foregroundColor="#66ccff" backgroundColor="#251f1f1f" font="Regular;%d" halign="left" valign="center" />
````

## File: images/playerskin.xml
````xml
<screen name="IPTVExtMoviePlayer"    position="center,center" size="%d,%d" flags="wfNoBorder" backgroundColor="#FFFFFFFF" >
                    <widget name="pleaseWait"         noWrap="1" position="center,30"        size="500,40"    zPosition="3" transparent="1" foregroundColor="#999999"   backgroundColor="transparent" font="Regular;25" halign="center"  valign="center"/>
                    
                    <widget name="logoIcon"           position="1176,110"        size="160,40"    zPosition="4"             transparent="1" alphatest="blend" />
                    <widget name="playbackInfoBaner"  position="0,0"           size="1280,177"  zPosition="2" pixmap="%s" />
                    <widget name="progressBar"        position="220,86"        size="840,7"     zPosition="5" pixmap="%s" transparent="1" borderWidth="1" borderColor="#888888" />
                    <widget name="bufferingCBar"      position="220,86"        size="840,7"     zPosition="4" pixmap="%s" transparent="1" borderWidth="1" borderColor="#888888" />
                    <widget name="bufferingBar"       position="220,86"        size="840,7"     zPosition="3" pixmap="%s" borderWidth="1" borderColor="#888888" />
                    <widget name="statusIcon"         position="135,55"        size="72,72"     zPosition="4"             transparent="1" alphatest="blend" />
                    <widget name="loopIcon"           position="60,80"       size="40,40"     zPosition="4"             transparent="1" alphatest="blend" />
                    
                    <widget name="goToSeekPointer"    position="94,30"          size="150,60"  zPosition="8" pixmap="%s" transparent="1" alphatest="blend" />
                    <widget name="goToSeekLabel"      noWrap="1" position="94,30"         size="150,40"   zPosition="9" transparent="1" foregroundColor="white"     backgroundColor="#251f1f1f" font="Regular;27" halign="center" valign="center"/>
                    <widget name="infoBarTitle"       noWrap="1" position="220,41"        size="1000,50"  zPosition="3" transparent="1" foregroundColor="white"     backgroundColor="#251f1f1f" font="Regular;29" halign="left" valign="center"/>
                    <widget name="currTimeLabel"      noWrap="1" position="220,100"       size="200,40"   zPosition="3" transparent="1" foregroundColor="#66ccff"   backgroundColor="#251f1f1f" font="Regular;27" halign="left"   valign="top"/>
                    <widget name="lengthTimeLabel"    noWrap="1" position="540,115"       size="200,40"   zPosition="3" transparent="1" foregroundColor="#999999"   backgroundColor="#251f1f1f" font="Regular;30" halign="center" valign="top"/>
                    <widget name="remainedLabel"      noWrap="1" position="860,100"       size="200,40"   zPosition="3" transparent="1" foregroundColor="#66ccff"   backgroundColor="#251f1f1f" font="Regular;27" halign="right"  valign="top"/>
                    <widget name="videoInfo"          noWrap="1" position="732,8"        size="500,30"   zPosition="3" transparent="1" foregroundColor="#c8cedb"   backgroundColor="#251f1f1f" font="Regular;23" halign="right"  valign="top"/>
                    
                    %s
                    
                    <widget name="subSynchroIcon"     position="0,0"           size="180,66"  zPosition="4" transparent="1" alphatest="blend" />
                    <widget name="subSynchroLabel"    position="1,3"           size="135,50"  zPosition="5" transparent="1" foregroundColor="white"      backgroundColor="transparent" font="Regular;24" halign="center"  valign="center"/>
                    
                    %s
</screen>
````

## File: images/settings.json
````json
{
"clockFontSize_SD" : 24,
"clockFontSize_HD" : 24,
"clockFontSize_FHD" : 24,
"clockFormat_24H" : "%H:%M:%S",
"clockFormat_12H" : "%I:%M"  
}
````

## File: plugin.py
````python
# -*- coding: utf-8 -*-
"""
ArabicPlayer Plugin for Enigma2
================================
تشغيل مواقع الأفلام العربية مباشرة من الرسيفر
الموقع الأول: EgyDead

الأزرار:
  OK         → فتح / تشغيل
  Back       → رجوع
  Red        → أحدث أفلام
  Green      → أحدث مسلسلات
  Yellow     → بحث
  Blue       → إعدادات
  Info       → معلومات العنصر
"""

import os
import sys
import json
import re
import threading
import time
import http.server
import urllib.request as urllib2

try:
    from urllib.parse import quote, unquote, urlparse, parse_qs, urlencode
except ImportError:
    from urllib import quote, unquote, urlencode
    from urlparse import urlparse, parse_qs

# Dynamic plugin path
PLUGIN_PATH = os.path.dirname(__file__)
if PLUGIN_PATH not in sys.path:
    sys.path.insert(0, PLUGIN_PATH)

from Plugins.Plugin          import PluginDescriptor
from Screens.Screen          import Screen
from Screens.MessageBox      import MessageBox
from Components.ActionMap    import ActionMap
from Components.Label        import Label
from Components.Pixmap       import Pixmap
from Components.MenuList     import MenuList
from Components.ScrollLabel  import ScrollLabel
from enigma import eTimer, ePicLoad, eServiceReference, iPlayableService
from Components.ServiceEventTracker import ServiceEventTracker

_PLUGIN_VERSION = "2.0.2"
_PLUGIN_NAME    = "ArabicPlayer"
_PLUGIN_OWNER   = "أحمد إبراهيم"
_DEFAULT_TMDB_API_KEY = "01fd9e035ea1458748e99eb7216b0259"
_TYPE_LABELS    = {"movie": "فيلم", "series": "مسلسل", "episode": "حلقة"}
_TMDB_API_BASE  = "https://api.themoviedb.org/3"
_TMDB_IMG_BASE  = "https://image.tmdb.org/t/p/w500"
# FIX #1: removed invalid concatenated "shaheed""yts2" → was missing comma
_SEARCH_SITE_ORDER = ("egydead", "akoam", "arabseed", "wecima", "topcinema", "fasel", "shaheed")

# ─── Neon Color Palette ──────────────────────────────────────────────────────
_CLR = {
    "bg":           "#0D1117",
    "surface":      "#161B22",
    "surface2":     "#1C2333",
    "selected":     "#21262D",
    "border":       "#30363D",
    "cyan":         "#00E5FF",
    "purple":       "#E040FB",
    "gold":         "#FFD740",
    "green":        "#39D98A",
    "red":          "#FF6B6B",
    "blue":         "#58A6FF",
    "text":         "#F0F6FC",
    "text2":        "#8B949E",
    "text_dim":     "#484F58",
}

# ─── Poster Cache ────────────────────────────────────────────────────────────
import hashlib
_POSTER_CACHE_DIR = "/tmp/ap_cache"

def _poster_cache_path(url):
    if not url: return None
    try:
        if not os.path.isdir(_POSTER_CACHE_DIR):
            os.makedirs(_POSTER_CACHE_DIR)
    except Exception: pass
    url_hash = hashlib.md5(url.encode("utf-8", "ignore")).hexdigest()
    return os.path.join(_POSTER_CACHE_DIR, "{}.jpg".format(url_hash))

def _is_poster_cached(url):
    path = _poster_cache_path(url)
    return path and os.path.exists(path)

def _get_cached_poster(url):
    path = _poster_cache_path(url)
    if path and os.path.exists(path):
        return path
    return None

# ─── Extractor Factory ───────────────────────────────────────────────────────
_EXTRACTOR_MAP = {
    "egydead":    "extractors.egydead",
    "akoam":      "extractors.akoam",
    "arabseed":   "extractors.arabseed",
    "wecima":     "extractors.wecima",
    "shaheed":    "extractors.shaheed",
    "topcinema":  "extractors.topcinema",
    "fasel":      "extractors.fasel",
}

def _get_extractor(site):
    module_name = _EXTRACTOR_MAP.get(site)
    if not module_name:
        module_name = _EXTRACTOR_MAP.get("egydead")
    return __import__(module_name, fromlist=["get_categories", "get_category_items", "get_page", "search", "extract_stream"])

_SITE_META = {
    "egydead": {
        "title": "EgyDead",
        "tagline": "واجهة حديثة وبوسترات ومكتبة متجددة",
    },
    "akoam": {
        "title": "Akoam",
        "tagline": "محتوى متنوع مع صفحات تفصيلية واضحة",
    },
    "arabseed": {
        "title": "Arabseed",
        "tagline": "تصنيفات عربية وأجنبية وحلقات مرتبة",
    },
    "wecima": {
        "title": "Wecima",
        "tagline": "أقسام واسعة وبحث وسيرفرات مباشرة",
    },
    "shaheed": {
        "title": "Shaheed4u",
        "tagline": "تحديثات المسلسلات والأفلام الحصرية بجميع الجودات",
    },
    "topcinema": {
        "title": "TopCinemaa",
        "tagline": "مكتبة ضخمة من الأفلام والمسلسلات والسلاسل",
    },
    "fasel": {
        "title": "FaselHD",
        "tagline": "دقة عالية وسيرفرات متعددة للمشاهدة بدون تقطيع",
    },
}

# ─── Logging ─────────────────────────────────────────────────────────────────
from extractors.base import log as base_log, UA, fetch as base_fetch

SAFE_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_STATE_CACHE = None

def my_log(msg):
    base_log(msg)


# ─── Helper ──────────────────────────────────────────────────────────────────
def _site_label(site):
    return (_SITE_META.get(site) or {}).get("title", str(site or "").capitalize())


def _site_tagline(site):
    return (_SITE_META.get(site) or {}).get("tagline", "")


def _normalize_query(text):
    text = (text or "").strip().lower()
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    return "".join(ch for ch in text if ch.isalnum())


def _strip_arabic_from_english_title(title):
    """
    If a title is predominantly English/Latin (Arabic chars < 30% of non-space chars),
    strip all Arabic words and clean up leftover punctuation.
    Pure Arabic titles are returned unchanged.
    """
    if not title:
        return title
    stripped = title.replace(" ", "")
    if not stripped:
        return title
    ar_count = sum(1 for c in stripped if "\u0600" <= c <= "\u06ff")
    if ar_count / len(stripped) >= 0.30:
        return title
    cleaned = re.sub(r"[\u0600-\u06ff]+", " ", title)
    cleaned = re.sub(r"[\s|\-–_]+$", "", cleaned)
    cleaned = re.sub(r"^[\s|\-–_]+", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -|_")
    return cleaned if cleaned.strip() else title


def _clean_title_for_tmdb(title):
    if not title: return ""
    junk = [
        u"مترجم", u"اون لاين", u"بجودة", u"عالية", u"كامل", u"تحميل", u"مشاهدة", u"فيلم", u"مسلسل",
        u"انمي", u"كرتون", u"حصري", u"شاشه", u"كامله", u"نسخة", u"اصلية", u"bluray", u"web-dl", u"hdtv", u"720p", u"1080p", u"4k"
    ]
    title = title.lower()
    for word in junk:
        title = title.replace(word, "")
    title = re.sub(r'\s+\d{4}\s*$', '', title)
    return re.sub(r'\s+', ' ', title).strip()


def _wrap_ui_text(text, width=40, max_lines=2, fallback=""):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return fallback
    words = text.split(" ")
    lines = []
    current = ""

    for word in words:
        candidate = word if not current else "{} {}".format(current, word)
        if len(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
            if len(lines) >= max_lines:
                break
        current = word

    if len(lines) < max_lines and current:
        lines.append(current)
    if not lines:
        lines = [text[:width]]

    consumed = " ".join(lines)
    if len(consumed) < len(text):
        lines[-1] = lines[-1].rstrip(" .،") + "..."
    return "\n".join(lines[:max_lines])


def _single_line_text(text, width=54, fallback=""):
    return _wrap_ui_text(text, width=width, max_lines=1, fallback=fallback)


def _search_scope_label(scope):
    if scope == "all":
        return "كل المصادر: EgyDead / Akoam / Arabseed / Wecima / TopCinemaa"
    return "المصدر الحالي: {}".format(_site_label(scope))


def _site_search_item(site):
    return {
        "title": "بحث داخل {}".format(_site_label(site)),
        "_action": "search_site",
        "_site": site,
        "type": "tool",
        "plot": "ابحث داخل {} فقط بدون خلط النتائج مع باقي المصادر.".format(_site_label(site)),
    }


def _dedupe_items(items):
    unique = []
    seen = set()
    for item in items or []:
        key = item.get("url") or item.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _rank_search_items(items, query):
    q = _normalize_query(query)
    q_words = [w for w in q.split() if len(w) >= 2] if q else []

    strong   = []
    weak     = []
    no_match = []

    for item in _dedupe_items(items):
        title  = item.get("title", "")
        ntitle = _normalize_query(title)
        rank   = 9

        if not q:
            rank = 5
        elif ntitle == q:
            rank = 0
        elif ntitle.startswith(q):
            rank = 1
        elif q in ntitle:
            rank = 2
        elif q_words:
            matched_words = sum(1 for w in q_words if w in ntitle)
            if matched_words == len(q_words):
                rank = 3
            elif matched_words >= max(1, len(q_words) * 2 // 3):
                rank = 4
            elif matched_words > 0:
                rank = 5

        entry = (rank, title.lower(), item)
        if rank <= 3:
            strong.append(entry)
        elif rank <= 5:
            weak.append(entry)
        else:
            no_match.append(item)

    strong.sort(key=lambda r: (r[0], r[1]))
    weak.sort(key=lambda r: (r[0], r[1]))

    result = [r[2] for r in strong]

    if len(result) < 3:
        result += [r[2] for r in weak[:max(0, 5 - len(result))]]

    if not result and weak:
        result = [r[2] for r in weak]

    return result


def _quality_rank(server_name):
    text = (server_name or "").lower()
    if "2160" in text or "4k" in text:
        return 0
    if "1080" in text:
        return 1
    if "720" in text or "hd" in text:
        return 2
    if "480" in text:
        return 3
    if "360" in text:
        return 4
    return 9


def _sort_servers(servers):
    return sorted(servers or [], key=lambda s: (_quality_rank(s.get("name", "")), s.get("name", "").lower()))


def _decorate_item_title(item, site=None):
    title = _strip_arabic_from_english_title((item.get("title") or "---").strip())
    action = item.get("_action", "")
    item_type = item.get("type", action)
    if action.startswith("site_"):
        return title

    if item_type == "movie":
        prefix = "[فيلم]"
    elif item_type == "series":
        prefix = "[مسلسل]"
    elif item_type == "episode":
        prefix = "[حلقة]"
    elif item_type == "category":
        prefix = "[قسم]"
    else:
        prefix = "•"

    item_site = item.get("_site") or site
    if item_site and item_type in ("movie", "series", "episode"):
        return "{} [{}] {}".format(prefix, _site_label(item_site), title)
    return "{} {}".format(prefix, title)


def _state_path():
    for candidate in ("/etc/enigma2/arabicplayer_state.json", os.path.join(PLUGIN_PATH, "arabicplayer_state.json"), "/tmp/arabicplayer_state.json"):
        try:
            parent = os.path.dirname(candidate)
            if parent and os.path.isdir(parent) and os.access(parent, os.W_OK):
                return candidate
        except Exception:
            pass
    return "/tmp/arabicplayer_state.json"


# Thread-safe main-loop dispatcher
_CMIT_QUEUE = []
_CMIT_LOCK  = threading.Lock()
_CMIT_TIMER = None


def _default_state():
    return {
        "config": {
            "owner": _PLUGIN_OWNER,
            "tmdb_api_key": _DEFAULT_TMDB_API_KEY,
        },
        "favorites": [],
        "history": [],
    }


def _load_state():
    global _STATE_CACHE
    if _STATE_CACHE is not None:
        return _STATE_CACHE
    state = _default_state()
    path = _state_path()
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                state.update(loaded)
                state["config"] = dict(_default_state()["config"], **(loaded.get("config") or {}))
    except Exception as e:
        my_log("State load error: {}".format(e))
    _STATE_CACHE = state
    return _STATE_CACHE


def _save_state(state=None):
    global _STATE_CACHE
    _STATE_CACHE = state or _load_state()
    path = _state_path()
    tmp  = path + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(_STATE_CACHE, f)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, path)
    except Exception as e:
        my_log("State save error: {}".format(e))
        try: os.remove(tmp)
        except Exception: pass


def _get_config(key, default=""):
    value = (_load_state().get("config") or {}).get(key, default)
    if key == "tmdb_api_key" and not value:
        return _DEFAULT_TMDB_API_KEY
    if key == "owner" and not value:
        return _PLUGIN_OWNER
    return value


def _set_config(key, value):
    state = _load_state()
    state.setdefault("config", {})[key] = value
    _save_state(state)


def _entry_from_item(item, site, m_type, extra=None):
    entry = {
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "poster": item.get("poster") or item.get("image") or "",
        "plot": item.get("plot", ""),
        "year": item.get("year", ""),
        "rating": item.get("rating", ""),
        "type": item.get("type", "") or m_type,
        "_action": item.get("_action", "details"),
        "_site": item.get("_site", site),
        "_m_type": item.get("_m_type", m_type),
        "_saved_at": int(time.time()),
    }
    if extra:
        entry.update(extra)
    return entry


def _upsert_library_item(bucket, entry, limit=100):
    state = _load_state()
    items = state.setdefault(bucket, [])
    key   = entry.get("url")
    if not entry.get("last_position_sec"):
        for _old in items:
            if _old.get("url") == key and _old.get("last_position_sec"):
                entry["last_position_sec"] = _old["last_position_sec"]
                break
    items = [i for i in items if i.get("url") != key]
    items.insert(0, entry)
    state[bucket] = items[:limit]
    _save_state(state)


def _toggle_favorite_entry(entry):
    state = _load_state()
    favorites = state.setdefault("favorites", [])
    key = entry.get("url")
    for idx, item in enumerate(favorites):
        if item.get("url") == key:
            favorites.pop(idx)
            _save_state(state)
            return False
    favorites.insert(0, entry)
    state["favorites"] = favorites[:100]
    _save_state(state)
    return True


def _is_favorite(url):
    return any(item.get("url") == url for item in (_load_state().get("favorites") or []))


def _history_items():
    return _load_state().get("history") or []


def _favorite_items():
    return _load_state().get("favorites") or []


def _get_saved_position(url):
    for item in (_load_state().get("history") or []):
        if item.get("url") == url:
            pos = int(item.get("last_position_sec") or 0)
            return pos if pos > 30 else 0
    return 0


def _save_position(url, seconds):
    seconds = int(seconds or 0)
    if 0 < seconds < 30:
        my_log("_save_position: skipping {}s (< 30s threshold)".format(seconds))
        return
    state = _load_state()
    for item in (state.get("history") or []):
        if item.get("url") == url:
            item["last_position_sec"] = seconds
            _save_state(state)
            return


# Global position tracker
_GLOBAL_POS_TIMER      = None
_GLOBAL_POS_SESSION    = None
_GLOBAL_POS_ITEM       = ""
_GLOBAL_PLAY_START_WALL  = 0.0
_GLOBAL_PLAY_START_POS   = 0
_GLOBAL_LAST_SEEK_TARGET = -1


def _global_pos_tick():
    global _GLOBAL_POS_ITEM, _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
    if not _GLOBAL_POS_ITEM or not _GLOBAL_PLAY_START_WALL:
        return
    try:
        elapsed = time.time() - _GLOBAL_PLAY_START_WALL
        secs    = int(_GLOBAL_PLAY_START_POS + elapsed)
        if secs < 5:
            my_log("Pos tracker: skipping suspicious pos {}s".format(secs))
            return
        _save_position(_GLOBAL_POS_ITEM, secs)
        my_log("Pos tracker saved: {}s for {}".format(secs, _GLOBAL_POS_ITEM[:50]))
    except Exception as e:
        my_log("Pos tracker error: {}".format(e))


def _start_pos_tracker(session, item_url, start_pos=0):
    global _GLOBAL_POS_TIMER, _GLOBAL_POS_SESSION, _GLOBAL_POS_ITEM
    global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
    global _GLOBAL_LAST_SEEK_TARGET
    _GLOBAL_LAST_SEEK_TARGET = -1
    _GLOBAL_POS_SESSION     = session
    _GLOBAL_POS_ITEM        = item_url or ""
    _GLOBAL_PLAY_START_WALL = time.time()
    _GLOBAL_PLAY_START_POS  = int(start_pos or 0)
    if _GLOBAL_POS_TIMER is None:
        _GLOBAL_POS_TIMER = eTimer()
        _GLOBAL_POS_TIMER.callback.append(_global_pos_tick)
    try:
        _GLOBAL_POS_TIMER.stop()
    except Exception:
        pass
    if _GLOBAL_POS_ITEM:
        _GLOBAL_POS_TIMER.start(20000, False)
        my_log("Pos tracker started (wall-clock base={}s): {}".format(
            _GLOBAL_PLAY_START_POS, item_url[:50]))


def _stop_pos_tracker():
    global _GLOBAL_POS_ITEM
    _GLOBAL_POS_ITEM = ""
    try:
        if _GLOBAL_POS_TIMER:
            _GLOBAL_POS_TIMER.stop()
    except Exception:
        pass


def _library_search_suggestions(query="", current_site="", limit=8):
    q = _normalize_query(query)
    rows = []
    seen = set()
    for source_name, items, source_rank in (
        ("المفضلة", _favorite_items(), 0),
        ("السجل", _history_items(), 1),
    ):
        for item in items or []:
            title = re.sub(r"\s+", " ", item.get("title", "") or "").strip()
            if not title:
                continue
            norm = _normalize_query(title)
            if not norm or norm in seen:
                continue
            if q:
                if norm == q:
                    score = 0
                elif norm.startswith(q):
                    score = 1
                elif q in norm:
                    score = 2
                else:
                    continue
            else:
                score = 5
            if current_site and item.get("_site") == current_site:
                score -= 1
            seen.add(norm)
            rows.append((
                score,
                source_rank,
                -int(item.get("_saved_at") or 0),
                {
                    "title": title,
                    "query": title,
                    "source": source_name,
                    "site": item.get("_site", ""),
                    "kind": _TYPE_LABELS.get(item.get("type", ""), ""),
                    "year": item.get("year", ""),
                }
            ))
    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    return [row[3] for row in rows[:limit]]


def _tmdb_enabled():
    return bool((_get_config("tmdb_api_key", "") or "").strip())


def _tmdb_request(path, params=None):
    api_key = (_get_config("tmdb_api_key", "") or "").strip()
    if not api_key:
        return None
    base_payload = {"api_key": api_key}
    if params:
        base_payload.update(params)
    for language in ("ar", "en-US"):
        payload = dict(base_payload)
        payload["language"] = language
        url = "{}{}?{}".format(_TMDB_API_BASE, path, urlencode(payload))
        try:
            raw, _ = base_fetch(
                url,
                referer="https://www.themoviedb.org/",
                extra_headers={"Accept": "application/json"}
            )
            if not raw:
                continue
            data = json.loads(raw)
            if isinstance(data, dict):
                if data.get("overview") or data.get("results") or language == "en-US":
                    return data
        except Exception as e:
            my_log("TMDb request failed {} [{}]: {}".format(path, language, e))
    return None


def _tmdb_request_language(path, language="ar", params=None, accept_any=False):
    api_key = (_get_config("tmdb_api_key", "") or "").strip()
    if not api_key:
        return None
    payload = {"api_key": api_key, "language": language}
    if params:
        payload.update(params)
    url = "{}{}?{}".format(_TMDB_API_BASE, path, urlencode(payload))
    try:
        raw, _ = base_fetch(
            url,
            referer="https://www.themoviedb.org/",
            extra_headers={"Accept": "application/json"}
        )
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if accept_any or data.get("overview") or data.get("results"):
            return data
    except Exception as e:
        my_log("TMDb language request failed {} [{}]: {}".format(path, language, e))
    return None


def _tmdb_poster_url(path):
    if not path:
        return ""
    if path.startswith("http"):
        return path
    return _TMDB_IMG_BASE + path


def _tmdb_pick_poster(media_kind, tmdb_id, fallback_path=""):
    if not tmdb_id:
        return _tmdb_poster_url(fallback_path or "")
    images = _tmdb_request_language(
        "/{}/{}/images".format(media_kind, tmdb_id),
        language="en-US",
        params={"include_image_language": "ar,en,null"},
        accept_any=True,
    ) or {}
    posters = images.get("posters") or []
    for wanted_lang in ("ar", None, "en"):
        for poster in posters:
            if poster.get("iso_639_1") == wanted_lang and poster.get("file_path"):
                return _tmdb_poster_url(poster.get("file_path"))
    return _tmdb_poster_url(fallback_path or "")


def _tmdb_media_kind(item_type):
    if item_type in ("series", "episode", "tv"):
        return "tv"
    return "movie"


def _tmdb_pick_best(results, query, year=""):
    query_norm = _normalize_query(query)
    target_year = (year or "")[:4]
    scored = []
    for result in results or []:
        title = result.get("title") or result.get("name") or ""
        title_norm = _normalize_query(title)
        score = 9
        if title_norm == query_norm:
            score = 0
        elif title_norm.startswith(query_norm):
            score = 1
        elif query_norm and query_norm in title_norm:
            score = 2
        release = str(result.get("release_date") or result.get("first_air_date") or "")
        if target_year and release[:4] == target_year:
            score -= 1
        scored.append((score, title.lower(), result))
    scored.sort(key=lambda row: (row[0], row[1]))
    return scored[0][2] if scored else None


def _tmdb_search_metadata(title, year="", item_type="movie"):
    if not title or not _tmdb_enabled():
        return None
    media_kind = _tmdb_media_kind(item_type)
    variants = [title.strip()]
    simple = re.sub(r"\s*\(\d{4}\)\s*$", "", title).strip()
    if simple and simple not in variants:
        variants.append(simple)
    plain = re.sub(r"[:|_\-]+", " ", simple).strip()
    if plain and plain not in variants:
        variants.append(plain)
    clean = re.sub(r"\b(bluray|webrip|web-dl|hdrip|hdcam|cam|1080p|720p|480p|360p)\b", "", plain, flags=re.I).strip()
    clean = re.sub(r"\s+", " ", clean).strip(" -|")
    if clean and clean not in variants:
        variants.append(clean)
    arabic_clean = re.sub(
        r"\b(مشاهدة|فيلم|مسلسل|الحلقة|حلقة|الموسم|مترجم(?:ة)?|مدبلج(?:ة)?|اون لاين|أون لاين)\b",
        "",
        clean,
        flags=re.I,
    ).strip()
    arabic_clean = re.sub(r"\s+", " ", arabic_clean).strip(" -|")
    if arabic_clean and arabic_clean not in variants:
        variants.append(arabic_clean)

    best = None
    for query in variants:
        params = {"query": query}
        if year:
            if media_kind == "movie":
                params["year"] = year[:4]
            else:
                params["first_air_date_year"] = year[:4]
        data = _tmdb_request("/search/{}".format(media_kind), params) or {}
        best = _tmdb_pick_best(data.get("results") or [], query, year)
        if not best:
            params.pop("year", None)
            params.pop("first_air_date_year", None)
            best = _tmdb_pick_best((_tmdb_request("/search/{}".format(media_kind), params) or {}).get("results") or [], query, "")
        if best:
            break
    if not best:
        return None
    detail_ar = _tmdb_request_language(
        "/{}/{}".format(media_kind, best.get("id")),
        language="ar",
        params={"append_to_response": "credits"},
        accept_any=True,
    ) or {}
    detail_en = _tmdb_request_language(
        "/{}/{}".format(media_kind, best.get("id")),
        language="en-US",
        params={"append_to_response": "credits"},
        accept_any=True,
    ) or {}
    detail = detail_ar or detail_en
    if not detail:
        detail = _tmdb_request("/{}/{}".format(media_kind, best.get("id"))) or {}
    if not detail:
        detail = best
    genres_source = detail_ar or detail_en or detail
    genres = ", ".join([g.get("name", "") for g in genres_source.get("genres") or [] if g.get("name")])
    localized_plot = (
        (detail_ar.get("overview") or "").strip()
        or (detail_en.get("overview") or "").strip()
        or (best.get("overview") or "").strip()
    )
    localized_title = (
        detail_ar.get("title")
        or detail_ar.get("name")
        or detail_en.get("title")
        or detail_en.get("name")
        or detail.get("title")
        or detail.get("name")
        or title
    )
    return {
        "title": localized_title,
        "plot": localized_plot,
        "poster": _tmdb_pick_poster(media_kind, best.get("id"), detail_ar.get("poster_path") or detail_en.get("poster_path") or detail.get("poster_path") or ""),
        "rating": "{:.1f}".format(float(detail.get("vote_average") or 0)) if detail.get("vote_average") else "",
        "year": str(detail.get("release_date") or detail.get("first_air_date") or "")[:4],
        "genres": genres,
        "tmdb_id": detail.get("id"),
        "tmdb_kind": media_kind,
    }


def _merge_tmdb_data(data):
    if not data or not data.get("title"):
        return data
    data = dict(data)
    if not data.get("plot") and data.get("desc"):
        data["plot"] = data.get("desc")
    item_type = data.get("type", "movie")
    if item_type == "episode":
        return data
    tmdb = _tmdb_search_metadata(data.get("title"), data.get("year", ""), item_type)
    if not tmdb:
        return data
    merged = dict(data)
    if tmdb.get("title") and len((data.get("title") or "").strip()) < 2:
        merged["title"] = tmdb["title"]
    if tmdb.get("poster") and (not merged.get("poster")):
        merged["poster"] = tmdb["poster"]
    if tmdb.get("plot") and len(tmdb.get("plot", "")) > len(merged.get("plot", "")):
        merged["plot"] = tmdb["plot"]
    if tmdb.get("rating") and not merged.get("rating"):
        merged["rating"] = tmdb["rating"]
    if tmdb.get("year") and not merged.get("year"):
        merged["year"] = tmdb["year"]
    if tmdb.get("genres"):
        merged["genres"] = tmdb["genres"]
    if tmdb.get("plot") or tmdb.get("poster") or tmdb.get("rating") or tmdb.get("genres") or tmdb.get("year"):
        merged["_tmdb"] = tmdb
    return merged


def _tmdb_search_suggestions(query, limit=8):
    query = re.sub(r"\s+", " ", query or "").strip()
    if len(query) < 2 or not _tmdb_enabled():
        return []

    suggestions = []
    seen = set()
    for media_kind, kind_label in (("movie", "فيلم"), ("tv", "مسلسل")):
        try:
            data = _tmdb_request("/search/{}".format(media_kind), {"query": query, "page": 1}) or {}
            for result in data.get("results") or []:
                title = (result.get("title") or result.get("name") or "").strip()
                if not title:
                    continue
                norm = _normalize_query(title)
                if not norm or norm in seen:
                    continue
                seen.add(norm)
                year = str(result.get("release_date") or result.get("first_air_date") or "")[:4]
                suggestions.append({
                    "title": title,
                    "query": title,
                    "source": "TMDb",
                    "site": "",
                    "kind": kind_label,
                    "year": year,
                })
                if len(suggestions) >= limit:
                    return suggestions[:limit]
        except Exception as e:
            my_log("TMDb suggestions failed for {}: {}".format(media_kind, e))
    return suggestions[:limit]


def _display_plot_text(value):
    text = re.sub(r"\s+", " ", value or "").strip()
    return text or "القصة غير متوفرة حالياً لهذا العنصر."


def _pick_plot_text_with_source(*sources):
    best = ""
    best_source = ""
    for source in sources:
        if isinstance(source, dict):
            candidates = [
                ("plot", source.get("plot")),
                ("overview", source.get("overview")),
                ("desc", source.get("desc")),
                ("tmdb.plot", (source.get("_tmdb") or {}).get("plot")),
            ]
        else:
            candidates = [("value", source)]
        for label, candidate in candidates:
            text = _display_plot_text(candidate)
            if text == "القصة غير متوفرة حالياً لهذا العنصر.":
                continue
            if len(text) > len(best):
                best = text
                best_source = label
    return best or "القصة غير متوفرة حالياً لهذا العنصر.", best_source or "none"


def _pick_plot_text(*sources):
    return _pick_plot_text_with_source(*sources)[0]


def _drain_cmit_queue():
    with _CMIT_LOCK:
        items = list(_CMIT_QUEUE)
        del _CMIT_QUEUE[:]
    for _f, _a, _kw in items:
        try: _f(*_a, **_kw)
        except Exception as _e:
            try: my_log("CMIT drain: {}".format(_e))
            except Exception: pass


def callInMainThread(func, *args, **kwargs):
    global _CMIT_TIMER
    with _CMIT_LOCK:
        _CMIT_QUEUE.append((func, args, kwargs))
    if _CMIT_TIMER is None:
        try:
            _CMIT_TIMER = eTimer()
            _CMIT_TIMER.callback.append(_drain_cmit_queue)
        except Exception: pass
    if _CMIT_TIMER is not None:
        try: _CMIT_TIMER.start(50, True)
        except Exception: pass
    else:
        try:
            from twisted.internet import reactor
            reactor.callFromThread(_drain_cmit_queue)
        except Exception: pass

# ─── Local HTTP Proxy (HiSilicon SSL Shield) ─────────────────────────────────
_PROXY_PORT = 19888
_PROXY_STARTED = False
_PROXY_LAST_HIT = 0
_PROXY_LAST_BYTES = 0
_PROXY_LAST_URL = ""

def start_proxy():
    global _PROXY_STARTED
    if _PROXY_STARTED: return
    try:
        def run_server():
            server = http.server.HTTPServer(('0.0.0.0', _PROXY_PORT), LocalProxyHandler)
            server.serve_forever()
        t = threading.Thread(target=run_server)
        t.daemon = True
        t.start()
        _PROXY_STARTED = True
        my_log("LocalProxy Shield: ACTIVE (Port {})".format(_PROXY_PORT))
    except Exception as e:
        my_log("start_proxy failure: {}".format(e))

class LocalProxyHandler(http.server.BaseHTTPRequestHandler):

    def do_HEAD(self):
        self._handle("HEAD")

    def do_GET(self):
        self._handle("GET")

    def _handle(self, method):
        try:
            global _PROXY_LAST_HIT, _PROXY_LAST_BYTES, _PROXY_LAST_URL
            raw = self.path[1:]
            parsed_req = urlparse(self.path)
            query = parse_qs(parsed_req.query or "")

            piped_headers = ""
            if parsed_req.path == "/stream" and query.get("url"):
                stream_url = unquote(query.get("url", [""])[0]).strip()
                explicit_referer = unquote(query.get("referer", [""])[0]).strip()
                explicit_ua = unquote(query.get("ua", [""])[0]).strip()
            else:
                explicit_referer = ""
                explicit_ua = ""
                if not raw or "://" not in raw:
                    self.send_error(400, "Bad URL")
                    return
                if "|" in raw:
                    stream_url, piped_headers = raw.split("|", 1)
                    stream_url = stream_url.strip()
                else:
                    stream_url = raw.strip()

            headers = {"User-Agent": SAFE_UA}

            if explicit_ua:
                headers["User-Agent"] = explicit_ua

            if piped_headers:
                for part in piped_headers.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        headers[k.strip()] = v.strip()

            if explicit_referer:
                headers["Referer"] = explicit_referer
            elif "Referer" not in headers:
                try:
                    parts = stream_url.split("/")
                    headers["Referer"] = parts[0] + "//" + parts[2] + "/"
                except Exception:
                    pass

            range_hdr = self.headers.get("Range") or self.headers.get("range")
            if range_hdr:
                headers["Range"] = range_hdr
                my_log("Proxy: Range={}".format(range_hdr))

            my_log("Proxy: {} {}".format(method, stream_url[:80]))
            _PROXY_LAST_HIT = time.time()
            _PROXY_LAST_BYTES = 0
            _PROXY_LAST_URL = stream_url

            req = urllib2.Request(stream_url, headers=headers)

            try:
                resp = urllib2.urlopen(req, timeout=30)
                status = resp.getcode()
            except urllib2.HTTPError as http_err:
                my_log("Proxy: Upstream HTTP {} for {}".format(http_err.code, stream_url[:60]))
                status = http_err.code
                resp = http_err
            except Exception as e:
                my_log("Proxy: Upstream connection error: {}".format(e))
                try:
                    self.send_error(502, str(e))
                except Exception:
                    pass
                return

            self.send_response(status)

            resp_hdrs = {}
            try:
                for k, v in resp.getheaders():
                    resp_hdrs[k.lower()] = v
            except Exception:
                pass

            for key in ("content-type", "content-length",
                        "content-range", "accept-ranges",
                        "last-modified", "etag"):
                if key in resp_hdrs:
                    self.send_header(key.title(), resp_hdrs[key])

            if "accept-ranges" not in resp_hdrs:
                self.send_header("Accept-Ranges", "bytes")

            self.end_headers()

            if method == "HEAD":
                return

            try:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    _PROXY_LAST_BYTES += len(chunk)
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except Exception:
                pass

        except Exception as e:
            my_log("Proxy FATAL: {}".format(e))
            try:
                self.send_error(500)
            except Exception:
                pass

    def log_message(self, *args):
        pass


# ─── Home Screen ─────────────────────────────────────────────────────────────
class ArabicPlayerHome(Screen):
    skin = """
    <screen name="ArabicPlayerHome" position="center,center" size="1920,1080"
            title="ArabicPlayer" flags="wfNoBorder">
        <ePixmap position="0,0" size="1920,1080" pixmap="{}/images/bg.png" zPosition="0" alphatest="blend" />

        <!-- ═══ Header Bar ═══ -->
        <widget name="title_bar"  position="0,0"     size="1920,120" backgroundColor="#0D1117" zPosition="1" />
        <widget name="title_text" position="45,18"   size="750,57"  font="Regular;48" foregroundColor="#00E5FF" transparent="1" zPosition="3" />
        <widget name="subtitle"   position="45,75"   size="750,36"  font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="3" />
        <widget name="status"     position="1050,24"  size="825,42"  font="Regular;28" foregroundColor="#FFD740" transparent="1" halign="right" zPosition="3" />
        <widget name="footer"     position="1050,72"  size="825,36"  font="Regular;24" foregroundColor="#58A6FF" transparent="1" halign="right" zPosition="3" />

        <!-- ═══ Menu Panel (Left) ═══ -->
        <widget name="menu_box"   position="30,142"   size="1080,810" backgroundColor="#161B22" zPosition="1" />
        <widget name="menu"       position="52,165"  size="1035,765" zPosition="2"
                scrollbarMode="showOnDemand"
                foregroundColor="#F0F6FC"
                foregroundColorSelected="#00E5FF"
                backgroundColor="#161B22"
                backgroundColorSelected="#21262D"
                font="Regular;39" itemHeight="81" transparent="1" />

        <!-- ═══ Preview Panel (Right) ═══ -->
        <widget name="preview_box" position="1140,142"  size="750,810" backgroundColor="#1C2333" zPosition="1" />
        <widget name="poster"      position="1215,172" size="600,540" zPosition="3" alphatest="blend" />
        <widget name="preview_title" position="1162,735" size="705,90" font="Regular;36" foregroundColor="#FFD740" transparent="1" zPosition="3" halign="center" />
        <widget name="preview_meta"  position="1162,832" size="705,42" font="Regular;26" foregroundColor="#00E5FF" transparent="1" zPosition="3" halign="center" />
        <widget name="preview_info" position="1162,882" size="705,54" font="Regular;22" foregroundColor="#8B949E" transparent="1" zPosition="3" halign="center" />

        <!-- ═══ Button Bar ═══ -->
        <widget name="btn_bar"    position="0,975"   size="1920,105" backgroundColor="#0D1117" zPosition="1" />
        <widget name="key_red"    position="45,990"  size="420,42" font="Regular;27" foregroundColor="#FF6B6B" transparent="1" halign="center" zPosition="3" />
        <widget name="key_green"  position="510,990" size="420,42" font="Regular;27" foregroundColor="#39D98A" transparent="1" halign="center" zPosition="3" />
        <widget name="key_yellow" position="975,990" size="420,42" font="Regular;27" foregroundColor="#FFD740" transparent="1" halign="center" zPosition="3" />
        <widget name="key_blue"   position="1440,990" size="420,42" font="Regular;27" foregroundColor="#58A6FF" transparent="1" halign="center" zPosition="3" />
    </screen>
    """

    def __init__(self, session):
        self.skin = ArabicPlayerHome.skin.format(PLUGIN_PATH)
        Screen.__init__(self, session)
        self.session = session
        self._items  = []
        self._page   = 1
        self._source = "home"
        self._site   = "egydead"
        self._m_type = "movie"
        self._last_query = ""
        self._nav_stack = []
        self._debounce_timer = eTimer()
        self._debounce_timer.callback.append(self._debounced_load_poster)
        self._pending_poster_url = None

        self["title_bar"]  = Label("")
        self["title_text"] = Label("ArabicPlayer  v{}".format(_PLUGIN_VERSION))
        self["subtitle"]   = Label("المشغل العربي الاحترافي")
        self["status"]     = Label("جاري التحميل...")
        self["footer"]     = Label("TMDb  |  المفضلة  |  السجل")
        self["menu_box"]   = Label("")
        self["preview_box"] = Label("")
        self["poster"]     = Pixmap()
        self["menu"]       = MenuList([])
        self["preview_title"] = Label("")
        self["preview_meta"] = Label("")
        self["preview_info"] = Label("")
        self["btn_bar"]    = Label("")
        self["key_red"]    = Label("أحدث أفلام")
        self["key_green"]  = Label("أحدث مسلسلات")
        self["key_yellow"] = Label("بحث")
        self["key_blue"]   = Label("الصفحة التالية")

        self.picLoad = ePicLoad()
        self.picLoad.PictureData.get().append(self._paintPoster)
        self._tmp_posters = []
        self._requested_poster_url = None
        self._poster_lock = threading.Lock()
        self.onClose.append(self._onPluginClose)

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "InfobarMenuActions"],
            {
                "ok":     self._onOk,
                "cancel": self._onBack,
                "red":    self._loadMovies,
                "green":  self._loadSeries,
                "yellow": self._onSearch,
                "blue":   self._nextPage,
                "up":     lambda: self["menu"].up(),
                "down":   lambda: self["menu"].down(),
                "left":   lambda: self["menu"].pageUp(),
                "right":  lambda: self["menu"].pageDown(),
            },
            -1
        )

        try:
            self["menu"].onSelectionChanged.append(self._refreshPreview)
        except Exception:
            pass
        self.onLayoutFinish.append(self._init)

    def _init(self):
        self._showHome()

    def _setHeader(self, title, subtitle="", status=None):
        self["title_text"].setText(_single_line_text(title, width=42, fallback="ArabicPlayer"))
        self["subtitle"].setText(_wrap_ui_text(subtitle, width=56, max_lines=2))
        if status is not None:
            self["status"].setText(status)

    def _showHome(self):
        self._source = "home"
        self._page   = 1
        self._nav_stack = []
        self._setHeader(
            "ArabicPlayer  v{}".format(_PLUGIN_VERSION),
            "المشغل العربي الاحترافي",
            "الرئيسية"
        )
        items = [
            ("━━  المصادر  ━━━━━━━━━━━━━━━━━", "separator"),
            ("EgyDead          واجهة حديثة وبوسترات", "site_egydead"),
            ("Akoam            محتوى متنوع وصفحات تفصيلية", "site_akoam"),
            ("Arabseed         تصنيفات مرتبة", "site_arabseed"),
            ("Wecima           أقسام واسعة وبحث سريع", "site_wecima"),
            ("Shaheed4u        أفلام ومسلسلات حصرية", "site_shaheed"),
            ("TopCinemaa       مكتبة ضخمة", "site_topcinema"),
            ("FaselHD          دقة عالية بدون تقطيع", "site_fasel"),
            ("━━  الأدوات  ━━━━━━━━━━━━━━━━━", "separator"),
            ("البحث الشامل", "search"),
            ("المفضلة", "favorites"),
            ("السجل", "history"),
            ("الإعدادات", "settings"),
        ]
        self._items = [{"title": t, "_action": a} for t, a in items]
        self["menu"].setList([t for t, _ in items])
        self["footer"].setText("TMDb  |  {} مفضلة  |  {} سجل".format(len(_favorite_items()), len(_history_items())))
        self._refreshPreview()

    def _onOk(self):
        idx = self["menu"].getSelectedIndex()
        if idx < 0 or idx >= len(self._items):
            return
        item = self._items[idx]

        if "_action" in item:
            a = item["_action"]
            if a.startswith("site_"):
                self._site = a.replace("site_", "")
                self._showSiteCategories()
                return
            elif a == "search":
                self._onSearch()
                return
            elif a == "search_site":
                self._onSearch(item.get("_site", self._site))
                return
            elif a == "favorites":
                self._showLibrary("favorites")
                return
            elif a == "history":
                self._showLibrary("history")
                return
            elif a == "settings":
                self._openSettings()
                return

        curr_type = item.get("type", item.get("_action"))
        if curr_type == "category":
            if item.get("_m_type") in ("movie", "series"):
                self._m_type = item.get("_m_type")
            self._loadCategory(item["url"], item["title"])
            return

        if curr_type in ("movie", "series", "episode", "details"):
            self._openItem(item)

    def _onPluginClose(self):
        try:
            self.picLoad.PictureData.get().remove(self._paintPoster)
        except Exception:
            pass
        self._clearTmpPosters()

    def _onBack(self):
        if self._nav_stack:
            state = self._nav_stack.pop()
            self._source = state.get("source", "home")
            self._site = state.get("site", self._site)
            self._m_type = state.get("m_type", self._m_type)
            self._page = state.get("page", 1)
            items = state.get("items", [])
            header = state.get("header", {})
            if items:
                self._setList(items)
                self._setHeader(**header)
            else:
                self._showHome()
        elif self._source != "home":
            self._showHome()
        else:
            self.close()

    def _push_nav_state(self):
        self._nav_stack.append({
            "source": self._source,
            "site": self._site,
            "m_type": self._m_type,
            "page": self._page,
            "items": list(self._items),
            "header": {
                "title": self["title_text"].getText(),
                "subtitle": self["subtitle"].getText(),
                "status": self["status"].getText(),
            },
        })

    def _clearTmpPosters(self):
        for p in self._tmp_posters:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        self._tmp_posters = []

    def _paintPoster(self, picData=None):
        ptr = self.picLoad.getData()
        if ptr:
            self["poster"].instance.setPixmap(ptr)
            self["poster"].show()

    def _setList(self, items):
        self._items = items
        self["menu"].setList([_decorate_item_title(i, self._site) for i in items])
        self["status"].setText("{} عنصر".format(len(items)))
        self._refreshPreview()
        try:
            self._first_item_timer.stop()
        except Exception:
            pass
        self._first_item_timer = eTimer()
        self._first_item_timer.callback.append(self._refreshPreview)
        self._first_item_timer.start(700, True)

    def _refreshPreview(self):
        if not self._items:
            self["preview_title"].setText("")
            self["preview_meta"].setText("")
            self["preview_info"].setText("")
            self["poster"].hide()
            return

        idx = self["menu"].getSelectedIndex()
        if idx < 0 or idx >= len(self._items):
            idx = 0
        item = self._items[idx]
        action = item.get("_action", "")
        item_type = item.get("type", action)
        title = _strip_arabic_from_english_title(item.get("title", ""))
        site = item.get("_site", self._site)

        if action == "separator":
            self["preview_title"].setText("")
            self["preview_meta"].setText("")
            self["preview_info"].setText("")
            self["poster"].hide()
            return

        meta = []
        info_parts = []
        if action.startswith("site_"):
            site_key = action.replace("site_", "")
            meta.append("المصدر")
            info_parts.append(_site_tagline(site_key))
        elif action in ("search", "search_site", "favorites", "history", "settings"):
            meta.append("أداة")
        else:
            if site:
                meta.append(_site_label(site))
            if item.get("year"):
                meta.append(item.get("year"))
            if item.get("rating"):
                meta.append("{}/10".format(item.get("rating")))
            if item_type in _TYPE_LABELS:
                meta.append(_TYPE_LABELS.get(item_type))

        self["preview_title"].setText(_wrap_ui_text(title, width=28, max_lines=3, fallback="بدون عنوان"))
        self["preview_meta"].setText(_wrap_ui_text("  |  ".join(meta), width=36, max_lines=2))
        self["preview_info"].setText(_wrap_ui_text("  ".join(info_parts), width=36, max_lines=2) if info_parts else "")

        poster_url = item.get("poster") or item.get("image") or ""

        with self._poster_lock:
            self._requested_poster_url = poster_url

        if poster_url:
            cached = _get_cached_poster(poster_url)
            if cached:
                self._display_poster_from_file(cached)
            else:
                self._pending_poster_url = poster_url
                try:
                    self._debounce_timer.stop()
                except Exception:
                    pass
                self._debounce_timer.start(300, True)
        else:
            self["poster"].hide()

    def _debounced_load_poster(self):
        url = self._pending_poster_url
        if url:
            threading.Thread(target=self._downloadPoster, args=(url,), daemon=True).start()

    def _display_poster_from_file(self, path):
        try:
            self.picLoad.setPara((self["poster"].instance.size().width(), self["poster"].instance.size().height(), 1, 1, 0, 1, "#000000"))
            self.picLoad.startDecode(path)
        except Exception as e:
            my_log("_display_poster error: {}".format(e))

    def _downloadPoster(self, url):
        if not url: return
        with self._poster_lock:
            if url != self._requested_poster_url: return

        try:
            if url.startswith("//"): url = "https:" + url
            try:
                from urllib.parse import urlparse, quote, urlunparse
                p = list(urlparse(url))
                p[2] = quote(p[2])
                p[4] = quote(p[4])
                url = urlunparse(p)
            except Exception: pass

            cached = _get_cached_poster(url)
            if cached:
                with self._poster_lock:
                    if url != self._requested_poster_url: return
                callInMainThread(self._display_poster_from_file, cached)
                return

            cache_path = _poster_cache_path(url)
            req = urllib2.Request(url, headers={"User-Agent": SAFE_UA})
            data = urllib2.urlopen(req, timeout=7).read()

            with self._poster_lock:
                if url != self._requested_poster_url: return
                if cache_path:
                    with open(cache_path, "wb") as f:
                        f.write(data)
                    callInMainThread(self._display_poster_from_file, cache_path)
                else:
                    path = "/tmp/ap_preview_{}.jpg".format(int(time.time()))
                    with open(path, "wb") as f:
                        f.write(data)
                    self._tmp_posters.append(path)
                    callInMainThread(self._display_poster_from_file, path)
        except Exception as e:
            my_log("_downloadPoster preview error: {}".format(e))
            with self._poster_lock:
                if url == self._requested_poster_url:
                    callInMainThread(self["poster"].hide)

    def _nextPage(self):
        cat_url  = getattr(self, "_cat_url",  None)
        cat_name = getattr(self, "_cat_name", "")
        if self._source == "category" and cat_url:
            self._page += 1
            self._loadCategory(cat_url, cat_name)

    def _showSiteCategories(self):
        self._push_nav_state()
        try:
            extractor = _get_extractor(self._site)
            get_categories = getattr(extractor, "get_categories", None)
            if not get_categories:
                cats = [{"title": "لا توجد أقسام", "type": "error"}]
            elif self._site == "egydead":
                movie_cats = get_categories("movie")
                series_cats = get_categories("series")
                cats = [_site_search_item(self._site)]
                for item in movie_cats:
                    updated = dict(item)
                    updated["title"] = updated.get("title", "").replace("[فيلم] ", "").replace("[مسلسل] ", "")
                    updated["_m_type"] = "movie"
                    cats.append(updated)
                for item in series_cats:
                    updated = dict(item)
                    updated["title"] = updated.get("title", "").replace("[فيلم] ", "").replace("[مسلسل] ", "")
                    updated["_m_type"] = "series"
                    cats.append(updated)
            else:
                cats = [_site_search_item(self._site)] + (get_categories() or [])
        except Exception as e:
            my_log("_showSiteCategories error for site {}: {}".format(self._site, e))
            cats = [{"title": "فشل جلب الأقسام", "type": "error"}]

        self._source = "categories"
        self._setList(cats)
        self._setHeader(
            "تصنيفات {}".format(_site_label(self._site)),
            _site_tagline(self._site),
            "اختر القسم"
        )

    def _showCategories(self, m_type):
        self._push_nav_state()
        extractor = _get_extractor("egydead")
        get_categories = getattr(extractor, "get_categories", None)
        self._source = "categories"
        self._m_type = m_type
        cats = get_categories(m_type) if get_categories else []
        self._setList(cats)
        self._setHeader(
            "تصنيفات " + ("الأفلام" if m_type == "movie" else "المسلسلات"),
            "استعراض منظم حسب النوع داخل {}".format(_site_label("egydead")),
            "اختر التصنيف"
        )

    def _loadCategory(self, url, name):
        self._push_nav_state()
        self._source = "category"
        self._cat_url = url
        self._cat_name = name
        self["status"].setText("جاري تحميل {}...".format(name))
        self["menu"].setList(["جاري التحميل..."])
        threading.Thread(target=self._bgLoadCategory, args=(url,), daemon=True).start()

    def _bgLoadCategory(self, url):
        try:
            my_log("_bgLoadCategory started: {}, site={}, page={}".format(url, self._site, self._page))
            extractor = _get_extractor(self._site)
            get_category_items = getattr(extractor, "get_category_items", None)
            if not get_category_items:
                callInMainThread(self["status"].setText, "لا توجد نتائج")
                return
            my_log("_bgLoadCategory calling get_category_items for site: {}".format(self._site))
            items = get_category_items(url) if self._site != "egydead" else get_category_items(url, page=self._page)
            my_log("_bgLoadCategory got {} items".format(len(items) if items else 0))
            callInMainThread(self._onCategoryLoaded, items)
        except Exception as e:
            my_log("_bgLoadCategory error: {}".format(e))
            callInMainThread(self["status"].setText, "فشل: {}".format(str(e)[:60]))

    def _onCategoryLoaded(self, items):
        if not items:
            self["status"].setText("لا توجد نتائج")
            self["menu"].setList(["لا توجد نتائج"])
            return
        self._setHeader(
            "{} — صفحة {}".format(self._cat_name, self._page),
            "المصدر: {}".format(_site_label(self._site))
        )
        self._setList(_dedupe_items(items))

    def _loadMovies(self):
        self._showCategories("movie")

    def _loadSeries(self):
        self._showCategories("series")

    def _openSettings(self):
        self.session.open(ArabicPlayerSettings, self._site)

    def _showLibrary(self, kind):
        self._push_nav_state()
        self._source = kind
        if kind == "favorites":
            items = _favorite_items()
            title = "المفضلة"
            subtitle = "العناصر المحفوظة للوصول السريع"
        else:
            items = _history_items()
            title = "السجل"
            subtitle = "آخر العناصر التي تم تشغيلها"
        if not items:
            self._setHeader(title, subtitle, "لا توجد عناصر بعد")
            self["menu"].setList(["القائمة فارغة"])
            self._items = []
            return
        self._setHeader(title, subtitle)
        self._setList(items)

    def _onSearch(self, forced_scope=None):
        self.session.openWithCallback(
            self._onSearchQuery,
            ArabicPlayerSearch,
            current_site=self._site,
            default_scope=forced_scope or "all",
            query=self._last_query
        )

    def _onSearchQuery(self, result=None):
        if not result:
            return
        scope = "all"
        query = result
        if isinstance(result, tuple):
            query, scope = result
        query = (query or "").strip()
        if not query:
            return
        self._last_query = query
        self._source = "search"
        self._search_scope = scope
        self["status"].setText("بحث عن: {}...".format(query))
        self["menu"].setList(["جاري البحث..."])
        threading.Thread(
            target=self._bgSearch, args=(query, scope), daemon=True
        ).start()

    def _bgSearch(self, query, scope="all"):
        try:
            items = []
            extractors = []
            target_site = scope if scope not in ("", None, "all") else ""
            if target_site in _SEARCH_SITE_ORDER:
                extractors = [(target_site, __import__("extractors." + target_site, fromlist=["search"]))]
            else:
                for name in _SEARCH_SITE_ORDER:
                    try:
                        extractors.append((name, __import__("extractors." + name, fromlist=["search"])))
                    except Exception:
                        pass
            for site_name, module in extractors:
                search_fn = getattr(module, "search", None)
                if not callable(search_fn):
                    continue
                try:
                    for item in search_fn(query) or []:
                        item["_site"] = site_name
                        item["_m_type"] = item.get("type", "movie")
                        items.append(item)
                except Exception as e:
                    my_log("Search failed for {}: {}".format(site_name, e))
            callInMainThread(self._onSearchResults, items, query, scope)
        except Exception as e:
            my_log("_bgSearch error: {}".format(e))
            callInMainThread(self["status"].setText, "فشل البحث")

    def _onSearchResults(self, items, query, scope="all"):
        if not items:
            self["status"].setText("لا توجد نتائج لـ: {}".format(query))
            self["menu"].setList(["مفيش نتائج"])
            return
        items = _rank_search_items(items, query)
        if not items:
            self["status"].setText("لا توجد نتائج مطابقة لـ: {}".format(query))
            self["menu"].setList(["لا توجد نتائج مطابقة"])
            return
        subtitle = "بحث في {} — {} نتيجة".format(_search_scope_label(scope), len(items))
        self._setHeader(
            "نتائج: {}".format(query),
            subtitle
        )
        self._setList(items)

    def _openItem(self, item):
        self.session.open(
            ArabicPlayerDetail,
            item=item,
            site=item.get("_site", self._site),
            m_type=item.get("_m_type", self._m_type)
        )


# ─── Search Screen ────────────────────────────────────────────────────────────
class ArabicPlayerSearch(Screen):
    skin = """
    <screen name="ArabicPlayerSearch" position="center,center" size="1920,1080"
            flags="wfNoBorder">
        <ePixmap position="0,0" size="1920,1080" pixmap="{}/images/bg_search.png" zPosition="0" alphatest="blend" />
        <widget name="bg"       position="0,0"   size="1920,1080" backgroundColor="#0D1117" zPosition="1" />

        <!-- Header -->
        <widget name="title"    position="60,30" size="900,54"  font="Regular;45" foregroundColor="#00E5FF" transparent="1" zPosition="3" />
        <widget name="subtitle" position="60,90" size="1800,36" font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="3" />

        <!-- Query Box -->
        <widget name="query_box" position="60,150" size="1800,105" backgroundColor="#161B22" zPosition="2" />
        <widget name="query_label" position="90,165" size="180,27" font="Regular;24" foregroundColor="#00E5FF" transparent="1" zPosition="3" />
        <widget name="query"    position="90,198" size="1740,39" font="Regular;33" foregroundColor="#F0F6FC" transparent="1" zPosition="3" />

        <!-- Scope Box -->
        <widget name="scope_box" position="60,278" size="1800,72" backgroundColor="#1C2333" zPosition="2" />
        <widget name="scope_label" position="90,296" size="165,30" font="Regular;24" foregroundColor="#E040FB" transparent="1" zPosition="3" />
        <widget name="scope"    position="270,294" size="1560,33" font="Regular;28" foregroundColor="#F0F6FC" transparent="1" zPosition="3" />

        <!-- Suggestions -->
        <widget name="suggestions_box" position="60,372" size="1800,570" backgroundColor="#161B22" zPosition="2" />
        <widget name="suggestions_title" position="90,390" size="450,30" font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="3" />
        <widget name="suggestions" position="87,435" size="1746,480" zPosition="3"
                scrollbarMode="showOnDemand"
                foregroundColor="#F0F6FC"
                foregroundColorSelected="#00E5FF"
                backgroundColor="#161B22"
                backgroundColorSelected="#21262D"
                font="Regular;32" itemHeight="38" />

        <!-- Footer -->
        <widget name="hint"     position="60,960" size="1800,33" font="Regular;22" foregroundColor="#8B949E" transparent="1" zPosition="3" halign="center" />
        <widget name="key_red"  position="60,1002" size="420,33" font="Regular;24" foregroundColor="#FF6B6B" transparent="1" zPosition="3" halign="center" />
        <widget name="key_green" position="522,1002" size="420,33" font="Regular;24" foregroundColor="#39D98A" transparent="1" zPosition="3" halign="center" />
        <widget name="key_yellow" position="984,1002" size="420,33" font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="3" halign="center" />
        <widget name="key_blue" position="1446,1002" size="420,33" font="Regular;24" foregroundColor="#58A6FF" transparent="1" zPosition="3" halign="center" />
    </screen>
    """.format(PLUGIN_PATH)

    def __init__(self, session, current_site="egydead", default_scope="all", query=""):
        Screen.__init__(self, session)
        self._current_site = current_site
        self._query = query or ""
        self._scope = default_scope or "all"

        self["bg"] = Label("")
        self["title"] = Label("بحث احترافي")
        self["subtitle"] = Label("اكتب الاسم واختر النطاق للبحث في المصدر الحالي أو كل المصادر.")
        self["query_box"] = Label("")
        self["query_label"] = Label("نص البحث")
        self["query"] = Label("")
        self["scope_box"] = Label("")
        self["scope_label"] = Label("النطاق")
        self["scope"] = Label("")
        self["suggestions_box"] = Label("")
        self["suggestions_title"] = Label("اقتراحات سريعة")
        self["suggestions"] = MenuList([])
        self["hint"] = Label("OK يفتح الاقتراح  |  أعلى/أسفل للتنقل  |  أحمر: مسح  |  أصفر: اكتب  |  أزرق: نطاق")
        self["key_red"] = Label("مسح")
        self["key_green"] = Label("ابحث الآن")
        self["key_yellow"] = Label("اكتب")
        self["key_blue"] = Label("تبديل النطاق")
        self._suggestions = []
        self._suggestion_ticket = 0

        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self._submit_or_edit,
                "cancel": self.close,
                "up": self._suggestion_up,
                "down": self._suggestion_down,
                "left": self._toggle_scope,
                "right": self._toggle_scope,
                "red": self._clear_query,
                "green": self._submit,
                "yellow": self._edit_query,
                "blue": self._toggle_scope,
            },
            -1
        )

        self.onLayoutFinish.append(self._init_search)

    def _init_search(self):
        self._refresh_suggestions()
        self._refresh()

    def _refresh(self):
        preview = self._query or "اكتب اسم فيلم أو مسلسل أو ممثل"
        self["query"].setText(_wrap_ui_text(preview, width=42, max_lines=2))
        self["scope"].setText(_search_scope_label(self._scope if self._scope else "all"))
        self._refresh_suggestion_list()

    def _refresh_suggestion_list(self):
        if not self._suggestions:
            self["suggestions_title"].setText("اقتراحات سريعة")
            self["suggestions"].setList(["لا توجد اقتراحات حالياً"])
            return
        self["suggestions_title"].setText("اقتراحات سريعة: {}".format(len(self._suggestions)))
        rows = []
        for item in self._suggestions:
            meta = []
            if item.get("source"):
                meta.append(item.get("source"))
            if item.get("kind"):
                meta.append(item.get("kind"))
            if item.get("year"):
                meta.append(item.get("year"))
            label = _single_line_text(item.get("title", ""), width=34, fallback="اقتراح")
            meta_text = " | ".join([x for x in meta if x])
            if meta_text:
                label = "{} [{}]".format(label, meta_text)
            rows.append(label)
        self["suggestions"].setList(rows)

    def _refresh_suggestions(self):
        self._suggestions = _library_search_suggestions(self._query, self._current_site, limit=6)
        self._refresh_suggestion_list()
        ticket = self._suggestion_ticket = self._suggestion_ticket + 1
        if len((self._query or "").strip()) >= 2 and _tmdb_enabled():
            threading.Thread(target=self._bg_tmdb_suggestions, args=(self._query, ticket), daemon=True).start()

    def _bg_tmdb_suggestions(self, query, ticket):
        suggestions = _tmdb_search_suggestions(query, limit=6)
        callInMainThread(self._merge_tmdb_suggestions, query, ticket, suggestions)

    def _merge_tmdb_suggestions(self, query, ticket, suggestions):
        if ticket != self._suggestion_ticket:
            return
        if (query or "").strip() != (self._query or "").strip():
            return
        seen = set(_normalize_query(item.get("query", item.get("title", ""))) for item in self._suggestions)
        for item in suggestions:
            norm = _normalize_query(item.get("query", item.get("title", "")))
            if not norm or norm in seen:
                continue
            seen.add(norm)
            self._suggestions.append(item)
        self._suggestions = self._suggestions[:8]
        self._refresh_suggestion_list()

    def _toggle_scope(self):
        self._scope = self._current_site if self._scope == "all" else "all"
        self._refresh_suggestions()
        self._refresh()

    def _clear_query(self):
        self._query = ""
        self._refresh_suggestions()
        self._refresh()

    def _edit_query(self):
        from Screens.VirtualKeyBoard import VirtualKeyBoard
        self.session.openWithCallback(
            self._onKeyboard,
            VirtualKeyBoard,
            title="ابحث عن فيلم أو مسلسل",
            text=self._query
        )

    def _onKeyboard(self, result):
        if result is None:
            return
        self._query = result.strip()
        self._refresh_suggestions()
        self._refresh()

    def _suggestion_up(self):
        if self._suggestions:
            self["suggestions"].up()

    def _suggestion_down(self):
        if self._suggestions:
            self["suggestions"].down()

    def _submit_or_edit(self):
        idx = self["suggestions"].getSelectedIndex()
        if self._suggestions and idx >= 0 and idx < len(self._suggestions):
            chosen = self._suggestions[idx]
            self.close(((chosen.get("query") or chosen.get("title") or "").strip(), self._scope or "all"))
            return
        if self._query.strip():
            self._submit()
        else:
            self._edit_query()

    def _submit(self):
        query = self._query.strip()
        if not query:
            self._edit_query()
            return
        self.close((query, self._scope or "all"))


class ArabicPlayerSettings(Screen):
    skin = """
    <screen name="ArabicPlayerSettings" position="center,center" size="1920,1080"
            flags="wfNoBorder">
        <ePixmap position="0,0" size="1920,1080" pixmap="{}/images/bg_settings.png" zPosition="0" alphatest="blend" />
        <widget name="bg"     position="0,0"   size="1920,1080" backgroundColor="#0D1117" zPosition="1" />

        <!-- Header -->
        <widget name="title"  position="60,30" size="900,57"  font="Regular;45" foregroundColor="#00E5FF" transparent="1" zPosition="3" />
        <widget name="owner"  position="60,96" size="600,36"  font="Regular;27" foregroundColor="#FFD740" transparent="1" zPosition="3" />
        <widget name="site"   position="60,138" size="1800,36" font="Regular;24" foregroundColor="#8B949E" transparent="1" zPosition="3" />

        <!-- Body -->
        <widget name="body_box" position="60,195" size="1800,720" backgroundColor="#161B22" zPosition="2" />
        <widget name="body"   position="90,218" size="1740,675" font="Regular;28" foregroundColor="#F0F6FC" transparent="1" zPosition="3" />

        <!-- Footer -->
        <widget name="hint"   position="60,939" size="1800,36" font="Regular;22" foregroundColor="#8B949E" transparent="1" zPosition="3" halign="center" />
        <widget name="key_yellow_label" position="450,987" size="450,36" font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="3" halign="center" />
        <widget name="key_blue_label"   position="990,987" size="450,36" font="Regular;24" foregroundColor="#58A6FF" transparent="1" zPosition="3" halign="center" />
    </screen>
    """.format(PLUGIN_PATH)

    def __init__(self, session, current_site):
        Screen.__init__(self, session)
        self._current_site = current_site
        self["bg"] = Label("")
        self["title"] = Label("الإعدادات وحول النسخة")
        self["owner"] = Label("")
        self["site"] = Label("")
        self["body_box"] = Label("")
        self["body"] = ScrollLabel("")
        self["hint"] = Label("OK / Back للإغلاق  |  أصفر: مفتاح TMDb  |  أزرق: حذف المفتاح")
        self["key_yellow_label"] = Label("تعديل مفتاح TMDb")
        self["key_blue_label"] = Label("حذف المفتاح")
        self["actions"] = ActionMap(
            ["OkCancelActions", "DirectionActions", "ColorActions"],
            {
                "ok": self.close,
                "cancel": self.close,
                "up": self["body"].pageUp,
                "down": self["body"].pageDown,
                "left": self["body"].pageUp,
                "right": self["body"].pageDown,
                "yellow": self._edit_tmdb_key,
                "blue": self._clear_tmdb_key,
            },
            -1
        )
        self._refresh()

    def _refresh(self):
        self["owner"].setText("المالك: {}".format(_get_config("owner", _PLUGIN_OWNER)))
        self["site"].setText("المصدر الحالي: {}  |  {}".format(_site_label(self._current_site), _site_tagline(self._current_site)))
        api_key = (_get_config("tmdb_api_key", "") or "").strip()
        body = (
            "ArabicPlayer v{version}\n\n"
            "TMDb:\n"
            "• الحالة: {tmdb_status}\n"
            "• المفتاح الحالي: {tmdb_key}\n\n"
            "المكتبة:\n"
            "• المفضلة: {fav_count}\n"
            "• السجل: {hist_count}\n\n"
            "ما الجديد في النسخة الحالية:\n"
            "• إثراء معلومات الفيلم أو المسلسل من TMDb عند توفر المفتاح\n"
            "• دعم مفضلة وسجل محفوظين محليًا\n"
            "• واجهة إعدادات حقيقية بدل الرسالة القديمة\n"
            "• ترتيب أنظف للنتائج والسيرفرات\n\n"
            "طريقة الاستخدام:\n"
            "• اضغط الأصفر لإدخال أو تعديل مفتاح TMDb\n"
            "• اضغط الأزرق لحذف المفتاح الحالي\n"
            "• من شاشة التفاصيل استخدم الأحمر لإضافة العنصر إلى المفضلة"
        ).format(
            version=_PLUGIN_VERSION,
            tmdb_status="مفعل" if api_key else "غير مفعل",
            tmdb_key=("********" + api_key[-4:]) if api_key else "غير مضبوط",
            fav_count=len(_favorite_items()),
            hist_count=len(_history_items()),
        )
        self["body"].setText(body)

    def _edit_tmdb_key(self):
        from Screens.VirtualKeyBoard import VirtualKeyBoard
        self.session.openWithCallback(
            self._on_tmdb_key_entered,
            VirtualKeyBoard,
            title="أدخل TMDb API Key",
            text=_get_config("tmdb_api_key", "")
        )

    def _on_tmdb_key_entered(self, value):
        if value is None:
            return
        _set_config("tmdb_api_key", value.strip())
        self._refresh()

    def _clear_tmdb_key(self):
        _set_config("tmdb_api_key", "")
        self._refresh()


# ─── Detail / Episode Screen ──────────────────────────────────────────────────
class ArabicPlayerDetail(Screen):
    skin = """
    <screen name="ArabicPlayerDetail" position="center,center" size="1920,1080"
            flags="wfNoBorder">
        <ePixmap position="0,0" size="1920,1080" pixmap="{}/images/bg_detail.png" zPosition="0" alphatest="blend" />
        <widget name="bg"          position="0,0"    size="1920,1080" backgroundColor="#0D1117" zPosition="1" />

        <!-- Poster Panel -->
        <widget name="poster_box"  position="45,30"  size="420,600" backgroundColor="#1C2333" zPosition="2" />
        <widget name="poster"      position="68,52"  size="375,555" zPosition="4" alphatest="blend" />

        <!-- Info Panel -->
        <widget name="info_box"    position="495,30" size="1380,405" backgroundColor="#161B22" zPosition="2" />
        <widget name="badge"       position="525,52" size="1320,33"  font="Regular;26" foregroundColor="#E040FB" transparent="1" zPosition="4" />
        <widget name="title"       position="525,93" size="1320,90"  font="Regular;42" foregroundColor="#00E5FF" transparent="1" zPosition="4" />
        <widget name="meta"        position="525,189" size="1320,60" font="Regular;27" foregroundColor="#FFD740" transparent="1" zPosition="4" />
        <widget name="facts"       position="525,255" size="1320,42" font="Regular;24" foregroundColor="#8B949E" transparent="1" zPosition="4" />
        <widget name="source"      position="525,300" size="1320,42" font="Regular;24" foregroundColor="#58A6FF" transparent="1" zPosition="4" />
        <widget name="tmdb_note"   position="525,348" size="1320,33" font="Regular;22" foregroundColor="#39D98A" transparent="1" zPosition="4" />

        <!-- Plot Panel -->
        <widget name="plot_box"    position="495,450" size="1380,180" backgroundColor="#1C2333" zPosition="2" />
        <widget name="plot_title"  position="525,465" size="600,30"  font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="4" />
        <widget name="plot"        position="525,504" size="1320,150"  font="Regular;27" foregroundColor="#F0F6FC" transparent="1" halign="block" valign="top" zPosition="4" />

        <!-- Menu Panel -->
        <widget name="menu_box"    position="45,652" size="1830,315" backgroundColor="#161B22" zPosition="2" />
        <widget name="section"     position="75,663" size="1770,36"  font="Regular;26" foregroundColor="#FFD740" transparent="1" zPosition="4" />
        <widget name="menu"        position="72,708" size="1776,240" zPosition="4"
                scrollbarMode="showOnDemand"
                foregroundColor="#F0F6FC"
                foregroundColorSelected="#00E5FF"
                backgroundColor="#161B22"
                backgroundColorSelected="#21262D"
                font="Regular;32" itemHeight="57" />

        <!-- Footer -->
        <widget name="key_red"     position="45,990" size="420,36" font="Regular;24" foregroundColor="#FF6B6B" transparent="1" zPosition="4" />
        <widget name="key_yellow"  position="510,990" size="420,36" font="Regular;24" foregroundColor="#FFD740" transparent="1" zPosition="4" />
        <widget name="status"      position="990,990" size="870,36"  font="Regular;22" foregroundColor="#8B949E" transparent="1" halign="right" zPosition="4" />
    </screen>
    """.format(PLUGIN_PATH)

    def __init__(self, session, item, site="egydead", m_type="movie"):
        Screen.__init__(self, session)
        self.session = session
        self._item   = item
        self._site   = site
        self._m_type = m_type
        self._data   = None
        self._servers = []
        self._episodes = []
        self._tmp_posters = []
        self._poster_loaded = False
        self._raw_title = ""

        self["bg"]     = Label("")
        self["poster_box"] = Label("")
        self["info_box"] = Label("")
        self["plot_box"] = Label("")
        self["menu_box"] = Label("")
        self["poster"] = Pixmap()
        self["badge"]  = Label("")
        self["title"]  = Label(item.get("title", ""))
        self["meta"]   = Label("")
        self["facts"]  = Label("")
        self["source"] = Label("")
        self["tmdb_note"] = Label("")
        self["plot_title"] = Label("القصة")
        self["plot"]   = Label("")
        self["section"] = Label("جاري التحضير...")
        self["menu"]   = MenuList([])
        self["key_red"] = Label("المفضلة")
        self["key_yellow"] = Label("تحديث TMDb")
        self["status"] = Label("جاري تحميل التفاصيل...")

        self.picLoad = ePicLoad()
        self.picLoad.PictureData.get().append(self._paintPoster)

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok":     self._onOk,
                "cancel": self._onCancel,
                "red":    self._toggleFavorite,
                "yellow": self._refreshTMDb,
                "up":     lambda: self["menu"].up(),
                "down":   lambda: self["menu"].down(),
                "left":   lambda: self["menu"].pageUp(),
                "right":  lambda: self["menu"].pageDown(),
            },
            -1
        )

        self.onLayoutFinish.append(self._load)
        self.onExecBegin.append(self._refreshPoster)

    def _load(self):
        threading.Thread(target=self._bgLoad, args=(self._site, self._item["url"], self._m_type), daemon=True).start()

    def _bgLoad(self, site, url, m_type):
        _done = [False]
        def _watchdog():
            if not _done[0]:
                my_log("_bgLoad watchdog: timeout for {}".format(url[:60]))
                callInMainThread(self["status"].setText, u"Timeout — please try again")
        _wt = threading.Timer(30, _watchdog)
        _wt.daemon = True
        _wt.start()
        try:
            from extractors.base import log
            log("Detail _bgLoad: START site={}, m_type={}".format(site, m_type))
            extractor = _get_extractor(site)
            get_page = getattr(extractor, "get_page", None)
            if not get_page:
                callInMainThread(self["status"].setText, u"لا توجد بيانات")
                return
            if site == "egydead":
                data = get_page(url, m_type=m_type)
            else:
                data = get_page(url)
            merged_seed = dict(self._item or {})
            merged_seed.update(data or {})
            data = _merge_tmdb_data(merged_seed)
            _done[0] = True
            callInMainThread(self._onLoaded, data)
        except Exception as e:
            _done[0] = True
            from extractors.base import log
            log("_bgLoad error: {} -- trying TMDb fallback".format(e))
            try:
                fallback = _merge_tmdb_data(dict(self._item or {}))
                if fallback and (fallback.get("plot") or fallback.get("poster")):
                    callInMainThread(self._onLoaded, fallback)
                else:
                    callInMainThread(self["status"].setText,
                        u"فشل التحميل — {}".format(str(e)[:40]))
            except Exception as e2:
                log("TMDb fallback failed: {}".format(e2))
                callInMainThread(self["status"].setText,
                    u"فشل التحميل — {}".format(str(e)[:40]))
        finally:
            _wt.cancel()

    def _onCancel(self):
        try:
            self.picLoad.PictureData.get().remove(self._paintPoster)
        except Exception:
            pass
        for p in self._tmp_posters:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        self.close()

    def _paintPoster(self, picData=None):
        ptr = self.picLoad.getData()
        if ptr:
            self["poster"].instance.setPixmap(ptr)
            self["poster"].show()
            self._poster_loaded = True

    def _onLoaded(self, data):
        if not data:
            self["status"].setText("تعذر تحميل الصفحة")
            return

        self._data = data
        current_title = _strip_arabic_from_english_title(
            data.get("title") or self._item.get("title", ""))
        self._raw_title = re.sub(r"\s+", " ", current_title).strip()
        self["title"].setText(_wrap_ui_text(current_title, width=30, max_lines=2, fallback="بدون عنوان"))

        meta = []
        if data.get("year"):   meta.append(data["year"])
        if data.get("rating"): meta.append("{}/10".format(data["rating"]))
        if data.get("type"):   meta.append(_TYPE_LABELS.get(data["type"], "عنصر"))
        if data.get("genres"): meta.append(data["genres"])
        self["meta"].setText(_wrap_ui_text("   ".join(meta), width=58, max_lines=2))
        self["badge"].setText("{}  •  {}".format(_site_label(self._site), _TYPE_LABELS.get(data.get("type"), "عنصر")))
        facts = [
            "المفضلة: {}  |  النسخة: {}  |  الوصف: {}".format(
                "محفوظ" if _is_favorite(self._item.get("url")) else "غير محفوظ",
                _PLUGIN_VERSION,
                "موجود" if _pick_plot_text(data, self._item) != "القصة غير متوفرة حالياً لهذا العنصر." else "غير متوفر"
            ),
        ]
        self["facts"].setText(_single_line_text("".join(facts), width=62))
        counts = []
        has_episodes = bool(data.get("items"))
        is_series_item = (
            data.get("type") in ("series", "show")
            or self._item.get("type") in ("series", "show")
            or has_episodes
        )
        if is_series_item:
            counts.append("الحلقات: {}".format(len([e for e in data.get("items", []) if e.get("type") == "episode"])))
        else:
            counts.append("السيرفرات: {}".format(len([s for s in data.get("servers", []) if s.get("url")])))
        if data.get("year"):
            counts.append("السنة: {}".format(data.get("year")))
        self["source"].setText(_wrap_ui_text("المصدر: {}  |  {}".format(_site_label(self._site), "  |  ".join(counts)), width=58, max_lines=2))
        self["tmdb_note"].setText("TMDb: تم تعزيز البيانات والبوستر" if data.get("_tmdb") else "TMDb: لا توجد بيانات إضافية حالياً")
        if is_series_item:
            plot_label = "قصة المسلسل"
        else:
            plot_label = "قصة الفيلم"
        if current_title:
            plot_label = "{}: {}".format(plot_label, current_title[:32])
        self["plot_title"].setText(_single_line_text(plot_label, width=46, fallback="القصة"))

        plot_text, plot_source = _pick_plot_text_with_source(data, self._item)
        plot_text = re.sub(r"^\[.*?\]\s*|^المصدر:\s*.*?\|\s*", "", plot_text)
        _MID_SITES = (
            "EgyDead", "Wecima", "Akoam", "ArabSeed",
            "TopCinema", "TopCinemaa", "FaselHD", "Shaheed", "Shaheed4u",
        )
        for _ms in _MID_SITES:
            plot_text = re.sub(
                r"\s*[|\-]\s*" + re.escape(_ms) + r"[^\u0600-\u06ff\n]{0,25}",
                " ", plot_text, flags=re.I)
            plot_text = re.sub(
                r"\u0639\u0644\u0649\s+\u0645\u0648\u0642\u0639\s+" + re.escape(_ms)
                + r"[^\u0600-\u06ff\n]{0,30}",
                " ", plot_text, flags=re.I)
        plot_text = re.sub(r"  +", " ", plot_text).strip()
        my_log("Detail plot source: {} | len={}".format(plot_source, len(plot_text)))

        _pt = (plot_text or "").strip()
        if len(_pt) > 500:
            _pt = _pt[:500].rsplit(" ", 1)[0] + "…"
        # FIX #2: use correct U+200F RIGHT-TO-LEFT MARK (not embedding chars U+202B/202C)
        _ar_count = sum(1 for _c in _pt[:80] if "\u0600" <= _c <= "\u06ff")
        if _ar_count > int(len(_pt[:80]) * 0.3):
            _pt = "\u200f" + _pt
        self["plot"].setText(_pt)

        self._servers = _sort_servers([s for s in data.get("servers", []) if s.get("url")])
        self._episodes = [e for e in data.get("items", []) if e.get("type") == "episode"]

        my_log("Detail _onLoaded: servers={}, items={}".format(len(self._servers), len(self._episodes)))

        is_series = (
            data.get("type") in ("series", "show")
            or self._item.get("type") in ("series", "show")
            or bool(self._episodes)
        )

        if is_series:
            if self._episodes:
                self["section"].setText(_single_line_text("الحلقات المتاحة: {}  |  اختر الحلقة المطلوبة".format(len(self._episodes)), width=90))
                self["menu"].setList(["{}. {}".format(i + 1, _single_line_text(ep.get("title", "Episode"), width=58, fallback="حلقة")) for i, ep in enumerate(self._episodes)])
                self["status"].setText(self._status_hint("اختار حلقة — OK"))
            else:
                self["section"].setText("الحلقات المتاحة: 0")
                self["menu"].setList(["لا توجد حلقات متاحة حالياً"])
                self["status"].setText("لا توجد حلقات")
        else:
            if self._servers:
                self["section"].setText(_single_line_text("السيرفرات المتاحة: {}  |  اختر الجودة أو السيرفر".format(len(self._servers)), width=90))
                self["menu"].setList(["{}. {}".format(i + 1, _single_line_text(s.get("name", "Server"), width=58, fallback="Server")) for i, s in enumerate(self._servers)])
                self["status"].setText(self._status_hint("اختار سيرفر — OK"))
            else:
                self["section"].setText("السيرفرات المتاحة: 0")
                self["menu"].setList(["لا توجد سيرفرات متاحة"])
                self["status"].setText("لا توجد سيرفرات")

        poster_url = data.get("poster") or self._item.get("poster", "")
        if poster_url:
            threading.Thread(
                target=self._downloadPoster, args=(poster_url,), daemon=True
            ).start()

    def _status_hint(self, prefix):
        fav_state = "محفوظ" if _is_favorite(self._item.get("url")) else "غير محفوظ"
        tmdb_state = "TMDb مفعل" if _tmdb_enabled() else "TMDb غير مفعل"
        return "{}  |  {}  |  {}".format(prefix, fav_state, tmdb_state)

    def _refreshPoster(self):
        if getattr(self, "_poster_loaded", False):
            try:
                self["poster"].show()
            except Exception:
                pass
            return
        poster_url = None
        if self._data and self._data.get("poster"):
            poster_url = self._data["poster"]
        elif self._item.get("poster"):
            poster_url = self._item["poster"]
        if poster_url:
            self._downloadPoster(poster_url)
        else:
            callInMainThread(self["poster"].hide)

    def _downloadPoster(self, url):
        try:
            if not url: return
            if url.startswith("//"): url = "https:" + url

            import urllib.request as urllib2
            try:
                from urllib.parse import urlparse, quote, urlunparse
                p = list(urlparse(url))
                p[2] = quote(p[2])
                p[4] = quote(p[4])
                url = urlunparse(p)
            except Exception: pass

            cached = _get_cached_poster(url)
            if cached:
                callInMainThread(self.picLoad.setPara, (self["poster"].instance.size().width(), self["poster"].instance.size().height(), 1, 1, 0, 1, "#000000"))
                callInMainThread(self.picLoad.startDecode, cached)
                return

            cache_path = _poster_cache_path(url)
            req = urllib2.Request(url, headers={"User-Agent": SAFE_UA})
            data = urllib2.urlopen(req, timeout=10).read()

            save_path = cache_path or "/tmp/ap_detail_{}.jpg".format(int(time.time()))
            with open(save_path, "wb") as f:
                f.write(data)
            if not cache_path:
                self._tmp_posters.append(save_path)
            callInMainThread(self.picLoad.setPara, (self["poster"].instance.size().width(), self["poster"].instance.size().height(), 1, 1, 0, 1, "#000000"))
            callInMainThread(self.picLoad.startDecode, save_path)
        except Exception as e:
            my_log("_downloadPoster error: {} (URL: {})".format(e, url))

    def _onOk(self):
        idx = self["menu"].getSelectedIndex()
        if idx < 0:
            return

        is_series = bool(
            self._data and (
                self._data.get("type") in ("series", "show")
                or self._item.get("type") in ("series", "show")
                or self._episodes
            )
        )

        if is_series:
            if idx >= len(self._episodes):
                return
            ep = self._episodes[idx]
            self.session.open(ArabicPlayerDetail, ep, self._site, "episode")
        else:
            if idx >= len(self._servers):
                return
            server = self._servers[idx]
            self["status"].setText("Extracting stream...")
            self["status"].show()
            threading.Thread(target=self._bgExtract, args=(server,), daemon=True).start()

    def _toggleFavorite(self):
        base = self._data or self._item
        entry = _entry_from_item(
            dict(self._item, **(base or {})),
            self._site,
            self._m_type,
            {"type": (base or {}).get("type", self._item.get("type", self._m_type))}
        )
        added = _toggle_favorite_entry(entry)
        self["status"].setText("تمت الإضافة إلى المفضلة" if added else "تم الحذف من المفضلة")
        if self._data:
            self._onLoaded(self._data)

    def _refreshTMDb(self):
        if not _tmdb_enabled():
            self["status"].setText("أضف TMDb API Key من الإعدادات أولاً")
            return
        self["status"].setText("جاري تحديث البيانات من TMDb...")
        threading.Thread(target=self._bgRefreshTMDb, daemon=True).start()

    def _bgRefreshTMDb(self):
        try:
            merged = _merge_tmdb_data(self._data or self._item)
            callInMainThread(self._onLoaded, merged)
        except Exception as e:
            my_log("TMDb refresh failed: {}".format(e))
            callInMainThread(self["status"].setText, "فشل تحديث TMDb")

    def _bgExtract(self, server):
        try:
            from extractors.base import log
            log("Detail _bgExtract: START extracting for server={}".format(server.get("name", "Unknown")))

            extract_fn = None
            try:
                extractor = _get_extractor(self._site)
                extract_fn = getattr(extractor, "extract_stream", None)
            except Exception:
                extract_fn = None

            if extract_fn is None:
                from extractors.base import extract_stream as extract_fn

            url, qual, final_ref = extract_fn(server["url"])

            if url:
                log("Detail _bgExtract: SUCCESS! URL: {}".format(url))
                callInMainThread(self._onStreamFound, url, qual, final_ref, server)
            else:
                log("Detail _bgExtract: FAILED to resolve stream")
                callInMainThread(self["status"].setText, "فشل استخراج الرابط — جرب سيرفر تاني")
        except Exception as e:
            log("Detail _bgExtract CRITICAL ERROR: {}".format(e))
            callInMainThread(self["status"].setText, "خطأ في النظام: {}".format(str(e)[:30]))

    def _onStreamFound(self, stream_url, quality, final_ref, server):
        if not stream_url:
            self["status"].setText("{} — غير متاح، جرب سيرفر آخر".format(server["name"]))
            return
        my_log("Stream found: {} [{}]".format(stream_url, quality))
        history_entry = _entry_from_item(
            dict(self._item, **(self._data or {})),
            self._site,
            self._m_type,
            {
                "server_name": server.get("name", ""),
                "quality": quality or "",
                "last_stream_url": stream_url,
            }
        )
        _upsert_library_item("history", history_entry, limit=120)

        # FIX #3: removed unused _quality_tag variable
        # Use raw single-line title
        title = getattr(self, "_raw_title", None) or \
                re.sub(r"\s+", " ", self["title"].getText()).strip()

        try:
            raw_url = stream_url.strip()
            if "|" in raw_url:
                main_url, old_params = raw_url.split("|", 1)
            else:
                main_url, old_params = raw_url, ""

            lower_main_url = main_url.lower()
            is_media_url = any(marker in lower_main_url for marker in (
                ".m3u8", ".mp4", ".mkv", ".mp3", ".ts", ".avi",
                "master.txt", "/hls", "/stream", "/playlist"
            ))
            is_embed_page = any(marker in lower_main_url for marker in (
                "/embed-", "/embed/", "/e/", "/watch/"
            ))
            if is_embed_page and not is_media_url:
                self["status"].setText("الرابط صفحة تشغيل وليس ملف فيديو — جرب سيرفر آخر")
                return

            headers = {"User-Agent": SAFE_UA}

            if final_ref:
                headers["Referer"] = final_ref

            if old_params:
                for p in old_params.split("&"):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        if k not in headers: headers[k] = v

            header_str = "&".join(["{}={}".format(k, v) for k, v in headers.items()])
            pure_url = main_url.split("|")[0].strip()
            url = pure_url + "#" + header_str if header_str else pure_url

            _item_url = self._item.get("url", "")
            _saved_pos = _get_saved_position(_item_url)
            if _saved_pos > 30:
                if _saved_pos >= 3600:
                    _hours_r = _saved_pos // 3600
                    _mins_r = (_saved_pos % 3600) // 60
                    _secs_r = _saved_pos % 60
                    resume_text = "Resume from {:02d}:{:02d}:{:02d}?".format(_hours_r, _mins_r, _secs_r)
                else:
                    _mins_r = _saved_pos // 60
                    _secs_r = _saved_pos % 60
                    resume_text = "Resume from {}:{:02d}?".format(_mins_r, _secs_r)

                def _on_resume(_ans, _u=url, _t=title, _iu=_item_url, _sp=_saved_pos):
                    if not _ans:
                        _save_position(_iu, 0)
                    _play(self.session, _u, _t, resume_pos=_sp if _ans else 0, item_url=_iu)
                self["status"].setText("جاري فتح المشغل...")
                self.session.openWithCallback(
                    _on_resume, MessageBox,
                    resume_text,
                    MessageBox.TYPE_YESNO, timeout=8, default=True)
            else:
                self["status"].setText("Opening player...")
                _play(self.session, url, title, resume_pos=0, item_url=_item_url)
            self["status"].hide()

        except Exception as e:
            my_log("Error opening player: {}".format(e))
            self["status"].setText("خطأ في المشغل: {}".format(str(e)[:60]))


from Screens.InfoBar import InfoBar

def _build_remote_play_candidates(url):
    url = str(url).strip()
    plain_url = url.split("#", 1)[0].strip()
    headers = {}
    if "#" in url:
        for part in url.split("#", 1)[1].split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                headers[key] = value
    candidates = []
    seen = set()

    def add_candidate(p_type, svc_url, label, uses_proxy=False):
        key = (p_type, svc_url)
        if not svc_url or key in seen:
            return
        seen.add(key)
        candidates.append((p_type, svc_url, label, uses_proxy))

    if plain_url.startswith("https://") or plain_url.startswith("http://"):
        proxy_params = {"url": plain_url}
        if headers.get("Referer"):
            proxy_params["referer"] = headers["Referer"]
        if headers.get("User-Agent"):
            proxy_params["ua"] = headers["User-Agent"]
        proxied = "http://127.0.0.1:{}/stream?{}".format(_PROXY_PORT, urlencode(proxy_params))
        start_proxy()
        legacy_raw = url.replace("#", "|") if "#" in url else url
        legacy_proxied = "http://127.0.0.1:{}/{}".format(_PROXY_PORT, legacy_raw)
    else:
        proxied = ""
        legacy_proxied = ""

    is_hls = any(x in plain_url.lower() for x in (".m3u8", "master.txt", "/hls", "/playlist"))

    if is_hls:
        add_candidate(4097, plain_url, "4097 مباشر HLS")
        if proxied:
            add_candidate(4097, proxied, "4097 + proxy HLS", True)
        add_candidate(4097, url, "4097 + headers HLS")
        add_candidate(8193, plain_url, "8193 مباشر")
        if proxied:
            add_candidate(8193, proxied, "8193 + proxy", True)
    else:
        if proxied:
            add_candidate(5001, proxied, "5001 + proxy", True)
        add_candidate(5001, plain_url, "5001 مباشر")
        add_candidate(8193, plain_url, "8193 مباشر")
        if proxied:
            add_candidate(8193, proxied, "8193 + proxy", True)
        add_candidate(4097, plain_url, "4097 مباشر")
        if proxied:
            add_candidate(4097, proxied, "4097 + proxy", True)
        add_candidate(4097, url, "4097 + headers")
    if legacy_proxied:
        add_candidate(4097, legacy_proxied, "4097 + proxy قديم", True)

    if os.path.exists("/usr/bin/exteplayer3"):
        if plain_url.startswith("http://") or plain_url.startswith("https://"):
            add_candidate(5002, plain_url, "5002 مباشر")
            if proxied:
                add_candidate(5002, proxied, "5002 + proxy", True)
        add_candidate(5002, url, "5002 + headers")

    return candidates


def _copy_service_ref(sref):
    if not sref:
        return None
    try:
        return eServiceReference(sref.toString())
    except Exception:
        try:
            return eServiceReference(str(sref.toString()))
        except Exception:
            return sref


def _capture_previous_service(session):
    try:
        return _copy_service_ref(session.nav.getCurrentlyPlayingServiceReference())
    except Exception as e:
        my_log("Capture previous service failed: {}".format(e))
        return None


def _restore_previous_service(session, previous_service):
    if not previous_service:
        return
    try:
        session.nav.stopService()
    except Exception:
        pass
    try:
        session.nav.playService(previous_service)
        my_log("Previous service restored")
    except Exception as e:
        my_log("Restore previous service failed: {}".format(e))


# ─── Simple Player ────────────────────────────────────────────────────────────
class ArabicPlayerSimplePlayer(Screen):
    skin = """
    <screen name="ArabicPlayerSimplePlayer" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="transparent">

        <widget name="osd_shadow"   position="148,856" size="1624,230" backgroundColor="#000000" zPosition="9" />
        <widget name="overlay_bg"   position="160,860" size="1600,210" backgroundColor="#0A0E14" zPosition="10" />
        <widget name="osd_topline"  position="160,860" size="1600,3" backgroundColor="#00E5FF" zPosition="11" />
        <widget name="osd_titlebar" position="160,860" size="1600,52" backgroundColor="#0D1520" zPosition="11" />
        <widget name="osd_title"    position="180,868" size="1180,38" font="Regular;30" foregroundColor="#00E5FF" transparent="1" zPosition="12" halign="left" />
        <widget name="osd_durtext"  position="1380,868" size="360,38" font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="12" halign="right" />
        <widget name="prog_bar"     position="160,906" size="1600,30" font="Regular;22" foregroundColor="#00B4D8" transparent="1" zPosition="12" halign="left" />
        <widget name="osd_elapsed"  position="180,938" size="320,44" font="Regular;36" foregroundColor="#FFD740" transparent="1" zPosition="12" />
        <widget name="status"       position="640,938" size="640,44" font="Regular;36" foregroundColor="#39D98A" transparent="1" zPosition="12" halign="center" />
        <widget name="osd_hints"    position="1220,938" size="520,44" font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="12" halign="right" />
        <widget name="osd_divider"  position="160,982" size="1600,2" backgroundColor="#1C2333" zPosition="11" />
        <widget name="osd_keybar"   position="160,984" size="1600,46" backgroundColor="#0D1520" zPosition="11" />
        <widget name="osd_keys"     position="180,992" size="1560,34" font="Regular;24" foregroundColor="#484F58" transparent="1" zPosition="12" halign="center" />
        <widget name="osd_botline"  position="160,1027" size="1600,3" backgroundColor="#0A2040" zPosition="11" />
    </screen>
    """

    def __init__(self, session, title, candidates, previous_service=None, resume_pos=0, item_url=""):
        Screen.__init__(self, session)
        self["overlay_bg"]   = Label("")
        self["status"]       = Label("جاري التشغيل...")
        self["osd_shadow"]   = Label("")
        self["osd_titlebar"] = Label("")
        self["osd_title"]    = Label("")
        self["osd_durtext"]  = Label("")
        self["osd_topline"]  = Label("")
        self["prog_bar"]     = Label("")
        self["osd_elapsed"]  = Label("")
        self["osd_hints"]    = Label("")
        self["osd_divider"]  = Label("")
        self["osd_keybar"]   = Label("")
        self["osd_keys"]     = Label("")
        self["osd_botline"]  = Label("")
        _raw = (title or "").strip()
        _qtag_m = re.search(r'\s*(\[\d+p\])\s*$', _raw)
        _qtag = _qtag_m.group(1) if _qtag_m else ""
        _bare = _raw[:_qtag_m.start()].strip() if _qtag_m else _raw
        if len(_bare) > 34:
            _bare = _bare[:32].rstrip() + u"\u2026"
        self.title = (_bare + " " + _qtag).strip() if _qtag else _bare
        self.candidates = candidates or []
        self.previous_service = _copy_service_ref(previous_service)
        self.sref = None
        self._play_confirmed = False
        self._candidate_idx = -1
        self._candidate_start_ts = 0
        self._candidate_uses_proxy = False
        self._candidate_label = ""
        self._handoff = False
        self._restored_previous = False
        self._resume_pos = int(resume_pos or 0)
        self._item_url  = item_url or ""
        self._seek_timer = eTimer()
        self._seek_timer.callback.append(self.__doSeek)
        self._seek_retry_count = 0
        self._seek_verify_timer = eTimer()
        self._seek_verify_timer.callback.append(self.__verifySeek)
        self._hide_timer = eTimer()
        self._hide_timer.callback.append(self.__hideOSD)
        self._osd_update_timer = eTimer()
        self._osd_update_timer.callback.append(self.__updateOSD)
        self._osd_visible = False
        self._total_secs  = 0
        self._osd_auto_hide_secs = 4
        self._paused = False
        self._paused_elapsed = 0
        self._force_confirmation_timer = eTimer()
        self._force_confirmation_timer.callback.append(self.__forceConfirm)

        self["actions"] = ActionMap(
            ["OkCancelActions", "MediaPlayerActions", "InfobarSeekActions", "DirectionActions", "ColorActions"],
            {
                "cancel":           self.__onExit,
                "stop":             self.__onExit,
                "ok":               self.__togglePause,
                "playpauseService": self.__togglePause,
                "right":            lambda: self.__seek(+10),
                "left":             lambda: self.__seek(-10),
                "seekFwd":          lambda: self.__seek(+60),
                "seekBack":         lambda: self.__seek(-60),
                "green":            self.__onRestart,
            },
            -1
        )
        self._retry_timer = eTimer()
        self._retry_timer.callback.append(self.__onTimeout)
        eventmap = {
            iPlayableService.evTuneFailed: self.__onFailed,
            iPlayableService.evEOF: self.__onFailed,
        }
        ev_video = getattr(iPlayableService, "evVideoSizeChanged", None)
        if ev_video is not None:
            eventmap[ev_video] = self.__onConfirmed
        self._events = ServiceEventTracker(screen=self, eventmap=eventmap)
        self.onLayoutFinish.append(self.__initOSD)
        self.onLayoutFinish.append(self.__playNext)
        self.onClose.append(self.__stop)

    _OSD_WIDGETS = [
        "osd_shadow","overlay_bg","osd_topline","osd_botline",
        "osd_titlebar","osd_title","osd_durtext",
        "prog_bar","osd_elapsed",
        "status","osd_hints","osd_divider",
        "osd_keybar","osd_keys",
    ]

    def __initOSD(self):
        for w in self._OSD_WIDGETS:
            try: self[w].hide()
            except: pass

    def __hideOSD(self):
        self._osd_visible = False
        try: self._osd_update_timer.stop()
        except: pass
        for w in self._OSD_WIDGETS:
            try: self[w].hide()
            except: pass

    def __showOSD(self, auto_hide=True):
        self._osd_visible = True
        for w in self._OSD_WIDGETS:
            try: self[w].show()
            except: pass
        self.__updateOSD()
        try:
            self._osd_update_timer.start(1000, False)
        except: pass
        if auto_hide:
            try:
                self._hide_timer.stop()
                self._hide_timer.start(self._osd_auto_hide_secs * 1000, True)
            except: pass

    def __updateOSD(self):
        if not self._osd_visible:
            try: self._osd_update_timer.stop()
            except: pass
            return
        try:
            if self._paused:
                elapsed = self._paused_elapsed
            else:
                wall = _GLOBAL_PLAY_START_WALL
                base = _GLOBAL_PLAY_START_POS
                if wall and base >= 0:
                    elapsed = max(0, int((time.time() - wall) + base))
                else:
                    elapsed = 0
            he = elapsed // 3600; me = (elapsed % 3600) // 60; se = elapsed % 60
            self["osd_elapsed"].setText("{:02d}:{:02d}:{:02d}".format(he, me, se))
            total = self._total_secs
            if not total:
                try:
                    svc = self.session.nav.getCurrentService()
                    seek = svc and svc.seek()
                    if seek:
                        r = seek.getLength()
                        if r and r[0] == 0 and r[1] > 0:
                            total = r[1] // 90000
                            self._total_secs = total
                except: pass
            if total > 0:
                rem = max(0, total - elapsed)
                pct = min(1.0, float(elapsed) / float(total))
                hr = rem // 3600
                mr = (rem % 3600) // 60
                sr = rem % 60
                ht = total // 3600
                mt = (total % 3600) // 60
                st = total % 60
                self["osd_durtext"].setText("-{:02d}:{:02d}:{:02d}  {:02d}:{:02d}:{:02d}".format(hr, mr, sr, ht, mt, st))
                BAR_W = 96
                filled = max(0, min(BAR_W, int(pct * BAR_W)))
                bar = u"█" * filled + u"░" * (BAR_W - filled)
                self["prog_bar"].setText(u"{} {:.1f}%".format(bar, pct * 100))
            else:
                self["osd_durtext"].setText("")
                self["prog_bar"].setText("")
            self["osd_keys"].setText("OK=Pause   << -10s   +10s >>   <<< -60s   +60s >>>   Green=إعادة+استئناف   Stop=حفظ&خروج")
        except Exception as e:
            my_log("updateOSD error: {}".format(e))

    def __forceConfirm(self):
        if not self._play_confirmed:
            my_log("Force confirm (unconditional)")
            self.__onConfirmed()

    def __playNext(self):
        global _PROXY_LAST_HIT, _PROXY_LAST_BYTES
        self._candidate_idx += 1
        if self._candidate_idx >= len(self.candidates):
            self["status"].setText("تعذر تشغيل الرابط على كل المحاولات")
            return

        p_type, svc_url, label, uses_proxy = self.candidates[self._candidate_idx]
        self._play_confirmed = False
        self._candidate_start_ts = time.time()
        self._candidate_uses_proxy = uses_proxy
        self._candidate_label = label
        if uses_proxy:
            _PROXY_LAST_HIT = 0
            _PROXY_LAST_BYTES = 0
        self.sref = eServiceReference(p_type, 0, svc_url)
        if sys.version_info[0] == 3:
            self.sref.setName(str(self.title))
        else:
            self.sref.setName(self.title.encode("utf-8", "ignore"))

        self["status"].setText("جاري التشغيل... {}".format(label))
        my_log("Play attempt: {}".format(label))
        try:
            self.session.nav.stopService()
        except: pass
        try:
            self.session.nav.playService(self.sref)
            self._retry_timer.start(12000, True)
            self._force_confirmation_timer.start(3000, True)
        except Exception as e:
            my_log("SimplePlayer fallback error: {}".format(e))
            self.__playNext()

    def __onConfirmed(self):
        if self._play_confirmed:
            return
        self._play_confirmed = True
        try:
            self._retry_timer.stop()
            self._force_confirmation_timer.stop()
        except: pass
        my_log("Play confirmed: {}".format(self._candidate_label))
        _start_pos_tracker(self.session, self._item_url, start_pos=0)
        if self._resume_pos > 30:
            self._seek_retry_count = 0
            self._seek_timer.start(6000, True)
        self["osd_title"].setText(self.title)
        self["status"].setText(u"▶ Playing")
        self._total_secs = 0
        self.__showOSD(True)

    def __togglePause(self):
        try:
            svc = self.session.nav.getCurrentService()
            if not svc:
                self.__showOSD(True); return
            p = svc.pause()
            if not p:
                self.__showOSD(True); return
            if self._paused:
                p.unpause()
                self._paused = False
                global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
                _GLOBAL_PLAY_START_POS = self._paused_elapsed
                _GLOBAL_PLAY_START_WALL = time.time()
                self["status"].setText(u"▶ Playing")
            else:
                wall = _GLOBAL_PLAY_START_WALL
                base = _GLOBAL_PLAY_START_POS
                if wall:
                    elapsed = int((time.time() - wall) + base)
                else:
                    elapsed = 0
                self._paused_elapsed = max(0, elapsed)
                p.pause()
                self._paused = True
                self["status"].setText(u"⏸ Paused")
            self.__showOSD(True)
        except Exception as e:
            my_log("togglePause error: {}".format(e))
            self.__showOSD(True)

    def __seek(self, delta_secs):
        try:
            svc = self.session.nav.getCurrentService()
            if not svc: return
            sk = svc.seek()
            if not sk: return
            global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
            global _GLOBAL_LAST_SEEK_TARGET
            _wall = _GLOBAL_PLAY_START_WALL
            _base = _GLOBAL_PLAY_START_POS
            if _wall:
                elapsed = time.time() - _wall
            else:
                elapsed = 0
            current_est = int(_base + elapsed)
            target = max(0, current_est + int(delta_secs))
            _tot = self._total_secs
            if _tot > 0:
                target = min(target, _tot - 3)
            sk.seekTo(target * 90000)
            _GLOBAL_LAST_SEEK_TARGET = target
            _GLOBAL_PLAY_START_POS = max(0, target - 2)
            _GLOBAL_PLAY_START_WALL = time.time()
            if self._paused:
                self._paused_elapsed = target
            self._total_secs = 0
            _th = target // 3600; _tm = (target % 3600) // 60; _ts = target % 60
            _arr = u"➡" if delta_secs > 0 else u"⬅"
            self["status"].setText(u"{} {:02d}:{:02d}:{:02d}".format(_arr, _th, _tm, _ts))
            self.__showOSD(True)
            self._hide_timer.start(2500, True)
        except Exception as e:
            my_log("seek error: {}".format(e))

    def __onRestart(self):
        my_log("Restart+Resume requested by green button")
        if self._item_url:
            try:
                if self._paused:
                    secs = self._paused_elapsed
                else:
                    wall = _GLOBAL_PLAY_START_WALL
                    base = _GLOBAL_PLAY_START_POS
                    secs = int((time.time() - wall) + base) if wall else 0
                if secs > 30:
                    _save_position(self._item_url, secs)
                    self._resume_pos = secs
                    my_log("Restart: saved pos={}s, will re-seek after restart".format(secs))
            except Exception as e:
                my_log("Restart pos-save error: {}".format(e))
        try:
            self._seek_timer.stop()
            self._seek_verify_timer.stop()
        except: pass
        self._play_confirmed = False
        self._seek_retry_count = 0
        try:
            self.session.nav.stopService()
        except: pass
        self._candidate_idx = -1
        self["status"].setText(u"إعادة التشغيل + استئناف من {}:{:02d}...".format(
            self._resume_pos // 60, self._resume_pos % 60) if self._resume_pos > 30 else u"إعادة التشغيل...")
        self.__showOSD(True)
        restart_timer = eTimer()
        restart_timer.callback.append(self.__playNext)
        restart_timer.start(500, True)

    def __onExit(self):
        try:
            if self._item_url:
                if self._paused:
                    secs = self._paused_elapsed
                else:
                    wall = _GLOBAL_PLAY_START_WALL
                    base = _GLOBAL_PLAY_START_POS
                    if wall:
                        secs = int((time.time() - wall) + base)
                    else:
                        secs = 0
                _tot = self._total_secs
                if _tot > 0:
                    secs = min(secs, _tot - 5)
                secs = max(0, secs)
                if secs > 30:
                    _save_position(self._item_url, secs)
                    my_log("Exit save: {}s".format(secs))
        except Exception as e:
            my_log("Exit save error: {}".format(e))
        try:
            self.session.nav.stopService()
        except: pass
        _stop_pos_tracker()
        _restore_previous_service(self.session, self.previous_service)
        self.close()

    def __stop(self):
        self.__hideOSD()
        for t in ("_seek_timer","_seek_verify_timer","_retry_timer","_hide_timer","_osd_update_timer","_force_confirmation_timer"):
            try: getattr(self, t).stop()
            except: pass

    def __onFailed(self):
        if self._play_confirmed:
            return
        try:
            self._retry_timer.stop()
            self._force_confirmation_timer.stop()
        except: pass
        my_log("Play failed event: {}".format(self._candidate_label))
        self.__playNext()

    def __onTimeout(self):
        global _PROXY_LAST_HIT, _PROXY_LAST_BYTES
        if self._play_confirmed:
            return
        if self._candidate_uses_proxy and _PROXY_LAST_HIT >= self._candidate_start_ts and _PROXY_LAST_BYTES > 0:
            my_log("Play proxy confirmed by traffic: {} bytes".format(_PROXY_LAST_BYTES))
            self.__onConfirmed()
            return
        my_log("Play timeout: {}".format(self._candidate_label))
        self.__playNext()

    def __doSeek(self):
        if not self._resume_pos or self._resume_pos <= 30:
            my_log("Seek skipped: resume_pos={}".format(self._resume_pos))
            return
        try:
            svc = self.session.nav.getCurrentService()
            seek = svc and svc.seek()
            if not seek:
                self._seek_retry_count += 1
                if self._seek_retry_count <= 3:
                    my_log("doSeek: no seek interface, retry {}/3 in 4s".format(self._seek_retry_count))
                    self._seek_timer.start(4000, True)
                else:
                    my_log("doSeek: giving up after 3 retries")
                return

            seek.seekTo(self._resume_pos * 90000)
            my_log("Resume seekTo: {}s (attempt {})".format(self._resume_pos, self._seek_retry_count + 1))
            self._total_secs = 0

            self._seek_verify_timer.start(4000, True)

            if self._osd_visible:
                self.__updateOSD()
        except Exception as e:
            my_log("doSeek failed: {} — retry {}/3".format(e, self._seek_retry_count))
            self._seek_retry_count += 1
            if self._seek_retry_count <= 3:
                self._seek_timer.start(4000, True)

    def __verifySeek(self):
        if not self._resume_pos or self._resume_pos <= 30:
            return
        global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS, _GLOBAL_LAST_SEEK_TARGET
        try:
            svc = self.session.nav.getCurrentService()
            seek = svc and svc.seek()
            actual_pos = -1

            if seek:
                try:
                    r = seek.getPlayPosition()
                    if r and r[0] == 0 and r[1] > 0:
                        actual_pos = int(r[1] // 90000)
                except Exception:
                    pass

            if actual_pos >= 0:
                if actual_pos >= max(0, self._resume_pos - 60):
                    _GLOBAL_PLAY_START_POS = actual_pos
                    _GLOBAL_PLAY_START_WALL = time.time()
                    _GLOBAL_LAST_SEEK_TARGET = actual_pos
                    if self._paused:
                        self._paused_elapsed = actual_pos
                    my_log("verifySeek OK via PTS: actual={}s target={}s".format(
                        actual_pos, self._resume_pos))
                else:
                    if seek and self._seek_retry_count <= 3:
                        self._seek_retry_count += 1
                        seek.seekTo(self._resume_pos * 90000)
                        my_log("verifySeek double-tap {}/3: actual={}s target={}s".format(
                            self._seek_retry_count, actual_pos, self._resume_pos))
                        self._seek_verify_timer.start(3000, True)
                    else:
                        _GLOBAL_PLAY_START_POS = max(0, self._resume_pos - 2)
                        _GLOBAL_PLAY_START_WALL = time.time()
                        my_log("verifySeek giving up, setting display to target {}s".format(
                            self._resume_pos))
            else:
                if self._seek_retry_count <= 2:
                    if seek:
                        seek.seekTo(self._resume_pos * 90000)
                    self._seek_retry_count += 1
                    _GLOBAL_PLAY_START_POS = max(0, self._resume_pos - 2)
                    _GLOBAL_PLAY_START_WALL = time.time()
                    _GLOBAL_LAST_SEEK_TARGET = self._resume_pos
                    if self._paused:
                        self._paused_elapsed = self._resume_pos
                    my_log("verifySeek double-tap {}/3 (no PTS), target={}s".format(
                        self._seek_retry_count, self._resume_pos))
                    self._seek_verify_timer.start(3000, True)
                else:
                    my_log("verifySeek: max retries reached, target={}s".format(self._resume_pos))
        except Exception as e:
            my_log("verifySeek error: {}".format(e))

    def __restorePrevious(self):
        if self._restored_previous:
            return
        self._restored_previous = True
        _restore_previous_service(self.session, self.previous_service)


# ─── Global play function ─────────────────────────────────────────────────────
def _play(session, url, title, resume_pos=0, item_url=""):
    try:
        svc_url = str(url).strip()
        is_remote = svc_url.startswith("http://") or svc_url.startswith("https://")
        previous_service = _capture_previous_service(session)

        if is_remote:
            session.open(ArabicPlayerSimplePlayer, title, _build_remote_play_candidates(svc_url), previous_service, resume_pos=resume_pos, item_url=item_url)
            return

        sref = eServiceReference(4097, 0, svc_url)
        if sys.version_info[0] == 3:
            sref.setName(str(title))
        else:
            sref.setName(title.encode("utf-8", "ignore"))

        try:
            from Screens.InfoBar import MoviePlayer
            callback = lambda *args: _restore_previous_service(session, previous_service)
            try:
                if is_remote:
                    session.openWithCallback(callback, MoviePlayer, sref, streamMode=True, askBeforeLeaving=False)
                else:
                    session.openWithCallback(callback, MoviePlayer, sref, askBeforeLeaving=False)
            except TypeError:
                session.openWithCallback(callback, MoviePlayer, sref)
        except Exception as e:
            my_log("[PLAY_INFOBAR_FALLBACK] " + str(e))
            session.open(ArabicPlayerSimplePlayer, title, _build_remote_play_candidates(svc_url), previous_service)
    except Exception as e:
        my_log("[PLAY_ERROR] " + str(e))

# ─── Splash Screen ───────────────────────────────────────────────────────────
class ArabicPlayerSplash(Screen):
    skin = """
    <screen name="ArabicPlayerSplash" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="#000000">
        <widget name="splash_pic" position="0,0" size="1920,1080" zPosition="1" alphatest="blend" />
    </screen>
    """

    def __init__(self, session):
        self.skin = ArabicPlayerSplash.skin.format(PLUGIN_PATH)
        Screen.__init__(self, session)
        self["splash_pic"] = Pixmap()
        self._timer = eTimer()
        self._timer.callback.append(self._onFinish)

        self.picLoad = ePicLoad()
        self.picLoad.PictureData.get().append(self._paintSplash)

        self.onLayoutFinish.append(self._start)

    def _start(self):
        splash_path = os.path.join(PLUGIN_PATH, "images", "splash.png")
        if os.path.exists(splash_path):
            self.picLoad.setPara((1920, 1080, 1, 1, 0, 1, "#000000"))
            self.picLoad.startDecode(splash_path)
        self._timer.start(2500, True)

    def _paintSplash(self, picData=None):
        ptr = self.picLoad.getData()
        if ptr:
            self["splash_pic"].instance.setPixmap(ptr)
            self["splash_pic"].show()

    def _onFinish(self):
        self._timer.stop()
        try:
            self.picLoad.PictureData.get().remove(self._paintSplash)
        except Exception:
            pass
        self.session.open(ArabicPlayerHome)
        self.close()


# ─── Plugin Entry Points ──────────────────────────────────────────────────────
def main(session, **kwargs):
    session.open(ArabicPlayerSplash)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name        = _PLUGIN_NAME,
            description = "تشغيل أفلام ومسلسلات من مواقع عربية",
            where       = PluginDescriptor.WHERE_PLUGINMENU,
            icon        = "plugin.png",
            fnc         = main
        ),
        PluginDescriptor(
            name        = _PLUGIN_NAME,
            description = "تشغيل أفلام ومسلسلات من مواقع عربية",
            where       = PluginDescriptor.WHERE_EXTENSIONSMENU,
            fnc         = main
        ),
    ]
````

## File: README.md
````markdown
# 🎬 ArabicPlayer Plugin (Enigma2)
![ArabicPlayer Logo](plugin.png)

تطبيق **ArabicPlayer** هو بلاجن مخصص لأجهزة الاستقبال العاملة بنظام **Enigma2** (مثل Novaler 4K Pro, Dreambox, Vu+ وغيرها)، يتيح لك مشاهدة أحدث الأفلام والمسلسلات العربية والأجنبية المترجمة مباشرة من أشهر المواقع العربية بجودة عالية وبدون تقطيع.

---

## 🌟 المميزات (Premium Version)
*   **تصميم عصري "Neon Mode"**: واجهة مستخدم جديدة كلياً مع شعار وخلفية "Splash Screen" احترافية.
*   **دعم شامل لأشهر المواقع**:
    *   ✅ **TopCinema**: تم إصلاح استخراج السيرفرات وتجاوز مشاكل "صالة العرض".
    *   ✅ **FaselHD**: استعادة كافة الأقسام (أفلام، مسلسلات، أنمي) مع دعم السيرفرات المشفّرة.
    *   ✅ **Wecima**: بحث سريع وروابط مباشرة.
    *   ✅ **EgyDead**: مكتبة ضخمة وبوسترات بوضوح عالٍ.
    *   ✅ **Akoam & ArabSeed**: محتوى متجدد وتصنيفات مرتبة.
*   **تجاوز الحماية**: محاكاة كاملة للمتصفح لتجاوز حماية الـ WAF و Cloudflare.
*   **دعم TMDB**: جلب معلومات الأفلام والبوسترات المفقودة تلقائياً.

---

## 📸 معاينة الواجهة الجديدة (Splash Screen)
![Splash Screen](images/splash.png)

---

## 🚀 طريقة التثبيت
يمكنك تثبيت البلاجن مباشرة عبر **التلنت (Telnet)** باستخدام هذا الأمر:
```bash
wget -q "--no-check-certificate" https://raw.githubusercontent.com/asdrere123-alt/ArabicPlayer/main/installer.sh -O - | /bin/sh
```

أو يدوياً:
1. قم بتحميل الملفات ووضعها في المسار:
   `/usr/lib/enigma2/python/Plugins/Extensions/ArabicPlayer`
2. قم بعمل **Restart Enigma2**.
3. استمتع بالمشاهدة!

---

## 👨‍💻 المطور
*   **الإصدار**: 1.3.1 (Modern UI)
*   **بواسطة**: أحمد إبراهيم

---

> [!TIP]
> جميع الحقوق محفوظة للمواقع الأصلية، هذا البلاجن هو وسيلة لتسهيل الوصول للمحتوى على أجهزة الإنيجما 2 فقط.
````
`````
