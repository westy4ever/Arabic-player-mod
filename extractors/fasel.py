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