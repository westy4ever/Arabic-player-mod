This file is a merged representation of the entire codebase, combined into a single document by Repomix.
The content has been processed where security check has been disabled.

# File Summary

## Purpose
This file contains a packed representation of the entire repository's contents.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Security check has been disabled - content may contain sensitive information
- Files are sorted by Git change count (files with more changes are at the bottom)

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
installer.sh
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
from urllib.parse import urljoin  # FIX: use standard library, not from base
from .base import fetch

MAIN_URL = "https://ak.sv/"


def _clean_title(title):
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("تحميل", "")
        .strip()
    )


def _extract_boxes(html):
    pattern = (
        r'<div class="(?:entry-box|episode-box)[^>]*>.*?'
        r'<a href="([^"]+)"[^>]*>.*?'
        r'<img[^>]+(?:data-src|src)="([^"]+)"[^>]*alt="([^"]+)"'
    )
    return re.findall(pattern, html or "", re.S)


def _normalize_watch_url(link):
    link = (link or "").replace("&amp;", "&").strip()
    if link.startswith("http://go.ak.sv/"):
        link = "https://" + link[len("http://"):]
    if link.startswith("https://go.ak.sv/watch/"):
        parts = link.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            return link
    return link


def _resolve_go_watch_url(link):
    link = _normalize_watch_url(link)

    # Case 1: it's already a direct ak.sv/watch URL
    if link.startswith("https://ak.sv/watch/") and not link.startswith("https://go.ak.sv/"):
        return link

    # Case 2: it's a go.ak.sv shortener URL — follow the redirect page to get real URL
    html, _ = fetch(link, referer=MAIN_URL)
    if not html:
        return link

    # Look for the real ak.sv/watch URL inside the redirect page
    resolved = re.search(r'https://ak\.sv/watch/[^\s\'"<>]+', html, re.I)
    if resolved:
        return resolved.group(0).replace("&amp;", "&")
    return link


def _extract_watch_links(html):
    links = []
    seen = set()
    patterns = [
        r'href="(https?://(?:go\.)?ak\.sv/watch/[^"]+)"',
        r'href="(https?://ak\.sv/watch/[^"]+)"',
        r'href="(https?://ak\.sv/download/[^"]+)"',
    ]
    for pattern in patterns:
        for link in re.findall(pattern, html or "", re.I):
            link = _resolve_go_watch_url(link)
            if link in seen:
                continue
            seen.add(link)
            links.append(link)
    return links


