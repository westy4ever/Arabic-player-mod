# -*- coding: utf-8 -*-
"""
Plugin for arablionztv.xyz
Arabic / English movies and series
"""

import re
from urllib.parse import urljoin
from .base import fetch, extract_stream as base_extract_stream

MAIN_URL = "https://arablionztv.xyz/"


def _clean_title(title):
    """Remove common clutter from titles"""
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("تحميل", "")
        .replace("فيلم", "")
        .replace("مسلسل", "")
        .strip()
    )


def _extract_boxes(html):
    """
    Extract movie/series cards from category pages.
    Typical pattern: <article> or <div class="item"> with image and link.
    """
    patterns = [
        # Common pattern 1
        r'<a[^>]+href="([^"]+)"[^>]*>\s*<img[^>]+src="([^"]+)"[^>]+alt="([^"]+)"',
        # Pattern 2 (more generic)
        r'<div[^>]*class="[^"]*?(?:post|item|movie|episode)[^"]*?"[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)"[^>]+alt="([^"]+)"',
    ]
    for pat in patterns:
        matches = re.findall(pat, html or "", re.S | re.I)
        if matches:
            return matches
    return []


def _extract_episodes(html, base_url):
    """
    Extract episode links from a series detail page.
    Returns list of dicts with 'title' and 'url'.
    """
    episodes = []
    seen = set()

    # Typical episode links: /episode/... or ?ep=...
    patterns = [
        r'<a[^>]+href="([^"]+)"[^>]*>.*?(?:حلقة|Episode|EP)\s*(\d+)',
        r'href="([^"]+/(?:episode|ep|season)/[^"]+)"[^>]*>(?:حلقة|Episode|EP)\s*([\d]+)',
    ]

    for pat in patterns:
        for match in re.finditer(pat, html or "", re.I | re.S):
            url = match.group(1)
            ep_num = match.group(2) if len(match.groups()) > 1 else ""
            full_url = urljoin(base_url, url).replace("&amp;", "&")
            if full_url in seen:
                continue
            seen.add(full_url)
            title = f"حلقة {ep_num}" if ep_num else "حلقة"
            episodes.append({
                "title": title,
                "url": full_url,
                "type": "episode",
                "_action": "item"
            })
            if len(episodes) >= 50:  # safety limit
                return episodes

    # Fallback: any link containing "episode" or "season"
    if not episodes:
        for link in re.findall(r'href="([^"]*(?:episode|season|ep)[^"]*)"', html, re.I):
            full_url = urljoin(base_url, link).replace("&amp;", "&")
            if full_url in seen or "category" in full_url:
                continue
            seen.add(full_url)
            episodes.append({
                "title": "حلقة",
                "url": full_url,
                "type": "episode",
                "_action": "item"
            })
    return episodes


def get_categories():
    """Return main categories (movies & series) with language filters."""
    return [
        {"title": "🎬 أفلام إنجليزية", "url": urljoin(MAIN_URL, "category/movies/english-movies/"), "type": "category", "_action": "category"},
        {"title": "🎬 أفلام عربية", "url": urljoin(MAIN_URL, "category/movies/arabic-movies/"), "type": "category", "_action": "category"},
        {"title": "🎬 كارتون", "url": urljoin(MAIN_URL, "category/movies/cartoon/"), "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات إنجليزية", "url": urljoin(MAIN_URL, "category/series/english-series/"), "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات عربية", "url": urljoin(MAIN_URL, "category/series/arabic-series/"), "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات تركية", "url": urljoin(MAIN_URL, "category/series/turkish-series/"), "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    """Parse a category page and return list of movies/series items."""
    html, final_url = fetch(url)
    if not html:
        return []

    items = []
    seen = set()

    for link, img, title in _extract_boxes(html):
        if link in seen:
            continue
        seen.add(link)

        # Determine if it's a series or movie based on URL or title
        is_series = "/series/" in link or "مسلسل" in title or "series" in link.lower()
        item_type = "series" if is_series else "movie"

        items.append({
            "title": _clean_title(title),
            "url": link,
            "image": img,
            "type": item_type,
            "_action": "details",
        })

    # Pagination: look for "next page" link
    next_match = re.search(r'<a[^>]+class="next"[^>]+href="([^"]+)"', html, re.I)
    if not next_match:
        next_match = re.search(r'<link[^>]+rel="next"[^>]+href="([^"]+)"', html, re.I)
    if next_match:
        next_url = next_match.group(1).replace("&amp;", "&")
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": next_url,
            "type": "category",
            "_action": "category",
        })

    return items


def get_page(url):
    """Parse a movie or series detail page."""
    html, final_url = fetch(url)
    result = {
        "url": url,
        "title": "",
        "poster": "",
        "plot": "",
        "servers": [],
        "items": [],
        "type": "movie"
    }

    if not html:
        return result

    # Title
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
    if title_match:
        result["title"] = _clean_title(title_match.group(1))

    # Poster image
    poster_match = re.search(r'<img[^>]+class="[^"]*?(?:poster|cover|img-fluid)[^"]*?"[^>]+src="([^"]+)"', html, re.I)
    if not poster_match:
        poster_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html, re.I)
    if poster_match:
        result["poster"] = poster_match.group(1).replace("&amp;", "&")

    # Plot / description
    plot_match = re.search(r'<div[^>]*class="[^"]*?(?:description|summary|plot)[^"]*?"[^>]*>(.*?)</div>', html, re.S | re.I)
    if not plot_match:
        plot_match = re.search(r'<p[^>]*>(.*?)</p>', html, re.S | re.I)
    if plot_match:
        result["plot"] = _clean_title(plot_match.group(1))

    # Check if it's a series (has episode links)
    is_series = "/series/" in final_url or "مسلسل" in result["title"]
    if is_series:
        result["type"] = "series"
        episodes = _extract_episodes(html, final_url)
        result["items"] = episodes
        return result

    # For movies: extract watch/download links (iframes or direct)
    # Look for iframes first (most common)
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    for idx, iframe in enumerate(iframes, 1):
        if iframe.startswith("//"):
            iframe = "https:" + iframe
        if not iframe.startswith("http"):
            continue
        result["servers"].append({
            "name": f"🌐 سيرفر {idx}",
            "url": iframe,
            "type": "iframe"
        })

    # Also look for direct links to video host pages
    host_links = re.findall(r'href="(https?://(?:streamtape|dood|mixdrop|uqload|voe|vidbom|upstream)[^"]+)"', html, re.I)
    for idx, link in enumerate(host_links, len(result["servers"]) + 1):
        result["servers"].append({
            "name": f"🎬 مشاهدة {idx}",
            "url": link,
            "type": "direct"
        })

    # If no servers found, try generic embedded player
    if not result["servers"]:
        # Look for video source directly in page (m3u8/mp4)
        video_url = None
        for pat in [r'file\s*:\s*"([^"]+)"', r'src:\s*"([^"]+)"', r'data-video="([^"]+)"']:
            m = re.search(pat, html, re.I)
            if m:
                video_url = m.group(1)
                break
        if video_url:
            result["servers"].append({
                "name": "🎬 مشاهدة",
                "url": video_url,
                "type": "direct"
            })

    return result


def extract_stream(url):
    """Extract direct video URL from a watch page or iframe."""
    # If it's already a direct video link
    if url.startswith("http") and any(x in url.lower() for x in (".m3u8", ".mp4", ".mkv")):
        return url, None, MAIN_URL

    # If it's an iframe or host page, let base extractor handle it
    return base_extract_stream(url)