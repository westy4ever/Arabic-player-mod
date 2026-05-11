# -*- coding: utf-8 -*-
"""
Extractor for faselhdx.bid (FaselHD variant)
Written from scratch based on real HTML analysis.

Site:       https://web5106x.faselhdx.bid  (also web596x.faselhdx.bid)
Player:     /video_player?player_token=BASE64  → ZFG / scdns.io CDN
Stream CDN: master.c.scdns.io  (IP-bound signed HLS, requires the ZFG JS runtime)

Card HTML (confirmed from saved pages):
  <div class="postDiv ">
    <a href="URL">
      <div class="imgdiv-class">
        <img data-src="POSTER" alt="TITLE" …>
      </div>
      <div class="postInner">
        <div class="h1">TITLE</div>
      </div>
    </a>
  </div>

Server HTML (detail page, confirmed):
  <ul class="tabs-ul">
    <li … onclick="player_iframe.location.href = 'VIDEO_PLAYER_URL'">…</li>
  </ul>
  <iframe name="player_iframe" data-src="VIDEO_PLAYER_URL" …>

Video player URL:
  https://web5106x.faselhdx.bid/video_player?player_token=BASE64_ENCRYPTED_TOKEN

Stream URL (from network log, requires browser/JS):
  https://master.c.scdns.io/stream/v2/TOKEN/TIMESTAMP/normal/0/IP/yes/FP/DOMAIN/master.m3u8
  The token is IP-bound and signed by the ZFG CDN at runtime.
  Without a JS engine we cannot replicate it; we return the video_player URL as
  an embed server and let the host app resolve it (e.g. via WebView interception).
"""

import re
import json
import sys

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urljoin as _urljoin, urlparse
else:
    from urllib import quote_plus
    from urlparse import urlparse, urljoin as _urljoin

from extractors.base import fetch, urljoin, log
from extractors.base import extract_stream as base_extract_stream

# Primary domain – overridden dynamically via _set_domain()
BASE_URL = "https://web5106x.faselhdx.bid"

# Known domain variants – update _set_domain() as the site rotates
_KNOWN_DOMAINS = [
    "https://web5106x.faselhdx.bid",
    "https://web596x.faselhdx.bid",
    "https://web5306x.faselhdx.bid",
    "https://faselhd.bid",
]

_DEFAULT_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
    "DNT":             "1",
}


# ── helpers ────────────────────────────────────────────────────────────────────

def _set_domain(url):
    """Update BASE_URL if the given URL belongs to a known faselhdx domain."""
    global BASE_URL
    for d in _KNOWN_DOMAINS:
        if d in url:
            BASE_URL = d
            return
    # Generic: extract scheme+host from any URL and use it
    p = urlparse(url)
    if p.scheme and p.netloc and "faselhdx" in p.netloc:
        BASE_URL = "{}://{}".format(p.scheme, p.netloc)


def _normalize_url(url):
    if not url:
        return ""
    url = str(url).strip().replace("&amp;", "&")
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return BASE_URL + "/" + url.lstrip("/")
    return url


def _clean_title(title):
    if not title:
        return ""
    title = re.sub(r'<[^>]+>', '', title)       # strip HTML tags
    title = title.replace("&amp;", "&")
    title = title.replace("فاصل إعلاني", "").replace("FaselHD", "")
    title = re.sub(r'\s*[-|]\s*(فاصل\s*إعلاني|FaselHD).*$', '', title, flags=re.I)
    return title.strip()


def _fetch(url, referer=None):
    hdrs = dict(_DEFAULT_HEADERS)
    hdrs["Referer"] = referer or BASE_URL
    return fetch(url, referer=referer or BASE_URL, extra_headers=hdrs)


# ── categories ────────────────────────────────────────────────────────────────

