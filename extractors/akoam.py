# -*- coding: utf-8 -*-
import re
from .base import fetch, urljoin

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