def get_categories():
    return [
        {"title": "🎬 الأفلام", "url": urljoin(MAIN_URL, "movies"), "type": "category", "_action": "category"},
        {"title": "📺 المسلسلات", "url": urljoin(MAIN_URL, "series"), "type": "category", "_action": "category"},
        {"title": "🎭 العروض", "url": urljoin(MAIN_URL, "shows"), "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, _ = fetch(url)
    if not html:
        return []

    items = []
    seen = set()
    for link, img, title in _extract_boxes(html):
        if link in seen or "/category/" in link:
            continue
        seen.add(link)
        item_type = "series" if "/series-" in link or "/series/" in link or "مسلسل" in title else "movie"
        items.append(
            {
                "title": _clean_title(title),
                "url": link,
                "image": img,
                "type": item_type,
                "_action": "details",
            }
        )

    next_page = re.search(r'href="([^"]+)"[^>]*rel="next"', html)
    if next_page:
        items.append(
            {
                "title": "➡️ الصفحة التالية",
                "url": next_page.group(1).replace("&amp;", "&"),
                "type": "category",
                "_action": "category",
            }
        )
    return items


def _quote_url(url):
    import sys
    if sys.version_info[0] == 3:
        from urllib.parse import quote
        return quote(url, safe=":/%?=&")
    else:
        from urllib import quote
        u = url.encode("utf-8") if isinstance(url, type(u"")) else url
        return quote(u, safe=":/%?=&")

def get_page(url):
    url = _quote_url(url)
    html, final_url = fetch(url)
    result = {"url": url, "title": "", "poster": "", "plot": "", "servers": [], "items": [], "type": "movie"}

    if not html:
        return result

    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
    if title_match:
        result["title"] = _clean_title(title_match.group(1))

    poster_match = re.search(r'<img[^>]+class="img-fluid"[^>]+src="([^"]+)"', html, re.I)
    if poster_match:
        result["poster"] = poster_match.group(1).replace("&amp;", "&")

    plot_match = re.search(r'<p[^>]+class="text-white[^>]*>(.*?)</p>', html, re.S | re.I)
    if not plot_match:
        plot_match = re.search(r'القصة\s*.*?<p[^>]*>(.*?)</p>', html, re.S | re.I)
    if plot_match:
        result["plot"] = _clean_title(plot_match.group(1))

    is_series = ("/series/" in (final_url or url) or "مسلسل" in result["title"]) and "/episode/" not in (final_url or url)

    if is_series:
        result["type"] = "series"
        seen_eps = set()

        episode_patterns = [
            r'<a[^>]+href=["\']([^"\']+/episode/[^"\']+)["\'][^>]*>(.*?)</a>',
            r'<a[^>]+href=["\']([^"\']*episode[^"\']*)["\'][^>]*>(.*?)</a>',
        ]

        for ep_pat in episode_patterns:
            html_eps = re.findall(ep_pat, html, re.S | re.I)
            for ep_url, ep_title in html_eps:
                full_url = urljoin(final_url or url, ep_url).replace("&amp;", "&")
                if full_url in seen_eps:
                    continue
                seen_eps.add(full_url)

                ep_title_clean = _clean_title(ep_title)
                if not ep_title_clean:
                    ep_title_clean = "حلقة {0}".format(len(result["items"]) + 1)

                result["items"].append({
                    "title": ep_title_clean,
                    "url": full_url,
                    "type": "episode",
                    "_action": "item"
                })

        return result

    for index, link in enumerate(_extract_watch_links(html), 1):
        label = "🌐 مشاهدة {}".format(index) if "/watch/" in link else "⬇️ تحميل {}".format(index)
        result["servers"].append({"name": label, "url": link, "type": "direct"})

    return result


def extract_stream(url):
    # For ak.sv/watch pages, fetch the page directly and grab the source
    if "ak.sv/watch/" in url or "akw.cam/watch/" in url or "akw-cdn" in url:
        html, final_url = fetch(url, referer=MAIN_URL)
        if html:
            match = re.search(r'<source[^>]+src="([^"]+)"[^>]*type="video/mp4"', html, re.I)
            if match:
                return match.group(1).replace("&amp;", "&"), None, MAIN_URL
            match = re.search(r'<source[^>]+src="([^"]+(?:m3u8|mp4)[^"]*)"', html, re.I)
            if match:
                return match.group(1).replace("&amp;", "&"), None, MAIN_URL
            match = re.search(r'"file"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"', html, re.I)
            if match:
                return match.group(1).replace("\\u0026", "&").replace("&amp;", "&"), None, MAIN_URL
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
`````

## File: extractors/arablionztv.py
`````python
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
`````

## File: extractors/arabseed.py
`````python
# -*- coding: utf-8 -*-
import base64
import json
import re
from .base import fetch, log, urljoin

MAIN_URL = "https://asd.pics/"
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
        log("ArabSeed: Missing AJAX token/post id")
        return []

    quality_url = urljoin(home_url, "get__quality__servers/")
    watch_server_url = urljoin(home_url, "get__watch__server/")
    results = []
    seen = set()

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
            log("ArabSeed: Failed to decode quality JSON")
            continue
        if data.get("type") != "success":
            continue

        # Some pages expose the default active server directly in `server`.
        direct_server = _decode_hidden_url(data.get("server", ""))
        if direct_server.startswith("http") and not any(host in direct_server for host in BLOCKED_HOSTS):
            key = (quality, direct_server)
            if key not in seen:
                seen.add(key)
                results.append(
                    {
                        "quality": quality,
                        "url": direct_server,
                        "name": _server_name(direct_server, "سيرفر عرب سيد"),
                    }
                )

        server_rows = re.findall(
            r'<li[^>]+data-post="([^"]+)"[^>]+data-server="([^"]+)"[^>]+data-qu="([^"]+)"[^>]*>.*?<span>([^<]+)</span>',
            data.get("html", ""),
            re.S,
        )
        for row_post_id, server_id, row_quality, label in server_rows:
            watch_body, _ = fetch(
                watch_server_url,
                post_data={
                    "post_id": row_post_id,
                    "quality": row_quality,
                    "server": server_id,
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

            server_url = _decode_hidden_url(watch_data.get("server", ""))
            if not server_url.startswith("http"):
                continue
            if any(host in server_url for host in BLOCKED_HOSTS):
                continue

            key = (row_quality, server_url)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "quality": row_quality,
                    "url": server_url,
                    "name": _server_name(server_url, label),
                }
            )

    results.sort(key=lambda item: (QUALITY_ORDER.get(item["quality"], 9), _server_priority(item["url"]), item["name"]))
    return results


def get_categories():
    return [
        {"title": "🌍 أفلام أجنبي", "url": urljoin(MAIN_URL, "category/foreign-movies-12/"), "type": "category", "_action": "category"},
        {"title": "🇪🇬 أفلام عربي", "url": urljoin(MAIN_URL, "category/arabic-movies-12/"), "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أجنبي", "url": urljoin(MAIN_URL, "category/foreign-series-5/"), "type": "category", "_action": "category"},
        {"title": "🇸🇦 مسلسلات عربي", "url": urljoin(MAIN_URL, "category/arabic-series-10/"), "type": "category", "_action": "category"},
        {"title": "🎭 مسلسلات انمي", "url": urljoin(MAIN_URL, "category/anime-series-1/"), "type": "category", "_action": "category"},
        {"title": "🎮 عروض مصارعة", "url": urljoin(MAIN_URL, "category/wwe-shows-1/"), "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, _ = fetch(url)
    if not html:
        return []

    items = []
    seen = set()
    # Match various card/block containers
    blocks = re.findall(r'<div[^>]+class=[\"\'](?:recent--block|post--block|item)[^>]*>(.*?)</div>', html, re.S | re.IGNORECASE)
    if not blocks:
        # Fallback to general link/img pattern if no blocks found
        blocks = re.findall(r'(<a[^>]+href=[\"\'][^>]*>.*?<img[^>]+(?:data-src|src)=[\"\'][^>]*>.*?</a>)', html, re.S | re.IGNORECASE)

    for block in blocks:
        m = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]+title=["\']([^"\']+)["\'][^>]*>', block, re.S)
        if not m:
            m = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?<img[^>]+alt=["\']([^"\']+)["\']', block, re.S)
        if m:
            link, title = m.groups()
            img_m = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', block)
            img = img_m.group(1) if img_m else ""
            
            if link in seen or "/category/" in link:
                continue
            seen.add(link)
            
            title = _clean_title(title)
            item_type = "series" if "/series-" in link or "مسلسل" in title else "movie"
            items.append({"title": title, "url": link, "image": img, "type": item_type, "_action": "details"})

    if not items:
        # Final fallback to the old regex if block parsing failed completely
        regex = r'<a[^>]+href=["\']([^"\']+)["\'][^>]+title=["\']([^"\']+)["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']'
        for link, title, img in re.findall(regex, html, re.S | re.IGNORECASE):
            if link in seen or "/category/" in link: continue
            seen.add(link)
            item_type = "series" if "/series-" in link or "مسلسل" in title else "movie"
            items.append({"title": title.strip(), "url": link, "image": img, "type": item_type, "_action": "details"})

    next_page = re.search(r'href="([^"]+/page/\d+/)"', html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page.group(1), "type": "category", "_action": "category"})
    return items


def get_page(url):
    html, final_url = fetch(url)
    if not html:
        return {"title": "Error", "servers": []}

    result = {
        "url": final_url or url,
        "title": "",
        "plot": "",
        "poster": "",
        "rating": "",
        "year": "",
        "servers": [],
        "items": [],
    }

    title_match = re.search(r'og:title[^>]+content="([^"]+)"', html) or re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    if title_match:
        result["title"] = _clean_title(title_match.group(1).split("-")[0])

    poster_match = re.search(r'og:image"[^>]+content="([^"]+)"', html)
    if poster_match:
        result["poster"] = poster_match.group(1)

    plot_match = re.search(r'name="description"[^>]+content="([^"]+)"', html)
    if plot_match:
        result["plot"] = plot_match.group(1)

    is_series = any(marker in (final_url or url) for marker in ("/series-", "/season-", "/episode-")) or "مسلسل" in result["title"]

    watch_url = (final_url or url).rstrip("/") + "/watch/"
    watch_match = re.search(r'href="([^"]+/watch/)"', html)
    if watch_match:
        watch_url = watch_match.group(1)

    watch_html, watch_final = fetch(watch_url, referer=final_url or url)
    if not watch_html:
        watch_html, watch_final = html, (final_url or url)

    for server in _collect_ajax_servers(watch_html, watch_final or watch_url):
        result["servers"].append(
            {
                "name": "[{}p] {}".format(server["quality"], server["name"]),
                "url": server["url"],
                "type": "direct",
            }
        )

    if is_series:
        seen_eps = set()
        blocks_html = " ".join(re.findall(r'<div[^>]+class=[\"\'](?:Blocks-Episodes|Episode--List|seasons--episodes|Blocks-Container|List--Episodes|List--Seasons|episodes)[^>]*>(.*?)</section>', html, re.S | re.I)) or html
        for ep_url, ep_title in re.findall(r'<a[^>]+href="(https?://[^/]+/[^"]+)"[^>]+title="([^"]+)"', blocks_html, re.S):
            if ("الحلقة" not in ep_title and "حلقة" not in ep_title) or ep_url in seen_eps:
                continue
            if "series-" not in ep_url and "-season" not in ep_url and "-%d8%a7%d9%84%d9%85%d9%88%d8%b3%d9%85-" not in ep_url.lower():
                # Some basic protection against unrelated side-bar items if blocks_html is just `html`.
                continue
            seen_eps.add(ep_url)
            result["items"].append({"title": ep_title.strip(), "url": ep_url, "type": "episode", "_action": "details"})

    if not result["servers"]:
        for fallback in re.findall(r'data-(?:link|url|iframe|src|href)="([^"]+)"', watch_html or "", re.S):
            fallback = _decode_hidden_url(fallback)
            if not fallback.startswith("http"):
                continue
            if any(host in fallback for host in BLOCKED_HOSTS):
                continue
            if fallback not in [srv["url"] for srv in result["servers"]]:
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
Hosts supported: Streamtape, Doodstream, Vidbom, Upstream, Govid, Uqload, Mixdrop, Voe, etc.
"""

import re
import json
import time
import random
# FIX: removed duplicate standalone "import urllib.request" — only the from-import below is needed
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor, HTTPSHandler
from urllib.parse import urljoin, urlparse, unquote, urlencode
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

# Global session/opener with cookie support
_opener = None

def log(msg):
    """Central logging for device debugging"""
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = "[{}] {}\n".format(ts, msg)
        with open("/tmp/arabicplayer.log", "a") as f:
            f.write(line)
        print("[ArabicPlayer] {}".format(msg))
    except:
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

    _opener = build_opener(
        HTTPCookieProcessor(cj),
        HTTPSHandler(context=ctx)
    )

    return _opener


def _decode_response_body(raw, info):
    ce = info.get('Content-Encoding', '').lower()
    if 'gzip' in ce:
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    elif 'deflate' in ce:
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except Exception:
            raw = zlib.decompress(raw)
    elif 'br' in ce and brotli is not None:
        raw = brotli.decompress(raw)

    charset = 'utf-8'
    ctype = info.get('Content-Type', '').lower()
    if 'charset=' in ctype:
        charset = ctype.split('charset=')[-1].split(';')[0].strip()

    try:
        return raw.decode(charset)
    except Exception:
        try:
            return raw.decode('utf-8', errors='ignore')
        except Exception:
            return raw.decode('latin-1', errors='ignore')

def fetch(url, referer=None, extra_headers=None, post_data=None):
    """Stable fetch: robust headers for ACE/Bot bypass and SSL handle"""
    try:
        opener = _get_opener()
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not referer:
            if "wecima" in domain or "mycima" in domain: referer = "https://wecima.click/"
            elif "fasel" in domain: referer = "https://www.faselhd.cam/"
            elif "topcinema" in domain: referer = "https://topcinemaa.com/"
            elif "shaheed" in domain: referer = "https://shaheeid4u.net/"
            elif "egydead" in domain or "x7k9f.sbs" in domain: referer = "https://x7k9f.sbs/"
            else: referer = "{}://{}/".format(parsed.scheme, domain)

        headers = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
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
        if any(x in url.lower() for x in ["ajax", "get__watch", "api/"]):
            headers.update({
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors"
            })
        if extra_headers: headers.update(extra_headers)

        data = post_data
        if data and isinstance(data, dict):
            data = urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif data and isinstance(data, str):
            data = data.encode("utf-8")

        log("Fetching: {}".format(url))
        req = Request(url, headers=headers, data=data)
        with opener.open(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            final_url = resp.geturl()
            info = resp.info()

            if "alliance4creativity.com" in final_url.lower() or "watch-it-legally" in final_url.lower():
                log("!!! ALERT: ACE Redirect detected for {} !!!".format(url))
                return None, final_url
            html = _decode_response_body(raw, info)

            log("Fetch Success: {} ({} bytes)".format(final_url, len(html)))
            return html, final_url
    except HTTPError as e:
        try:
            raw = e.read()
            html = _decode_response_body(raw, e.info()) if raw else ""
            log("Fetch HTTPError: {} -> {} {} ({} bytes)".format(url, e.code, e.reason, len(html)))
        except Exception:
            log("Fetch HTTPError: {} -> {} {}".format(url, getattr(e, "code", "?"), getattr(e, "reason", e)))
        return None, url
    except URLError as e:
        log("Fetch URLError: {} -> {}".format(url, e))
        global _opener
        _opener = None
        return None, url
    except Exception as e:
        log("Fetch Error: {} -> {}".format(url, e))
        return None, url


def extract_iframes(html, base_url=""):
    """Return list of iframe src URLs from HTML"""
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    result = []
    for src in iframes:
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            parsed = urlparse(base_url)
            src = parsed.scheme + "://" + parsed.netloc + src
        if src.startswith("http"):
            result.append(src)
    return result


def find_m3u8(html):
    """Find m3u8 URL in page source with robust patterns"""
    if not html: return None
    patterns = [
        r'["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'hls\.loadSource\(["\']([^"\']+)["\']',
        r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'data-url=["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'data-src=["\']([^"\']+\.m3u8[^"\']*)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").strip()
            if url.startswith("//"): url = "https:" + url
            if url.startswith("http") and ".m3u8" in url:
                return url
    return None


def find_mp4(html):
    """Find mp4 URL in page source with robust patterns"""
    if not html: return None
    patterns = [
        r'["\']([^"\']+\.mp4[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
        r'data-url=["\']([^"\']+\.mp4[^"\']*)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").strip()
            if url.startswith("//"): url = "https:" + url
            if url.startswith("http") and ".mp4" in url:
                return url
    return None


def _best_media_url(text):
    """Pick the best visible video source from plain or unpacked JS."""
    candidates = []
    seen = set()
    patterns = [
        r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
        r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)',
    ]

    def score(url):
        lowered = url.lower()
        if "2160" in lowered or "4k" in lowered:
            return 5000
        if "1080" in lowered or "fhd" in lowered:
            return 4000
        if "720" in lowered or "hd" in lowered:
            return 3000
        if "480" in lowered:
            return 2000
        if "360" in lowered:
            return 1000
        if "240" in lowered or "sd" in lowered:
            return 500
        if ".m3u8" in lowered:
            return 3500
        return 100

    for pat in patterns:
        for match in re.findall(pat, text or "", re.I):
            url = match.replace("\\/", "/").replace("&amp;", "&")
            if url in seen:
                continue
            seen.add(url)
            candidates.append((score(url), url))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _extract_packer_blocks(html):
    """Return likely Dean Edwards packer blocks even when regex would stop early."""
    blocks = []
    marker = "eval(function(p,a,c,k,e,d){"
    tail = ".split('|')))"
    pos = 0
    while True:
        start = (html or "").find(marker, pos)
        if start == -1:
            break
        end = (html or "").find(tail, start)
        if end == -1:
            break
        blocks.append(html[start:end + len(tail)])
        pos = end + len(tail)
    return blocks


def decode_packer(packed):
    """Decodes Dean Edwards Packer compressed JS"""
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

        def e(c):
            result = ""
            while True:
                result = "0123456789abcdefghijklmnopqrstuvwxyz"[c % a] + result
                c = c // a
                if c == 0:
                    break
            return result

        d = {}
        for i in range(c):
            d[e(i)] = k[i] or e(i)

        return re.sub(r'\b(\w+)\b', lambda x: d.get(x.group(1), x.group(1)), p)
    except:
        return ""


def find_packed_links(html):
    """Find video links inside Packer-obfuscated JS"""
    evals = _extract_packer_blocks(html)
    if not evals:
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
    for ev in evals:
        dec = decode_packer(ev)
        if dec:
            res = find_m3u8(dec) or find_mp4(dec)
            if res: return res
    return None


# ─── Video Host Resolvers ────────────────────────────────────────────────────

def resolve_streamtape(url):
    """Extract from streamtape.com"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        m = re.search(r"robotlink\)\.innerHTML = '([^']+)'\s*\+\s*'([^']+)'", html)
        if m:
            link = m.group(1) + m.group(2)
            link = link.replace("//streamtape.com", "https://streamtape.com")
            if not link.startswith("http"):
                link = "https:" + link
            return link
        m = re.search(r'(/get_video\?[^"\'&\s]+)', html)
        if m:
            return "https://streamtape.com" + m.group(1)
    except Exception:
        pass
    return None


def resolve_doodstream(url):
    """Extract from dood.* / doodstream / dsvplay and variants"""
    try:
        dood_base = "https://dood.re"
        for pat, domain in [
            (r'dood\.[a-z]+', 'dood.re'),
            (r'dsvplay\.[a-z]+', 'dood.re'),
            (r'd0o0d\.[a-z]+', 'dood.re'),
        ]:
            url_try = re.sub(pat, domain, url)
            html, final_url = fetch(url_try)
            if html:
                break
        else:
            html, final_url = fetch(url)
        if not html:
            return None

        m = re.search(r'\$\.get\(["\'](/pass_md5/[^"\']+)["\']', html)
        if not m:
            m = re.search(r'pass_md5/([^"\'\.\s&]+)', html)
            if m:
                pass_path = "/pass_md5/" + m.group(1)
            else:
                return None
        else:
            pass_path = m.group(1)

        pass_url = dood_base + pass_path
        token_html, _ = fetch(pass_url, referer=url)
        if not token_html:
            return None
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        rand = "".join(random.choice(chars) for _ in range(10))
        return token_html.strip() + rand + "?token=" + pass_path.split("/")[-1] + "&expiry=" + str(int(time.time() * 1000))
    except Exception:
        pass
    return None


def resolve_vidbom(url):
    """Extract from vidbom.com / vidshare.tv and similar"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        m3u8 = find_m3u8(html)
        if m3u8:
            return m3u8
        mp4 = find_mp4(html)
        return mp4
    except Exception:
        pass
    return None


def resolve_uqload(url):
    """Extract from uqload.co"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        m = re.search(r'sources:\s*\["([^"]+)"\]', html)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def resolve_govid(url):
    """Extract from govid.me"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_upstream(url):
    """Extract from upstream.to"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_mixdrop(url):
    """Extract from mixdrop.co / .top (handles Packer)"""
    try:
        html, _ = fetch(url)
        if not html:
            return None

        m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', html)
        if m:
            link = m.group(1)
            return ("https:" + link) if link.startswith("//") else link

        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
        for ev in evals:
            dec = decode_packer(ev)
            if dec:
                m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', dec)
                if m:
                    link = m.group(1)
                    return ("https:" + link) if link.startswith("//") else link
    except Exception:
        pass
    return None

def resolve_voe(url):
    """Extract from voe.sx — uses obfuscated JS"""
    try:
        html, final = fetch(url, referer="https://x7k9f.sbs/")
        if not html:
            return None
        for pat in [r"'hls'\s*:\s*'([^']+)'", r'"hls"\s*:\s*"([^"]+)"',
                    r"sources\s*=\s*\[\s*\{[^}]*file\s*:\s*'([^']+)'"]:
            m = re.search(pat, html)
            if m:
                return m.group(1)
        import base64
        for enc in re.finditer(r"atob\(['\"]([A-Za-z0-9+/=]+)['\"]\)", html):
            try:
                dec = base64.b64decode(enc.group(1) + "==").decode("utf-8", errors="ignore")
                if "http" in dec:
                    mm = re.search(r"(https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*)", dec)
                    if mm:
                        return mm.group(1)
            except Exception:
                pass
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None

def resolve_streamruby(url):
    """Extract from streamruby.com / stmruby.com"""
    try:
        html, _ = fetch(url)
        if not html: return None
        m = find_m3u8(html) or find_mp4(html)
        if m: return m
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
        for ev in evals:
            dec = decode_packer(ev)
            if dec:
                m = find_m3u8(dec) or find_mp4(dec)
                if m: return m
    except: pass
    return None

def resolve_hgcloud(url):
    """Extract from hgcloud.to / masukestin.me"""
    try:
        html, _ = fetch(url)
        if not html: return None
        return find_m3u8(html) or find_mp4(html)
    except: pass
    return None


def resolve_vidtube(url):
    """Extract direct MP4/HLS from vidtube.one embeds."""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        if "restricted for this domain" in html.lower():
            html = None
            for _ in range(2):
                html, _ = fetch(url, referer="https://topcinema.fan/")
                if html:
                    break
            if not html:
                return None

        direct = _best_media_url(html)
        if direct:
            return direct

        for ev in _extract_packer_blocks(html):
            dec = decode_packer(ev)
            if not dec:
                continue
            direct = _best_media_url(dec)
            if direct:
                return direct
    except Exception:
        pass
    return None

HOST_RESOLVERS = {
    "streamtape": resolve_streamtape,
    "dood":       resolve_doodstream,
    "dsvplay":    resolve_doodstream,
    "vidbom":     resolve_vidbom,
    "vidshare":   resolve_vidbom,
    "uqload":     resolve_uqload,
    "govid":      resolve_govid,
    "upstream":   resolve_upstream,
    "mixdrop":    resolve_mixdrop,
    "voe":        resolve_voe,
    "streamruby": resolve_streamruby,
    "hgcloud":    resolve_hgcloud,
    "masukestin": resolve_hgcloud,
    "vidtube":    resolve_vidtube,
}

def resolve_generic_embed(url):
    """Generic resolver for embed hosts — tries m3u8/mp4 directly then iframes"""
    try:
        html, final = fetch(url, referer="https://x7k9f.sbs/")
        if not html:
            return None
        result = find_m3u8(html) or find_mp4(html)
        if result:
            return result
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
        for ev in evals:
            dec = decode_packer(ev)
            if dec:
                result = find_m3u8(dec) or find_mp4(dec)
                if result:
                    return result
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        for ifr in iframes:
            if ifr.startswith("//"): ifr = "https:" + ifr
            h2, _ = fetch(ifr, referer=url)
            if h2:
                result = find_m3u8(h2) or find_mp4(h2)
                if result:
                    return result
    except Exception:
        pass
    return None


# ─── Multi-Provider Resolvers (TMDB Based) ──────────────────────────────────

def _get_stream_moviesapi(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://moviesapi.club/api/v1/movies/{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://moviesapi.club/api/v1/tv/{}/{}/{}".format(tmdb_id, s, e)
    body, _ = fetch(url, extra_headers={"Accept": "application/json"})
    if not body: return None
    try:
        data = json.loads(body)
        sources = data.get("sources") or []
        for src in sources:
            f = src.get("file") or src.get("url") or ""
            if ".m3u8" in f: return f
        for src in sources:
            f = src.get("file") or src.get("url") or ""
            if f.startswith("http"): return f
    except: pass
    return find_m3u8(body) or find_mp4(body)

def _get_stream_multiembed(tmdb_id, m_type, season=None, episode=None):
    url = "https://multiembed.mov/directstream.php?video_id={}&tmdb=1".format(tmdb_id)
    if season and episode: url += "&s={}&e={}".format(season, episode)
    html, final = fetch(url)
    if not html: return None
    if final != url and final.startswith("http"):
        if ".m3u8" in final: return final
        h2, _ = fetch(final, referer=url)
        if h2:
            m = find_m3u8(h2)
            if m: return m
    return find_m3u8(html) or find_mp4(html)

def _get_stream_superembed(tmdb_id, m_type, season=None, episode=None):
    url = "https://getsuperembed.link/?video_id={}&tmdb=1".format(tmdb_id)
    if season and episode: url += "&s={}&e={}".format(season, episode)
    body, final = fetch(url)
    if not body: return None
    body = body.strip()
    if body.startswith("http") and len(body) < 500:
        h2, _ = fetch(body, referer=url)
        if h2: return find_m3u8(h2) or find_mp4(h2)
        return body
    try:
        data = json.loads(body)
        for k in ["url", "link", "src", "stream"]:
            if k in data and data[k]: return data[k]
    except: pass
    mm = re.search(r'(https?://[^\s"\'<>]{10,})', body)
    return mm.group(1) if mm else None

def _get_stream_2embed(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://www.2embed.cc/embedtmdb/{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://www.2embed.cc/embedtvtmdb/{}&s={}&e={}".format(tmdb_id, s, e)
    html, _ = fetch(url)
    if not html: return None
    for iframe in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
        if iframe.startswith("//"): iframe = "https:" + iframe
        if iframe.startswith("http"):
            h2, _ = fetch(iframe, referer=url)
            if h2:
                m = find_m3u8(h2)
                if m: return m
    return find_m3u8(html) or find_mp4(html)

def _get_stream_autoembed(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://autoembed.cc/movie/tmdb-{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://autoembed.cc/tv/tmdb-{}-{}-{}".format(tmdb_id, s, e)
    html, _ = fetch(url)
    if not html: return None
    return find_m3u8(html) or find_mp4(html)

def _get_stream_vidsrc(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://vidsrc.me/embed/movie/{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://vidsrc.me/embed/tv/{}/{}/{}".format(tmdb_id, s, e)
    html, _ = fetch(url, referer="https://vidsrc.me/")
    if not html:
        return None
    m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    if m:
        iframe_url = m.group(1)
        if iframe_url.startswith("//"): iframe_url = "https:" + iframe_url
        h2, _ = fetch(iframe_url, referer=url)
        if h2:
            return find_m3u8(h2) or find_mp4(h2)
    return find_m3u8(html) or find_mp4(html)

_PREMIUM_METHODS = {
    "moviesapi":   _get_stream_moviesapi,
    "multiembed":  _get_stream_multiembed,
    "superembed":  _get_stream_superembed,
    "2embed":      _get_stream_2embed,
    "autoembed":   _get_stream_autoembed,
    "vidsrc":      _get_stream_vidsrc,
}

def get_premium_servers(m_type, tmdb_id, season=None, episode=None):
    """Return a list of premium multi-provider servers as dicts"""
    res = []
    suffix = ""
    if season and episode:
        suffix = ":{}:{}".format(season, episode)

    res.append({"name": "Premium: AutoEmbed 🚀",  "url": "autoembed://{}:{}{}".format(m_type, tmdb_id, suffix)})
    res.append({"name": "Premium: VidSrc 🔥",     "url": "vidsrc://{}:{}{}".format(m_type, tmdb_id, suffix)})
    return res

# ─── Host Dispatcher ─────────────────────────────────────────────────────────

def resolve_host(url, referer=None):
    """Auto-detect host and resolve to direct stream URL"""
    m = re.match(r'(\w+)://(movie|series|tv|episode):(\d+)(?::(\d+):(\d+))?', url)
    if m:
        method_name, m_type, tmdb_id, season, episode = m.groups()
        m_type = "movie" if m_type in ("movie", "film") else "series"
        if method_name in _PREMIUM_METHODS:
            return _PREMIUM_METHODS[method_name](tmdb_id, m_type, season, episode)
        elif method_name == "auto":
            for name, func in _PREMIUM_METHODS.items():
                try:
                    res = func(tmdb_id, m_type, season, episode)
                    if res: return res
                except: pass
            return None

    domain = urlparse(url).netloc.lower()
    log("Resolving host: {} (URL: {})".format(domain, url))
    if "streamruby" in domain:
        return resolve_streamruby(url)
    if "hgcloud" in domain or "masukestin" in domain:
        return resolve_hgcloud(url)

    for key, resolver in HOST_RESOLVERS.items():
        if key in domain:
            log("Using resolver: {}".format(key))
            return resolver(url)

    log("Using generic fallback for: {}".format(domain))
    html, final_url = fetch(url, referer=referer or url)
    if not html:
        log("Generic fallback failed: No HTML")
        return None
    res = find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    if res:
        log("Generic fallback success: {}".format(res))
        return res

    evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
    log("Found {} packed scripts".format(len(evals)))
    for ev in evals:
        dec = decode_packer(ev)
        if dec:
            r = find_m3u8(dec) or find_mp4(dec)
            if r:
                log("Packer success: {}".format(r))
                return r

    log("All resolution attempts failed for: {}".format(url))
    return None


def resolve_iframe_chain(url, referer=None, depth=0, max_depth=6):
    """
    Follows a chain of iframes/redirects to find a playable stream.
    Supports src, data-src, data-url attributes.
    """
    if depth > max_depth: return None, ""

    html, final_url = fetch(url, referer=referer)
    if not html: return None, ""

    domain = urlparse(final_url or url).netloc.lower()

    stream = find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    if stream: return stream, domain

    iframes = re.findall(r'<(?:iframe|embed|frame)[^>]+(?:src|data-src|data-url)=["\']([^"\']+)["\']', html, re.I)
    for iframe in iframes:
        if iframe.startswith("//"): iframe = "https:" + iframe
        if not iframe.startswith("http"):
            if iframe.startswith("/"):
                p = urlparse(final_url or url)
                iframe = "{}://{}{}".format(p.scheme, p.netloc, iframe)
            else:
                continue

        if any(x in iframe.lower() for x in ["facebook", "twitter", "googletag", "ads", "analytics", "doubleclick"]):
            continue

        res, h = resolve_iframe_chain(iframe, referer=url, depth=depth+1, max_depth=max_depth)
        if res: return res, h

    return None, ""


def extract_stream(url):
    """Standard wrapper for plugin to get (URL, Quality, FinalReferer)"""
    log("--- Starting Extraction for: {} ---".format(url))
    raw_url = (url or "").strip()
    if not raw_url:
        return None, "", url

    piped_headers = {}
    main_url = raw_url
    if "|" in raw_url:
        main_url, raw_headers = raw_url.split("|", 1)
        for part in raw_headers.split("&"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            piped_headers[key.strip()] = value.strip()

    lower_main_url = main_url.lower()
    if main_url.startswith("http") and any(ext in lower_main_url for ext in (".m3u8", ".mp4", ".mkv", ".mp3")):
        referer = piped_headers.get("Referer")
        if not referer:
            parsed = urlparse(main_url)
            referer = "{}://{}/".format(parsed.scheme, parsed.netloc)
        log("Extraction DIRECT URL shortcut: {}".format(main_url))
        q = "1080p" if "1080" in lower_main_url else ("720p" if "720" in lower_main_url else "HD")
        return raw_url, q, referer

    _, final_referer = fetch(main_url, referer=piped_headers.get("Referer"))
    if not final_referer:
        return None, "", main_url

    stream = resolve_host(main_url, referer=piped_headers.get("Referer"))
    if not stream:
        log("Initial resolve_host failed, trying resolve_iframe_chain")
        stream, h = resolve_iframe_chain(main_url, referer=piped_headers.get("Referer"), depth=0)

    if stream:
        log("Extraction SUCCESS: {}".format(stream))
        q = "1080p" if "1080" in stream else ("720p" if "720" in stream else "HD")
        return stream, q, final_referer

    log("Extraction FINAL FAILURE for: {}".format(main_url))
    return None, "", final_referer
`````

## File: extractors/egydead.py
`````python
# -*- coding: utf-8 -*-
"""
EgyDead extractor for the current Next.js site.
Domain: egydead.today
"""

import json
import base64
import re
import sys

from .base import fetch, log, _extract_packer_blocks, decode_packer

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urljoin
    from html import unescape as html_unescape
else:
    from urllib import quote_plus
    from urlparse import urljoin
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape


DOMAINS = [
    "https://www.egydead.today/",
    "https://egydead.today/",
]
BASE_URL = None
MAX_EPISODES = 350
VIDTUBE_QUALITY_LABELS = {
    "h": "720p",
    "n": "480p",
    "l": "360p",
    "x": "1080p",
}
# FIX: removed unused VIDTUBE_QUALITY_ORDER constant
FORCE_TOPCINEMA_API_FIRST = True
DISABLE_VIDKING_WHEN_TOPCINEMA_EXISTS = True


def _get_base():
    global BASE_URL
    if BASE_URL:
        return BASE_URL
    BASE_URL = DOMAINS[0]
    return BASE_URL


def _strip_html(text):
    if not text:
        return ""
    text = html_unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def _img(path, size="w342"):
    if not path:
        return ""
    path = str(path).strip()
    if path.startswith("http"):
        return path
    if path.startswith("//"):
        return "https:" + path
    if not path.startswith("/"):
        path = "/" + path
    return "https://image.tmdb.org/t/p/{0}{1}".format(size, path)


def _extract_next_data(html):
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception as exc:
        log("EgyDead: __NEXT_DATA__ parse failed: {}".format(exc))
        return {}


def _clean_title_text(text):
    text = _strip_html(text)
    if not text:
        return ""
    text = text.replace("EgyDead", " ")
    text = re.sub(r"\s*[-|]\s*EgyDead.*$", "", text, flags=re.I)
    year_split = re.split(r"\(\s*(?:19|20|21)\d{2}\s*\)|\b(?:19|20|21)\d{2}\b", text, 1)
    if year_split and year_split[0].strip():
        text = year_split[0]
    text = re.sub(r"\b(?:مترجم(?:ة)?|مدبلج(?:ة)?|اون لاين|أون لاين|كامل)\b", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" -|")


def _meta_description(html):
    if not html:
        return ""
    for pattern in (
        r'property="og:description"[^>]+content="([^"]+)"',
        r'name="description"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:description"',
        r'<meta[^>]+content="([^"]+)"[^>]+name="description"',
    ):
        match = re.search(pattern, html, re.I)
        if match:
            text = _strip_html(match.group(1))
            if text:
                return text
    return ""


def _meta_title(html):
    if not html:
        return ""
    for pattern in (
        r'property="og:title"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:title"',
        r'<title>(.*?)</title>',
        r'<h1[^>]*>(.*?)</h1>',
    ):
        match = re.search(pattern, html, re.S | re.I)
        if match:
            text = _clean_title_text(match.group(1))
            if text:
                return text
    return ""


def _meta_image(html):
    if not html:
        return ""
    for pattern in (
        r'property="og:image"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"',
    ):
        match = re.search(pattern, html, re.I)
        if match:
            image = match.group(1).strip()
            if image:
                return _img(image)
    return ""


def _json_ld_object(html):
    scripts = re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        html or "",
        re.S | re.I,
    )
    for script in scripts:
        if not script:
            continue
        try:
            data = json.loads(script)
        except Exception:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") in ("Movie", "TVSeries", "TVEpisode"):
                    return item
        if isinstance(data, dict):
            if data.get("@type") in ("Movie", "TVSeries", "TVEpisode"):
                return data
            graph = data.get("@graph") or []
            for item in graph:
                if isinstance(item, dict) and item.get("@type") in ("Movie", "TVSeries", "TVEpisode"):
                    return item
    return {}


def _year_from_text(text):
    match = re.search(r'\b(19\d{2}|20\d{2}|21\d{2})\b', text or "")
    return match.group(1) if match else ""


def _page_props(data):
    return (((data or {}).get("props") or {}).get("pageProps") or {})


def _year_from_entry(entry):
    value = (
        entry.get("release_date")
        or entry.get("first_air_date")
        or entry.get("air_date")
        or ""
    )
    value = str(value)
    return value[:4] if len(value) >= 4 else ""


def _rating_text(value):
    try:
        rating = float(value)
        if rating <= 0:
            return ""
        return "{0:.1f}".format(rating)
    except Exception:
        return ""


def _unique_titles(*values):
    seen = set()
    res = []
    for value in values:
        value = _strip_html(value)
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        res.append(value)
    return res


def _title_variants(*values):
    variants = []
    seen = set()
    for value in values:
        base = _clean_title_text(value)
        for candidate in (
            base,
            re.sub(r"[:|_\-]+", " ", base or "").strip(),
            re.sub(r"\b(?:part|season|episode)\b.*$", "", (base or ""), flags=re.I).strip(),
        ):
            candidate = re.sub(r"\s+", " ", candidate or "").strip(" -|")
            if not candidate:
                continue
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            variants.append(candidate)
    return variants


def _detail_result(url, title, poster, plot, year, rating, item_type):
    return {
        "url": url,
        "title": title or "",
        "poster": poster or "",
        "plot": plot or "",
        "year": year or "",
        "rating": rating or "",
        "servers": [],
        "items": [],
        "type": item_type,
    }


def _entry_to_item(entry, forced_type=None):
    if not isinstance(entry, dict):
        return None

    media_type = forced_type or entry.get("media_type")
    if media_type not in ("movie", "tv"):
        if entry.get("title") or entry.get("release_date"):
            media_type = "movie"
        else:
            media_type = "tv"

    item_id = entry.get("id")
    title = _strip_html(entry.get("title") or entry.get("name") or "")
    if not item_id or not title:
        return None

    if media_type == "movie":
        rel_url = "/movie/{0}".format(item_id)
        item_type = "movie"
    else:
        rel_url = "/tv/{0}".format(item_id)
        item_type = "series"

    return {
        "title": title,
        "url": urljoin(_get_base(), rel_url),
        "poster": _img(entry.get("poster_path") or entry.get("poster")),
        "type": item_type,
        "_action": "details",
    }


def _items_from_page_props(props):
    items = []
    seen = set()

    for entry in props.get("results") or []:
        item = _entry_to_item(entry, entry.get("media_type"))
        if item and item["url"] not in seen:
            seen.add(item["url"])
            items.append(item)

    for entry in props.get("initialMovies") or []:
        item = _entry_to_item(entry, "movie")
        if item and item["url"] not in seen:
            seen.add(item["url"])
            items.append(item)

    for entry in props.get("initialSeries") or []:
        item = _entry_to_item(entry, "tv")
        if item and item["url"] not in seen:
            seen.add(item["url"])
            items.append(item)

    return items


def _parse_cards(html):
    items = []
    seen = set()
    base = _get_base()
    regex = (
        r'<a[^>]+class="[^"]*movie-card[^"]*"[^>]+href="([^"]+)"[^>]*>'
        r'(.*?)</a>'
    )
    for href, block in re.findall(regex, html, re.S | re.I):
        if "/movie/" not in href and "/tv/" not in href:
            continue
        full_url = urljoin(base, href)
        if full_url in seen:
            continue

        mtype = "movie" if "/movie/" in href else "series"
        title = ""
        poster = ""

        m = re.search(r'alt="([^"]+)"', block, re.I)
        if m:
            title = _strip_html(m.group(1))
        if not title:
            m = re.search(r'class="card-title"[^>]*>(.*?)</div>', block, re.S | re.I)
            if m:
                title = _strip_html(m.group(1))

        m = re.search(r'<img[^>]+src="([^"]+)"', block, re.I)
        if m:
            poster = _img(m.group(1))

        if not title:
            continue

        seen.add(full_url)
        items.append(
            {
                "title": title,
                "url": full_url,
                "poster": poster,
                "type": mtype,
                "_action": "details",
            }
        )
    return items


def _fetch_json(url):
    body, _ = fetch(
        url,
        extra_headers={
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    if not body:
        return None
    try:
        return json.loads(body)
    except Exception as exc:
        log("EgyDead: JSON parse failed for {}: {}".format(url, exc))
        return None


def _topcinema_lookup(content_type, season, episode, year, titles):
    base = _get_base().rstrip("/")
    title_variants = _title_variants(*(titles or []))
    if not title_variants:
        title_variants = _unique_titles(*(titles or []))

    for title in title_variants:
        movie_years = [year] if year else []
        if content_type == "movie":
            movie_years.append("")
        else:
            movie_years = [""]

        for movie_year in movie_years:
            api_url = "{0}/api/topcinema-links?title={1}&type={2}".format(
                base,
                quote_plus(title),
                content_type,
            )
            if content_type == "movie" and movie_year:
                api_url += "&year={0}".format(quote_plus(movie_year))
            if content_type == "tv":
                api_url += "&season={0}&episode={1}".format(season or 1, episode or 1)

            data = _fetch_json(api_url)
            if data and data.get("success") and data.get("iframe_url"):
                return data
    return None


def _watch_url(content_type, tmdb_id, season=None, episode=None):
    base = _get_base().rstrip("/")
    if content_type == "movie":
        return "{0}/watch/movie/{1}".format(base, tmdb_id)
    return "{0}/watch/tv/{1}/{2}/{3}".format(base, tmdb_id, season or 1, episode or 1)


def _extract_player_src(html):
    m = re.search(r'<iframe[^>]+id="player"[^>]+src="([^"]+)"', html, re.I)
    if not m:
        m = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.I)
    if not m:
        return ""
    return m.group(1).strip()


def _extract_player_sources(html):
    out = []
    seen = set()
    if not html:
        return out

    patterns = [
        r'<iframe[^>]+src="([^"]+)"',
        r"<iframe[^>]+src='([^']+)'",
        r'data-src="([^"]+)"',
        r"data-src='([^']+)'",
        r'"src"\s*:\s*"([^"]+embed[^"]+)"',
        r"'src'\s*:\s*'([^']+embed[^']+)'",
        r'(https?://[^\s"\']+(?:vidtube|vidking|viking)[^\s"\']*)',
    ]
    for pat in patterns:
        for u in re.findall(pat, html, re.I | re.S):
            u = (u or "").replace("\\/", "/").strip()
            if not u:
                continue
            if u.startswith("//"):
                u = "https:" + u
            if u not in seen:
                out.append(u)
                seen.add(u)
    return out


def _vidtube_quality_servers(embed_url):
    html, _ = fetch(embed_url, referer="https://topcinema.fan/")
    if not html:
        html, _ = fetch(embed_url, referer="https://topcinema.fan/")
    if not html:
        html, _ = fetch(embed_url, referer=_get_base())
    if not html:
        return []

    texts = [html]
    for ev in _extract_packer_blocks(html):
        dec = decode_packer(ev)
        if dec:
            texts.append(dec)

    found = {}

    def _store(code, media_url):
        code = (code or "").lower().strip()
        media_url = (media_url or "").replace("\\/", "/").replace("&amp;", "&").strip()
        if not code or not media_url or code in found:
            return
        found[code] = media_url

    for text in texts:
        if not text:
            continue

        for media_url in re.findall(r'(https?://[^\s"\'<>]+(?:\.mp4|\.m3u8)[^\s"\'<>]*)', text, re.I):
            q = ""
            qmatch = re.search(r'[_/\-]([xhln])(?:\.mp4|\.m3u8)', media_url, re.I)
            if qmatch:
                q = qmatch.group(1).lower()
            else:
                qmatch = re.search(r'(1080|720|480|360)', media_url)
                if qmatch:
                    q = {"1080": "x", "720": "h", "480": "n", "360": "l"}.get(qmatch.group(1), "")
            _store(q, media_url)

        for label, media_url in re.findall(r'"label"\s*:\s*"?(1080p|720p|480p|360p)"?\s*,\s*"file"\s*:\s*"([^"]+)"', text, re.I):
            code = {"1080p": "x", "720p": "h", "480p": "n", "360p": "l"}.get(label.lower(), "")
            _store(code, media_url)

        for media_url, label in re.findall(r'"(?:file|src)"\s*:\s*"([^"]+)"[^}]{0,120}"(?:label|res|quality)"\s*:\s*"?(1080p|720p|480p|360p)"?', text, re.I | re.S):
            code = {"1080p": "x", "720p": "h", "480p": "n", "360p": "l"}.get(label.lower(), "")
            _store(code, media_url)

    servers = []
    for code in ("x", "h", "n", "l"):
        if code not in found:
            continue
        label = VIDTUBE_QUALITY_LABELS.get(code, code.upper())
        servers.append({
            "name": "VidTube {}".format(label),
            "url": "{}|Referer={}".format(found[code], embed_url),
            "type": "direct",
        })
    return servers


def _server_candidates(content_type, tmdb_id, season=None, episode=None):
    if content_type == "movie":
        return [
            ("VidKing", "https://www.vidking.net/embed/movie/{0}".format(tmdb_id)),
        ]
    return [
        (
            "VidKing",
            "https://www.vidking.net/embed/tv/{0}/{1}/{2}".format(
                tmdb_id, season or 1, episode or 1
            ),
        ),
    ]


def _topcinema_fallback_servers(content_type, titles, year="", season=None, episode=None):
    try:
        from . import topcinema as topmod
    except Exception as exc:
        log("EgyDead TopCinema import failed: {}".format(exc))
        return []

    title_variants = _title_variants(*(titles or []))
    if not title_variants:
        title_variants = _unique_titles(*(titles or []))

    def _norm(s):
        s = _strip_html(s or "").lower()
        s = re.sub(r'[^a-z0-9\u0600-\u06ff ]+', ' ', s)
        return re.sub(r'\s+', ' ', s).strip()

    want_year = str(year or "").strip()
    wanted = [_norm(t) for t in title_variants if t]
    out = []
    seen = set()

    def _push(name, url):
        url = (url or "").strip()
        if not url or url in seen:
            return
        out.append({"name": name, "url": url, "type": "direct"})
        seen.add(url)

    def _extract_iframe_from_server(server_url):
        try:
            if not server_url.startswith("topcinema_server|"):
                return ""
            parts = server_url.split("|")
            ajax_url = parts[1]
            post_id = parts[2]
            server_index = parts[3]
            referer_url = parts[4] if len(parts) > 4 else getattr(topmod, "MAIN_URL", "")

            html, _ = topmod.fetch(
                ajax_url,
                referer=referer_url,
                extra_headers={"X-Requested-With": "XMLHttpRequest"},
                post_data={"id": post_id, "i": server_index}
            )
            m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html or "", re.I)
            if not m:
                return ""
            iframe = m.group(1).replace("\\/", "/").strip()
            if iframe.startswith("//"):
                iframe = "https:" + iframe
            return iframe
        except Exception as exc:
            log("EgyDead TopCinema iframe extraction failed: {}".format(exc))
            return ""

    for raw_title in title_variants[:6]:
        query = raw_title
        if content_type == "movie" and want_year:
            query = "{} {}".format(raw_title, want_year)

        try:
            results = topmod.search(query, 1) or []
        except Exception as exc:
            log("EgyDead TopCinema search failed for {}: {}".format(query, exc))
            continue

        for item in results[:12]:
            item_title = _norm(item.get("title") or "")
            if wanted and not any(w in item_title or item_title in w for w in wanted):
                continue

            try:
                page = topmod.get_page(item.get("url"))
            except Exception as exc:
                log("EgyDead TopCinema get_page failed: {}".format(exc))
                continue

            for srv in (page or {}).get("servers", []):
                sname = (srv.get("name") or "")
                surl = (srv.get("url") or "")
                low_name = sname.lower()

                if ("vidtube" in low_name) or (u"متعدد الجودات" in sname) or ("multiple" in low_name):
                    iframe_url = _extract_iframe_from_server(surl)
                    log("EgyDead TopCinema iframe_url={}".format(iframe_url))
                    if iframe_url and "vidtube" in iframe_url.lower():
                        try:
                            qservers = _vidtube_quality_servers(iframe_url)
                        except Exception as exc:
                            log("EgyDead VidTube quality extraction failed: {}".format(exc))
                            qservers = []

                        if qservers:
                            for qs in qservers:
                                qurl = qs.get("url") or ""
                                if qurl and qurl not in seen:
                                    out.append(qs)
                                    seen.add(qurl)
                            if out:
                                return out
                        elif iframe_url:
                            _push("VidTube", iframe_url)
                            return out

                try:
                    resolved = topmod.extract_stream(surl)
                except Exception as exc:
                    log("EgyDead TopCinema extract_stream failed: {}".format(exc))
                    continue

                stream_url = ""
                if isinstance(resolved, tuple):
                    stream_url = resolved[0] or ""
                else:
                    stream_url = resolved or ""

                if not stream_url:
                    continue
                if stream_url.startswith("//"):
                    stream_url = "https:" + stream_url

                if "vidtube" in stream_url.lower():
                    try:
                        qservers = _vidtube_quality_servers(stream_url)
                    except Exception as exc:
                        log("EgyDead VidTube quality extraction failed: {}".format(exc))
                        qservers = []

                    if qservers:
                        for qs in qservers:
                            qurl = qs.get("url") or ""
                            if qurl and qurl not in seen:
                                out.append(qs)
                                seen.add(qurl)
                        if out:
                            return out
                    else:
                        _push("VidTube", stream_url)
                        return out
                elif "vidking" not in stream_url.lower() and "viking" not in stream_url.lower():
                    _push("TopCinema", stream_url)

        if out:
            return out

    return out


def _vidking_resolve(embed_url):
    embed_url = (embed_url or "").strip()
    if not embed_url:
        return None, None, _get_base()

    html, _ = fetch(embed_url, referer=_get_base(), extra_headers={
        "Referer": _get_base(),
        "Origin": "https://www.vidking.net",
        "X-Requested-With": "XMLHttpRequest",
    })
    if not html:
        return embed_url, None, _get_base()

    texts = [html]

    for block in _extract_packer_blocks(html):
        try:
            dec = decode_packer(block)
        except Exception:
            dec = ""
        if dec:
            texts.append(dec)

    for b64 in re.findall(r'atob\(["\']([A-Za-z0-9+/=]{40,})["\']\)', html, re.I):
        try:
            dec = base64.b64decode(b64).decode("utf-8", "ignore")
        except Exception:
            dec = ""
        if dec:
            texts.append(dec)

    for b64 in re.findall(r'["\']([A-Za-z0-9+/=]{120,})["\']', html):
        try:
            dec = base64.b64decode(b64).decode("utf-8", "ignore")
        except Exception:
            dec = ""
        if dec and ("m3u8" in dec or "mp4" in dec or "source" in dec or "file" in dec):
            texts.append(dec)

    patterns = [
        r'<source[^>]+src=["\']([^"\']+(?:m3u8|mp4)[^"\']*)["\']',
        r'<iframe[^>]+src=["\']([^"\']+)["\']',
        r'"file"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        r"'file'\s*:\s*'([^']+(?:m3u8|mp4)[^']*)'",
        r'"src"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        r"'src'\s*:\s*'([^']+(?:m3u8|mp4)[^']*)'",
        r'"hls"\s*:\s*"([^"]+)"',
        r"'hls'\s*:\s*'([^']+)'",
        r'"playlist"\s*:\s*"([^"]+)"',
        r"'playlist'\s*:\s*'([^']+)'",
        r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
        r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
    ]

    found = []
    seen = set()

    def _add(u):
        u = (u or "").replace("\\/", "/").replace("\\u0026", "&").replace("&amp;", "&").strip()
        if not u:
            return
        if u.startswith("//"):
            u = "https:" + u
        if u.startswith("/"):
            u = urljoin(embed_url, u)
        if u not in seen:
            found.append(u)
            seen.add(u)

    for txt in texts:
        if not txt:
            continue
        for pat in patterns:
            for u in re.findall(pat, txt, re.I | re.S):
                _add(u)

    nested = [u for u in found if "vidking.net/embed/" not in u.lower() and ("/embed" in u.lower() or "player" in u.lower())]
    for iframe_url in nested[:3]:
        try:
            html2, _ = fetch(iframe_url, referer=embed_url, extra_headers={"Referer": embed_url})
        except Exception:
            html2 = ""
        if not html2:
            continue
        for pat in patterns:
            for u in re.findall(pat, html2, re.I | re.S):
                _add(u)

    media = [u for u in found if ".m3u8" in u.lower() or ".mp4" in u.lower()]
    media.sort(key=lambda x: (".m3u8" not in x.lower(), ".mp4" not in x.lower(), len(x)))
    if media:
        media_url = media[0]
        final = "{}|Referer={}&Origin=https://www.vidking.net".format(media_url, embed_url)
        log("EgyDead VidKing resolved: {}".format(media_url[:160]))
        return final, None, _get_base()

    sample = re.sub(r"\s+", " ", html[:400]).strip()
    log("EgyDead VidKing unresolved sample: {}".format(sample[:220]))
    log("EgyDead VidKing fallback to base resolver: {}".format(embed_url))
    return embed_url, None, _get_base()


def _build_servers(content_type, tmdb_id, titles, year="", season=None, episode=None, watch_html=""):
    servers = []
    seen = set()

    def _push(name, url, stype="direct"):
        url = (url or "").strip()
        if not url or url in seen:
            return
        servers.append({"name": name, "url": url, "type": stype})
        seen.add(url)

    top_iframe = ""
    topcinema = _topcinema_lookup(content_type, season, episode, year, titles)
    if topcinema and topcinema.get("iframe_url"):
        top_iframe = (topcinema.get("iframe_url") or "").strip()
        if top_iframe.startswith("//"):
            top_iframe = "https:" + top_iframe

    if top_iframe:
        log("EgyDead top_iframe(api)={}".format(top_iframe))
        low = top_iframe.lower()

        if "vidtube" in low:
            quality_servers = _vidtube_quality_servers(top_iframe)
            if quality_servers:
                for server in quality_servers:
                    _push(server["name"], server["url"], server.get("type", "direct"))
            else:
                _push("VidTube", top_iframe, "direct")

            if servers and FORCE_TOPCINEMA_API_FIRST:
                log("EgyDead servers(from api vidtube): {}".format(repr([s.get("name") for s in servers])))
                return servers

        elif "vidking" not in low and "viking" not in low:
            _push("TopCinema", top_iframe, "direct")
            if servers and FORCE_TOPCINEMA_API_FIRST:
                log("EgyDead servers(from api direct): {}".format(repr([s.get("name") for s in servers])))
                return servers

    if not servers and not top_iframe:
        try:
            tc_servers = _topcinema_fallback_servers(content_type, titles, year, season, episode)
        except Exception as exc:
            log("EgyDead TopCinema fallback failed: {}".format(exc))
            tc_servers = []

        for s in tc_servers:
            _push(s.get("name") or "TopCinema", s.get("url") or "", s.get("type", "direct"))

        if servers:
            log("EgyDead servers(from topcinema fallback): {}".format(repr([s.get("name") for s in servers])))
            return servers

    if top_iframe and DISABLE_VIDKING_WHEN_TOPCINEMA_EXISTS:
        log("EgyDead guard: top_iframe exists, skipping watch/page vidking fallback")
        return servers

    if not watch_html:
        try:
            watch_html, _ = fetch(_watch_url(content_type, tmdb_id, season, episode))
        except Exception:
            watch_html = ""

    sources = _extract_player_sources(watch_html)
    log("EgyDead watch sources: {}".format(repr(sources[:10])))

    for src_url in sources:
        low = src_url.lower()
        if "vidtube" in low:
            quality_servers = _vidtube_quality_servers(src_url)
            if quality_servers:
                for server in quality_servers:
                    _push(server["name"], server["url"], server.get("type", "direct"))
            else:
                _push("VidTube", src_url, "direct")

    if servers:
        log("EgyDead servers(from watch vidtube): {}".format(repr([s.get("name") for s in servers])))
        return servers

    for src_url in sources:
        low = src_url.lower()
        if "vidking" in low or "viking" in low:
            continue
        _push("Player", src_url, "direct")

    if servers:
        log("EgyDead servers(from watch non-vidking): {}".format(repr([s.get("name") for s in servers])))
        return servers

    try:
        candidates = _server_candidates(content_type, tmdb_id, season, episode)
    except Exception:
        candidates = []

    for name, url in candidates:
        low = (url or "").lower()
        if "vidtube" in low:
            quality_servers = _vidtube_quality_servers(url)
            if quality_servers:
                for server in quality_servers:
                    _push(server["name"], server["url"], server.get("type", "direct"))
            else:
                _push("VidTube", url, "direct")
        elif "vidking" in low or "viking" in low:
            continue
        else:
            _push(name, url, "direct")

    if servers:
        log("EgyDead servers(final non-vidking): {}".format(repr([s.get("name") for s in servers])))
        return servers

    for name, url in candidates:
        low = (url or "").lower()
        if "vidking" in low or "viking" in low:
            _push("VidKing", url, "direct")

    log("EgyDead servers(final): {}".format(repr([s.get("name") for s in servers])))
    return servers


def _episode_title(show_title, season, episode, ep_name):
    bits = ["الموسم {0}".format(season), "الحلقة {0}".format(episode)]
    ep_name = _strip_html(ep_name)
    if ep_name:
        bits.append(ep_name)
    prefix = _strip_html(show_title)
    return "{0} - {1}".format(prefix, " - ".join(bits)) if prefix else " - ".join(bits)


def _season_items(tmdb_id, details, current_props=None):
    items = []
    total = 0
    base = _get_base().rstrip("/")
    show_title = details.get("name") or details.get("title") or ""
    seasons = details.get("seasons") or []
    initial_season = (current_props or {}).get("initialSeason")
    initial_data = (current_props or {}).get("initialSeasonData") or {}

    for season in seasons:
        season_number = season.get("season_number")
        if season_number is None or int(season_number) < 1:
            continue

        if initial_season == season_number and initial_data:
            season_data = initial_data
        else:
            season_url = "{0}/api/tmdb/tv/{1}/season/{2}".format(base, tmdb_id, season_number)
            season_data = _fetch_json(season_url) or {}

        episodes = season_data.get("episodes") or []
        for ep in episodes:
            ep_num = ep.get("episode_number")
            if not ep_num:
                continue
            items.append(
                {
                    "title": _episode_title(show_title, season_number, ep_num, ep.get("name")),
                    "url": "{0}/watch/tv/{1}/{2}/{3}".format(base, tmdb_id, season_number, ep_num),
                    "type": "episode",
                }
            )
            total += 1
            if total >= MAX_EPISODES:
                log("EgyDead: episode list limited to {}".format(MAX_EPISODES))
                return items

    return items


def _category_api_path(url):
    path = (url or "").lower()
    if "/movies/recent" in path:
        return "/api/tmdb/discover/movie"
    if "/movies/popular" in path:
        return "/api/tmdb/movie/popular"
    if "/movies/top-rated" in path:
        return "/api/tmdb/movie/top_rated"
    if "/series/recent" in path:
        return "/api/tmdb/discover/tv"
    if "/series/popular" in path:
        return "/api/tmdb/tv/popular"
    if "/series/top-rated" in path:
        return "/api/tmdb/tv/top_rated"
    return ""


def _page_from_url(url, default=1):
    try:
        match = re.search(r'[\?&]page=(\d+)', url or "", re.I)
        if match:
            return max(1, int(match.group(1)))
    except Exception:
        pass
    return default


def _with_page(url, page_num):
    page_num = max(1, int(page_num or 1))
    url = url or ""
    if re.search(r'([\?&])page=\d+', url, re.I):
        return re.sub(r'([\?&])page=\d+', r'\1page={0}'.format(page_num), url, flags=re.I)
    return url + ('&' if '?' in url else '?') + 'page={0}'.format(page_num)


def _append_next_page(items, url, current_page, total_pages=None, has_more=None):
    try:
        current_page = max(1, int(current_page or 1))
    except Exception:
        current_page = 1

    should_add = False
    if has_more is True:
        should_add = True
    elif total_pages:
        try:
            should_add = int(total_pages) > current_page
        except Exception:
            should_add = False

    if should_add:
        next_url = _with_page(url, current_page + 1)
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": next_url,
            "type": "category",
            "_action": "category"
        })
    return items


def get_categories(mtype="movie"):
    base = _get_base().rstrip("/")
    if mtype == "movie":
        return [
            {"title": "🎬 أحدث الأفلام", "url": base + "/movies/recent", "type": "category", "_action": "category"},
            {"title": "🔥 الأكثر شهرة", "url": base + "/movies/popular", "type": "category", "_action": "category"},
            {"title": "⭐ الأعلى تقييماً", "url": base + "/movies/top-rated", "type": "category", "_action": "category"},
        ]
    return [
        {"title": "📺 أحدث المسلسلات", "url": base + "/series/recent", "type": "category", "_action": "category"},
        {"title": "🔥 الأكثر شهرة", "url": base + "/series/popular", "type": "category", "_action": "category"},
        {"title": "⭐ الأعلى تقييماً", "url": base + "/series/top-rated", "type": "category", "_action": "category"},
    ]


def get_category_items(url, page=1):
    base = _get_base().rstrip("/")
    current_page = 1
    try:
        current_page = int(page or 1)
    except Exception:
        current_page = 1

    url_page = _page_from_url(url, 1)
    if url_page > 1 and current_page <= 1:
        current_page = url_page

    api_path = _category_api_path(url)
    if api_path:
        fetch_url = "{}{}?page={}".format(base, api_path, current_page)
        data = _fetch_json(fetch_url)
        if data:
            items = []
            for entry in (data or {}).get("results", []):
                item = _entry_to_item(entry)
                if item:
                    items.append(item)

            total_pages = (data or {}).get("total_pages") or (data or {}).get("pages")
            has_more = None
            try:
                if total_pages:
                    has_more = int(total_pages) > int(current_page)
            except Exception:
                has_more = None

            if has_more is None and items:
                has_more = len(items) >= 18

            return _append_next_page(items, url, current_page, total_pages=total_pages, has_more=has_more)

    fetch_target = url if current_page <= 1 else _with_page(url, current_page)
    html, _ = fetch(fetch_target)
    if not html:
        return []

    data = _extract_next_data(html)
    props = _page_props(data)
    items = _items_from_page_props(props)
    if not items:
        items = _parse_cards(html)

    total_pages = (
        props.get("totalPages")
        or props.get("total_pages")
        or props.get("pages")
        or props.get("pagesCount")
        or props.get("lastPage")
    )
    props_page = (
        props.get("page")
        or props.get("currentPage")
        or props.get("current_page")
    )
    if props_page:
        try:
            current_page = int(props_page)
        except Exception:
            pass

    has_more = None
    try:
        if total_pages:
            has_more = int(total_pages) > int(current_page)
    except Exception:
        has_more = None

    if has_more is None:
        if re.search(r'href=["\'][^"\']*[\?&]page={0}["\']'.format(current_page + 1), html, re.I):
            has_more = True
        elif items:
            has_more = len(items) >= 18
        else:
            has_more = False

    return _append_next_page(items, url, current_page, total_pages=total_pages, has_more=has_more)


def search(query, page=1):
    base = _get_base().rstrip("/")
    current_page = 1
    try:
        current_page = int(page or 1)
    except Exception:
        current_page = 1

    search_url = "{0}/search?q={1}".format(base, quote_plus(query))
    if current_page > 1:
        search_url += "&page={0}".format(current_page)

    html, _ = fetch(search_url)
    if not html:
        return []

    data = _extract_next_data(html)
    props = _page_props(data)
    items = _items_from_page_props(props)
    if not items:
        items = _parse_cards(html)

    total_pages = (
        props.get("totalPages")
        or props.get("total_pages")
        or props.get("pages")
        or props.get("pagesCount")
        or props.get("lastPage")
    )
    props_page = props.get("page") or props.get("currentPage") or props.get("current_page")
    if props_page:
        try:
            current_page = int(props_page)
        except Exception:
            pass

    has_more = None
    try:
        if total_pages:
            has_more = int(total_pages) > int(current_page)
    except Exception:
        has_more = None

    if has_more is None:
        if re.search(r'href=["\'][^"\']*[\?&]page={0}["\']'.format(current_page + 1), html, re.I):
            has_more = True
        elif items:
            has_more = len(items) >= 18
        else:
            has_more = False

    if has_more:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": "{0}/search?q={1}&page={2}".format(base, quote_plus(query), current_page + 1),
            "type": "category",
            "_action": "category"
        })
    return items


def get_page(url, m_type="movie"):
    html, final_url = fetch(url)
    result = _detail_result(url, "", "", "", "", "", m_type or "movie")

    if not html:
        log("EgyDead: failed to fetch {}".format(url))
        return result

    data = _extract_next_data(html)
    props = _page_props(data)
    details = props.get("details") or {}
    ld = _json_ld_object(html)
    meta_plot = _meta_description(html)
    meta_title = _meta_title(html)
    meta_poster = _meta_image(html)
    ld_title = _clean_title_text(ld.get("name") or ld.get("headline") or "")
    ld_plot = _strip_html(ld.get("description"))
    ld_poster = _img(ld.get("image") or "")
    ld_year = _year_from_text(ld.get("datePublished") or "")
    ld_rating = _rating_text(((ld.get("aggregateRating") or {}).get("ratingValue")))

    watch_match = re.search(r"/watch/(movie|tv)/(\d+)(?:/(\d+)/(\d+))?", final_url or url)
    detail_match = re.search(r"/(movie|tv)/(\d+)$", final_url or url)

    if watch_match:
        content_type, tmdb_id, season, episode = watch_match.groups()
        poster = _img(details.get("poster_path")) or ld_poster or meta_poster
        plot = _strip_html(details.get("overview")) or ld_plot or meta_plot
        year = _year_from_entry(details) or ld_year or _year_from_text(meta_title)
        rating = _rating_text(details.get("vote_average")) or ld_rating

        if content_type == "movie":
            titles = _unique_titles(details.get("title"), details.get("original_title"), ld_title, meta_title)
            title = titles[0] if titles else "Movie {0}".format(tmdb_id)
            result = _detail_result(url, title, poster, plot, year, rating, "movie")
            result["servers"] = _build_servers("movie", tmdb_id, titles, year=year, watch_html=html)
            return result

        titles = _unique_titles(details.get("name"), details.get("original_name"), ld_title, meta_title)
        season = season or str(props.get("initialSeason") or 1)
        episode = episode or str(props.get("initialEpisode") or 1)
        season_data = props.get("initialSeasonData") or {}
        current_ep = None
        for ep in season_data.get("episodes") or []:
            if str(ep.get("episode_number")) == str(episode):
                current_ep = ep
                break
        ep_name = (current_ep or {}).get("name") or ""
        title = _episode_title(titles[0] if titles else details.get("name"), season, episode, ep_name)
        result = _detail_result(url, title, poster, plot, year, rating, "episode")
        result["servers"] = _build_servers("tv", tmdb_id, titles, season=season, episode=episode, watch_html=html)
        return result

    if detail_match:
        content_type, tmdb_id = detail_match.groups()
    else:
        content_type = props.get("type") or ("movie" if m_type == "movie" else "tv")
        tmdb_id = str(details.get("id") or "")

    poster = _img(details.get("poster_path")) or ld_poster or meta_poster
    plot = _strip_html(details.get("overview")) or ld_plot or meta_plot
    year = _year_from_entry(details) or ld_year or _year_from_text(meta_title)
    rating = _rating_text(details.get("vote_average")) or ld_rating

    if content_type == "movie":
        titles = _unique_titles(details.get("title"), details.get("original_title"), ld_title, meta_title)
        title = titles[0] if titles else "Movie {0}".format(tmdb_id or "")
        result = _detail_result(url, title, poster, plot, year, rating, "movie")
        if tmdb_id:
            result["servers"] = _build_servers("movie", tmdb_id, titles, year=year)
        return result

    titles = _unique_titles(details.get("name"), details.get("original_name"), ld_title, meta_title)
    title = titles[0] if titles else "Series {0}".format(tmdb_id or "")
    result = _detail_result(url, title, poster, plot, year, rating, "series")
    if tmdb_id:
        result["items"] = _season_items(tmdb_id, details, props)
    return result


def extract_stream(url):
    low = (url or "").lower()
    if "vidking.net/embed/" in low or "viking" in low:
        resolved, sub, ref = _vidking_resolve(url)
        if resolved and resolved != url:
            return resolved, sub, ref
        from .base import extract_stream as base_extract_stream
        return base_extract_stream(url)

    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
`````

## File: extractors/fasel.py
`````python
# -*- coding: utf-8 -*-
import sys
import re
import time
from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, quote, urlparse
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, quote
    from urlparse import urlparse
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

DOMAINS = [
    "https://faselhd.fit/",
    "https://www.faselhd.cam",
    "https://faselhd.pro",
    "https://faselhd.cc",
]

BLOCKED_MARKERS = ("alliance4creativity", "watch-it-legally", "just a moment", "cf-chl", "telegram")

_ACTIVE_URL = None
_ACTIVE_BASE_FETCH_TIME = 0

def _get_base():
    global _ACTIVE_URL
    for domain in DOMAINS:
        log("FaselHD: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        if html and not any(m in (final_url or "").lower() for m in BLOCKED_MARKERS):
            log("FaselHD: using domain {}".format(domain))
            _ACTIVE_URL = domain.rstrip('/')
            return _ACTIVE_URL
    _ACTIVE_URL = DOMAINS[0].rstrip('/')
    return _ACTIVE_URL

def _base():
    global _ACTIVE_URL, _ACTIVE_BASE_FETCH_TIME
    if not _ACTIVE_URL or (time.time() - _ACTIVE_BASE_FETCH_TIME) > 3600:
        _ACTIVE_URL = _get_base()
        _ACTIVE_BASE_FETCH_TIME = time.time()
    return _ACTIVE_URL

def _normalize_url(url):
    if not url: return ""
    url = html_unescape(url.strip())
    if url.startswith("//"): return "https:" + url
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
        {"title": "🎬 افلام اجنبي", "url": base + "/category/افلام-اجنبي", "type": "category"},
        {"title": "🎬 افلام عربي", "url": base + "/category/افلام-عربي", "type": "category"},
        {"title": "📺 مسلسلات اجنبي", "url": base + "/category/مسلسلات-اجنبي", "type": "category"},
        {"title": "📺 مسلسلات عربي", "url": base + "/category/مسلسلات-عربي", "type": "category"},
    ]
    if not html:
        return fallback
    pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
    for match in re.finditer(pattern, html):
        url = match.group(1)
        title = match.group(2).strip()
        if '/category/' in url and title and len(title) < 30:
            emoji = "🎬" if 'فيلم' in title or 'افلام' in title else "📺" if 'مسلسل' in title else "📁"
            categories.append({"title": f"{emoji} {title}", "url": _normalize_url(url), "type": "category"})
    if categories:
        seen = set()
        unique = []
        for cat in categories:
            if cat['url'] not in seen:
                seen.add(cat['url'])
                unique.append(cat)
        return unique
    return fallback

def _extract_items(html):
    items = []
    # New pattern for FaselHD category page (grid-card structure)
    pattern = r'<div[^>]*class="[^"]*grid-card[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)".*?<img[^>]*class="[^"]*thumb-img[^"]*"[^>]*src="([^"]+)".*?<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>'
    matches = re.findall(pattern, html, re.DOTALL | re.I)
    if not matches:
        # Fallback to older pattern
        pattern = r'<div[^>]*class="[^"]*post[^"]*"[^>]*>.*?<a href="([^"]+)".*?<img[^>]*(?:src|data-src)="([^"]+)".*?<h[23][^>]*>([^<]+)</h[23]>'
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
        })
    return items

def get_category_items(url):
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        return []
    # Bypass Telegram wall on category pages
    if "telegram" in html.lower():
        log("FaselHD: Telegram wall on category page, trying to bypass")
        refresh = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;url=([^"\']+)["\']', html, re.I)
        if refresh:
            new_url = _normalize_url(refresh.group(1))
            log("FaselHD: Following meta refresh to {}".format(new_url))
            return get_category_items(new_url)
        link = re.search(r'<a[^>]+href="([^"]+)"[^>]*>.*?(?:متابعة|continue|here).*?</a>', html, re.I)
        if link:
            new_url = _normalize_url(link.group(1))
            log("FaselHD: Following link to {}".format(new_url))
            return get_category_items(new_url)
        return []
    items = _extract_items(html)
    # Pagination
    next_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>التالي|Next</a>', html, re.I)
    if not next_match:
        next_match = re.search(r'<li[^>]*class="next"[^>]*>.*?<a href="([^"]+)"', html, re.I)
    if next_match:
        items.append({"title": "➡️ الصفحة التالية", "url": _normalize_url(next_match.group(1)), "type": "category"})
    return items

def search(query, page=1):
    base = _base()
    url = base + "/?s=" + quote_plus(query)
    html, _ = fetch(url, referer=base)
    return _extract_items(html)

def get_page(url):
    base = _base()
    html, final_url = fetch(url, referer=base)
    if not html:
        return {"title": "Error", "servers": [], "items": []}
    # Title
    title_match = re.search(r'<title>(.*?)</title>', html)
    title = _clean_title(title_match.group(1)) if title_match else "FaselHD"
    # Poster
    poster_match = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(poster_match.group(1)) if poster_match else ""
    # Plot
    plot_match = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html)
    plot = _clean_title(plot_match.group(1)) if plot_match else ""

    servers = []
    episodes = []
    item_type = "movie"

    # Series detection
    if '/series/' in url or 'مسلسل' in title:
        item_type = "series"
        ep_pattern = r'<a[^>]+href="([^"]+)"[^>]*>.*?الحلقة\s*(\d+)'
        ep_matches = re.findall(ep_pattern, html, re.I)
        for ep_url, ep_num in ep_matches:
            episodes.append({"title": f"الحلقة {ep_num}", "url": _normalize_url(ep_url), "type": "episode"})
        if not episodes:
            season_pattern = r'<a[^>]+href="([^"]+)"[^>]*>.*?الموسم\s*(\d+)'
            season_matches = re.findall(season_pattern, html, re.I)
            for s_url, s_num in season_matches:
                episodes.append({"title": f"الموسم {s_num}", "url": _normalize_url(s_url), "type": "category"})

    # Extract govid.live download link (or other hosters)
    download_match = re.search(r'href="(https?://govid\.live/d/[^"]+)"', html, re.I)
    if download_match:
        stream_url = download_match.group(1)
        log("FaselHD: Found govid download link: {}".format(stream_url))
        servers.append({"name": "فاصل - سيرفر رئيسي", "url": stream_url})

    other_hosters = re.findall(r'href="(https?://(?:streamtape|dood|mixdrop|voe)[^"]+)"', html, re.I)
    for hurl in other_hosters:
        servers.append({"name": "فاصل - سيرفر", "url": hurl})

    return {"url": final_url, "title": title, "plot": plot, "poster": poster, "servers": servers, "items": episodes, "type": item_type}

def extract_stream(url):
    log("Fasel extract_stream: {}".format(url))
    referer = _base()

    def follow_chain(current_url, ref, depth=0, max_depth=12):
        if depth > max_depth:
            return None
        log("Chain depth {}: {}".format(depth, current_url))
        html, final = fetch(current_url, referer=ref)
        if not html:
            return None
        # Direct m3u8
        m = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html, re.I)
        if m:
            return m.group(1)
        # Meta refresh
        refresh = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\']\d+;url=([^"\']+)["\']', html, re.I)
        if refresh:
            new_url = refresh.group(1)
            if new_url.startswith("//"):
                new_url = "https:" + new_url
            elif not new_url.startswith("http"):
                new_url = urljoin(current_url, new_url)
            return follow_chain(new_url, current_url, depth+1, max_depth)
        # Iframe
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.I)
        if iframe:
            iframe_url = iframe.group(1)
            if iframe_url.startswith("//"):
                iframe_url = "https:" + iframe_url
            elif not iframe_url.startswith("http"):
                iframe_url = urljoin(current_url, iframe_url)
            return follow_chain(iframe_url, current_url, depth+1, max_depth)
        # Hoster link
        hoster = re.search(r'href=["\'](https?://(?:govid|streamtape|dood|mixdrop)[^"\']+)["\']', html, re.I)
        if hoster:
            return follow_chain(hoster.group(1), current_url, depth+1, max_depth)
        # Any other link
        any_link = re.search(r'href=["\'](https?://[^"\']+)["\']', html, re.I)
        if any_link:
            next_url = any_link.group(1)
            if next_url != current_url and not next_url.endswith("/"):
                return follow_chain(next_url, current_url, depth+1, max_depth)
        return None

    stream = follow_chain(url, referer)
    if stream:
        quality = "HD" if "1080" in stream else ("720p" if "720" in stream else "Auto")
        return stream, quality, referer
    # Fallback
    from .base import resolve_iframe_chain
    stream, _ = resolve_iframe_chain(url, referer=referer)
    if stream:
        return stream, "Auto", referer
    return None, None, referer