def get_categories():
    """
    All category URLs confirmed from nav HTML of web5106x.faselhdx.bid.
    Using slug-based URLs (not Arabic-encoded WordPress category paths).
    """
    return [
        # Movies
        {"title": "🆕 المضاف حديثا",         "url": BASE_URL + "/most_recent",        "type": "category", "_action": "category"},
        {"title": "🎬 جميع الافلام",          "url": BASE_URL + "/all-movies",          "type": "category", "_action": "category"},
        {"title": "🎬 افلام اجنبي",           "url": BASE_URL + "/movies",              "type": "category", "_action": "category"},
        {"title": "🎬 افلام مدبلجة",          "url": BASE_URL + "/dubbed-movies",       "type": "category", "_action": "category"},
        {"title": "🎬 افلام هندي",            "url": BASE_URL + "/hindi",               "type": "category", "_action": "category"},
        {"title": "🎬 افلام اسيوي",           "url": BASE_URL + "/asian-movies",        "type": "category", "_action": "category"},
        {"title": "🎬 افلام انمي",            "url": BASE_URL + "/anime-movies",        "type": "category", "_action": "category"},
        {"title": "⭐ الاعلي تصويتا",         "url": BASE_URL + "/movies_top_votes",    "type": "category", "_action": "category"},
        {"title": "👁️ الاعلي مشاهدة",        "url": BASE_URL + "/movies_top_views",    "type": "category", "_action": "category"},
        {"title": "🏆 الاعلي IMDB",           "url": BASE_URL + "/movies_top_imdb",     "type": "category", "_action": "category"},
        {"title": "🏆 جوائز الاوسكار",        "url": BASE_URL + "/oscars-winners",      "type": "category", "_action": "category"},
        # Series
        {"title": "📺 جميع المسلسلات",        "url": BASE_URL + "/series",              "type": "category", "_action": "category"},
        {"title": "📺 المضاف حديثا (مسلسلات)", "url": BASE_URL + "/recent_series",      "type": "category", "_action": "category"},
        {"title": "📺 احدث الحلقات",          "url": BASE_URL + "/episodes",            "type": "category", "_action": "category"},
        {"title": "📺 الاعلي مشاهدة (مسلسلات)", "url": BASE_URL + "/series_top_views",  "type": "category", "_action": "category"},
        {"title": "📺 الاعلي IMDB (مسلسلات)", "url": BASE_URL + "/series_top_imdb",    "type": "category", "_action": "category"},
        # TV Shows
        {"title": "📡 جميع البرامج",          "url": BASE_URL + "/tvshows",             "type": "category", "_action": "category"},
        {"title": "📡 المضاف حديثا (برامج)",  "url": BASE_URL + "/recent_tvshows",      "type": "category", "_action": "category"},
        # Asian
        {"title": "🌏 مسلسلات اسيوي",         "url": BASE_URL + "/asian-series",        "type": "category", "_action": "category"},
        {"title": "🌏 المضاف حديثا (اسيوي)",  "url": BASE_URL + "/recent_asian",        "type": "category", "_action": "category"},
        # Anime
        {"title": "🎌 جميع الانمي",            "url": BASE_URL + "/anime",               "type": "category", "_action": "category"},
        {"title": "🎌 المضاف حديثا (انمي)",   "url": BASE_URL + "/recent_anime",        "type": "category", "_action": "category"},
    ]


# ── category item parsing ─────────────────────────────────────────────────────

