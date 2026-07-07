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