`````

## File: extractors/shaheed.py
`````python
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

VALID_HOST_MARKERS = ("shahid4u.guru", "shahieed4u.net", "shaheeid4u.net")
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
    if any(marker in host for marker in BLOCKED_HOST_MARKERS):
        return False
    return any(marker in host for marker in VALID_HOST_MARKERS)

def _is_blocked_page(html, final_url=""):
    text = (html or "").lower()
    final = (final_url or "").lower()
    return (
        not text
        or "just a moment" in text
        or "cf-chl" in text
        or "alliance for creativity" in text
        or any(marker in final for marker in BLOCKED_HOST_MARKERS)
        or (final and not _is_valid_site_url(final))
    )

def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)

def _get_base(force_refresh=False):
    global MAIN_URL, _HOME_HTML, _HOME_LAST_FETCH
    if MAIN_URL and not force_refresh and (time.time() - _HOME_LAST_FETCH) < 21600:
        return MAIN_URL
    for domain in DOMAINS:
        log("Shaheed: probing base {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Shaheed: blocked base {}".format(final_url))
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
    if not _is_valid_site_url(url):
        log("Shaheed: rejecting invalid target {}".format(url))
        return "", ""
    ref = referer or _get_base()
    h, start_url = fetch(url, referer=ref)
    if _is_blocked_page(h, start_url):
        return "", ""
    return h, start_url

def get_categories():
    base = _get_base().rstrip("/")
    html, _ = _fetch_live(base)
    categories = []
    seen_urls = set()
    if html:
        pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
        for match in re.finditer(pattern, html):
            url = match.group(1)
            title = match.group(2).strip()
            if '/category/' in url and title and len(title) < 30 and url not in seen_urls:
                seen_urls.add(url)
                emoji = "📁"
                if 'فيلم' in title or 'افلام' in title:
                    emoji = "🎬"
                elif 'مسلسل' in title or 'مسلسلات' in title:
                    emoji = "📺"
                categories.append({"title": f"{emoji} {title}", "url": _normalize_url(url), "type": "category"})
    if not categories:
        categories = [
            {"title": "🎬 افلام اجنبي", "url": base + "/category/افلام-اجنبي", "type": "category"},
            {"title": "🎬 افلام عربي", "url": base + "/category/افلام-عربي", "type": "category"},
            {"title": "📺 مسلسلات اجنبي", "url": base + "/category/مسلسلات-اجنبي", "type": "category"},
            {"title": "📺 مسلسلات عربي", "url": base + "/category/مسلسلات-عربي", "type": "category"},
        ]
    return categories

def _extract_cards(html):
    items = []
    # Try JSON-LD first
    json_ld_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    if json_ld_match:
        try:
            data = json.loads(json_ld_match.group(1))
            if data.get("@type") == "ItemList":
                for entry in data.get("itemListElement", []):
                    item = entry.get("item", {})
                    if item.get("@type") in ("Movie", "TVSeries"):
                        title = item.get("name", "")
                        url = item.get("url", "")
                        poster = item.get("image", "")
                        if title and url:
                            items.append({
                                "title": html_unescape(title),
                                "url": _normalize_url(url),
                                "poster": _normalize_url(poster),
                                "type": "movie" if item.get("@type") == "Movie" else "series",
                                "_action": "item",
                            })
                if items:
                    return items
        except:
            pass

    # Fallback patterns
    patterns = [
        r'<div[^>]*class="[^"]*post[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)".*?<img[^>]+src="([^"]+)".*?<h[23][^>]*>([^<]+)</h[23]>',
        r'<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)".*?<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>',
        r'<div[^>]*class="[^"]*movie-card[^"]*"[^>]*>.*?<a[^>]+href="([^"]+)".*?<img[^>]+src="([^"]+)".*?<div[^>]*class="[^"]*name[^"]*"[^>]*>([^<]+)</div>',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL | re.I)
        if matches:
            for match in matches:
                url = match[0]
                poster = match[1]
                title = match[2].strip()
                if title and url:
                    items.append({
                        "title": html_unescape(title),
                        "url": _normalize_url(url),
                        "poster": _normalize_url(poster),
                        "type": "movie",
                        "_action": "item",
                    })
            if items:
                break
    return items

def get_category_items(url):
    html, final_url = _fetch_live(url)
    if not html:
        return []
    items = _extract_cards(html)
    log("Shaheed: category {} -> {} items".format(url, len(items)))
    # Pagination
    next_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*>التالي|Next</a>', html, re.I)
    if next_match:
        items.append({"title": "➡️ الصفحة التالية", "url": _normalize_url(next_match.group(1)), "type": "category", "_action": "category"})
    return items

def search(query, page=1):
    base = _get_base()
    url = base + "/search?s=" + quote_plus(query) + "&page=" + str(page)
    html, _ = _fetch_live(url)
    return _extract_cards(html)

def get_page(url):
    html, final_url = _fetch_live(url)
    if not html:
        return {"title": "Error", "servers": [], "items": []}
    # Title
    title_match = re.search(r'<title>(.*?)</title>', html)
    title = html_unescape(title_match.group(1)) if title_match else ""
    # Poster
    poster_match = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(poster_match.group(1)) if poster_match else ""
    # Plot
    plot_match = re.search(r'class=["\']description["\'][^>]*>(.*?)</p>', html, re.S)
    plot = ""
    if plot_match:
        plot = re.sub(r'<[^>]+>', ' ', plot_match.group(1)).strip()
        plot = html_unescape(plot)
    # Servers and episodes
    servers = []
    episodes = []
    # Check if series
    if '/series/' in final_url or 'مسلسل' in title:
        ep_pattern = r'<a[^>]+href="([^"]+)"[^>]*>.*?الحلقة\s*(\d+)'
        ep_matches = re.findall(ep_pattern, html, re.I)
        for ep_url, ep_num in ep_matches:
            episodes.append({"title": f"الحلقة {ep_num}", "url": _normalize_url(ep_url), "type": "episode"})
        if not episodes:
            season_pattern = r'<a[^>]+href="([^"]+)"[^>]*>.*?الموسم\s*(\d+)'
            season_matches = re.findall(season_pattern, html, re.I)
            for s_url, s_num in season_matches:
                episodes.append({"title": f"الموسم {s_num}", "url": _normalize_url(s_url), "type": "category"})
    # Extract watch page link
    watch_match = re.search(r'href=["\']([^"\']+/watch/[^"\']+)["\']', html)
    if watch_match:
        watch_url = _normalize_url(watch_match.group(1))
        wh, _ = _fetch_live(watch_url, referer=final_url)
        if wh:
            # Look for servers in JSON
            js_servers = re.search(r'let servers = JSON\.parse\(\'(.*?)\'\)', wh)
            if not js_servers:
                js_servers = re.search(r'var servers = (\[.*?\])', wh, re.S)
            if js_servers:
                try:
                    srv_str = js_servers.group(1).replace("'", '"')
                    srv_data = json.loads(srv_str)
                    for s in srv_data:
                        if s.get("url"):
                            servers.append({"name": s.get("name", "Server"), "url": s["url"] + "|Referer=" + _site_root(final_url)})
                except:
                    pass
            else:
                iframe = re.search(r'<iframe[^>]+src="([^"]+)"', wh)
                if iframe:
                    servers.append({"name": "Stream", "url": iframe.group(1) + "|Referer=" + _site_root(final_url)})
    return {
        "url": final_url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "servers": servers,
        "items": episodes,
        "type": "series" if episodes else "movie",
    }

def extract_stream(url):
    log("Shaheed extract_stream: {}".format(url))
    referer = _get_base()
    if "|" in url:
        parts = url.split("|", 1)
        url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()
    from .base import resolve_iframe_chain
    stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=6)
    if stream:
        return stream, None, referer
    return url, None, referer
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
    "https://wecima.rent/",
    "https://wecima.date/",
    "https://www.wecima.site/",
]
VALID_HOST_MARKERS = (
    "wecima.rent",
    "wecima.date",
    "wecima.site",
)
BLOCKED_HOST_MARKERS = (
    "alliance4creativity.com",
)
MAIN_URL = None
_HOME_HTML = None

