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