def get_category_items(url, page=1):
    """
    Parse a faselhdx.bid category/listing page.

    Card HTML (confirmed from .htm files):
      <div class="postDiv ">
        <a href="ITEM_URL">
          <div class="imgdiv-class">
            <img data-src="POSTER_URL" alt="TITLE_FALLBACK">
          </div>
          <div class="postInner">
            <div class="h1">TITLE</div>
          </div>
        </a>
      </div>

    Note: <img src> is a local blank.gif placeholder; real poster is in data-src.

    Pagination: Bootstrap  <a class="page-link" href=".../page/N">
    """
    _set_domain(url)

    # Resolve page number from URL or parameter
    pm = re.search(r'/page/(\d+)/?$', url.rstrip('/'))
    if pm and page == 1:
        page = int(pm.group(1))

    log("faselhd_hdx: get_category_items page={} url={}".format(page, url))

    # Build page URL
    clean = re.sub(r'/page/\d+/?$', '', url.rstrip('/'))
    current_url = "{}/page/{}/".format(clean, page) if page > 1 else clean + "/"

    html, _ = _fetch(current_url, referer=BASE_URL)
    if not html:
        log("faselhd_hdx: fetch failed: {}".format(current_url))
        return []

    items     = []
    seen_urls = set()

    # ── card pattern ──────────────────────────────────────────────────────────
    # Match every <div class="postDiv …"> block
    # We extract the <a href>, the data-src from <img>, and the <div class="h1"> title.
    card_pat = re.compile(
        r'<div[^>]*class="postDiv[^"]*"[^>]*>\s*'
        r'<a\s+href="([^"]+)"[^>]*>'          # group 1: item URL
        r'.*?'
        r'data-src="([^"]+)"'                  # group 2: poster URL (real, in data-src)
        r'.*?'
        r'<div[^>]*class="h1"[^>]*>([^<]+)</div>',  # group 3: title
        re.DOTALL | re.I
    )

    for m in card_pat.finditer(html):
        item_url  = _normalize_url(m.group(1))
        poster    = _normalize_url(m.group(2))
        title     = _clean_title(m.group(3))

        if not item_url or item_url in seen_urls:
            continue
        if "/page/" in item_url:
            continue

        item_type = "series" if (
            "/series" in item_url or
            "/episodes" in item_url or
            "مسلسل" in title or
            "/anime" in item_url and "افلام" not in item_url
        ) else "movie"

        seen_urls.add(item_url)
        items.append({
            "title":   title,
            "url":     item_url,
            "poster":  poster,
            "rating":  "",
            "year":    "",
            "type":    item_type,
            "_action": "details",
        })
        if len(items) >= 50:
            break

    log("faselhd_hdx: extracted {} items (page {})".format(len(items), page))

    # ── pagination ────────────────────────────────────────────────────────────
    # Bootstrap pagination: <a class="page-link" href="…/page/N">
    next_n   = page + 1
    next_pat = re.compile(
        r'<a[^>]+class="[^"]*page-link[^"]*"[^>]+href="([^"]+/page/{}/[^"]*)"'.format(next_n),
        re.I
    )
    nm = next_pat.search(html)
    if nm:
        items.append({
            "title":   "➡️ Next Page - Page {}".format(next_n),
            "url":     _normalize_url(nm.group(1)),
            "type":    "category",
            "_action": "category",
        })
    else:
        # Fallback: look for any › arrow link
        arrow = re.search(
            r'<a[^>]+class="[^"]*page-link[^"]*"[^>]+href="([^"]+)"[^>]*>\s*[›»]\s*</a>',
            html, re.I
        )
        if arrow:
            items.append({
                "title":   "➡️ Next Page",
                "url":     _normalize_url(arrow.group(1)),
                "type":    "category",
                "_action": "category",
            })

    return items


# ── search ────────────────────────────────────────────────────────────────────

def search(query, page=1):
    _set_domain(BASE_URL)
    url = BASE_URL + "/?s=" + quote_plus(query)
    if page > 1:
        url += "&paged=" + str(page)

    html, _ = _fetch(url, referer=BASE_URL)
    if not html:
        return []

    items, seen = [], set()
    card_pat = re.compile(
        r'<div[^>]*class="postDiv[^"]*"[^>]*>\s*'
        r'<a\s+href="([^"]+)"[^>]*>'
        r'.*?data-src="([^"]+)"'
        r'.*?<div[^>]*class="h1"[^>]*>([^<]+)</div>',
        re.DOTALL | re.I
    )
    for m in card_pat.finditer(html):
        item_url = _normalize_url(m.group(1))
        if item_url in seen:
            continue
        seen.add(item_url)
        items.append({
            "title":   _clean_title(m.group(3)),
            "url":     item_url,
            "poster":  _normalize_url(m.group(2)),
            "type":    "movie",
            "_action": "details",
        })
    return items


# ── detail page ───────────────────────────────────────────────────────────────