_CATEGORY_FALLBACKS = {
    "افلام اجنبي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/",
    "افلام عربي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%b9%d8%b1%d8%a8%d9%8a/",
    "مسلسلات اجنبي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/",
    "مسلسلات عربية": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b9%d8%b1%d8%a8%d9%8a%d8%a9/",
    "مسلسلات انمي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d9%86%d9%85%d9%8a/",
    "تريندج": "/",
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
    if any(marker in host for marker in BLOCKED_HOST_MARKERS):
        return False
    return any(marker in host for marker in VALID_HOST_MARKERS)


def _is_blocked_page(html, final_url=""):
    text = (html or "").lower()
    final = (final_url or "").lower()
    return (
        not text
        or "just a moment" in text
        or "cf-chl" in text
        or "__cf_chl" in text
        or "enable javascript and cookies to continue" in text
        or "watch it legally" in text
        or "alliance for creativity" in text
        or any(marker in final for marker in BLOCKED_HOST_MARKERS)
        or (final and not _is_valid_site_url(final))
    )


def _looks_like_wecima_page(html):
    text = html or ""
    return (
        "Grid--WecimaPosts" in text
        or "NavigationMenu" in text
        or "Thumb--GridItem" in text
        or "WECIMA" in text
        or "وي سيما" in text
    )


def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)


def _get_base():
    global MAIN_URL, _HOME_HTML
    if MAIN_URL:
        return MAIN_URL
    for domain in DOMAINS:
        log("Wecima: probing base {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked base {}".format(final_url))
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
    # Decode unicode escapes like \u0026 -> &
    try:
        url = url.encode('utf-8').decode('unicode_escape') if '\\u' in url else url
    except Exception:
        pass
    url = url.replace("\\u0026", "&").replace("&amp;", "&").replace("\\/", "/")
    url = html_unescape(url)
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(_get_base(), url)
    if any(marker in _host(url) for marker in BLOCKED_HOST_MARKERS):
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
    chosen = ""
    for candidate in _candidate_urls(url):
        log("Wecima: fetch candidate {}".format(candidate))
        html, final_url = fetch(candidate, referer=referer or _get_base())
        final_url = final_url or candidate
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked candidate {}".format(final_url))
            continue
        if html and _looks_like_wecima_page(html):
            log("Wecima: fetch success {}".format(final_url))
            return html, final_url
        if html:
            log("Wecima: invalid page shape {}".format(final_url))
        chosen = final_url
    log("Wecima: fetch failed for {}".format(url))
    return "", chosen


def _clean_html(text):
    text = html_unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title):
    title = _clean_html(title)
    for token in (
        "مشاهدة فيلم",
        "مشاهدة مسلسل",
        "مشاهدة",
        "فيلم",
        "مسلسل",
        "اون لاين",
        "أون لاين",
        "مترجم",
        "مترجمة",
        "مدبلج",
        "مدبلجة",
    ):
        title = title.replace(token, "")
    return re.sub(r"\s+", " ", title).strip(" -|")


def _home_html():
    base = _get_base()
    global _HOME_HTML
    if _HOME_HTML:
        return _HOME_HTML
    html, final_url = _fetch_live(base, referer=base)
    _HOME_HTML = html if not _is_blocked_page(html, final_url) else ""
    return _HOME_HTML


def _guess_type(title, url):
    text = "{} {}".format(title or "", url or "").lower()
    if any(token in text for token in ("/episode/", "الحلقة", "حلقة")):
        return "episode"
    if any(token in text for token in ("/series", "/season", "مسلسل", "series-")):
        return "series"
    return "movie"


def _grid_blocks(html):
    blocks = []
    for block in re.split(r'(?=<div[^>]+class="GridItem")', html or "", flags=re.I):
        if 'class="GridItem"' not in block:
            continue
        end_match = re.search(
            r'<ul[^>]+class="PostItemStats"[^>]*>.*?</ul>\s*</div>',
            block,
            re.S | re.I,
        )
        if end_match:
            blocks.append(block[:end_match.end()])
        else:
            blocks.append(block[:2500])
    return blocks


def _extract_cards(html):
    cards = []
    seen = set()
    for block in _grid_blocks(html):
        href_match = re.search(r'<a[^>]+href="([^"]+)"', block, re.I)
        if not href_match:
            continue

        url = _normalize_url(href_match.group(1))
        lowered = (url or "").lower()
        if not url or url in seen:
            continue
        if any(token in lowered for token in ("/category/", "/tag/", "/page/", "/filtering", "/feed/")):
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
        poster_match = re.search(r'data-lazy-style="[^"]*url\(([^)]+)\)"', block, re.I)
        if poster_match:
            poster = poster_match.group(1).strip("'\" ")
        if not poster:
            poster_match = re.search(r'(?:data-src|src)="([^"]+)"', block, re.I)
            if poster_match:
                poster = poster_match.group(1).strip()

        year_match = re.search(r'<span[^>]+class="year"[^>]*>\(\s*(\d{4})', block, re.I)
        year = year_match.group(1) if year_match else ""

        seen.add(url)
        cards.append(
            {
                "title": title,
                "url": url,
                "poster": _normalize_url(poster) if poster else "",
                "plot": year,
                "type": _guess_type(title, url),
                "_action": "details",
            }
        )
    log("Wecima: extracted {} cards".format(len(cards)))
    return cards


def _extract_next_page(html):
    match = re.search(r'<a[^>]+class="[^"]*next[^"]*page-numbers[^"]*"[^>]+href="([^"]+)"', html or "", re.I)
    if match:
        return _normalize_url(match.group(1))
    match = re.search(r'<a[^>]+rel="next"[^>]+href="([^"]+)"', html or "", re.I)
    if match:
        return _normalize_url(match.group(1))
    return ""


def _category_from_home(label, fallback):
    html = _home_html()
    patterns = [
        r'<a[^>]+href="([^"]+)"[^>]*>\s*' + re.escape(label) + r'\s*</a>',
        r'<a[^>]+href="([^"]+)"[^>]*>\s*<span[^>]*>\s*' + re.escape(label) + r'\s*</span>',
    ]
    for pattern in patterns:
        match = re.search(pattern, html or "", re.S | re.I)
        if match:
            url = _normalize_url(match.group(1))
            if url:
                return url
    return _normalize_url(urljoin(_get_base(), _CATEGORY_FALLBACKS.get(label, "/")))


def _extract_servers(html):
    servers = []
    seen = set()

    # Method 1: <ul id="watch"> with data-watch attribute
    watch_list = re.search(r'<ul[^>]+id="watch"[^>]*>(.*?)</ul>', html or "", re.S | re.I)
    if watch_list:
        for idx, match in enumerate(re.finditer(r'<li[^>]+data-watch="([^"]+)"[^>]*>(.*?)</li>', watch_list.group(1), re.S | re.I)):
            server_url = html_unescape(match.group(1)).strip()
            if not server_url or server_url in seen:
                continue
            seen.add(server_url)
            name = _clean_html(match.group(2)) or "Server {}".format(idx + 1)
            servers.append({"name": name, "url": server_url, "type": "direct"})

    if servers:
        return servers

    # Method 2: links with class containing "server" or "watch"
    for m in re.finditer(r'<(?:a|div|li|button)[^>]+(?:class|id)="[^"]*(?:server|watch|player)[^"]*"[^>]*>.*?href="([^"]+)"', html or "", re.S | re.I):
        url = _normalize_url(m.group(1))
        if url and url not in seen and "://" in url:
            seen.add(url)
            servers.append({"name": "Server {}".format(len(servers) + 1), "url": url})

    # Method 3: iframes
    if not servers:
        for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', html or "", re.I):
            url = _normalize_url(m.group(1))
            if url and url not in seen and "://" in url:
                if any(k in url for k in ["embed", "player", "watch", "stream", "video"]):
                    seen.add(url)
                    servers.append({"name": "Player {}".format(len(servers) + 1), "url": url})

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
        match = re.search(pattern, html or "", re.S | re.I)
        if match:
            title = _clean_title(match.group(1))
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
        r'content="([^"]+)"[^>]+name="description"',
    ):
        match = re.search(pattern, html or "", re.S | re.I)
        if match:
            text = _clean_html(match.group(1))
            if text and "موقع وي سيما" not in text and "مشاهدة احدث الافلام" not in text:
                return text
    return ""


def _detail_poster(html):
    for pattern in (
        r'<wecima[^>]+style="[^"]*--img:url\(([^)]+)\)',
        r'property="og:image"[^>]+content="([^"]+)"',
        r'content="([^"]+)"[^>]+property="og:image"',
        r'(?:data-src|src)="([^"]+)"[^>]+itemprop="image"',
        r'itemprop="image"[^>]+(?:data-src|src)="([^"]+)"',
    ):
        match = re.search(pattern, html or "", re.I)
        if match:
            poster = match.group(1).strip("'\" ")
            if poster:
                return _normalize_url(poster) or poster
    return ""


def _detail_year(title, html):
    match = re.search(r'\b(19\d{2}|20\d{2}|21\d{2})\b', title or "")
    if match:
        return match.group(1)
    match = re.search(r'datePublished[^>]*?(\d{4})', html or "", re.I)
    if match:
        return match.group(1)
    match = re.search(r'"datePublished"\s*:\s*"(\d{4})', html or "", re.I)
    if match:
        return match.group(1)
    return ""


def _detail_rating(html):
    match = re.search(r'"ratingValue"\s*:\s*"?(\\?\d+(?:\.\d+)?)', html or "", re.I)
    if match:
        return match.group(1).replace("\\", "")
    match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', html or "", re.I)
    if match:
        return match.group(1)
    return ""


