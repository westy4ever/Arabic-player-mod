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