def get_page(url):
    """
    Parse a faselhdx.bid movie/series/episode detail page.

    Server list (confirmed HTML):
      <ul class="tabs-ul">
        <li onclick="player_iframe.location.href = 'VIDEO_PLAYER_URL'">
          <a href="javascript:;">سيرفر المشاهدة #01</a>
        </li>
        ...
      </ul>
      <iframe name="player_iframe" data-src="VIDEO_PLAYER_URL" …>

    VIDEO_PLAYER_URL = https://DOMAIN/video_player?player_token=BASE64TOKEN
    The token is server-encrypted; the ZFG CDN system resolves it to a
    scdns.io HLS stream at runtime in the browser (IP-bound, cannot be
    reproduced server-side without a JS engine).
    We return the video_player URLs as "embed" servers.
    """
    _set_domain(url)
    log("faselhd_hdx: get_page {}".format(url))

    html, final_url = _fetch(url, referer=BASE_URL)
    if not html:
        log("faselhd_hdx: get_page failed: {}".format(url))
        return {"title": "Error", "servers": [], "items": [], "type": "movie"}

    # ── post ID ───────────────────────────────────────────────────────────────
    # Found in <body class="… postid-298828 …">
    post_id = None
    pid_m = re.search(r'\bpostid-(\d+)\b', html)
    if pid_m:
        post_id = pid_m.group(1)
        log("faselhd_hdx: post_id={}".format(post_id))

    # ── metadata ──────────────────────────────────────────────────────────────
    # Title: <div class="h1 title">TITLE<span …>rating</span></div>
    title_m = re.search(
        r'<div[^>]*class="[^"]*h1 title[^"]*"[^>]*>(.*?)(?:<span|</div>)',
        html, re.I | re.DOTALL
    )
    if not title_m:
        # Fallback: og:title
        title_m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    title = _clean_title(title_m.group(1)) if title_m else ""

    # Poster: og:image
    pm = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(pm.group(1)) if pm else ""

    # Plot: <div class="singleDesc"><p>TEXT</p>
    plotm = re.search(r'class="singleDesc"[^>]*>\s*<p>(.*?)</p>', html, re.I | re.DOTALL)
    plot  = _clean_title(plotm.group(1)) if plotm else ""

    # Year: text after سنة or سنة الإنتاج
    ym = re.search(r'(?:سنة[^<]{0,20})<[^>]*>(\d{4})', html, re.I | re.DOTALL)
    if not ym:
        ym = re.search(r'\b(20\d{2})\b', title)
    year = ym.group(1) if ym else ""

    # Rating: <span class="singleStar">…<strong>6.4</strong>
    rm = re.search(r'class="singleStar"[^>]*>.*?<strong>([\d.]+)</strong>', html, re.I | re.DOTALL)
    if not rm:
        rm = re.search(r'class="pImdb"[^>]*>.*?([\d.]+)', html, re.I | re.DOTALL)
    rating = rm.group(1) if rm else ""

    item_type = "series" if (
        "/series" in url or "/episodes" in url or
        "مسلسل" in title or "/anime" in url
    ) else "movie"

    # ── servers ───────────────────────────────────────────────────────────────
    # Primary: onclick attributes in <ul class="tabs-ul"> <li> elements
    servers, seen_urls = [], set()

    def _add_server(embed_url, name=None):
        embed_url = embed_url.replace("&amp;", "&").strip()
        if embed_url and embed_url not in seen_urls:
            seen_urls.add(embed_url)
            label = name or "🎬 Server {}".format(len(servers) + 1)
            servers.append({"name": label, "url": embed_url, "type": "embed"})
            log("faselhd_hdx: server {}: {}".format(len(servers), embed_url[:80]))

    # Find the tabs-ul block first for scope
    tabs_m = re.search(r'<ul[^>]*class="[^"]*tabs-ul[^"]*"[^>]*>(.*?)</ul>', html, re.I | re.DOTALL)
    if tabs_m:
        tabs_html = tabs_m.group(1)
        # Each <li onclick="player_iframe.location.href = 'URL'">
        for li_m in re.finditer(
            r'onclick=["\']player_iframe\.location\.href\s*=\s*["\']([^"\']+)["\']',
            tabs_html, re.I
        ):
            server_url = _normalize_url(li_m.group(1))
            # Get the server label
            label_m = re.search(r'<a[^>]*>.*?</a>', tabs_html[li_m.start():li_m.start()+300], re.DOTALL | re.I)
            label = "🎬 Server {}".format(len(servers) + 1)
            if label_m:
                raw_label = re.sub(r'<[^>]+>', '', label_m.group(0)).strip()
                if raw_label:
                    label = raw_label
            _add_server(server_url, label)

    # Fallback: iframe[name="player_iframe"] data-src
    ifm = re.search(
        r'<iframe[^>]+name=["\']player_iframe["\'][^>]+data-src=["\']([^"\']+)["\']',
        html, re.I
    )
    if ifm:
        _add_server(_normalize_url(ifm.group(1)))

    log("faselhd_hdx: {} servers found for {}".format(len(servers), url))

    # ── episodes (series) ─────────────────────────────────────────────────────
    episodes = []
    if item_type == "series":
        for ep_m in re.finditer(
            r'<a[^>]+href="([^"]+(?:faselhdx|faselhd)[^"]+)"[^>]*>'
            r'[^<]*(?:الحلقة|Episode)\s*(\d+)',
            html, re.I
        ):
            ep_url = _normalize_url(ep_m.group(1))
            episodes.append({
                "title":   "الحلقة {}".format(ep_m.group(2)),
                "url":     ep_url,
                "type":    "episode",
                "_action": "details",
            })

    return {
        "url":     final_url or url,
        "title":   title,
        "plot":    plot,
        "poster":  poster,
        "year":    year,
        "rating":  rating,
        "servers": servers,
        "items":   episodes,
        "type":    item_type,
    }


