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