def get_categories(mtype="movie"):
    return [
        {"title": "أفلام أجنبية",  "url": _category_from_home("افلام اجنبي",   _CATEGORY_FALLBACKS["افلام اجنبي"]),   "type": "category", "_action": "category"},
        {"title": "أفلام عربية",   "url": _category_from_home("افلام عربي",    _CATEGORY_FALLBACKS["افلام عربي"]),    "type": "category", "_action": "category"},
        {"title": "مسلسلات أجنبية","url": _category_from_home("مسلسلات اجنبي", _CATEGORY_FALLBACKS["مسلسلات اجنبي"]),"type": "category", "_action": "category"},
        {"title": "مسلسلات عربية", "url": _category_from_home("مسلسلات عربية", _CATEGORY_FALLBACKS["مسلسلات عربية"]),"type": "category", "_action": "category"},
        {"title": "كارتون وانمي", "url": _category_from_home("مسلسلات انمي",  _CATEGORY_FALLBACKS["مسلسلات انمي"]), "type": "category", "_action": "category"},
        {"title": "ترند",          "url": _category_from_home("تريندج",        _CATEGORY_FALLBACKS["تريندج"]),        "type": "category", "_action": "category"},
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

    log("Wecima: category {} -> {} items".format(url, len(items)))
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def search(query, page=1):
    base = _get_base()
    items = []
    html = ""
    search_urls = [
        _search_url() + quote_plus(query),
        urljoin(base, "search/") + quote_plus(query),
    ]
    for search_url in search_urls:
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

    title = _detail_title(html)
    poster = _detail_poster(html)
    plot = _detail_plot(html)
    year = _detail_year(title, html)
    rating = _detail_rating(html)

    servers = _extract_servers(html)
    episodes = [] if servers else _extract_episode_cards(html)
    log("Wecima: detail {} -> servers={}, episodes={}".format(url, len(servers), len(episodes)))

    item_type = m_type or (_guess_type(title, final_url or url))
    if episodes:
        item_type = "series"
    elif servers and any(token in (title or "") for token in ("الحلقة", "حلقة")):
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
    import re as _re
    import base64 as _base64
    from .base import fetch, _extract_packer_blocks, decode_packer, urljoin as _urljoin

    base_url = "https://wecima.rent/"
    stream_url = url
    referer = base_url

    if "|" in url:
        parts = url.split("|", 1)
        stream_url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()

    def _norm(u, base=None):
        u = (u or "").replace("&amp;", "&").replace("\\/", "/").replace("\\u0026", "&").strip()
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return _urljoin(base or stream_url, u)
        return u

    def _extract_media_from_text(text, base=None):
        if not text:
            return ""

        patterns = [
            r'<source[^>]+src=["\']([^"\']+(?:m3u8|mp4|txt)[^"\']*)["\']',
            r'"file"\s*:\s*"([^"]+(?:m3u8|mp4|txt)[^"]*)"',
            r"'file'\s*:\s*'([^']+(?:m3u8|mp4|txt)[^']*)'",
            r'"src"\s*:\s*"([^"]+(?:m3u8|mp4|txt)[^"]*)"',
            r"'src'\s*:\s*'([^']+(?:m3u8|mp4|txt)[^']*)'",
            r'"(?:hls|hls2|hls3|hls4|playlist|master)"\s*:\s*"([^"]+)"',
            r"'(?:hls|hls2|hls3|hls4|playlist|master)'\s*:\s*'([^']+)'",
            r'(https?://[^\s"\'<>]+(?:m3u8|mp4|txt)[^\s"\'<>]*)',
        ]
        for pat in patterns:
            m = _re.search(pat, text, _re.I | _re.S)
            if m:
                return _norm(m.group(1), base)

        # location redirects / window.open
        redirect_patterns = [
            r'location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
            r'window\.open\(\s*["\']([^"\']+)["\']',
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*(?:Click|Continue|تحميل|مشاهدة)',
        ]
        for pat in redirect_patterns:
            m = _re.search(pat, text, _re.I | _re.S)
            if m:
                return _norm(m.group(1), base)

        # base64 blobs
        for b64 in _re.findall(r'atob\(["\']([A-Za-z0-9+/=]{40,})["\']\)', text, _re.I):
            try:
                dec = _base64.b64decode(b64).decode("utf-8", "ignore")
            except Exception:
                dec = ""
            u = _extract_media_from_text(dec, base)
            if u:
                return u

        return ""

    def _extract_from_html(html, base=None):
        if not html:
            return ""
        # direct html
        u = _extract_media_from_text(html, base)
        if u:
            return u

        # packed js
        for block in _extract_packer_blocks(html):
            try:
                dec = decode_packer(block)
            except Exception:
                dec = ""
            if dec:
                u = _extract_media_from_text(dec, base)
                if u:
                    return u
        return ""

    # akhbarworld helper param decode
    real_server_url = ""
    if "akhbarworld.online" in stream_url or "mycimafsd=" in stream_url:
        b64_match = _re.search(r'mycimafsd=([A-Za-z0-9+/=]+)', stream_url)
        if b64_match:
            try:
                real_server_url = _base64.b64decode(b64_match.group(1) + "==").decode("utf-8").strip()
            except Exception:
                real_server_url = ""

    # Step 1: fetch original server page
    html, final_url = fetch(stream_url, referer=referer)
    current_url = final_url or stream_url

    # Step 2: if bad html and encoded fallback exists, use it
    if (not html or len(html) < 300) and real_server_url:
        html, final_url = fetch(real_server_url, referer=referer)
        current_url = final_url or real_server_url

    # Step 3: extract candidate from returned html
    candidate = _extract_from_html(html, current_url)
    if not candidate and real_server_url:
        candidate = _norm(real_server_url, current_url)

    # Step 4: follow one or two intermediate hops if candidate is not final media
    hops = 0
    seen = set()
    while candidate and hops < 3:
        if candidate in seen:
            break
        seen.add(candidate)

        low = candidate.lower()
        if ".m3u8" in low or ".mp4" in low or ".txt" in low:
            return candidate, None, referer

        # fetch intermediate url (like link.mycima.cv / gate / redirect pages)
        html2, final2 = fetch(candidate, referer=current_url or referer)
        next_base = final2 or candidate

        # if fetch redirected directly to media
        if next_base and any(x in next_base.lower() for x in (".m3u8", ".mp4", ".txt")):
            return _norm(next_base, next_base), None, current_url or referer

        next_candidate = _extract_from_html(html2, next_base)
        if not next_candidate:
            # maybe the fetched page itself is a final opaque link – return it for proxy/headers as last chance
            if "mycima.cv/" in low or "akhbarworld.online" in low:
                return candidate + "|Referer=" + (current_url or referer), None, current_url or referer
            break

        current_url = next_base
        candidate = next_candidate
        hops += 1

    # final attempt from original html
    if html:
        last = _extract_from_html(html, current_url)
        if last:
            return last, None, referer

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

## File: installer.sh
`````bash
#!/bin/sh

# ArabicPlayer Enigma2 Plugin Installer
# Professional Script for Novaler 4K Pro and other E2 devices

PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/ArabicPlayer"
GITHUB_USER="asdrere123-alt"
REPO_NAME="ArabicPlayer"
TMP_DIR="/tmp/arabicplayer_install"

echo "========================================================="
echo "   ArabicPlayer Installer - Modern Premium UI Version    "
echo "========================================================="

# 1. Cleanup old version
if [ -d "$PLUGIN_PATH" ]; then
    echo "> Removing existing installation..."
    rm -rf "$PLUGIN_PATH"
fi

# 2. Dependency Check (Optional but helpful)
echo "> Checking dependencies..."
# Add any specific opkg packages if needed, e.g., python3-requests
# opkg update > /dev/null 2>&1
# opkg install python3-requests > /dev/null 2>&1

# 3. Download and Extract
echo "> Downloading latest version from GitHub..."
mkdir -p "$TMP_DIR"
cd "$TMP_DIR"

wget -q "--no-check-certificate" "https://github.com/$GITHUB_USER/$REPO_NAME/archive/refs/heads/main.tar.gz" -O main.tar.gz
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to download from GitHub!"
    exit 1
fi

echo "> Extracting files..."
tar -xzf main.tar.gz
CP_DIR=$(ls -d */ | grep "$REPO_NAME")
mv "$CP_DIR" "/usr/lib/enigma2/python/Plugins/Extensions/ArabicPlayer"

# 4. Final Cleanup
echo "> Cleaning up temporary files..."
rm -rf "$TMP_DIR"

# 5. Success and Restart
echo "========================================================="
echo "   ArabicPlayer INSTALLED SUCCESSFULLY!                  "
echo "   Restarting Enigma2 to load the new Premium UI...      "
echo "========================================================="

# Auto-restart Enigma2 (Ultra-robust approach)
echo "> Sending restart command..."
# Try Web Interface first (Most reliable across all images)
wget -qO - http://127.0.0.1/web/powerstate?newstate=3 > /dev/null 2>&1

# Fallbacks
if [ -f /usr/bin/systemctl ]; then
    systemctl restart enigma2
elif [ -f /sbin/init ]; then
    killall -9 enigma2 > /dev/null 2>&1
    init 4 && sleep 1 && init 3
else
    killall -9 enigma2
fi

exit 0

exit 0
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
installer.sh
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
from urllib.parse import urljoin  # FIX: use standard library, not from base
from .base import fetch

MAIN_URL = "https://ak.sv/"


def _clean_title(title):
    return (
        (title or "")
        .replace("&amp;", "&")
        .replace("مشاهدة", "")
        .replace("تحميل", "")
        .strip()
    )


def _extract_boxes(html):
    pattern = (
        r'<div class="(?:entry-box|episode-box)[^>]*>.*?'
        r'<a href="([^"]+)"[^>]*>.*?'
        r'<img[^>]+(?:data-src|src)="([^"]+)"[^>]*alt="([^"]+)"'
    )
    return re.findall(pattern, html or "", re.S)


def _normalize_watch_url(link):
    link = (link or "").replace("&amp;", "&").strip()
    if link.startswith("http://go.ak.sv/"):
        link = "https://" + link[len("http://"):]
    if link.startswith("https://go.ak.sv/watch/"):
        parts = link.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            return link
    return link


def _resolve_go_watch_url(link):
    link = _normalize_watch_url(link)

    # Case 1: it's already a direct ak.sv/watch URL
    if link.startswith("https://ak.sv/watch/") and not link.startswith("https://go.ak.sv/"):
        return link

    # Case 2: it's a go.ak.sv shortener URL — follow the redirect page to get real URL
    html, _ = fetch(link, referer=MAIN_URL)
    if not html:
        return link

    # Look for the real ak.sv/watch URL inside the redirect page
    resolved = re.search(r'https://ak\.sv/watch/[^\s\'"<>]+', html, re.I)
    if resolved:
        return resolved.group(0).replace("&amp;", "&")
    return link


def _extract_watch_links(html):
    links = []
    seen = set()
    patterns = [
        r'href="(https?://(?:go\.)?ak\.sv/watch/[^"]+)"',
        r'href="(https?://ak\.sv/watch/[^"]+)"',
        r'href="(https?://ak\.sv/download/[^"]+)"',
    ]
    for pattern in patterns:
        for link in re.findall(pattern, html or "", re.I):
            link = _resolve_go_watch_url(link)
            if link in seen:
                continue
            seen.add(link)
            links.append(link)
    return links


def get_categories():
    return [
        {"title": "🎬 الأفلام", "url": urljoin(MAIN_URL, "movies"), "type": "category", "_action": "category"},
        {"title": "📺 المسلسلات", "url": urljoin(MAIN_URL, "series"), "type": "category", "_action": "category"},
        {"title": "🎭 العروض", "url": urljoin(MAIN_URL, "shows"), "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, _ = fetch(url)
    if not html:
        return []

    items = []
    seen = set()
    for link, img, title in _extract_boxes(html):
        if link in seen or "/category/" in link:
            continue
        seen.add(link)
        item_type = "series" if "/series-" in link or "/series/" in link or "مسلسل" in title else "movie"
        items.append(
            {
                "title": _clean_title(title),
                "url": link,
                "image": img,
                "type": item_type,
                "_action": "details",
            }
        )

    next_page = re.search(r'href="([^"]+)"[^>]*rel="next"', html)
    if next_page:
        items.append(
            {
                "title": "➡️ الصفحة التالية",
                "url": next_page.group(1).replace("&amp;", "&"),
                "type": "category",
                "_action": "category",
            }
        )
    return items


def _quote_url(url):
    import sys
    if sys.version_info[0] == 3:
        from urllib.parse import quote
        return quote(url, safe=":/%?=&")
    else:
        from urllib import quote
        u = url.encode("utf-8") if isinstance(url, type(u"")) else url
        return quote(u, safe=":/%?=&")

def get_page(url):
    url = _quote_url(url)
    html, final_url = fetch(url)
    result = {"url": url, "title": "", "poster": "", "plot": "", "servers": [], "items": [], "type": "movie"}

    if not html:
        return result

    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
    if title_match:
        result["title"] = _clean_title(title_match.group(1))

    poster_match = re.search(r'<img[^>]+class="img-fluid"[^>]+src="([^"]+)"', html, re.I)
    if poster_match:
        result["poster"] = poster_match.group(1).replace("&amp;", "&")

    plot_match = re.search(r'<p[^>]+class="text-white[^>]*>(.*?)</p>', html, re.S | re.I)
    if not plot_match:
        plot_match = re.search(r'القصة\s*.*?<p[^>]*>(.*?)</p>', html, re.S | re.I)
    if plot_match:
        result["plot"] = _clean_title(plot_match.group(1))

    is_series = ("/series/" in (final_url or url) or "مسلسل" in result["title"]) and "/episode/" not in (final_url or url)

    if is_series:
        result["type"] = "series"
        seen_eps = set()

        episode_patterns = [
            r'<a[^>]+href=["\']([^"\']+/episode/[^"\']+)["\'][^>]*>(.*?)</a>',
            r'<a[^>]+href=["\']([^"\']*episode[^"\']*)["\'][^>]*>(.*?)</a>',
        ]

        for ep_pat in episode_patterns:
            html_eps = re.findall(ep_pat, html, re.S | re.I)
            for ep_url, ep_title in html_eps:
                full_url = urljoin(final_url or url, ep_url).replace("&amp;", "&")
                if full_url in seen_eps:
                    continue
                seen_eps.add(full_url)

                ep_title_clean = _clean_title(ep_title)
                if not ep_title_clean:
                    ep_title_clean = "حلقة {0}".format(len(result["items"]) + 1)

                result["items"].append({
                    "title": ep_title_clean,
                    "url": full_url,
                    "type": "episode",
                    "_action": "item"
                })

        return result

    for index, link in enumerate(_extract_watch_links(html), 1):
        label = "🌐 مشاهدة {}".format(index) if "/watch/" in link else "⬇️ تحميل {}".format(index)
        result["servers"].append({"name": label, "url": link, "type": "direct"})

    return result


def extract_stream(url):
    # For ak.sv/watch pages, fetch the page directly and grab the source
    if "ak.sv/watch/" in url or "akw.cam/watch/" in url or "akw-cdn" in url:
        html, final_url = fetch(url, referer=MAIN_URL)
        if html:
            match = re.search(r'<source[^>]+src="([^"]+)"[^>]*type="video/mp4"', html, re.I)
            if match:
                return match.group(1).replace("&amp;", "&"), None, MAIN_URL
            match = re.search(r'<source[^>]+src="([^"]+(?:m3u8|mp4)[^"]*)"', html, re.I)
            if match:
                return match.group(1).replace("&amp;", "&"), None, MAIN_URL
            match = re.search(r'"file"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"', html, re.I)
            if match:
                return match.group(1).replace("\\u0026", "&").replace("&amp;", "&"), None, MAIN_URL
    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
````

## File: extractors/arablionztv.py
````python
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
````

## File: extractors/arabseed.py
````python
# -*- coding: utf-8 -*-
import base64
import json
import re
from .base import fetch, log, urljoin

MAIN_URL = "https://asd.pics/"
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
        log("ArabSeed: Missing AJAX token/post id")
        return []

    quality_url = urljoin(home_url, "get__quality__servers/")
    watch_server_url = urljoin(home_url, "get__watch__server/")
    results = []
    seen = set()

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
            log("ArabSeed: Failed to decode quality JSON")
            continue
        if data.get("type") != "success":
            continue

        # Some pages expose the default active server directly in `server`.
        direct_server = _decode_hidden_url(data.get("server", ""))
        if direct_server.startswith("http") and not any(host in direct_server for host in BLOCKED_HOSTS):
            key = (quality, direct_server)
            if key not in seen:
                seen.add(key)
                results.append(
                    {
                        "quality": quality,
                        "url": direct_server,
                        "name": _server_name(direct_server, "سيرفر عرب سيد"),
                    }
                )

        server_rows = re.findall(
            r'<li[^>]+data-post="([^"]+)"[^>]+data-server="([^"]+)"[^>]+data-qu="([^"]+)"[^>]*>.*?<span>([^<]+)</span>',
            data.get("html", ""),
            re.S,
        )
        for row_post_id, server_id, row_quality, label in server_rows:
            watch_body, _ = fetch(
                watch_server_url,
                post_data={
                    "post_id": row_post_id,
                    "quality": row_quality,
                    "server": server_id,
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

            server_url = _decode_hidden_url(watch_data.get("server", ""))
            if not server_url.startswith("http"):
                continue
            if any(host in server_url for host in BLOCKED_HOSTS):
                continue

            key = (row_quality, server_url)
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "quality": row_quality,
                    "url": server_url,
                    "name": _server_name(server_url, label),
                }
            )

    results.sort(key=lambda item: (QUALITY_ORDER.get(item["quality"], 9), _server_priority(item["url"]), item["name"]))
    return results


def get_categories():
    return [
        {"title": "🌍 أفلام أجنبي", "url": urljoin(MAIN_URL, "category/foreign-movies-12/"), "type": "category", "_action": "category"},
        {"title": "🇪🇬 أفلام عربي", "url": urljoin(MAIN_URL, "category/arabic-movies-12/"), "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أجنبي", "url": urljoin(MAIN_URL, "category/foreign-series-5/"), "type": "category", "_action": "category"},
        {"title": "🇸🇦 مسلسلات عربي", "url": urljoin(MAIN_URL, "category/arabic-series-10/"), "type": "category", "_action": "category"},
        {"title": "🎭 مسلسلات انمي", "url": urljoin(MAIN_URL, "category/anime-series-1/"), "type": "category", "_action": "category"},
        {"title": "🎮 عروض مصارعة", "url": urljoin(MAIN_URL, "category/wwe-shows-1/"), "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, _ = fetch(url)
    if not html:
        return []

    items = []
    seen = set()
    # Match various card/block containers
    blocks = re.findall(r'<div[^>]+class=[\"\'](?:recent--block|post--block|item)[^>]*>(.*?)</div>', html, re.S | re.IGNORECASE)
    if not blocks:
        # Fallback to general link/img pattern if no blocks found
        blocks = re.findall(r'(<a[^>]+href=[\"\'][^>]*>.*?<img[^>]+(?:data-src|src)=[\"\'][^>]*>.*?</a>)', html, re.S | re.IGNORECASE)

    for block in blocks:
        m = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]+title=["\']([^"\']+)["\'][^>]*>', block, re.S)
        if not m:
            m = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>.*?<img[^>]+alt=["\']([^"\']+)["\']', block, re.S)
        if m:
            link, title = m.groups()
            img_m = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', block)
            img = img_m.group(1) if img_m else ""
            
            if link in seen or "/category/" in link:
                continue
            seen.add(link)
            
            title = _clean_title(title)
            item_type = "series" if "/series-" in link or "مسلسل" in title else "movie"
            items.append({"title": title, "url": link, "image": img, "type": item_type, "_action": "details"})

    if not items:
        # Final fallback to the old regex if block parsing failed completely
        regex = r'<a[^>]+href=["\']([^"\']+)["\'][^>]+title=["\']([^"\']+)["\'][^>]*>.*?<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']'
        for link, title, img in re.findall(regex, html, re.S | re.IGNORECASE):
            if link in seen or "/category/" in link: continue
            seen.add(link)
            item_type = "series" if "/series-" in link or "مسلسل" in title else "movie"
            items.append({"title": title.strip(), "url": link, "image": img, "type": item_type, "_action": "details"})

    next_page = re.search(r'href="([^"]+/page/\d+/)"', html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page.group(1), "type": "category", "_action": "category"})
    return items


def get_page(url):
    html, final_url = fetch(url)
    if not html:
        return {"title": "Error", "servers": []}

    result = {
        "url": final_url or url,
        "title": "",
        "plot": "",
        "poster": "",
        "rating": "",
        "year": "",
        "servers": [],
        "items": [],
    }

    title_match = re.search(r'og:title[^>]+content="([^"]+)"', html) or re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
    if title_match:
        result["title"] = _clean_title(title_match.group(1).split("-")[0])

    poster_match = re.search(r'og:image"[^>]+content="([^"]+)"', html)
    if poster_match:
        result["poster"] = poster_match.group(1)

    plot_match = re.search(r'name="description"[^>]+content="([^"]+)"', html)
    if plot_match:
        result["plot"] = plot_match.group(1)

    is_series = any(marker in (final_url or url) for marker in ("/series-", "/season-", "/episode-")) or "مسلسل" in result["title"]

    watch_url = (final_url or url).rstrip("/") + "/watch/"
    watch_match = re.search(r'href="([^"]+/watch/)"', html)
    if watch_match:
        watch_url = watch_match.group(1)

    watch_html, watch_final = fetch(watch_url, referer=final_url or url)
    if not watch_html:
        watch_html, watch_final = html, (final_url or url)

    for server in _collect_ajax_servers(watch_html, watch_final or watch_url):
        result["servers"].append(
            {
                "name": "[{}p] {}".format(server["quality"], server["name"]),
                "url": server["url"],
                "type": "direct",
            }
        )

    if is_series:
        seen_eps = set()
        blocks_html = " ".join(re.findall(r'<div[^>]+class=[\"\'](?:Blocks-Episodes|Episode--List|seasons--episodes|Blocks-Container|List--Episodes|List--Seasons|episodes)[^>]*>(.*?)</section>', html, re.S | re.I)) or html
        for ep_url, ep_title in re.findall(r'<a[^>]+href="(https?://[^/]+/[^"]+)"[^>]+title="([^"]+)"', blocks_html, re.S):
            if ("الحلقة" not in ep_title and "حلقة" not in ep_title) or ep_url in seen_eps:
                continue
            if "series-" not in ep_url and "-season" not in ep_url and "-%d8%a7%d9%84%d9%85%d9%88%d8%b3%d9%85-" not in ep_url.lower():
                # Some basic protection against unrelated side-bar items if blocks_html is just `html`.
                continue
            seen_eps.add(ep_url)
            result["items"].append({"title": ep_title.strip(), "url": ep_url, "type": "episode", "_action": "details"})

    if not result["servers"]:
        for fallback in re.findall(r'data-(?:link|url|iframe|src|href)="([^"]+)"', watch_html or "", re.S):
            fallback = _decode_hidden_url(fallback)
            if not fallback.startswith("http"):
                continue
            if any(host in fallback for host in BLOCKED_HOSTS):
                continue
            if fallback not in [srv["url"] for srv in result["servers"]]:
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
Hosts supported: Streamtape, Doodstream, Vidbom, Upstream, Govid, Uqload, Mixdrop, Voe, etc.
"""

import re
import json
import time
import random  # FIX: moved import to top
import urllib.request
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor, HTTPSHandler
from urllib.parse import urljoin, urlparse, unquote, urlencode  # FIX: export urljoin
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

# Global session/opener with cookie support
_opener = None

def log(msg):
    """Central logging for device debugging"""
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = "[{}] {}\n".format(ts, msg)
        with open("/tmp/arabicplayer.log", "a") as f:
            f.write(line)
        print("[ArabicPlayer] {}".format(msg))
    except:
        pass

def _get_opener():
    global _opener
    if _opener:
        return _opener
    
    cj = cookiejar.CookieJar()
    
    # SSL context to ignore verification (required for many Arabic streaming sites)
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    except AttributeError:
        ctx = ssl._create_unverified_context()

    _opener = build_opener(
        HTTPCookieProcessor(cj), 
        HTTPSHandler(context=ctx)
    )
    
    return _opener


def _decode_response_body(raw, info):
    # Handle Compression
    ce = info.get('Content-Encoding', '').lower()
    if 'gzip' in ce:
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    elif 'deflate' in ce:
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except Exception:
            raw = zlib.decompress(raw)
    elif 'br' in ce and brotli is not None:
        raw = brotli.decompress(raw)

    # Handle Encoding
    charset = 'utf-8'
    ctype = info.get('Content-Type', '').lower()
    if 'charset=' in ctype:
        charset = ctype.split('charset=')[-1].split(';')[0].strip()

    try:
        return raw.decode(charset)
    except Exception:
        try:
            return raw.decode('utf-8', errors='ignore')
        except Exception:
            return raw.decode('latin-1', errors='ignore')

def fetch(url, referer=None, extra_headers=None, post_data=None):
    """Stable fetch: robust headers for ACE/Bot bypass and SSL handle"""
    try:
        opener = _get_opener()
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not referer:
            if "wecima" in domain or "mycima" in domain: referer = "https://wecima.click/"
            elif "fasel" in domain: referer = "https://www.faselhd.cam/"
            elif "topcinema" in domain: referer = "https://topcinemaa.com/"
            elif "shaheed" in domain: referer = "https://shaheeid4u.net/"
            elif "egydead" in domain or "x7k9f.sbs" in domain: referer = "https://x7k9f.sbs/"
            else: referer = "{}://{}/".format(parsed.scheme, domain)

        headers = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
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
        if any(x in url.lower() for x in ["ajax", "get__watch", "api/"]):
            headers.update({
                "X-Requested-With": "XMLHttpRequest", 
                "Accept": "application/json, text/javascript, */*; q=0.01", 
                "Sec-Fetch-Dest": "empty", 
                "Sec-Fetch-Mode": "cors"
            })
        if extra_headers: headers.update(extra_headers)
        
        data = post_data
        if data and isinstance(data, dict):
            data = urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif data and isinstance(data, str):
            data = data.encode("utf-8")

        log("Fetching: {}".format(url))
        req = Request(url, headers=headers, data=data)
        with opener.open(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            final_url = resp.geturl()
            info = resp.info()
            
            # ACE Redirection Check
            if "alliance4creativity.com" in final_url.lower() or "watch-it-legally" in final_url.lower():
                log("!!! ALERT: ACE Redirect detected for {} !!!".format(url))
                return None, final_url
            html = _decode_response_body(raw, info)
            
            log("Fetch Success: {} ({} bytes)".format(final_url, len(html)))
            return html, final_url
    except HTTPError as e:
        try:
            raw = e.read()
            html = _decode_response_body(raw, e.info()) if raw else ""
            log("Fetch HTTPError: {} -> {} {} ({} bytes)".format(url, e.code, e.reason, len(html)))
        except Exception:
            log("Fetch HTTPError: {} -> {} {}".format(url, getattr(e, "code", "?"), getattr(e, "reason", e)))
        return None, url
    except URLError as e:
        log("Fetch URLError: {} -> {}".format(url, e))
        global _opener
        _opener = None  # rebuild SSL context on next request
        return None, url
    except Exception as e:
        log("Fetch Error: {} -> {}".format(url, e))
        return None, url


def extract_iframes(html, base_url=""):
    """Return list of iframe src URLs from HTML"""
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    result = []
    for src in iframes:
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            parsed = urlparse(base_url)
            src = parsed.scheme + "://" + parsed.netloc + src
        if src.startswith("http"):
            result.append(src)
    return result


def find_m3u8(html):
    """Find m3u8 URL in page source with robust patterns"""
    if not html: return None
    patterns = [
        r'["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'hls\.loadSource\(["\']([^"\']+)["\']',
        r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'data-url=["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'data-src=["\']([^"\']+\.m3u8[^"\']*)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").strip()
            if url.startswith("//"): url = "https:" + url
            if url.startswith("http") and ".m3u8" in url:
                return url
    return None


def find_mp4(html):
    """Find mp4 URL in page source with robust patterns"""
    if not html: return None
    patterns = [
        r'["\']([^"\']+\.mp4[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
        r'data-url=["\']([^"\']+\.mp4[^"\']*)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").strip()
            if url.startswith("//"): url = "https:" + url
            if url.startswith("http") and ".mp4" in url:
                return url
    return None


def _best_media_url(text):
    """Pick the best visible video source from plain or unpacked JS."""
    candidates = []
    seen = set()
    patterns = [
        r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
        r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)',
    ]

    def score(url):
        lowered = url.lower()
        if "2160" in lowered or "4k" in lowered:
            return 5000
        if "1080" in lowered or "fhd" in lowered:
            return 4000
        if "720" in lowered or "hd" in lowered:
            return 3000
        if "480" in lowered:
            return 2000
        if "360" in lowered:
            return 1000
        if "240" in lowered or "sd" in lowered:
            return 500
        if ".m3u8" in lowered:
            return 3500
        return 100

    for pat in patterns:
        for match in re.findall(pat, text or "", re.I):
            url = match.replace("\\/", "/").replace("&amp;", "&")
            if url in seen:
                continue
            seen.add(url)
            candidates.append((score(url), url))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _extract_packer_blocks(html):
    """Return likely Dean Edwards packer blocks even when regex would stop early."""
    blocks = []
    marker = "eval(function(p,a,c,k,e,d){"
    tail = ".split('|')))"
    pos = 0
    while True:
        start = (html or "").find(marker, pos)
        if start == -1:
            break
        end = (html or "").find(tail, start)
        if end == -1:
            break
        blocks.append(html[start:end + len(tail)])
        pos = end + len(tail)
    return blocks


def decode_packer(packed):
    """Decodes Dean Edwards Packer compressed JS"""
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
        
        def e(c):
            result = ""
            while True:
                result = "0123456789abcdefghijklmnopqrstuvwxyz"[c % a] + result
                c = c // a
                if c == 0:
                    break
            return result
        
        d = {}
        for i in range(c):
            d[e(i)] = k[i] or e(i)
            
        return re.sub(r'\b(\w+)\b', lambda x: d.get(x.group(1), x.group(1)), p)
    except:
        return ""


def find_packed_links(html):
    """Find video links inside Packer-obfuscated JS"""
    evals = _extract_packer_blocks(html)
    if not evals:
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
    for ev in evals:
        dec = decode_packer(ev)
        if dec:
            res = find_m3u8(dec) or find_mp4(dec)
            if res: return res
    return None


# ─── Video Host Resolvers ────────────────────────────────────────────────────

def resolve_streamtape(url):
    """Extract from streamtape.com"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        # Streamtape obfuscates the link in two parts
        m = re.search(r"robotlink\)\.innerHTML = '([^']+)'\s*\+\s*'([^']+)'", html)
        if m:
            link = m.group(1) + m.group(2)
            link = link.replace("//streamtape.com", "https://streamtape.com")
            if not link.startswith("http"):
                link = "https:" + link
            return link
        # Alternative pattern
        m = re.search(r'(/get_video\?[^"\'&\s]+)', html)
        if m:
            return "https://streamtape.com" + m.group(1)
    except Exception:
        pass
    return None


def resolve_doodstream(url):
    """Extract from dood.* / doodstream / dsvplay and variants"""
    try:
        # Normalize dood domains to dood.re
        dood_base = "https://dood.re"
        # Try multiple domain patterns
        for pat, domain in [
            (r'dood\.[a-z]+', 'dood.re'),
            (r'dsvplay\.[a-z]+', 'dood.re'),
            (r'd0o0d\.[a-z]+', 'dood.re'),
        ]:
            url_try = re.sub(pat, domain, url)
            html, final_url = fetch(url_try)
            if html:
                break
        else:
            html, final_url = fetch(url)
        if not html:
            return None

        m = re.search(r'\$\.get\(["\'](/pass_md5/[^"\']+)["\']', html)
        if not m:
            m = re.search(r'pass_md5/([^"\'\.\s&]+)', html)
            if m:
                pass_path = "/pass_md5/" + m.group(1)
            else:
                return None
        else:
            pass_path = m.group(1)

        pass_url = dood_base + pass_path
        token_html, _ = fetch(pass_url, referer=url)
        if not token_html:
            return None
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        rand = "".join(random.choice(chars) for _ in range(10))  # FIX: use top-level random
        return token_html.strip() + rand + "?token=" + pass_path.split("/")[-1] + "&expiry=" + str(int(time.time() * 1000))
    except Exception:
        pass
    return None


def resolve_vidbom(url):
    """Extract from vidbom.com / vidshare.tv and similar"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        m3u8 = find_m3u8(html)
        if m3u8:
            return m3u8
        mp4 = find_mp4(html)
        return mp4
    except Exception:
        pass
    return None


def resolve_uqload(url):
    """Extract from uqload.co"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        m = re.search(r'sources:\s*\["([^"]+)"\]', html)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def resolve_govid(url):
    """Extract from govid.me"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_upstream(url):
    """Extract from upstream.to"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_mixdrop(url):
    """Extract from mixdrop.co / .top (handles Packer)"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        
        # 1. Try plain text first
        m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', html)
        if m:
            link = m.group(1)
            return ("https:" + link) if link.startswith("//") else link
            
        # 2. Try Packer
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
        for ev in evals:
            dec = decode_packer(ev)
            if dec:
                m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', dec)
                if m:
                    link = m.group(1)
                    return ("https:" + link) if link.startswith("//") else link
    except Exception:
        pass
    return None

def resolve_voe(url):
    """Extract from voe.sx — uses obfuscated JS"""
    try:
        html, final = fetch(url, referer="https://x7k9f.sbs/")
        if not html:
            return None
        # Pattern 1: hls key in JS object
        for pat in [r"'hls'\s*:\s*'([^']+)'", r'"hls"\s*:\s*"([^"]+)"',
                    r"sources\s*=\s*\[\s*\{[^}]*file\s*:\s*'([^']+)'"]:
            m = re.search(pat, html)
            if m:
                return m.group(1)
        # Pattern 2: atob encoded
        import base64
        for enc in re.finditer(r"atob\(['\"]([A-Za-z0-9+/=]+)['\"]\)", html):
            try:
                dec = base64.b64decode(enc.group(1) + "==").decode("utf-8", errors="ignore")
                if "http" in dec:
                    mm = re.search(r"(https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*)", dec)
                    if mm:
                        return mm.group(1)
            except Exception:
                pass
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None

def resolve_streamruby(url):
    """Extract from streamruby.com / stmruby.com"""
    try:
        html, _ = fetch(url)
        if not html: return None
        # Pattern 1: Plain text
        m = find_m3u8(html) or find_mp4(html)
        if m: return m
        # Pattern 2: Packed JS
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
        for ev in evals:
            dec = decode_packer(ev)
            if dec:
                m = find_m3u8(dec) or find_mp4(dec)
                if m: return m
    except: pass
    return None

def resolve_hgcloud(url):
    """Extract from hgcloud.to / masukestin.me"""
    try:
        html, _ = fetch(url)
        if not html: return None
        return find_m3u8(html) or find_mp4(html)
    except: pass
    return None


def resolve_vidtube(url):
    """Extract direct MP4/HLS from vidtube.one embeds."""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        if "restricted for this domain" in html.lower():
            html = None
            for _ in range(2):
                html, _ = fetch(url, referer="https://topcinema.fan/")
                if html:
                    break
            if not html:
                return None

        direct = _best_media_url(html)
        if direct:
            return direct

        for ev in _extract_packer_blocks(html):
            dec = decode_packer(ev)
            if not dec:
                continue
            direct = _best_media_url(dec)
            if direct:
                return direct
    except Exception:
        pass
    return None

HOST_RESOLVERS = {
    "streamtape": resolve_streamtape,
    "dood":       resolve_doodstream,
    "dsvplay":    resolve_doodstream,
    "vidbom":     resolve_vidbom,
    "vidshare":   resolve_vidbom,
    "uqload":     resolve_uqload,
    "govid":      resolve_govid,
    "upstream":   resolve_upstream,
    "mixdrop":    resolve_mixdrop,
    "voe":        resolve_voe,
    "streamruby": resolve_streamruby,
    "hgcloud":    resolve_hgcloud,
    "masukestin": resolve_hgcloud,
    "vidtube":    resolve_vidtube,
}
def resolve_generic_embed(url):
    """Generic resolver for embed hosts — tries m3u8/mp4 directly then iframes"""
    try:
        html, final = fetch(url, referer="https://x7k9f.sbs/")
        if not html:
            return None
        result = find_m3u8(html) or find_mp4(html)
        if result:
            return result
        # Try Packer-obfuscated JS
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
        for ev in evals:
            dec = decode_packer(ev)
            if dec:
                result = find_m3u8(dec) or find_mp4(dec)
                if result:
                    return result
        # Follow iframes one level
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        for ifr in iframes:
            if ifr.startswith("//"): ifr = "https:" + ifr
            h2, _ = fetch(ifr, referer=url)
            if h2:
                result = find_m3u8(h2) or find_mp4(h2)
                if result:
                    return result
    except Exception:
        pass
    return None


# ─── Host Dispatcher ─────────────────────────────────────────────────────────

# ─── Multi-Provider Resolvers (TMDB Based) ──────────────────────────────────

def _get_stream_moviesapi(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://moviesapi.club/api/v1/movies/{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://moviesapi.club/api/v1/tv/{}/{}/{}".format(tmdb_id, s, e)
    body, _ = fetch(url, extra_headers={"Accept": "application/json"})
    if not body: return None
    try:
        data = json.loads(body)
        sources = data.get("sources") or []
        for src in sources:
            f = src.get("file") or src.get("url") or ""
            if ".m3u8" in f: return f
        for src in sources:
            f = src.get("file") or src.get("url") or ""
            if f.startswith("http"): return f
    except: pass
    return find_m3u8(body) or find_mp4(body)

def _get_stream_multiembed(tmdb_id, m_type, season=None, episode=None):
    url = "https://multiembed.mov/directstream.php?video_id={}&tmdb=1".format(tmdb_id)
    if season and episode: url += "&s={}&e={}".format(season, episode)
    html, final = fetch(url)
    if not html: return None
    if final != url and final.startswith("http"):
        if ".m3u8" in final: return final
        h2, _ = fetch(final, referer=url)
        if h2:
            m = find_m3u8(h2)
            if m: return m
    return find_m3u8(html) or find_mp4(html)

def _get_stream_superembed(tmdb_id, m_type, season=None, episode=None):
    url = "https://getsuperembed.link/?video_id={}&tmdb=1".format(tmdb_id)
    if season and episode: url += "&s={}&e={}".format(season, episode)
    body, final = fetch(url)
    if not body: return None
    body = body.strip()
    if body.startswith("http") and len(body) < 500:
        h2, _ = fetch(body, referer=url)
        if h2: return find_m3u8(h2) or find_mp4(h2)
        return body
    try:
        data = json.loads(body)
        for k in ["url", "link", "src", "stream"]:
            if k in data and data[k]: return data[k]
    except: pass
    mm = re.search(r'(https?://[^\s"\'<>]{10,})', body)
    return mm.group(1) if mm else None

def _get_stream_2embed(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://www.2embed.cc/embedtmdb/{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://www.2embed.cc/embedtvtmdb/{}&s={}&e={}".format(tmdb_id, s, e)
    html, _ = fetch(url)
    if not html: return None
    for iframe in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
        if iframe.startswith("//"): iframe = "https:" + iframe
        if iframe.startswith("http"):
            h2, _ = fetch(iframe, referer=url)
            if h2:
                m = find_m3u8(h2)
                if m: return m
    return find_m3u8(html) or find_mp4(html)

def _get_stream_autoembed(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://autoembed.cc/movie/tmdb-{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://autoembed.cc/tv/tmdb-{}-{}-{}".format(tmdb_id, s, e)
    html, _ = fetch(url)
    if not html: return None
    return find_m3u8(html) or find_mp4(html)

def _get_stream_vidsrc(tmdb_id, m_type, season=None, episode=None):
    """FIX: Added resolver for vidsrc:// scheme"""
    if m_type == "movie":
        url = "https://vidsrc.me/embed/movie/{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://vidsrc.me/embed/tv/{}/{}/{}".format(tmdb_id, s, e)
    html, _ = fetch(url, referer="https://vidsrc.me/")
    if not html:
        return None
    # Try to find iframe redirect or direct source
    m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    if m:
        iframe_url = m.group(1)
        if iframe_url.startswith("//"): iframe_url = "https:" + iframe_url
        h2, _ = fetch(iframe_url, referer=url)
        if h2:
            return find_m3u8(h2) or find_mp4(h2)
    return find_m3u8(html) or find_mp4(html)

_PREMIUM_METHODS = {
    "moviesapi":   _get_stream_moviesapi,
    "multiembed":  _get_stream_multiembed,
    "superembed":  _get_stream_superembed,
    "2embed":      _get_stream_2embed,
    "autoembed":   _get_stream_autoembed,
    "vidsrc":      _get_stream_vidsrc,   # FIX: added vidsrc handler
}

def get_premium_servers(m_type, tmdb_id, season=None, episode=None):
    """Return a list of premium multi-provider servers as dicts"""
    res = []
    suffix = ""
    if season and episode:
        suffix = ":{}:{}".format(season, episode)
    
    res.append({"name": "Premium: AutoEmbed 🚀",  "url": "autoembed://{}:{}{}".format(m_type, tmdb_id, suffix)})
    res.append({"name": "Premium: VidSrc 🔥",     "url": "vidsrc://{}:{}{}".format(m_type, tmdb_id, suffix)})
    return res

# ─── Updated Dispatcher ──────────────────────────────────────────────────────

def resolve_host(url, referer=None):
    """Auto-detect host and resolve to direct stream URL"""
    # 1. Custom URI Schemes
    m = re.match(r'(\w+)://(movie|series|tv|episode):(\d+)(?::(\d+):(\d+))?', url)
    if m:
        method_name, m_type, tmdb_id, season, episode = m.groups()
        m_type = "movie" if m_type in ("movie", "film") else "series"
        if method_name in _PREMIUM_METHODS:
            return _PREMIUM_METHODS[method_name](tmdb_id, m_type, season, episode)
        elif method_name == "auto":
            for name, func in _PREMIUM_METHODS.items():
                try:
                    res = func(tmdb_id, m_type, season, episode)
                    if res: return res
                except: pass
            return None

    # 2. Domain Dispatch
    domain = urlparse(url).netloc.lower()
    log("Resolving host: {} (URL: {})".format(domain, url))
    if "streamruby" in domain:
        return resolve_streamruby(url)
    if "hgcloud" in domain or "masukestin" in domain:
        return resolve_hgcloud(url)

    for key, resolver in HOST_RESOLVERS.items():
        if key in domain:
            log("Using resolver: {}".format(key))
            return resolver(url)
    
    # Generic fallback
    log("Using generic fallback for: {}".format(domain))
    html, final_url = fetch(url, referer=referer or url)
    if not html: 
        log("Generic fallback failed: No HTML")
        return None
    res = find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    if res: 
        log("Generic fallback success: {}".format(res))
        return res
    
    evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
    log("Found {} packed scripts".format(len(evals)))
    for ev in evals:
        dec = decode_packer(ev)
        if dec:
            r = find_m3u8(dec) or find_mp4(dec)
            if r: 
                log("Packer success: {}".format(r))
                return r
            
    log("All resolution attempts failed for: {}".format(url))
    return None



def resolve_iframe_chain(url, referer=None, depth=0, max_depth=6):
    """
    Follows a chain of iframes/redirects to find a playable stream.
    Supports src, data-src, data-url attributes.
    """
    if depth > max_depth: return None, ""
    
    html, final_url = fetch(url, referer=referer)
    if not html: return None, ""
    
    domain = urlparse(final_url or url).netloc.lower()
    
    # 1. Check for stream in current HTML
    stream = find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    if stream: return stream, domain
    
    # 2. Look for iframes (src, data-src, data-url)
    iframes = re.findall(r'<(?:iframe|embed|frame)[^>]+(?:src|data-src|data-url)=["\']([^"\']+)["\']', html, re.I)
    for iframe in iframes:
        if iframe.startswith("//"): iframe = "https:" + iframe
        if not iframe.startswith("http"):
            if iframe.startswith("/"):
                p = urlparse(final_url or url)
                iframe = "{}://{}{}".format(p.scheme, p.netloc, iframe)
            else:
                continue
        
        # Avoid common ad iframes or social trackers
        if any(x in iframe.lower() for x in ["facebook", "twitter", "googletag", "ads", "analytics", "doubleclick"]):
            continue
            
        res, h = resolve_iframe_chain(iframe, referer=url, depth=depth+1, max_depth=max_depth)
        if res: return res, h
        
    return None, ""


def extract_stream(url):
    """Standard wrapper for plugin to get (URL, Quality, FinalReferer)"""
    log("--- Starting Extraction for: {} ---".format(url))
    raw_url = (url or "").strip()
    if not raw_url:
        return None, "", url

    piped_headers = {}
    main_url = raw_url
    if "|" in raw_url:
        main_url, raw_headers = raw_url.split("|", 1)
        for part in raw_headers.split("&"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            piped_headers[key.strip()] = value.strip()

    lower_main_url = main_url.lower()
    if main_url.startswith("http") and any(ext in lower_main_url for ext in (".m3u8", ".mp4", ".mkv", ".mp3")):
        referer = piped_headers.get("Referer")
        if not referer:
            parsed = urlparse(main_url)
            referer = "{}://{}/".format(parsed.scheme, parsed.netloc)
        log("Extraction DIRECT URL shortcut: {}".format(main_url))
        q = "1080p" if "1080" in lower_main_url else ("720p" if "720" in lower_main_url else "HD")
        return raw_url, q, referer

    # 1. Resolve host with redirection tracking
    _, final_referer = fetch(main_url, referer=piped_headers.get("Referer"))
    if not final_referer: # Check if fetch itself failed to get a final URL
        return None, "", main_url # Return original URL as referer if no final_referer
        
    stream = resolve_host(main_url, referer=piped_headers.get("Referer"))
    if not stream:
        log("Initial resolve_host failed, trying resolve_iframe_chain")
        # Try recursive chain if domain dispatch failed
        stream, h = resolve_iframe_chain(main_url, referer=piped_headers.get("Referer"), depth=0)
        
    if stream:
        log("Extraction SUCCESS: {}".format(stream))
        q = "1080p" if "1080" in stream else ("720p" if "720" in stream else "HD")
        return stream, q, final_referer
    
    log("Extraction FINAL FAILURE for: {}".format(main_url))
    return None, "", final_referer
````

## File: extractors/egydead.py
````python
# -*- coding: utf-8 -*-
"""
EgyDead extractor for the current Next.js site.
Domain: egydead.today
"""

import json
import base64
import re
import sys

from .base import fetch, log, _extract_packer_blocks, decode_packer

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urljoin
    from html import unescape as html_unescape
else:
    from urllib import quote_plus
    from urlparse import urljoin
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape


DOMAINS = [
    "https://www.egydead.today/",
    "https://egydead.today/",
]
BASE_URL = None
MAX_EPISODES = 350
VIDTUBE_QUALITY_LABELS = {
    "h": "720p",
    "n": "480p",
    "l": "360p",
    "x": "1080p",
}
VIDTUBE_QUALITY_ORDER = ("h", "n", "l", "x")
FORCE_TOPCINEMA_API_FIRST = True
DISABLE_VIDKING_WHEN_TOPCINEMA_EXISTS = True


def _get_base():
    global BASE_URL
    if BASE_URL:
        return BASE_URL
    BASE_URL = DOMAINS[0]
    return BASE_URL


def _strip_html(text):
    if not text:
        return ""
    text = html_unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def _img(path, size="w342"):
    if not path:
        return ""
    path = str(path).strip()
    if path.startswith("http"):
        return path
    if path.startswith("//"):
        return "https:" + path
    if not path.startswith("/"):
        path = "/" + path
    return "https://image.tmdb.org/t/p/{0}{1}".format(size, path)


def _extract_next_data(html):
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception as exc:
        log("EgyDead: __NEXT_DATA__ parse failed: {}".format(exc))
        return {}


def _clean_title_text(text):
    text = _strip_html(text)
    if not text:
        return ""
    text = text.replace("EgyDead", " ")
    text = re.sub(r"\s*[-|]\s*EgyDead.*$", "", text, flags=re.I)
    year_split = re.split(r"\(\s*(?:19|20|21)\d{2}\s*\)|\b(?:19|20|21)\d{2}\b", text, 1)
    if year_split and year_split[0].strip():
        text = year_split[0]
    text = re.sub(r"\b(?:مترجم(?:ة)?|مدبلج(?:ة)?|اون لاين|أون لاين|كامل)\b", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" -|")


def _meta_description(html):
    if not html:
        return ""
    for pattern in (
        r'property="og:description"[^>]+content="([^"]+)"',
        r'name="description"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:description"',
        r'<meta[^>]+content="([^"]+)"[^>]+name="description"',
    ):
        match = re.search(pattern, html, re.I)
        if match:
            text = _strip_html(match.group(1))
            if text:
                return text
    return ""


def _meta_title(html):
    if not html:
        return ""
    for pattern in (
        r'property="og:title"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:title"',
        r'<title>(.*?)</title>',
        r'<h1[^>]*>(.*?)</h1>',
    ):
        match = re.search(pattern, html, re.S | re.I)
        if match:
            text = _clean_title_text(match.group(1))
            if text:
                return text
    return ""


def _meta_image(html):
    if not html:
        return ""
    for pattern in (
        r'property="og:image"[^>]+content="([^"]+)"',
        r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"',
    ):
        match = re.search(pattern, html, re.I)
        if match:
            image = match.group(1).strip()
            if image:
                return _img(image)
    return ""


def _json_ld_object(html):
    scripts = re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        html or "",
        re.S | re.I,
    )
    for script in scripts:
        if not script:
            continue
        try:
            data = json.loads(script)
        except Exception:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") in ("Movie", "TVSeries", "TVEpisode"):
                    return item
        if isinstance(data, dict):
            if data.get("@type") in ("Movie", "TVSeries", "TVEpisode"):
                return data
            graph = data.get("@graph") or []
            for item in graph:
                if isinstance(item, dict) and item.get("@type") in ("Movie", "TVSeries", "TVEpisode"):
                    return item
    return {}


def _year_from_text(text):
    match = re.search(r'\b(19\d{2}|20\d{2}|21\d{2})\b', text or "")
    return match.group(1) if match else ""


def _page_props(data):
    return (((data or {}).get("props") or {}).get("pageProps") or {})


def _year_from_entry(entry):
    value = (
        entry.get("release_date")
        or entry.get("first_air_date")
        or entry.get("air_date")
        or ""
    )
    value = str(value)
    return value[:4] if len(value) >= 4 else ""


def _rating_text(value):
    try:
        rating = float(value)
        if rating <= 0:
            return ""
        return "{0:.1f}".format(rating)
    except Exception:
        return ""


def _unique_titles(*values):
    seen = set()
    res = []
    for value in values:
        value = _strip_html(value)
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        res.append(value)
    return res


def _title_variants(*values):
    variants = []
    seen = set()
    for value in values:
        base = _clean_title_text(value)
        for candidate in (
            base,
            re.sub(r"[:|_\-]+", " ", base or "").strip(),
            re.sub(r"\b(?:part|season|episode)\b.*$", "", (base or ""), flags=re.I).strip(),
        ):
            candidate = re.sub(r"\s+", " ", candidate or "").strip(" -|")
            if not candidate:
                continue
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            variants.append(candidate)
    return variants


def _detail_result(url, title, poster, plot, year, rating, item_type):
    return {
        "url": url,
        "title": title or "",
        "poster": poster or "",
        "plot": plot or "",
        "year": year or "",
        "rating": rating or "",
        "servers": [],
        "items": [],
        "type": item_type,
    }


def _entry_to_item(entry, forced_type=None):
    if not isinstance(entry, dict):
        return None

    media_type = forced_type or entry.get("media_type")
    if media_type not in ("movie", "tv"):
        if entry.get("title") or entry.get("release_date"):
            media_type = "movie"
        else:
            media_type = "tv"

    item_id = entry.get("id")
    title = _strip_html(entry.get("title") or entry.get("name") or "")
    if not item_id or not title:
        return None

    if media_type == "movie":
        rel_url = "/movie/{0}".format(item_id)
        item_type = "movie"
    else:
        rel_url = "/tv/{0}".format(item_id)
        item_type = "series"

    return {
        "title": title,
        "url": urljoin(_get_base(), rel_url),
        "poster": _img(entry.get("poster_path") or entry.get("poster")),
        "type": item_type,
        "_action": "details",
    }


def _items_from_page_props(props):
    items = []
    seen = set()

    for entry in props.get("results") or []:
        item = _entry_to_item(entry, entry.get("media_type"))
        if item and item["url"] not in seen:
            seen.add(item["url"])
            items.append(item)

    for entry in props.get("initialMovies") or []:
        item = _entry_to_item(entry, "movie")
        if item and item["url"] not in seen:
            seen.add(item["url"])
            items.append(item)

    for entry in props.get("initialSeries") or []:
        item = _entry_to_item(entry, "tv")
        if item and item["url"] not in seen:
            seen.add(item["url"])
            items.append(item)

    return items


def _parse_cards(html):
    items = []
    seen = set()
    base = _get_base()
    regex = (
        r'<a[^>]+class="[^"]*movie-card[^"]*"[^>]+href="([^"]+)"[^>]*>'
        r'(.*?)</a>'
    )
    for href, block in re.findall(regex, html, re.S | re.I):
        if "/movie/" not in href and "/tv/" not in href:
            continue
        full_url = urljoin(base, href)
        if full_url in seen:
            continue

        mtype = "movie" if "/movie/" in href else "series"
        title = ""
        poster = ""

        m = re.search(r'alt="([^"]+)"', block, re.I)
        if m:
            title = _strip_html(m.group(1))
        if not title:
            m = re.search(r'class="card-title"[^>]*>(.*?)</div>', block, re.S | re.I)
            if m:
                title = _strip_html(m.group(1))

        m = re.search(r'<img[^>]+src="([^"]+)"', block, re.I)
        if m:
            poster = _img(m.group(1))

        if not title:
            continue

        seen.add(full_url)
        items.append(
            {
                "title": title,
                "url": full_url,
                "poster": poster,
                "type": mtype,
                "_action": "details",
            }
        )
    return items


def _fetch_json(url):
    body, _ = fetch(
        url,
        extra_headers={
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    if not body:
        return None
    try:
        return json.loads(body)
    except Exception as exc:
        log("EgyDead: JSON parse failed for {}: {}".format(url, exc))
        return None


def _topcinema_lookup(content_type, season, episode, year, titles):
    base = _get_base().rstrip("/")
    title_variants = _title_variants(*(titles or []))
    if not title_variants:
        title_variants = _unique_titles(*(titles or []))

    for title in title_variants:
        movie_years = [year] if year else []
        if content_type == "movie":
            movie_years.append("")
        else:
            movie_years = [""]

        for movie_year in movie_years:
            api_url = "{0}/api/topcinema-links?title={1}&type={2}".format(
                base,
                quote_plus(title),
                content_type,
            )
            if content_type == "movie" and movie_year:
                api_url += "&year={0}".format(quote_plus(movie_year))
            if content_type == "tv":
                api_url += "&season={0}&episode={1}".format(season or 1, episode or 1)

            data = _fetch_json(api_url)
            if data and data.get("success") and data.get("iframe_url"):
                return data
    return None


def _watch_url(content_type, tmdb_id, season=None, episode=None):
    base = _get_base().rstrip("/")
    if content_type == "movie":
        return "{0}/watch/movie/{1}".format(base, tmdb_id)
    return "{0}/watch/tv/{1}/{2}/{3}".format(base, tmdb_id, season or 1, episode or 1)


def _extract_player_src(html):
    m = re.search(r'<iframe[^>]+id="player"[^>]+src="([^"]+)"', html, re.I)
    if not m:
        m = re.search(r'<iframe[^>]+src="([^"]+)"', html, re.I)
    if not m:
        return ""
    return m.group(1).strip()




def _extract_player_sources(html):
    out = []
    seen = set()
    if not html:
        return out

    patterns = [
        r'<iframe[^>]+src="([^"]+)"',
        r"<iframe[^>]+src='([^']+)'",
        r'data-src="([^"]+)"',
        r"data-src='([^']+)'",
        r'"src"\s*:\s*"([^"]+embed[^"]+)"',
        r"'src'\s*:\s*'([^']+embed[^']+)'",
        r'(https?://[^\s"\']+(?:vidtube|vidking|viking)[^\s"\']*)',
    ]
    for pat in patterns:
        for u in re.findall(pat, html, re.I | re.S):
            u = (u or "").replace("\\/", "/").strip()
            if not u:
                continue
            if u.startswith("//"):
                u = "https:" + u
            if u not in seen:
                out.append(u)
                seen.add(u)
    return out

def _vidtube_quality_servers(embed_url):
    html, _ = fetch(embed_url, referer="https://topcinema.fan/")
    if not html:
        html, _ = fetch(embed_url, referer="https://topcinema.fan/")
    if not html:
        html, _ = fetch(embed_url, referer=_get_base())
    if not html:
        return []

    texts = [html]
    for ev in _extract_packer_blocks(html):
        dec = decode_packer(ev)
        if dec:
            texts.append(dec)

    found = {}

    def _store(code, media_url):
        code = (code or "").lower().strip()
        media_url = (media_url or "").replace("\\/", "/").replace("&amp;", "&").strip()
        if not code or not media_url or code in found:
            return
        found[code] = media_url

    for text in texts:
        if not text:
            continue

        for media_url in re.findall(r'(https?://[^\s"\'<>]+(?:\.mp4|\.m3u8)[^\s"\'<>]*)', text, re.I):
            q = ""
            qmatch = re.search(r'[_/\-]([xhln])(?:\.mp4|\.m3u8)', media_url, re.I)
            if qmatch:
                q = qmatch.group(1).lower()
            else:
                qmatch = re.search(r'(1080|720|480|360)', media_url)
                if qmatch:
                    q = {"1080":"x", "720":"h", "480":"n", "360":"l"}.get(qmatch.group(1), "")
            _store(q, media_url)

        for label, media_url in re.findall(r'"label"\s*:\s*"?(1080p|720p|480p|360p)"?\s*,\s*"file"\s*:\s*"([^"]+)"', text, re.I):
            code = {"1080p":"x", "720p":"h", "480p":"n", "360p":"l"}.get(label.lower(), "")
            _store(code, media_url)

        for media_url, label in re.findall(r'"(?:file|src)"\s*:\s*"([^"]+)"[^}]{0,120}"(?:label|res|quality)"\s*:\s*"?(1080p|720p|480p|360p)"?', text, re.I | re.S):
            code = {"1080p":"x", "720p":"h", "480p":"n", "360p":"l"}.get(label.lower(), "")
            _store(code, media_url)

    servers = []
    for code in ("x", "h", "n", "l"):
        if code not in found:
            continue
        label = VIDTUBE_QUALITY_LABELS.get(code, code.upper())
        servers.append({
            "name": "VidTube {}".format(label),
            "url": "{}|Referer={}".format(found[code], embed_url),
            "type": "direct",
        })
    return servers

def _server_candidates(content_type, tmdb_id, season=None, episode=None):
    if content_type == "movie":
        return [
            ("VidKing", "https://www.vidking.net/embed/movie/{0}".format(tmdb_id)),
        ]
    return [
        (
            "VidKing",
            "https://www.vidking.net/embed/tv/{0}/{1}/{2}".format(
                tmdb_id, season or 1, episode or 1
            ),
        ),
    ]


def _topcinema_fallback_servers(content_type, titles, year="", season=None, episode=None):
    try:
        from . import topcinema as topmod
    except Exception as exc:
        log("EgyDead TopCinema import failed: {}".format(exc))
        return []

    title_variants = _title_variants(*(titles or []))
    if not title_variants:
        title_variants = _unique_titles(*(titles or []))

    def _norm(s):
        s = _strip_html(s or "").lower()
        s = re.sub(r'[^a-z0-9\u0600-\u06ff ]+', ' ', s)
        return re.sub(r'\s+', ' ', s).strip()

    want_year = str(year or "").strip()
    wanted = [_norm(t) for t in title_variants if t]
    out = []
    seen = set()

    def _push(name, url):
        url = (url or "").strip()
        if not url or url in seen:
            return
        out.append({"name": name, "url": url, "type": "direct"})
        seen.add(url)

    def _extract_iframe_from_server(server_url):
        try:
            if not server_url.startswith("topcinema_server|"):
                return ""
            parts = server_url.split("|")
            ajax_url = parts[1]
            post_id = parts[2]
            server_index = parts[3]
            referer_url = parts[4] if len(parts) > 4 else getattr(topmod, "MAIN_URL", "")

            html, _ = topmod.fetch(
                ajax_url,
                referer=referer_url,
                extra_headers={"X-Requested-With": "XMLHttpRequest"},
                post_data={"id": post_id, "i": server_index}
            )
            m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html or "", re.I)
            if not m:
                return ""
            iframe = m.group(1).replace("\\/", "/").strip()
            if iframe.startswith("//"):
                iframe = "https:" + iframe
            return iframe
        except Exception as exc:
            log("EgyDead TopCinema iframe extraction failed: {}".format(exc))
            return ""

    for raw_title in title_variants[:6]:
        query = raw_title
        if content_type == "movie" and want_year:
            query = "{} {}".format(raw_title, want_year)

        try:
            results = topmod.search(query, 1) or []
        except Exception as exc:
            log("EgyDead TopCinema search failed for {}: {}".format(query, exc))
            continue

        for item in results[:12]:
            item_title = _norm(item.get("title") or "")
            if wanted and not any(w in item_title or item_title in w for w in wanted):
                continue

            try:
                page = topmod.get_page(item.get("url"))
            except Exception as exc:
                log("EgyDead TopCinema get_page failed: {}".format(exc))
                continue

            for srv in (page or {}).get("servers", []):
                sname = (srv.get("name") or "")
                surl = (srv.get("url") or "")
                low_name = sname.lower()

                # أولًا: متعدد الجودات / VidTube
                if ("vidtube" in low_name) or (u"متعدد الجودات" in sname) or ("multiple" in low_name):
                    iframe_url = _extract_iframe_from_server(surl)
                    log("EgyDead TopCinema iframe_url={}".format(iframe_url))
                    if iframe_url and "vidtube" in iframe_url.lower():
                        try:
                            qservers = _vidtube_quality_servers(iframe_url)
                        except Exception as exc:
                            log("EgyDead VidTube quality extraction failed: {}".format(exc))
                            qservers = []

                        if qservers:
                            for qs in qservers:
                                qurl = qs.get("url") or ""
                                if qurl and qurl not in seen:
                                    out.append(qs)
                                    seen.add(qurl)
                            if out:
                                return out
                        elif iframe_url:
                            _push("VidTube", iframe_url)
                            return out

                # fallback لباقي السيرفرات
                try:
                    resolved = topmod.extract_stream(surl)
                except Exception as exc:
                    log("EgyDead TopCinema extract_stream failed: {}".format(exc))
                    continue

                stream_url = ""
                if isinstance(resolved, tuple):
                    stream_url = resolved[0] or ""
                else:
                    stream_url = resolved or ""

                if not stream_url:
                    continue
                if stream_url.startswith("//"):
                    stream_url = "https:" + stream_url

                if "vidtube" in stream_url.lower():
                    try:
                        qservers = _vidtube_quality_servers(stream_url)
                    except Exception as exc:
                        log("EgyDead VidTube quality extraction failed: {}".format(exc))
                        qservers = []

                    if qservers:
                        for qs in qservers:
                            qurl = qs.get("url") or ""
                            if qurl and qurl not in seen:
                                out.append(qs)
                                seen.add(qurl)
                        if out:
                            return out
                    else:
                        _push("VidTube", stream_url)
                        return out
                elif "vidking" not in stream_url.lower() and "viking" not in stream_url.lower():
                    _push("TopCinema", stream_url)

        if out:
            return out

    return out

def _vidking_resolve(embed_url):
    embed_url = (embed_url or "").strip()
    if not embed_url:
        return None, None, _get_base()

    html, _ = fetch(embed_url, referer=_get_base(), extra_headers={
        "Referer": _get_base(),
        "Origin": "https://www.vidking.net",
        "X-Requested-With": "XMLHttpRequest",
    })
    if not html:
        return embed_url, None, _get_base()

    texts = [html]

    # packed/eval blocks
    for block in _extract_packer_blocks(html):
        try:
            dec = decode_packer(block)
        except Exception:
            dec = ""
        if dec:
            texts.append(dec)

    # atob("...")
    for b64 in re.findall(r'atob\(["\']([A-Za-z0-9+/=]{40,})["\']\)', html, re.I):
        try:
            dec = base64.b64decode(b64).decode("utf-8", "ignore")
        except Exception:
            dec = ""
        if dec:
            texts.append(dec)

    # obvious base64-ish strings inside quotes
    for b64 in re.findall(r'["\']([A-Za-z0-9+/=]{120,})["\']', html):
        try:
            dec = base64.b64decode(b64).decode("utf-8", "ignore")
        except Exception:
            dec = ""
        if dec and ("m3u8" in dec or "mp4" in dec or "source" in dec or "file" in dec):
            texts.append(dec)

    patterns = [
        r'<source[^>]+src=["\']([^"\']+(?:m3u8|mp4)[^"\']*)["\']',
        r'<iframe[^>]+src=["\']([^"\']+)["\']',
        r'"file"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        r"'file'\s*:\s*'([^']+(?:m3u8|mp4)[^']*)'",
        r'"src"\s*:\s*"([^"]+(?:m3u8|mp4)[^"]*)"',
        r"'src'\s*:\s*'([^']+(?:m3u8|mp4)[^']*)'",
        r'"hls"\s*:\s*"([^"]+)"',
        r"'hls'\s*:\s*'([^']+)'",
        r'"playlist"\s*:\s*"([^"]+)"',
        r"'playlist'\s*:\s*'([^']+)'",
        r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
        r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
    ]

    found = []
    seen = set()

    def _add(u):
        u = (u or "").replace("\\/", "/").replace("\\u0026", "&").replace("&amp;", "&").strip()
        if not u:
            return
        if u.startswith("//"):
            u = "https:" + u
        if u.startswith("/"):
            u = urljoin(embed_url, u)
        if u not in seen:
            found.append(u)
            seen.add(u)

    for txt in texts:
        if not txt:
            continue
        for pat in patterns:
            for u in re.findall(pat, txt, re.I | re.S):
                _add(u)

    # iframes inside VidKing page: fetch nested one more step
    nested = [u for u in found if "vidking.net/embed/" not in u.lower() and ("/embed" in u.lower() or "player" in u.lower())]
    for iframe_url in nested[:3]:
        try:
            html2, _ = fetch(iframe_url, referer=embed_url, extra_headers={"Referer": embed_url})
        except Exception:
            html2 = ""
        if not html2:
            continue
        for pat in patterns:
            for u in re.findall(pat, html2, re.I | re.S):
                _add(u)

    media = [u for u in found if ".m3u8" in u.lower() or ".mp4" in u.lower()]
    media.sort(key=lambda x: (".m3u8" not in x.lower(), ".mp4" not in x.lower(), len(x)))
    if media:
        media_url = media[0]
        final = "{}|Referer={}&Origin=https://www.vidking.net".format(media_url, embed_url)
        log("EgyDead VidKing resolved: {}".format(media_url[:160]))
        return final, None, _get_base()

    # log a short fingerprint to help diagnose this specific page shape
    sample = re.sub(r"\s+", " ", html[:400]).strip()
    log("EgyDead VidKing unresolved sample: {}".format(sample[:220]))
    log("EgyDead VidKing fallback to base resolver: {}".format(embed_url))
    return embed_url, None, _get_base()

def _build_servers(content_type, tmdb_id, titles, year="", season=None, episode=None, watch_html=""):
    servers = []
    seen = set()

    def _push(name, url, stype="direct"):
        url = (url or "").strip()
        if not url or url in seen:
            return
        servers.append({"name": name, "url": url, "type": stype})
        seen.add(url)

    top_iframe = ""
    topcinema = _topcinema_lookup(content_type, season, episode, year, titles)
    if topcinema and topcinema.get("iframe_url"):
        top_iframe = (topcinema.get("iframe_url") or "").strip()
        if top_iframe.startswith("//"):
            top_iframe = "https:" + top_iframe

    # 1) حارس صريح: لو الـ API رجعت لينك صالح، ما ترجعش لـ VidKing بعدها
    if top_iframe:
        log("EgyDead top_iframe(api)={}".format(top_iframe))
        low = top_iframe.lower()

        if "vidtube" in low:
            quality_servers = _vidtube_quality_servers(top_iframe)
            if quality_servers:
                for server in quality_servers:
                    _push(server["name"], server["url"], server.get("type", "direct"))
            else:
                _push("VidTube", top_iframe, "direct")

            if servers and FORCE_TOPCINEMA_API_FIRST:
                log("EgyDead servers(from api vidtube): {}".format(repr([s.get("name") for s in servers])))
                return servers

        elif "vidking" not in low and "viking" not in low:
            _push("TopCinema", top_iframe, "direct")
            if servers and FORCE_TOPCINEMA_API_FIRST:
                log("EgyDead servers(from api direct): {}".format(repr([s.get("name") for s in servers])))
                return servers

    # 2) fallback TopCinema module only when API missing/empty
    if not servers and not top_iframe:
        try:
            tc_servers = _topcinema_fallback_servers(content_type, titles, year, season, episode)
        except Exception as exc:
            log("EgyDead TopCinema fallback failed: {}".format(exc))
            tc_servers = []

        for s in tc_servers:
            _push(s.get("name") or "TopCinema", s.get("url") or "", s.get("type", "direct"))

        if servers:
            log("EgyDead servers(from topcinema fallback): {}".format(repr([s.get("name") for s in servers])))
            return servers

    # 3) لو عندنا top_iframe لكنه طلع غير صالح للجودات، ممنوع VidKing لو الخيار مفعّل
    if top_iframe and DISABLE_VIDKING_WHEN_TOPCINEMA_EXISTS:
        log("EgyDead guard: top_iframe exists, skipping watch/page vidking fallback")
        return servers

    # 4) scan watch page only if no TopCinema result at all
    if not watch_html:
        try:
            watch_html, _ = fetch(_watch_url(content_type, tmdb_id, season, episode))
        except Exception:
            watch_html = ""

    sources = _extract_player_sources(watch_html)
    log("EgyDead watch sources: {}".format(repr(sources[:10])))

    for src_url in sources:
        low = src_url.lower()
        if "vidtube" in low:
            quality_servers = _vidtube_quality_servers(src_url)
            if quality_servers:
                for server in quality_servers:
                    _push(server["name"], server["url"], server.get("type", "direct"))
            else:
                _push("VidTube", src_url, "direct")

    if servers:
        log("EgyDead servers(from watch vidtube): {}".format(repr([s.get("name") for s in servers])))
        return servers

    for src_url in sources:
        low = src_url.lower()
        if "vidking" in low or "viking" in low:
            continue
        _push("Player", src_url, "direct")

    if servers:
        log("EgyDead servers(from watch non-vidking): {}".format(repr([s.get("name") for s in servers])))
        return servers

    # 5) generic candidates; postpone vidking to final fallback
    try:
        candidates = _server_candidates(content_type, tmdb_id, season, episode)
    except Exception:
        candidates = []

    for name, url in candidates:
        low = (url or "").lower()
        if "vidtube" in low:
            quality_servers = _vidtube_quality_servers(url)
            if quality_servers:
                for server in quality_servers:
                    _push(server["name"], server["url"], server.get("type", "direct"))
            else:
                _push("VidTube", url, "direct")
        elif "vidking" in low or "viking" in low:
            continue
        else:
            _push(name, url, "direct")

    if servers:
        log("EgyDead servers(final non-vidking): {}".format(repr([s.get("name") for s in servers])))
        return servers

    for name, url in candidates:
        low = (url or "").lower()
        if "vidking" in low or "viking" in low:
            _push("VidKing", url, "direct")

    log("EgyDead servers(final): {}".format(repr([s.get("name") for s in servers])))
    return servers

def _episode_title(show_title, season, episode, ep_name):
    bits = ["الموسم {0}".format(season), "الحلقة {0}".format(episode)]
    ep_name = _strip_html(ep_name)
    if ep_name:
        bits.append(ep_name)
    prefix = _strip_html(show_title)
    return "{0} - {1}".format(prefix, " - ".join(bits)) if prefix else " - ".join(bits)


def _season_items(tmdb_id, details, current_props=None):
    items = []
    total = 0
    base = _get_base().rstrip("/")
    show_title = details.get("name") or details.get("title") or ""
    seasons = details.get("seasons") or []
    initial_season = (current_props or {}).get("initialSeason")
    initial_data = (current_props or {}).get("initialSeasonData") or {}

    for season in seasons:
        season_number = season.get("season_number")
        if season_number is None or int(season_number) < 1:
            continue

        if initial_season == season_number and initial_data:
            season_data = initial_data
        else:
            season_url = "{0}/api/tmdb/tv/{1}/season/{2}".format(base, tmdb_id, season_number)
            season_data = _fetch_json(season_url) or {}

        episodes = season_data.get("episodes") or []
        for ep in episodes:
            ep_num = ep.get("episode_number")
            if not ep_num:
                continue
            items.append(
                {
                    "title": _episode_title(show_title, season_number, ep_num, ep.get("name")),
                    "url": "{0}/watch/tv/{1}/{2}/{3}".format(base, tmdb_id, season_number, ep_num),
                    "type": "episode",
                }
            )
            total += 1
            if total >= MAX_EPISODES:
                log("EgyDead: episode list limited to {}".format(MAX_EPISODES))
                return items

    return items


def _category_api_path(url):
    path = (url or "").lower()
    if "/movies/recent" in path:
        return "/api/tmdb/discover/movie"
    if "/movies/popular" in path:
        return "/api/tmdb/movie/popular"
    if "/movies/top-rated" in path:
        return "/api/tmdb/movie/top_rated"
    if "/series/recent" in path:
        return "/api/tmdb/discover/tv"
    if "/series/popular" in path:
        return "/api/tmdb/tv/popular"
    if "/series/top-rated" in path:
        return "/api/tmdb/tv/top_rated"
    return ""


def _page_from_url(url, default=1):
    try:
        match = re.search(r'[\?&]page=(\d+)', url or "", re.I)
        if match:
            return max(1, int(match.group(1)))
    except Exception:
        pass
    return default


def _with_page(url, page_num):
    page_num = max(1, int(page_num or 1))
    url = url or ""
    if re.search(r'([\?&])page=\d+', url, re.I):
        return re.sub(r'([\?&])page=\d+', r'\1page={0}'.format(page_num), url, flags=re.I)
    return url + ('&' if '?' in url else '?') + 'page={0}'.format(page_num)


def _append_next_page(items, url, current_page, total_pages=None, has_more=None):
    try:
        current_page = max(1, int(current_page or 1))
    except Exception:
        current_page = 1

    should_add = False
    if has_more is True:
        should_add = True
    elif total_pages:
        try:
            should_add = int(total_pages) > current_page
        except Exception:
            should_add = False

    if should_add:
        next_url = _with_page(url, current_page + 1)
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": next_url,
            "type": "category",
            "_action": "category"
        })
    return items

def get_categories(mtype="movie"):
    base = _get_base().rstrip("/")
    if mtype == "movie":
        return [
            {"title": "🎬 أحدث الأفلام", "url": base + "/movies/recent", "type": "category", "_action": "category"},
            {"title": "🔥 الأكثر شهرة", "url": base + "/movies/popular", "type": "category", "_action": "category"},
            {"title": "⭐ الأعلى تقييماً", "url": base + "/movies/top-rated", "type": "category", "_action": "category"},
        ]
    return [
        {"title": "📺 أحدث المسلسلات", "url": base + "/series/recent", "type": "category", "_action": "category"},
        {"title": "🔥 الأكثر شهرة", "url": base + "/series/popular", "type": "category", "_action": "category"},
        {"title": "⭐ الأعلى تقييماً", "url": base + "/series/top-rated", "type": "category", "_action": "category"},
    ]


def get_category_items(url, page=1):
    base = _get_base().rstrip("/")
    current_page = 1
    try:
        current_page = int(page or 1)
    except Exception:
        current_page = 1

    url_page = _page_from_url(url, 1)
    if url_page > 1 and current_page <= 1:
        current_page = url_page

    api_path = _category_api_path(url)
    if api_path:
        fetch_url = "{}{}?page={}".format(base, api_path, current_page)
        data = _fetch_json(fetch_url)
        if data:
            items = []
            for entry in (data or {}).get("results", []):
                item = _entry_to_item(entry)
                if item:
                    items.append(item)

            total_pages = (data or {}).get("total_pages") or (data or {}).get("pages")
            has_more = None
            try:
                if total_pages:
                    has_more = int(total_pages) > int(current_page)
            except Exception:
                has_more = None

            if has_more is None and items:
                # fallback heuristic لو الـ API ما رجعش total_pages
                has_more = len(items) >= 18

            return _append_next_page(items, url, current_page, total_pages=total_pages, has_more=has_more)

    fetch_target = url if current_page <= 1 else _with_page(url, current_page)
    html, _ = fetch(fetch_target)
    if not html:
        return []

    data = _extract_next_data(html)
    props = _page_props(data)
    items = _items_from_page_props(props)
    if not items:
        items = _parse_cards(html)

    total_pages = (
        props.get("totalPages")
        or props.get("total_pages")
        or props.get("pages")
        or props.get("pagesCount")
        or props.get("lastPage")
    )
    props_page = (
        props.get("page")
        or props.get("currentPage")
        or props.get("current_page")
    )
    if props_page:
        try:
            current_page = int(props_page)
        except Exception:
            pass

    has_more = None
    try:
        if total_pages:
            has_more = int(total_pages) > int(current_page)
    except Exception:
        has_more = None

    if has_more is None:
        # لو مفيش pagination صريحة، جرّب من وجود لينك next أو حجم الصفحة
        if re.search(r'href=["\'][^"\']*[\?&]page={0}["\']'.format(current_page + 1), html, re.I):
            has_more = True
        elif items:
            has_more = len(items) >= 18
        else:
            has_more = False

    return _append_next_page(items, url, current_page, total_pages=total_pages, has_more=has_more)

def search(query, page=1):
    base = _get_base().rstrip("/")
    current_page = 1
    try:
        current_page = int(page or 1)
    except Exception:
        current_page = 1

    search_url = "{0}/search?q={1}".format(base, quote_plus(query))
    if current_page > 1:
        search_url += "&page={0}".format(current_page)

    html, _ = fetch(search_url)
    if not html:
        return []

    data = _extract_next_data(html)
    props = _page_props(data)
    items = _items_from_page_props(props)
    if not items:
        items = _parse_cards(html)

    total_pages = (
        props.get("totalPages")
        or props.get("total_pages")
        or props.get("pages")
        or props.get("pagesCount")
        or props.get("lastPage")
    )
    props_page = props.get("page") or props.get("currentPage") or props.get("current_page")
    if props_page:
        try:
            current_page = int(props_page)
        except Exception:
            pass

    has_more = None
    try:
        if total_pages:
            has_more = int(total_pages) > int(current_page)
    except Exception:
        has_more = None

    if has_more is None:
        if re.search(r'href=["\'][^"\']*[\?&]page={0}["\']'.format(current_page + 1), html, re.I):
            has_more = True
        elif items:
            has_more = len(items) >= 18
        else:
            has_more = False

    if has_more:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": "{0}/search?q={1}&page={2}".format(base, quote_plus(query), current_page + 1),
            "type": "category",
            "_action": "category"
        })
    return items

def get_page(url, m_type="movie"):
    html, final_url = fetch(url)
    result = _detail_result(url, "", "", "", "", "", m_type or "movie")

    if not html:
        log("EgyDead: failed to fetch {}".format(url))
        return result

    data = _extract_next_data(html)
    props = _page_props(data)
    details = props.get("details") or {}
    ld = _json_ld_object(html)
    meta_plot = _meta_description(html)
    meta_title = _meta_title(html)
    meta_poster = _meta_image(html)
    ld_title = _clean_title_text(ld.get("name") or ld.get("headline") or "")
    ld_plot = _strip_html(ld.get("description"))
    ld_poster = _img(ld.get("image") or "")
    ld_year = _year_from_text(ld.get("datePublished") or "")
    ld_rating = _rating_text(((ld.get("aggregateRating") or {}).get("ratingValue")))

    watch_match = re.search(r"/watch/(movie|tv)/(\d+)(?:/(\d+)/(\d+))?", final_url or url)
    detail_match = re.search(r"/(movie|tv)/(\d+)$", final_url or url)

    if watch_match:
        content_type, tmdb_id, season, episode = watch_match.groups()
        poster = _img(details.get("poster_path")) or ld_poster or meta_poster
        plot = _strip_html(details.get("overview")) or ld_plot or meta_plot
        year = _year_from_entry(details) or ld_year or _year_from_text(meta_title)
        rating = _rating_text(details.get("vote_average")) or ld_rating

        if content_type == "movie":
            titles = _unique_titles(details.get("title"), details.get("original_title"), ld_title, meta_title)
            title = titles[0] if titles else "Movie {0}".format(tmdb_id)
            result = _detail_result(url, title, poster, plot, year, rating, "movie")
            result["servers"] = _build_servers("movie", tmdb_id, titles, year=year, watch_html=html)
            return result

        titles = _unique_titles(details.get("name"), details.get("original_name"), ld_title, meta_title)
        season = season or str(props.get("initialSeason") or 1)
        episode = episode or str(props.get("initialEpisode") or 1)
        season_data = props.get("initialSeasonData") or {}
        current_ep = None
        for ep in season_data.get("episodes") or []:
            if str(ep.get("episode_number")) == str(episode):
                current_ep = ep
                break
        ep_name = (current_ep or {}).get("name") or ""
        title = _episode_title(titles[0] if titles else details.get("name"), season, episode, ep_name)
        result = _detail_result(url, title, poster, plot, year, rating, "episode")
        result["servers"] = _build_servers("tv", tmdb_id, titles, season=season, episode=episode, watch_html=html)
        return result

    if detail_match:
        content_type, tmdb_id = detail_match.groups()
    else:
        content_type = props.get("type") or ("movie" if m_type == "movie" else "tv")
        tmdb_id = str(details.get("id") or "")

    poster = _img(details.get("poster_path")) or ld_poster or meta_poster
    plot = _strip_html(details.get("overview")) or ld_plot or meta_plot
    year = _year_from_entry(details) or ld_year or _year_from_text(meta_title)
    rating = _rating_text(details.get("vote_average")) or ld_rating

    if content_type == "movie":
        titles = _unique_titles(details.get("title"), details.get("original_title"), ld_title, meta_title)
        title = titles[0] if titles else "Movie {0}".format(tmdb_id or "")
        result = _detail_result(url, title, poster, plot, year, rating, "movie")
        if tmdb_id:
            result["servers"] = _build_servers("movie", tmdb_id, titles, year=year)
        return result

    titles = _unique_titles(details.get("name"), details.get("original_name"), ld_title, meta_title)
    title = titles[0] if titles else "Series {0}".format(tmdb_id or "")
    result = _detail_result(url, title, poster, plot, year, rating, "series")
    if tmdb_id:
        result["items"] = _season_items(tmdb_id, details, props)
    return result

def extract_stream(url):
    low = (url or "").lower()
    if "vidking.net/embed/" in low or "viking" in low:
        resolved, sub, ref = _vidking_resolve(url)
        if resolved and resolved != url:
            return resolved, sub, ref
        from .base import extract_stream as base_extract_stream
        return base_extract_stream(url)

    from .base import extract_stream as base_extract_stream
    return base_extract_stream(url)
````

## File: extractors/fasel.py
````python
# -*- coding: utf-8 -*-
import sys
import re
from .base import fetch, urljoin, log

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, quote
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, quote
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

DOMAINS = [
    "https://www.faselhd.cam",
    "https://faselhd.pro",
    "https://faselhd.cc",
    "https://web33012x.faselhdx.bid",
    "https://faselhd.center",
    "https://www.faselhdx.bid",
    "https://faselhd.fm",
    "https://www.fasel-hd.com",
]
MAIN_URL = DOMAINS[0]

BLOCKED_MARKERS = ("alliance4creativity", "watch-it-legally")

def _get_base():
    """Try all domains and return the first working one"""
    for domain in DOMAINS:
        html, final_url = fetch(domain, referer=domain)
        if html and not any(m in (final_url or "").lower() for m in BLOCKED_MARKERS):
            log("FaselHD: using domain {}".format(domain))
            return domain
        log("FaselHD: domain {} is blocked or down".format(domain))
    return DOMAINS[0]

_ACTIVE_URL = None
def _base():
    global _ACTIVE_URL, MAIN_URL
    if not _ACTIVE_URL:
        _ACTIVE_URL = _get_base()
        MAIN_URL = _ACTIVE_URL
    return _ACTIVE_URL

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
    # Adding a clear User-Agent to mimic a real browser to help with Cloudflare
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
    }
    return [
        {"title": "🎬 الأفلام الأجنبية", "url": MAIN_URL + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a-foreign-movies/", "type": "category", "_action": "category"},
        {"title": "📺 المسلسلات الأجنبية", "url": MAIN_URL + "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a-foreign-series/", "type": "category", "_action": "category"},
        {"title": "🎭 عروض المصارعة", "url": MAIN_URL + "/category/%d8%b9%d8%b1%d9%88%d8%b6-%d8%a7%d9%84%d9%85%d8%b5%d8%a7%d8%b1%d8%b9%d8%a9-wrestling/", "type": "category", "_action": "category"},
    ]

def _extract_items(html):
    items = []
    # Pattern for post grid
    matches = re.findall(r'<div class="postDiv[^>]*>.*?<a href="([^"]+)".*?<img[^>]*?(?:data-src|src)="([^"]+)".*?class="h1">([^<]+)</div>', html, re.DOTALL)
    
    for href, img, title in matches:
        title = _clean_title(title)
        href  = _normalize_url(href)
        img   = _normalize_url(img)
        item_type = "movie"
        if any(x in title for x in [u"مسلسل", u"انمي", u"موسم"]):
            item_type = "series"
        items.append({"title": title, "url": href, "poster": img,
                      "type": item_type, "_action": "item"})

    if not items:
        seen_fb = set()
        _ip = re.compile(r'(?:data-src|data-lazy|src)=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)["\']', re.I)
        _tp = re.compile(r'<h[0-9][^>]*>([^<]+)</h[0-9]>|alt=["\']([^"\']+)["\']', re.I)
        for block in re.findall(r"<(?:div|article|li)[^>]+>.*?</(?:div|article|li)>", html or "", re.S|re.I):
            hm = re.search(r'href=["\']([^"\']+)["\']', block, re.I)
            if not hm: continue
            href_fb = _normalize_url(hm.group(1))
            if not href_fb or href_fb in seen_fb: continue
            if not any(x in href_fb for x in ("/movie","/film","/series","/episode","?p=")): continue
            im = _ip.search(block)
            img_fb = _normalize_url(im.group(1)) if im else ""
            tm = _tp.search(block)
            title_fb = _clean_title((tm.group(1) or tm.group(2) or "").strip()) if tm else ""
            if not title_fb: continue
            seen_fb.add(href_fb)
            itype = "series" if u"مسلسل" in title_fb else "movie"
            items.append({"title":title_fb,"url":href_fb,"poster":img_fb,"type":itype,"_action":"item"})
    return items

def get_category_items(url):
    base = _base()
    # Rebuild URL with active domain if needed
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc not in base:
        path = parsed.path
        url = base.rstrip('/') + path
    html, final_url = fetch(url, referer=base)
    if not html:
        log("FaselHD: fetch returned None for {}".format(url))
        return []
    items = _extract_items(html)
    
    # Pagination
    nav_match = re.search(r'<ul class="pagination">.*?<li class="active">.*?</li>.*?<li><a href="([^"]+)">', html, re.DOTALL)
    if nav_match:
        items.append({
            "title": "➡️ الصفحة التالية",
            "url": _normalize_url(nav_match.group(1)),
            "type": "category",
            "_action": "category"
        })
    return items

def search(query, page=1):
    url = MAIN_URL + "/?s=" + quote_plus(query)
    html, final_url = fetch(url, referer=MAIN_URL)
    return _extract_items(html)

def get_page(url):
    html, final_url = fetch(url, referer=MAIN_URL)
    
    title_m = re.search(r'<title>(.*?)</title>', html)
    title = _clean_title(title_m.group(1)) if title_m else "FaselHD"
    
    poster_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(poster_m.group(1)) if poster_m else ""
    
    plot_m = re.search(r'name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html)
    plot = _clean_title(plot_m.group(1)) if plot_m else ""

    servers = []
    items = [] # Used for seasons or episodes
    item_type = "movie"

    # 1. Check if it's a Season page (lists episodes)
    if '/seasons/' in url:
        item_type = "series"
        ep_matches = re.findall(r'<div class="epAll">.*?<a href="([^"]+)">([^<]+)</a>', html, re.DOTALL)
        for e_url, e_title in ep_matches:
            items.append({
                "title": _clean_title(e_title),
                "url": _normalize_url(e_url),
                "type": "episode",
                "_action": "item"
            })
    
    # 2. Check if it's a Series page (lists seasons)
    elif '/series/' in url:
        item_type = "series"
        s_matches = re.findall(r'<div class="seasonDiv[^>]*>.*?<a href="([^"]+)">.*?<div class="title">([^<]+)</div>', html, re.DOTALL)
        for s_url, s_title in s_matches:
            items.append({
                "title": _clean_title(s_title),
                "url": _normalize_url(s_url),
                "type": "category", # Seasons act as categories
                "_action": "category"
            })
        
        # If no seasons, maybe episodes directly
        if not items:
            ep_matches = re.findall(r'<div class="epAll">.*?<a href="([^"]+)">([^<]+)</a>', html, re.DOTALL)
            for e_url, e_title in ep_matches:
                items.append({
                    "title": _clean_title(e_title),
                    "url": _normalize_url(e_url),
                    "type": "episode",
                    "_action": "item"
                })

    # 3. Handle playback (movies or episodes)
    # Look for the "Watch" page or direct player
    player_match = re.search(r'player_iframe\.location\.href\s*=\s*\'([^\']+)\'', html)
    if not player_match:
        # Check for watch button
        watch_m = re.search(r'<a href="([^"]+)"[^>]*>مشاهدة وتحميل</a>', html)
        if watch_m:
            watch_url = _normalize_url(watch_m.group(1))
            w_html, _ = fetch(watch_url, referer=url)
            player_match = re.search(r'player_iframe\.location\.href\s*=\s*\'([^\']+)\'', w_html)
            if player_match:
                html = w_html # Use watch page html for server parsing
    
    if player_match:
        player_url = player_match.group(1)
        # Parse servers from the watch page tabs if available
        # <ul class="tabs-ul"> ... <li onclick="player_iframe.location.href = 'URL'">NAME</li>
        # Parse servers from the watch page tabs if available
        # <ul class="tabs-ul"> ... <li onclick="player_iframe.location.href = 'URL'">NAME</li>
        srv_matches = re.findall(r'<li[^>]*onclick=["\']player_iframe\.location\.href\s*=\s*[\\"\']([^\\"\']+)[\\"\'][^>]*>(.*?)</li>', html, re.DOTALL | re.IGNORECASE)
        for srv_url, srv_name in srv_matches:
            name = _clean_title(re.sub(r'<[^>]+>', '', srv_name))
            if not name: name = u"سيرفر"
            servers.append({
                "name": u"فاصل - " + name,
                "url": _normalize_url(srv_url)
            })
        
        # Fallback if no list found but player_match worked
        if not servers:
            servers.append({
                "name": u"فاصل - سيرفر رئيسي",
                "url": _normalize_url(player_url)
            })

    return {
        "url": final_url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "servers": servers,
        "items": items,
        "type": item_type
    }

def extract_stream(url):
    log("Fasel: extracting from {}".format(url))
    # Fetch player page with MAIN_URL as referer
    html, final_url = fetch(url, referer=MAIN_URL)
    if not html: return url, None, MAIN_URL
    
    # Use the final_url of the player as the referer for subsequent requests
    player_referer = final_url or url
    
    # 1. Try simple data-url buttons
    btn_matches = re.findall(r'data-url=["\']([^"\']+)["\']', html, re.I)
    if btn_matches:
        return _normalize_url(btn_matches[0]), None, player_referer

    # 2. Try the obfuscated JS cipher used by faselhdx.bid
    # var t="...".replace(/(.)/g,(function(e,t){return String.fromCharCode(e.charCodeAt(0)-t%2)}))
    cipher_match = re.search(r'var\s+t\s*=\s*[\"\']([^\"\']+)[\"\']\.replace', html)
    if cipher_match:
        encoded = cipher_match.group(1)
        decoded = "".join([chr(ord(c) - (i % 2)) for i, c in enumerate(encoded)])
        
        # Look for the file URL in the decoded string
        file_m = re.search(r'file\s*:\s*[\"\']([^\"\']+)[\"\']', decoded)
        if file_m:
            v_url = _normalize_url(file_m.group(1))
            # Handle .txt obfuscated extensions
            if v_url.endswith(".txt"):
                v_url = v_url.replace(".txt", "/master.m3u8") # common pattern for these mirrors
            return v_url, None, player_referer

    # 3. Try fallback regexes
    m3u8_match = re.search(r'https?://[^\s\'"]+?\.m3u8[^\s\'"]*', html)
    if not m3u8_match:
        m3u8_match = re.search(r'https?://[^\s\'"]+?\.txt[^\s\'"]*', html) # Some mirrors use .txt extension
        
    if m3u8_match:
        v_url = m3u8_match.group(0)
        # Final safety check for .txt obfuscation
        if ".txt" in v_url:
            # Some mirrors use /v/token.txt?params which needs to become /v/token.m3u8?params
            v_url = v_url.replace(".txt", ".m3u8")
            if "/master." not in v_url and ".m3u8" in v_url:
                # Common fix for certain mirrors
                v_url = v_url.replace(".m3u8", "/master.m3u8")
        return v_url, None, player_referer

    # 4. Concatenated strings
    parts = re.findall(r"'(?:https?:|//)[^']+'", html)
    if parts:
        combined = "".join([p.strip("'") for p in parts])
        m3u8_match = re.search(r'(https?://[^\s\'"]+?\.m3u8)', combined)
        if m3u8_match:
            return m3u8_match.group(1), None, player_referer

    log("Fasel: could not extract stream from player page")
    return "", None, MAIN_URL
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


# Updated domain list with working mirrors
DOMAINS = [
    "https://shahieed4u.net/",      # Current working (user provided)
    "https://shaheeid4u.net/",      # Original (may redirect)
    "https://shahid4u.guru/",       # Active mirror
    "https://shahid4u.boutique/",   # Another mirror
    "https://shhahhid4u.net/",      # Redirects to shah4u.media
]

VALID_HOST_MARKERS = (
    "shahieed4u.net",
    "shaheeid4u.net",
    "shahid4u",
    "shhahhid4u",
)
BLOCKED_HOST_MARKERS = (
    "alliance4creativity.com",
)
MAIN_URL = None
_HOME_HTML = None
_HOME_LAST_FETCH = 0

_CATEGORY_FALLBACKS = {
    "افلام اجنبي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a",
    "افلام عربي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%b9%d8%b1%d8%a8%d9%8a",
    "افلام انمي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d9%86%d9%85%d9%8a",
    "افلام اسيوي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%b3%d9%8a%d9%88%d9%8a%d8%a9",
    "مسلسلات اجنبي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a",
    "مسلسلات عربي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b9%d8%b1%d8%a8%d9%8a",
    "مسلسلات تركي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%aa%d8%b1%d9%83%d9%8a%d8%a9",
    "مسلسلات انمي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d9%86%d9%85%d9%8a",
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
    if any(marker in host for marker in BLOCKED_HOST_MARKERS):
        return False
    return any(marker in host for marker in VALID_HOST_MARKERS)


def _is_blocked_page(html, final_url=""):
    text = (html or "").lower()
    final = (final_url or "").lower()
    return (
        not text
        or "just a moment" in text
        or "cf-chl" in text
        or "__cf_chl" in text
        or "alliance for creativity" in text
        or any(marker in final for marker in BLOCKED_HOST_MARKERS)
        or (final and not _is_valid_site_url(final))
    )


def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)


def _get_base(force_refresh=False):
    global MAIN_URL, _HOME_HTML, _HOME_LAST_FETCH
    # Refresh home page every 6 hours
    if MAIN_URL and not force_refresh and (time.time() - _HOME_LAST_FETCH) < 21600:
        return MAIN_URL
    for domain in DOMAINS:
        log("Shaheed: probing base {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Shaheed: blocked base {}".format(final_url))
            continue
        if html and ("shah" in html.lower() or "film" in html.lower()):
            MAIN_URL = _site_root(final_url)
            _HOME_HTML = html
            _HOME_LAST_FETCH = time.time()
            log("Shaheed: selected base {}".format(MAIN_URL))
            return MAIN_URL
    # Fallback: first domain
    MAIN_URL = DOMAINS[0]
    log("Shaheed: fallback base {}".format(MAIN_URL))
    return MAIN_URL


def _search_url():
    return _get_base().rstrip("/") + "/search?s="


def _quote_url(url):
    if not url: return url
    try:
        from urllib.parse import urlparse, urlunparse, quote, unquote
        url_dec = unquote(url)
        p = list(urlparse(url_dec))
        p[2] = quote(p[2])
        p[4] = quote(p[4], safe='=&/%')
        return urlunparse(p)
    except Exception:
        return url


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
    url = _quote_url(url)
    log("Shaheed: fetch candidate {}".format(url))
    if not _is_valid_site_url(url):
        log("Shaheed: rejecting invalid target {}".format(url))
        return "", ""
    ref = referer or _get_base()
    h, start_url = fetch(url, referer=ref)
    if _is_blocked_page(h, start_url):
        return "", ""
    log("Shaheed: fetch success {}".format(start_url))
    return h, start_url


def _category_from_home(label, fallback):
    global _HOME_HTML
    if not _HOME_HTML:
        _get_base()
    if _HOME_HTML:
        token = '>{}<'.format(label)
        start = _HOME_HTML.find(token)
        if start > 0:
            block = _HOME_HTML[max(0, start - 200):start]
            m = re.search(r'href=["\']([^"\']+)["\']', block)
            if m:
                u = _normalize_url(m.group(1))
                if _is_valid_site_url(u):
                    return u
    return _normalize_url(urljoin(_get_base(), fallback))


def _extract_cards(html):
    items = []
    # Find all <a> tags that have class "show-card"
    blocks = re.findall(r'(<a[^>]+(?:class=["\'][^"\']*show-card[^"\']*["\']|href=["\'][^"\']+(?:/film/|/series/|/episode/|/anime/)[^"\']+["\'])[^>]*>.*?</a>)', html, re.S | re.IGNORECASE)
    
    seen = set()
    for block in blocks:
        href_m = re.search(r'href=["\']([^"\']+)["\']', block)
        if not href_m: continue
        url = href_m.group(1)
        if url in seen: continue
        seen.add(url)
        
        img_m = re.search(r'url\([\'"]?([^)\'"]+)[\'"]?\)', block)
        if not img_m:
            img_m = re.search(r'src=["\']([^"\']+)["\']', block)
        img = img_m.group(1) if img_m else ""
        
        title_m = re.search(r'class=["\']title["\']>([^<]+)<', block)
        if not title_m:
             title_m = re.search(r'alt=["\']([^"\']+)["\']', block)
        title = title_m.group(1).strip() if title_m else ""
        
        if title:
            items.append({
                "title": html_unescape(title),
                "url": _normalize_url(url),
                "poster": _normalize_url(img.strip("'\"")),
                "type": "series" if "/series" in url or "/season" in url else ("episode" if "/episode" in url else "movie"),
                "_action": "item",
            })

    if not items:
        seen_fb = set()
        _lp = re.compile(r'<a[^>]+href=["\']([^"\']+/(?:film|series|episode|anime|watch)/[^"\']+)["\'][^>]*>(.*?)</a>', re.S|re.I)
        _ip = re.compile(r'(?:data-src|src)=["\']([^"\']+\.(?:jpe?g|png|webp)[^"\']*)["\']', re.I)
        _tp = re.compile(r'class=["\'][^"\']*title[^"\']*["\'][^>]*>([^<]+)<|alt=["\']([^"\']+)["\']', re.I)
        for hm in _lp.finditer(html or ""):
            url_fb = _normalize_url(hm.group(1))
            inner  = hm.group(2)
            if url_fb in seen_fb: continue
            seen_fb.add(url_fb)
            im = _ip.search(inner)
            img_fb = _normalize_url(im.group(1)) if im else ""
            tm = _tp.search(inner)
            title_fb = html_unescape((tm.group(1) or tm.group(2) or "").strip()) if tm else ""
            if not title_fb: continue
            itype = "series" if "/series" in url_fb else ("episode" if "/episode" in url_fb else "movie")
            items.append({"title":title_fb,"url":url_fb,"poster":img_fb,"type":itype,"_action":"item"})
    return items


def _extract_next_page(html):
    m = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*rel=["\']next["\']', html)
    if m:
        return _normalize_url(m.group(1))
    return None


def get_categories():
    base = _get_base().rstrip("/")
    return [
        {"title": "🎬 الأفلام الأجنبية",
         "url": base + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a-foreign-movies/",
         "type": "category", "_action": "category"},
        {"title": "📺 المسلسلات الأجنبية",
         "url": base + "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a-foreign-series/",
         "type": "category", "_action": "category"},
        {"title": "🎭 عروض المصارعة",
         "url": base + "/category/%d8%b9%d8%b1%d9%88%d8%b6-%d8%a7%d9%84%d9%85%d8%b5%d8%a7%d8%b1%d8%b9%d8%a9-wrestling/",
         "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات عربية",
         "url": _category_from_home("مسلسلات عربي", _CATEGORY_FALLBACKS["مسلسلات عربي"]),
         "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات تركية",
         "url": _category_from_home("مسلسلات تركية", _CATEGORY_FALLBACKS["مسلسلات تركي"]),
         "type": "category", "_action": "category"},
        {"title": "📺 أفلام أنمي",
         "url": _category_from_home("افلام انمي", _CATEGORY_FALLBACKS["افلام انمي"]),
         "type": "category", "_action": "category"},
        {"title": "📺 مسلسلات أنمي",
         "url": _category_from_home("مسلسلات انمي", _CATEGORY_FALLBACKS["مسلسلات انمي"]),
         "type": "category", "_action": "category"},
    ]


def get_category_items(url):
    html, final_url = _fetch_live(url)
    if not html:
        return []

    items = _extract_cards(html)
    log("Shaheed: category {} -> {} items".format(url, len(items)))
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def search(query, page=1):
    items = []
    html, final_url = _fetch_live(_search_url() + quote_plus(query) + "&page=" + str(page))
    if not html:
        return items

    items = _extract_cards(html)
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})

    return items


def _detail_title(html):
    m = re.search(r'<title>(.*?)</title>', html)
    if m:
        return html_unescape(m.group(1))
    return ""


def _detail_poster(html):
    m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    return _normalize_url(m.group(1)) if m else ""


def _detail_plot(html):
    m = re.search(r'class=["\']description["\'][^>]*>(.*?)</p>', html, re.S)
    if m:
        txt = re.sub(r'<[^>]+>', ' ', m.group(1)).strip()
        return html_unescape(txt)
    return ""


def get_page(url):
    html, final_url = _fetch_live(url)
    if not html:
        log("Shaheed: detail failed {}".format(url))
        return {"title": "Error", "servers": [], "items": []}

    title = _detail_title(html)
    poster = _detail_poster(html)
    plot = _detail_plot(html)
    
    servers = []
    episodes = []

    # Could be a series page
    if "/series/" in final_url or "مسلسل" in title:
        ep_cards = re.findall(r'<a[^>]+href=["\'](https?://[^"\']+/episode/[^"\']+)["\'][^>]*class=["\']ep-card["\'][^>]*>.*?<span[^>]*>([^<]+)</span>', html, re.S)
        for ep_url, ep_title in ep_cards:
            episodes.append({
                "title": html_unescape(ep_title.strip()),
                "url": _normalize_url(ep_url),
                "type": "episode",
                "_action": "item"
            })
    
    # If it's a film or episode, extract servers
    watch_page_link = None
    m = re.search(r'href=["\']([^"\']+/watch/[^"\']+)["\']', html)
    if m:
        watch_page_link = _normalize_url(m.group(1))
    
    if watch_page_link:
        wh, wfinal = _fetch_live(watch_page_link, referer=final_url)
        # Try to find servers in various patterns
        js_servers = re.search(r'let servers = JSON\.parse\(\'(.*?)\'\)', wh)
        if not js_servers:
            js_servers = re.search(r'var servers = (\[.*?\])', wh, re.S)
        if not js_servers:
            js_servers = re.search(r'"servers"\s*:\s*(\[.*?\])', wh, re.S)
        if js_servers:
            try:
                srv_str = js_servers.group(1)
                srv_str = srv_str.replace("'", '"')
                srv_data = json.loads(srv_str)
                for s in srv_data:
                    if s.get("url"):
                        servers.append({
                            "name": s.get("name", s.get("label", "Server")),
                            "url": s["url"] + "|Referer=" + _site_root(final_url)
                        })
            except Exception as e:
                log("Shaheed: JSON decode error: {}".format(e))
                urls = re.findall(r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)', wh)
                for u in urls:
                    servers.append({"name": "Stream", "url": u + "|Referer=" + _site_root(final_url)})
    else:
        # Fallback: servers inline
        js_servers = re.search(r'let servers = JSON\.parse\(\'(.*?)\'\)', html)
        if not js_servers:
            js_servers = re.search(r'var servers = (\[.*?\])', html, re.S)
        if js_servers:
            try:
                srv_str = js_servers.group(1).replace("'", '"')
                srv_data = json.loads(srv_str)
                for s in srv_data:
                    if s.get("url"):
                        servers.append({
                            "name": s.get("name", "Server"),
                            "url": s["url"] + "|Referer=" + _site_root(final_url)
                        })
            except Exception as e:
                log("Shaheed: JSON decode error inline: {}".format(e))

    item_type = "series" if episodes else "movie"
    if "/episode/" in final_url:
        item_type = "episode"

    return {
        "url": final_url or url,
        "title": title,
        "plot": plot,
        "poster": poster,
        "servers": servers,
        "items": episodes,
        "type": item_type,
    }


def extract_stream(url):
    log("Shaheed extract_stream: {}".format(url))
    referer = _get_base()
    if "|" in url:
        parts = url.split("|", 1)
        url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()
            
    from .base import resolve_iframe_chain
    stream, _ = resolve_iframe_chain(url, referer=referer, max_depth=6)
    if stream:
        return stream, None, referer
    return url, None, referer
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


DOMAINS = [
    "https://wecima.rent/",
    "https://wecima.date/",
    "https://www.wecima.site/",
]
VALID_HOST_MARKERS = (
    "wecima.rent",
    "wecima.date",
    "wecima.site",
)
BLOCKED_HOST_MARKERS = (
    "alliance4creativity.com",
)
MAIN_URL = None
_HOME_HTML = None

_CATEGORY_FALLBACKS = {
    "افلام اجنبي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/",
    "افلام عربي": "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%b9%d8%b1%d8%a8%d9%8a/",
    "مسلسلات اجنبي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/",
    "مسلسلات عربية": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%b9%d8%b1%d8%a8%d9%8a%d8%a9/",
    "مسلسلات انمي": "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d9%86%d9%85%d9%8a/",
    "تريندج": "/",
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
    if any(marker in host for marker in BLOCKED_HOST_MARKERS):
        return False
    return any(marker in host for marker in VALID_HOST_MARKERS)


def _is_blocked_page(html, final_url=""):
    text = (html or "").lower()
    final = (final_url or "").lower()
    return (
        not text
        or "just a moment" in text
        or "cf-chl" in text
        or "__cf_chl" in text
        or "enable javascript and cookies to continue" in text
        or "watch it legally" in text
        or "alliance for creativity" in text
        or any(marker in final for marker in BLOCKED_HOST_MARKERS)
        or (final and not _is_valid_site_url(final))
    )


def _looks_like_wecima_page(html):
    text = html or ""
    return (
        "Grid--WecimaPosts" in text
        or "NavigationMenu" in text
        or "Thumb--GridItem" in text
        or "WECIMA" in text
        or "وي سيما" in text
    )


def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)


def _get_base():
    global MAIN_URL, _HOME_HTML
    if MAIN_URL:
        return MAIN_URL
    for domain in DOMAINS:
        log("Wecima: probing base {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked base {}".format(final_url))
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
    # Decode unicode escapes like \u0026 -> &
    try:
        url = url.encode('utf-8').decode('unicode_escape') if '\\u' in url else url
    except Exception:
        pass
    url = url.replace("\\u0026", "&").replace("&amp;", "&").replace("\\/", "/")
    url = html_unescape(url)
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(_get_base(), url)
    if any(marker in _host(url) for marker in BLOCKED_HOST_MARKERS):
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
    chosen = ""
    for candidate in _candidate_urls(url):
        log("Wecima: fetch candidate {}".format(candidate))
        html, final_url = fetch(candidate, referer=referer or _get_base())
        final_url = final_url or candidate
        if _is_blocked_page(html, final_url):
            log("Wecima: blocked candidate {}".format(final_url))
            continue
        if html and _looks_like_wecima_page(html):
            log("Wecima: fetch success {}".format(final_url))
            return html, final_url
        if html:
            log("Wecima: invalid page shape {}".format(final_url))
        chosen = final_url
    log("Wecima: fetch failed for {}".format(url))
    return "", chosen


def _clean_html(text):
    text = html_unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title):
    title = _clean_html(title)
    for token in (
        "مشاهدة فيلم",
        "مشاهدة مسلسل",
        "مشاهدة",
        "فيلم",
        "مسلسل",
        "اون لاين",
        "أون لاين",
        "مترجم",
        "مترجمة",
        "مدبلج",
        "مدبلجة",
    ):
        title = title.replace(token, "")
    return re.sub(r"\s+", " ", title).strip(" -|")


def _home_html():
    base = _get_base()
    global _HOME_HTML
    if _HOME_HTML:
        return _HOME_HTML
    html, final_url = _fetch_live(base, referer=base)
    _HOME_HTML = html if not _is_blocked_page(html, final_url) else ""
    return _HOME_HTML


def _guess_type(title, url):
    text = "{} {}".format(title or "", url or "").lower()
    if any(token in text for token in ("/episode/", "الحلقة", "حلقة")):
        return "episode"
    if any(token in text for token in ("/series", "/season", "مسلسل", "series-")):
        return "series"
    return "movie"


def _grid_blocks(html):
    blocks = []
    for block in re.split(r'(?=<div[^>]+class="GridItem")', html or "", flags=re.I):
        if 'class="GridItem"' not in block:
            continue
        end_match = re.search(
            r'<ul[^>]+class="PostItemStats"[^>]*>.*?</ul>\s*</div>',
            block,
            re.S | re.I,
        )
        if end_match:
            blocks.append(block[:end_match.end()])
        else:
            blocks.append(block[:2500])
    return blocks


def _extract_cards(html):
    cards = []
    seen = set()
    for block in _grid_blocks(html):
        href_match = re.search(r'<a[^>]+href="([^"]+)"', block, re.I)
        if not href_match:
            continue

        url = _normalize_url(href_match.group(1))
        lowered = (url or "").lower()
        if not url or url in seen:
            continue
        if any(token in lowered for token in ("/category/", "/tag/", "/page/", "/filtering", "/feed/")):
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
        poster_match = re.search(r'data-lazy-style="[^"]*url\(([^)]+)\)"', block, re.I)
        if poster_match:
            poster = poster_match.group(1).strip("'\" ")
        if not poster:
            poster_match = re.search(r'(?:data-src|src)="([^"]+)"', block, re.I)
            if poster_match:
                poster = poster_match.group(1).strip()

        year_match = re.search(r'<span[^>]+class="year"[^>]*>\(\s*(\d{4})', block, re.I)
        year = year_match.group(1) if year_match else ""

        seen.add(url)
        cards.append(
            {
                "title": title,
                "url": url,
                "poster": _normalize_url(poster) if poster else "",
                "plot": year,
                "type": _guess_type(title, url),
                "_action": "details",
            }
        )
    log("Wecima: extracted {} cards".format(len(cards)))
    return cards


def _extract_next_page(html):
    match = re.search(r'<a[^>]+class="[^"]*next[^"]*page-numbers[^"]*"[^>]+href="([^"]+)"', html or "", re.I)
    if match:
        return _normalize_url(match.group(1))
    match = re.search(r'<a[^>]+rel="next"[^>]+href="([^"]+)"', html or "", re.I)
    if match:
        return _normalize_url(match.group(1))
    return ""


def _category_from_home(label, fallback):
    html = _home_html()
    patterns = [
        r'<a[^>]+href="([^"]+)"[^>]*>\s*' + re.escape(label) + r'\s*</a>',
        r'<a[^>]+href="([^"]+)"[^>]*>\s*<span[^>]*>\s*' + re.escape(label) + r'\s*</span>',
    ]
    for pattern in patterns:
        match = re.search(pattern, html or "", re.S | re.I)
        if match:
            url = _normalize_url(match.group(1))
            if url:
                return url
    return _normalize_url(urljoin(_get_base(), _CATEGORY_FALLBACKS.get(label, "/")))


def _extract_servers(html):
    servers = []
    seen = set()

    # Method 1: <ul id="watch"> with data-watch attribute
    watch_list = re.search(r'<ul[^>]+id="watch"[^>]*>(.*?)</ul>', html or "", re.S | re.I)
    if watch_list:
        for idx, match in enumerate(re.finditer(r'<li[^>]+data-watch="([^"]+)"[^>]*>(.*?)</li>', watch_list.group(1), re.S | re.I)):
            server_url = html_unescape(match.group(1)).strip()
            if not server_url or server_url in seen:
                continue
            seen.add(server_url)
            name = _clean_html(match.group(2)) or "Server {}".format(idx + 1)
            servers.append({"name": name, "url": server_url, "type": "direct"})

    if servers:
        return servers

    # Method 2: links with class containing "server" or "watch"
    for m in re.finditer(r'<(?:a|div|li|button)[^>]+(?:class|id)="[^"]*(?:server|watch|player)[^"]*"[^>]*>.*?href="([^"]+)"', html or "", re.S | re.I):
        url = _normalize_url(m.group(1))
        if url and url not in seen and "://" in url:
            seen.add(url)
            servers.append({"name": "Server {}".format(len(servers) + 1), "url": url})

    # Method 3: iframes
    if not servers:
        for m in re.finditer(r'<iframe[^>]+src="([^"]+)"', html or "", re.I):
            url = _normalize_url(m.group(1))
            if url and url not in seen and "://" in url:
                if any(k in url for k in ["embed", "player", "watch", "stream", "video"]):
                    seen.add(url)
                    servers.append({"name": "Player {}".format(len(servers) + 1), "url": url})

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
        match = re.search(pattern, html or "", re.S | re.I)
        if match:
            title = _clean_title(match.group(1))
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
        r'content="([^"]+)"[^>]+name="description"',
    ):
        match = re.search(pattern, html or "", re.S | re.I)
        if match:
            text = _clean_html(match.group(1))
            if text and "موقع وي سيما" not in text and "مشاهدة احدث الافلام" not in text:
                return text
    return ""


def _detail_poster(html):
    for pattern in (
        r'<wecima[^>]+style="[^"]*--img:url\(([^)]+)\)',
        r'property="og:image"[^>]+content="([^"]+)"',
        r'content="([^"]+)"[^>]+property="og:image"',
        r'(?:data-src|src)="([^"]+)"[^>]+itemprop="image"',
        r'itemprop="image"[^>]+(?:data-src|src)="([^"]+)"',
    ):
        match = re.search(pattern, html or "", re.I)
        if match:
            poster = match.group(1).strip("'\" ")
            if poster:
                return _normalize_url(poster) or poster
    return ""


def _detail_year(title, html):
    match = re.search(r'\b(19\d{2}|20\d{2}|21\d{2})\b', title or "")
    if match:
        return match.group(1)
    match = re.search(r'datePublished[^>]*?(\d{4})', html or "", re.I)
    if match:
        return match.group(1)
    match = re.search(r'"datePublished"\s*:\s*"(\d{4})', html or "", re.I)
    if match:
        return match.group(1)
    return ""


def _detail_rating(html):
    match = re.search(r'"ratingValue"\s*:\s*"?(\\?\d+(?:\.\d+)?)', html or "", re.I)
    if match:
        return match.group(1).replace("\\", "")
    match = re.search(r'(\d+(?:\.\d+)?)\s*/\s*10', html or "", re.I)
    if match:
        return match.group(1)
    return ""


def get_categories(mtype="movie"):
    return [
        {"title": "أفلام أجنبية",  "url": _category_from_home("افلام اجنبي",   _CATEGORY_FALLBACKS["افلام اجنبي"]),   "type": "category", "_action": "category"},
        {"title": "أفلام عربية",   "url": _category_from_home("افلام عربي",    _CATEGORY_FALLBACKS["افلام عربي"]),    "type": "category", "_action": "category"},
        {"title": "مسلسلات أجنبية","url": _category_from_home("مسلسلات اجنبي", _CATEGORY_FALLBACKS["مسلسلات اجنبي"]),"type": "category", "_action": "category"},
        {"title": "مسلسلات عربية", "url": _category_from_home("مسلسلات عربية", _CATEGORY_FALLBACKS["مسلسلات عربية"]),"type": "category", "_action": "category"},
        {"title": "كارتون وانمي", "url": _category_from_home("مسلسلات انمي",  _CATEGORY_FALLBACKS["مسلسلات انمي"]), "type": "category", "_action": "category"},
        {"title": "ترند",          "url": _category_from_home("تريندج",        _CATEGORY_FALLBACKS["تريندج"]),        "type": "category", "_action": "category"},
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

    log("Wecima: category {} -> {} items".format(url, len(items)))
    next_page = _extract_next_page(html)
    if next_page:
        items.append({"title": "➡️ الصفحة التالية", "url": next_page, "type": "category", "_action": "category"})
    return items


def search(query, page=1):
    base = _get_base()
    items = []
    html = ""
    search_urls = [
        _search_url() + quote_plus(query),
        urljoin(base, "search/") + quote_plus(query),
    ]
    for search_url in search_urls:
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

    title = _detail_title(html)
    poster = _detail_poster(html)
    plot = _detail_plot(html)
    year = _detail_year(title, html)
    rating = _detail_rating(html)

    servers = _extract_servers(html)
    episodes = [] if servers else _extract_episode_cards(html)
    log("Wecima: detail {} -> servers={}, episodes={}".format(url, len(servers), len(episodes)))

    item_type = m_type or (_guess_type(title, final_url or url))
    if episodes:
        item_type = "series"
    elif servers and any(token in (title or "") for token in ("الحلقة", "حلقة")):
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
    import re as _re
    import base64 as _base64
    from .base import fetch, _extract_packer_blocks, decode_packer, urljoin as _urljoin

    base_url = "https://wecima.rent/"
    stream_url = url
    referer = base_url

    if "|" in url:
        parts = url.split("|", 1)
        stream_url = parts[0]
        if "Referer=" in parts[1]:
            referer = parts[1].split("Referer=")[1].strip()

    def _norm(u, base=None):
        u = (u or "").replace("&amp;", "&").replace("\\/", "/").replace("\\u0026", "&").strip()
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return _urljoin(base or stream_url, u)
        return u

    def _extract_media_from_text(text, base=None):
        if not text:
            return ""

        patterns = [
            r'<source[^>]+src=["\']([^"\']+(?:m3u8|mp4|txt)[^"\']*)["\']',
            r'"file"\s*:\s*"([^"]+(?:m3u8|mp4|txt)[^"]*)"',
            r"'file'\s*:\s*'([^']+(?:m3u8|mp4|txt)[^']*)'",
            r'"src"\s*:\s*"([^"]+(?:m3u8|mp4|txt)[^"]*)"',
            r"'src'\s*:\s*'([^']+(?:m3u8|mp4|txt)[^']*)'",
            r'"(?:hls|hls2|hls3|hls4|playlist|master)"\s*:\s*"([^"]+)"',
            r"'(?:hls|hls2|hls3|hls4|playlist|master)'\s*:\s*'([^']+)'",
            r'(https?://[^\s"\'<>]+(?:m3u8|mp4|txt)[^\s"\'<>]*)',
        ]
        for pat in patterns:
            m = _re.search(pat, text, _re.I | _re.S)
            if m:
                return _norm(m.group(1), base)

        # location redirects / window.open
        redirect_patterns = [
            r'location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
            r'window\.open\(\s*["\']([^"\']+)["\']',
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*(?:Click|Continue|تحميل|مشاهدة)',
        ]
        for pat in redirect_patterns:
            m = _re.search(pat, text, _re.I | _re.S)
            if m:
                return _norm(m.group(1), base)

        # base64 blobs
        for b64 in _re.findall(r'atob\(["\']([A-Za-z0-9+/=]{40,})["\']\)', text, _re.I):
            try:
                dec = _base64.b64decode(b64).decode("utf-8", "ignore")
            except Exception:
                dec = ""
            u = _extract_media_from_text(dec, base)
            if u:
                return u

        return ""

    def _extract_from_html(html, base=None):
        if not html:
            return ""
        # direct html
        u = _extract_media_from_text(html, base)
        if u:
            return u

        # packed js
        for block in _extract_packer_blocks(html):
            try:
                dec = decode_packer(block)
            except Exception:
                dec = ""
            if dec:
                u = _extract_media_from_text(dec, base)
                if u:
                    return u
        return ""

    # akhbarworld helper param decode
    real_server_url = ""
    if "akhbarworld.online" in stream_url or "mycimafsd=" in stream_url:
        b64_match = _re.search(r'mycimafsd=([A-Za-z0-9+/=]+)', stream_url)
        if b64_match:
            try:
                real_server_url = _base64.b64decode(b64_match.group(1) + "==").decode("utf-8").strip()
            except Exception:
                real_server_url = ""

    # Step 1: fetch original server page
    html, final_url = fetch(stream_url, referer=referer)
    current_url = final_url or stream_url

    # Step 2: if bad html and encoded fallback exists, use it
    if (not html or len(html) < 300) and real_server_url:
        html, final_url = fetch(real_server_url, referer=referer)
        current_url = final_url or real_server_url

    # Step 3: extract candidate from returned html
    candidate = _extract_from_html(html, current_url)
    if not candidate and real_server_url:
        candidate = _norm(real_server_url, current_url)

    # Step 4: follow one or two intermediate hops if candidate is not final media
    hops = 0
    seen = set()
    while candidate and hops < 3:
        if candidate in seen:
            break
        seen.add(candidate)

        low = candidate.lower()
        if ".m3u8" in low or ".mp4" in low or ".txt" in low:
            return candidate, None, referer

        # fetch intermediate url (like link.mycima.cv / gate / redirect pages)
        html2, final2 = fetch(candidate, referer=current_url or referer)
        next_base = final2 or candidate

        # if fetch redirected directly to media
        if next_base and any(x in next_base.lower() for x in (".m3u8", ".mp4", ".txt")):
            return _norm(next_base, next_base), None, current_url or referer

        next_candidate = _extract_from_html(html2, next_base)
        if not next_candidate:
            # maybe the fetched page itself is a final opaque link – return it for proxy/headers as last chance
            if "mycima.cv/" in low or "akhbarworld.online" in low:
                return candidate + "|Referer=" + (current_url or referer), None, current_url or referer
            break

        current_url = next_base
        candidate = next_candidate
        hops += 1

    # final attempt from original html
    if html:
        last = _extract_from_html(html, current_url)
        if last:
            return last, None, referer

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

## File: installer.sh
````bash
#!/bin/sh

# ArabicPlayer Enigma2 Plugin Installer
# Professional Script for Novaler 4K Pro and other E2 devices

PLUGIN_PATH="/usr/lib/enigma2/python/Plugins/Extensions/ArabicPlayer"
GITHUB_USER="asdrere123-alt"
REPO_NAME="ArabicPlayer"
TMP_DIR="/tmp/arabicplayer_install"

echo "========================================================="
echo "   ArabicPlayer Installer - Modern Premium UI Version    "
echo "========================================================="

# 1. Cleanup old version
if [ -d "$PLUGIN_PATH" ]; then
    echo "> Removing existing installation..."
    rm -rf "$PLUGIN_PATH"
fi

# 2. Dependency Check (Optional but helpful)
echo "> Checking dependencies..."
# Add any specific opkg packages if needed, e.g., python3-requests
# opkg update > /dev/null 2>&1
# opkg install python3-requests > /dev/null 2>&1

# 3. Download and Extract
echo "> Downloading latest version from GitHub..."
mkdir -p "$TMP_DIR"
cd "$TMP_DIR"

wget -q "--no-check-certificate" "https://github.com/$GITHUB_USER/$REPO_NAME/archive/refs/heads/main.tar.gz" -O main.tar.gz
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to download from GitHub!"
    exit 1
fi

echo "> Extracting files..."
tar -xzf main.tar.gz
CP_DIR=$(ls -d */ | grep "$REPO_NAME")
mv "$CP_DIR" "/usr/lib/enigma2/python/Plugins/Extensions/ArabicPlayer"

# 4. Final Cleanup
echo "> Cleaning up temporary files..."
rm -rf "$TMP_DIR"

# 5. Success and Restart
echo "========================================================="
echo "   ArabicPlayer INSTALLED SUCCESSFULLY!                  "
echo "   Restarting Enigma2 to load the new Premium UI...      "
echo "========================================================="

# Auto-restart Enigma2 (Ultra-robust approach)
echo "> Sending restart command..."
# Try Web Interface first (Most reliable across all images)
wget -qO - http://127.0.0.1/web/powerstate?newstate=3 > /dev/null 2>&1

# Fallbacks
if [ -f /usr/bin/systemctl ]; then
    systemctl restart enigma2
elif [ -f /sbin/init ]; then
    killall -9 enigma2 > /dev/null 2>&1
    init 4 && sleep 1 && init 3
else
    killall -9 enigma2
fi

exit 0

exit 0
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
import traceback
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
from Components.Sources.StaticText import StaticText
from enigma import eTimer, ePicLoad, eServiceReference, iPlayableService, eSize, ePoint
from Tools.LoadPixmap        import LoadPixmap
from Components.ServiceEventTracker import ServiceEventTracker

# Imports for custom player
try:
    from Screens.InfoBarGenerics import (
        InfoBarSeek, InfoBarShowHide,
        InfoBarAudioSelection, InfoBarNotifications,
    )
except ImportError:
     pass  # not used directly; safe to ignore on builds that split this module

_PLUGIN_VERSION = "2.0.2"  # green button added
_PLUGIN_NAME    = "ArabicPlayer"
_PLUGIN_OWNER   = "أحمد إبراهيم"
_DEFAULT_TMDB_API_KEY = "01fd9e035ea1458748e99eb7216b0259"
_TYPE_LABELS    = {"movie": "فيلم", "series": "مسلسل", "episode": "حلقة"}
_TMDB_API_BASE  = "https://api.themoviedb.org/3"
_TMDB_IMG_BASE  = "https://image.tmdb.org/t/p/w500"
_SEARCH_SITE_ORDER = ("egydead", "akoam", "arabseed", "wecima", "topcinema")

# ─── Neon Color Palette ──────────────────────────────────────────────────────
_CLR = {
    "bg":           "#0D1117",   # أسود مزرق عميق
    "surface":      "#161B22",   # رمادي مظلم
    "surface2":     "#1C2333",   # رمادي أفتح قليلاً
    "selected":     "#21262D",   # خلفية العنصر المحدد
    "border":       "#30363D",   # حدود خفيفة
    "cyan":         "#00E5FF",   # سيان نيون
    "purple":       "#E040FB",   # بنفسجي نيون
    "gold":         "#FFD740",   # ذهبي دافئ
    "green":        "#39D98A",   # أخضر نيون
    "red":          "#FF6B6B",   # أحمر ناعم
    "blue":         "#58A6FF",   # أزرق فاتح
    "text":         "#F0F6FC",   # نص أبيض فاتح
    "text2":        "#8B949E",   # نص ثانوي
    "text_dim":     "#484F58",   # نص باهت
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

# Global User-Agent matching the successful curl test
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


def _get_tmdb_poster(title, year=None, item_type="movie"):
    if not _DEFAULT_TMDB_API_KEY: return ""
    clean = _clean_title_for_tmdb(title)
    if not clean: return ""
    try:
        url = "{}/search/{}?api_key={}&query={}".format(
            _TMDB_API_BASE, 
            "movie" if item_type == "movie" else "tv",
            _DEFAULT_TMDB_API_KEY,
            quote(clean)
        )
        if year:
            url += "&year={}".format(year) if item_type == "movie" else "&first_air_date_year={}".format(year)
            
        req = urllib2.Request(url, headers={"User-Agent": SAFE_UA})
        data = json.loads(urllib2.urlopen(req, timeout=5).read())
        results = data.get("results", [])
        if results:
            path = results[0].get("poster_path")
            if path:
                return _TMDB_IMG_BASE + path
    except Exception:
        pass
    return ""


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
    ranked = []
    for item in _dedupe_items(items):
        title = item.get("title", "")
        ntitle = _normalize_query(title)
        rank = 9
        if ntitle == q:
            rank = 0
        elif ntitle.startswith(q):
            rank = 1
        elif q and q in ntitle:
            rank = 2
        ranked.append((rank, title.lower(), item))
    ranked.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in ranked]


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
    title = (item.get("title") or "---").strip()
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
    # preserve last_position_sec saved by the tracker from the previous session
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
    """Return last saved position in seconds (0 if none or < 30s)."""
    for item in (_load_state().get("history") or []):
        if item.get("url") == url:
            pos = int(item.get("last_position_sec") or 0)
            return pos if pos > 30 else 0
    return 0


def _save_position(url, seconds):
    """Persist last playback position to the matching history entry.
    Pass seconds=0 to explicitly clear the resume point.
    Positions 1-29s are ignored (not worth resuming).
    """
    seconds = int(seconds or 0)
    if 0 < seconds < 30:
        my_log("_save_position: skipping {}s (< 30s threshold)".format(seconds))
        return
    # seconds == 0 means explicit clear -- allow it through
    state = _load_state()
    for item in (state.get("history") or []):
        if item.get("url") == url:
            item["last_position_sec"] = seconds
            _save_state(state)
            return


# Global position tracker -- module-level so it survives
# SimplePlayer -> MoviePlayer screen transitions.
# Uses wall-clock time instead of getPlayPosition() because
# HiSilicon (VU+ Duo4K) returns a frozen PTS for HTTP streams.
_GLOBAL_POS_TIMER      = None
_GLOBAL_POS_SESSION    = None
_GLOBAL_POS_ITEM       = ""
_GLOBAL_PLAY_START_WALL  = 0.0   # time.time() when play confirmed
_GLOBAL_PLAY_START_POS   = 0     # resume_pos at play-start (seconds)
_GLOBAL_LAST_SEEK_TARGET = -1    # last seekTo target in seconds (-1=none)


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
    _GLOBAL_LAST_SEEK_TARGET = -1  # reset on each new play session
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


def _wrap_plot_text(text, width=48, max_lines=4):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return "القصة غير متوفرة حالياً لهذا العنصر."

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

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    if lines:
        consumed = " ".join(lines)
        if len(consumed) < len(text):
            lines[-1] = lines[-1].rstrip(" .،") + "..."
        return "\n".join(lines)

    return text


def _drain_cmit_queue():
    """Drain callInMainThread queue on Enigma2 main loop."""
    with _CMIT_LOCK:
        items = list(_CMIT_QUEUE)
        del _CMIT_QUEUE[:]
    for _f, _a, _kw in items:
        try: _f(*_a, **_kw)
        except Exception as _e:
            try: my_log("CMIT drain: {}".format(_e))
            except Exception: pass


def callInMainThread(func, *args, **kwargs):
    """Queue func for Enigma2 main loop via eTimer (50ms).
    Avoids direct cross-thread calls that crash HiSilicon builds."""
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
            # Listen on 0.0.0.0 for maximum loopback compatibility
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
        title = item.get("title", "")
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

    # ── Loaders ───────────────────────────────────────────────────────────────
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

    def _onSearchQuery(self, result):
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
        subtitle = "بحث في {}".format(_search_scope_label(scope))
        self._setHeader(
            "نتائج: {}".format(query),
            subtitle
        )
        self._setList(items)

    # ── Open Item ─────────────────────────────────────────────────────────────
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
                callInMainThread(self["status"].setText,
                    u"Timeout — please try again")
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

    def _onLoaded(self, data):
        if not data:
            self["status"].setText("تعذر تحميل الصفحة")
            return

        self._data = data
        current_title = data.get("title") or self._item.get("title", "")
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
        _ar_count = sum(1 for _c in _pt[:80] if "؀" <= _c <= "ۿ")
        if _ar_count > int(len(_pt[:80]) * 0.3):
            _pt = "‏" + _pt
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
        """Reload poster when screen is shown again (after returning from player)."""
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

        title = self["title"].getText()
        if quality:
            title += " [{}]".format(quality)
            
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
                # Format resume time with hours if needed
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
            self["poster"].hide()
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


# ─── Simple Player Fallback (CANVAS-BASED PROGRESS BAR, FULLY WORKING) ───────
class ArabicPlayerSimplePlayer(Screen):
    skin = """
    <screen name="ArabicPlayerSimplePlayer" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="transparent">

        <widget name="osd_shadow"   position="148,856" size="1624,230" backgroundColor="#000000" zPosition="9" />
        <widget name="overlay_bg"   position="160,860" size="1600,210" backgroundColor="#0A0E14" zPosition="10" />
        <widget name="osd_topline"  position="160,860" size="1600,3" backgroundColor="#00E5FF" zPosition="11" />
        <widget name="osd_titlebar" position="160,860" size="1600,52" backgroundColor="#0D1520" zPosition="11" />
        <widget name="osd_title"    position="180,868" size="1180,38" font="Regular;30" foregroundColor="#00E5FF" transparent="1" zPosition="12" />
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
        # OSD widgets
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
        self.title = title
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
        # Hide all OSD widgets first
        for w in self._OSD_WIDGETS:
            try: self[w].hide()
            except: pass
        # Text-based progress bar -- no canvas setup needed

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
                # Unicode text-based progress bar (works on HiSilicon during video)
                BAR_W = 48
                filled = max(0, min(BAR_W, int(pct * BAR_W)))
                bar = u"█" * filled + u"░" * (BAR_W - filled)
                self["prog_bar"].setText(u"{} {:.1f}%".format(bar, pct * 100))
            else:
                self["osd_durtext"].setText("")
                self["prog_bar"].setText("")
            self["osd_keys"].setText("OK=Pause  << -10s  +10s >>  <<< -60s  +60s >>>   Green=Restart   Stop=Save&Exit")
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
        _start_pos_tracker(self.session, self._item_url, start_pos=self._resume_pos)
        if self._resume_pos > 30:
            self._seek_retry_count = 0
            self._seek_timer.start(6000, True)
        self["osd_title"].setText(self.title)
        self["status"].setText(u"▶ Playing")
        self._total_secs = 0
        self.__showOSD(True)
        # (no canvas to show -- text bar updates automatically)

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
        my_log("Restart requested by green button")
        try:
            self._seek_timer.stop()
        except: pass
        self._play_confirmed = False
        try:
            self.session.nav.stopService()
        except: pass
        self._candidate_idx = -1
        self["status"].setText("Restarting stream...")
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
                # Stream not ready yet — retry if attempts remain
                self._seek_retry_count += 1
                if self._seek_retry_count <= 3:
                    my_log("doSeek: no seek interface, retry {}/3 in 4s".format(self._seek_retry_count))
                    self._seek_timer.start(4000, True)
                else:
                    my_log("doSeek: giving up after 3 retries")
                return

            # Fire the seek
            seek.seekTo(self._resume_pos * 90000)
            my_log("Resume seekTo: {}s (attempt {})".format(self._resume_pos, self._seek_retry_count + 1))

            global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
            global _GLOBAL_LAST_SEEK_TARGET
            _GLOBAL_LAST_SEEK_TARGET = self._resume_pos
            _GLOBAL_PLAY_START_POS = max(0, self._resume_pos - 2)
            _GLOBAL_PLAY_START_WALL = time.time()
            if self._paused:
                self._paused_elapsed = self._resume_pos
            self._total_secs = 0

            # Schedule a verification 4s later to confirm seek actually worked
            self._seek_verify_timer.start(4000, True)

            if self._osd_visible:
                self.__updateOSD()
        except Exception as e:
            my_log("doSeek failed: {} — retry {}/3".format(e, self._seek_retry_count))
            self._seek_retry_count += 1
            if self._seek_retry_count <= 3:
                self._seek_timer.start(4000, True)

    def __verifySeek(self):
        """Check that seek actually landed near the target; retry if not."""
        if not self._resume_pos or self._resume_pos <= 30:
            return
        try:
            wall = _GLOBAL_PLAY_START_WALL
            base = _GLOBAL_PLAY_START_POS
            if wall:
                elapsed = int((time.time() - wall) + base)
            else:
                elapsed = 0

            # If position is still near 0 the seek was silently ignored
            if elapsed < 10 and self._seek_retry_count <= 3:
                self._seek_retry_count += 1
                my_log("verifySeek: pos={}s, seek likely ignored — retry {}/3".format(
                    elapsed, self._seek_retry_count))
                self._seek_timer.start(3000, True)
            else:
                my_log("verifySeek: pos={}s OK (target={}s)".format(elapsed, self._resume_pos))
        except Exception as e:
            my_log("verifySeek error: {}".format(e))

    def __restorePrevious(self):
        if self._restored_previous:
            return
        self._restored_previous = True
        _restore_previous_service(self.session, self.previous_service)


# ─── Global play function (DO NOT INDENT INSIDE CLASS) ────────────────────────
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