# ── stream extraction ─────────────────────────────────────────────────────────

def extract_stream(url):
    """
    Extract a playable stream URL from a faselhdx.bid server URL.

    The server URL is of the form:
      https://DOMAIN/video_player?player_token=BASE64_TOKEN

    The token is decrypted server-side; the response page embeds a ZFG CDN
    script that generates a signed, IP-bound scdns.io HLS URL at runtime.

    Since the scdns.io token requires:
      - The viewer's real IP (embedded in the URL path)
      - A ZFG HMAC signature computed in the JS runtime
      - A short-lived timestamp (~10 min validity)
    … it cannot be reproduced from a non-browser context.

    Strategy:
      1. Fetch the video_player page; scan for any m3u8 URL directly embedded.
      2. If a data-zone-id is found, attempt to call the scdns.io API.
      3. Return the video_player URL itself as a passthrough for WebView players.
    """
    log("faselhd_hdx extract_stream: {}".format(url[:100]))
    url = url.replace("&amp;", "&").strip()
    _set_domain(url)

    # Already a direct m3u8 → pass through
    if ".m3u8" in url:
        quality = "1080p" if "1080" in url else ("720p" if "720" in url else "HD")
        return url, quality, BASE_URL

    # Fetch the video_player page
    if "video_player" in url or "player_token" in url:
        log("faselhd_hdx: fetching video_player page")
        html, _ = _fetch(url, referer=BASE_URL)
        if html:
            # Scan for any direct m3u8 in the page
            m = re.search(r'(https?://[^\s"\'<>`\\]+\.m3u8(?:\?[^\s"\'<>`\\]*)?)', html, re.I)
            if m:
                stream = m.group(1).replace("\\\/", "/").replace("&amp;", "&")
                log("faselhd_hdx: found m3u8 in video_player page: {}".format(stream[:80]))
                quality = "1080p" if "1080" in stream else ("720p" if "720" in stream else "HD")
                return stream, quality, url

            # Try scdns.io master endpoint via data-zone-id
            zone_m = re.search(r'data-zone-id=["\'](\d+)["\']', html, re.I)
            domain_m = re.search(r'data-domain=["\']([^"\']+)["\']', html, re.I)
            if zone_m:
                zone_id = zone_m.group(1)
                domain  = domain_m.group(1) if domain_m else urlparse(url).netloc
                log("faselhd_hdx: trying scdns zone_id={} domain={}".format(zone_id, domain))
                # The scdns.io endpoint infers the stream from the zone + calling IP
                scdns_url = "https://master.c.scdns.io/zfgplayer/{}/master.m3u8".format(zone_id)
                scdns_html, _ = fetch(
                    scdns_url, referer=url,
                    extra_headers={"Referer": url, "Origin": BASE_URL,
                                   "User-Agent": _DEFAULT_HEADERS["User-Agent"]}
                )
                if scdns_html and "#EXTM3U" in scdns_html:
                    log("faselhd_hdx: scdns zone URL worked: {}".format(scdns_url))
                    return scdns_url, "HD", url

        # Return the player URL itself – a WebView player can resolve the ZFG CDN
        log("faselhd_hdx: returning video_player URL for WebView resolution")
        return url, "HD", BASE_URL

    # Unknown embed – try the base extractor
    stream_url, quality, ref = base_extract_stream(url)
    if stream_url:
        return stream_url, quality, ref

    return None, "", BASE_URL
