# -*- coding: utf-8 -*-
"""
Extractor for faselhd.rip
Changelog:
  - govid /e/ page: 3899 bytes, 0 inline scripts → fetch ALL external scripts,
    not just govid.live domain; skip known CDN noise only
  - govid /play/ tokens: no raw digit run → stop guessing from token string;
    instead fetch the /play/ page and look for /e/{id}/ reference inside it
  - Added first-500-char page dump on failure for next debugging round
  - faselhd_hdx 0-items bug fixed in faselhd_hdx.py (separate file)
  - AJAX cap enforced before the fetch call
"""

import sys
import re
import json

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus
else:
    from urllib import quote_plus

from extractors.base import fetch, urljoin, log
from extractors.base import extract_stream as base_extract_stream

BASE_URL    = "https://faselhd.rip"
GOVID_BASE  = "https://govid.live"

# AJAX server probe cap — Server 1 (/e/) costs 0 calls; each probe ≈ 2 s
MAX_AJAX_SERVERS = 5

# External script domains that are known CDN noise — never contain player config
_NOISE_DOMAINS = {
    "unpkg.com", "cdn.jsdelivr.net", "cdnjs.cloudflare.com",
    "ajax.googleapis.com", "code.jquery.com", "stackpath.bootstrapcdn.com",
}


# ── helpers ────────────────────────────────────────────────────────────────────

def _normalize_url(url):
    if not url:
        return ""
    url = str(url).strip()
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(BASE_URL, url)
    return url


def _clean_title(title):
    if not title:
        return ""
    title = title.replace("&amp;", "&")
    title = title.replace("فاصل إعلاني", "").replace("FaselHD", "")
    title = re.sub(r'\s*[-|]\s*فاصل\s*إعلاني.*$', '', title)
    title = re.sub(r'\s*[-|]\s*FaselHD.*$', '', title, flags=re.I)
    return title.strip()


def _find_m3u8(text):
    """Return the first plausible m3u8 URL found anywhere in text."""
    if not text:
        return None
    # Full URL with optional query string
    m = re.search(
        r'(https?://[^\s"\'<>`\\]+\.m3u8(?:\?[^\s"\'<>`\\]*)?)',
        text, re.I)
    if m:
        return m.group(1).replace('\\/', '/').replace('&amp;', '&')
    # JS player config  file:"…"  src:"…"  url:"…"
    m = re.search(
        r'(?:file|src|url|source|hls)\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        text, re.I)
    if m:
        return m.group(1).replace('\\/', '/').replace('&amp;', '&')
    return None


def _is_noise_domain(url):
    for d in _NOISE_DOMAINS:
        if d in url:
            return True
    return False


# ── public API ────────────────────────────────────────────────────────────────

def get_categories():
    return [
        {"title": "🎬 Recent Movies",  "url": BASE_URL + "/movies",       "type": "category", "_action": "category"},
        {"title": "🎬 English Movies", "url": BASE_URL + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a/",           "type": "category", "_action": "category"},
        {"title": "🎬 Arabic Movies",  "url": BASE_URL + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%b9%d8%b1%d8%a8%d9%8a/",                  "type": "category", "_action": "category"},
        {"title": "🎬 Dubbed Movies",  "url": BASE_URL + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%ac%d9%86%d8%a8%d9%8a%d8%a9-%d9%85%d8%af%d8%a8%d9%84%d8%ac%d8%a9/", "type": "category", "_action": "category"},
        {"title": "🎬 Indian Movies",  "url": BASE_URL + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d9%87%d9%86%d8%af%d9%8a/",                   "type": "category", "_action": "category"},
        {"title": "🎬 Turkish Movies", "url": BASE_URL + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%aa%d8%b1%d9%83%d9%8a%d8%a9/",             "type": "category", "_action": "category"},
        {"title": "🎬 Asian Movies",   "url": BASE_URL + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d8%b3%d9%8a%d9%88%d9%8a%d8%a9/",       "type": "category", "_action": "category"},
        {"title": "🎬 Anime Movies",   "url": BASE_URL + "/category/%d8%a7%d9%81%d9%84%d8%a7%d9%85-%d8%a7%d9%86%d9%85%d9%8a/",                   "type": "category", "_action": "category"},
        {"title": "📺 English Series", "url": BASE_URL + "/series",        "type": "category", "_action": "category"},
        {"title": "📺 Turkish Series", "url": BASE_URL + "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%aa%d8%b1%d9%83%d9%8a%d8%a9/", "type": "category", "_action": "category"},
        {"title": "📺 Asian Series",   "url": BASE_URL + "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d8%b3%d9%8a%d9%88%d9%8a%d8%a9/", "type": "category", "_action": "category"},
        {"title": "📺 Anime Series",   "url": BASE_URL + "/category/%d9%85%d8%b3%d9%84%d8%b3%d9%84%d8%a7%d8%aa-%d8%a7%d9%86%d9%85%d9%8a/",       "type": "category", "_action": "category"},
    ]


def get_category_items(url, page=1):
    page_match = re.search(r'/page/(\d+)/', url)
    if page_match and page == 1:
        page = int(page_match.group(1))

    log("faselhd_rip: get_category_items page={} url={}".format(page, url))
    clean_url   = re.sub(r'/page/\d+/?$', '', url.rstrip('/'))
    current_url = clean_url + "/page/{}/".format(page) if page > 1 else clean_url + "/"

    html, _ = fetch(current_url, referer=BASE_URL)
    if not html:
        return []

    items     = []
    seen_urls = set()
    pattern   = (r'<a\s+href="([^"]+)"\s+class="[^"]*show-card[^"]*"'
                 r'[^>]*style="[^"]*background-image:\s*url\(([^)]+)\)[^"]*"'
                 r'[^>]*>(.*?)</a>')

    for href, poster_url, card_content in re.findall(pattern, html, re.DOTALL | re.I):
        full_url = _normalize_url(href)
        if '/category/' in full_url or '/page/' in full_url or full_url in seen_urls:
            continue
        tm = re.search(r'<p[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</p>', card_content, re.I)
        title = tm.group(1).strip() if tm else href.split('/')[-1].replace('-', ' ')
        seen_urls.add(full_url)
        items.append({
            "title":   _clean_title(title),
            "url":     full_url,
            "poster":  _normalize_url(poster_url.strip('\'"')),
            "rating":  "",
            "year":    "",
            "type":    "movie",
            "_action": "details",
        })
        if len(items) >= 50:
            break

    log("faselhd_rip: extracted {} items (page {})".format(len(items), page))

    next_n = page + 1
    nm = re.search(
        r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*page-btn[^"]*"[^>]*>\s*{}\s*</a>'.format(next_n),
        html, re.I)
    if nm:
        items.append({"title": "➡️ Next Page - Page {}".format(next_n),
                      "url": _normalize_url(nm.group(1)), "type": "category", "_action": "category"})
    else:
        am = re.search(r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*page-btn[^"]*"[^>]*>›</a>', html, re.I)
        if am:
            items.append({"title": "➡️ Next Page",
                          "url": _normalize_url(am.group(1)), "type": "category", "_action": "category"})
    return items


def search(query, page=1):
    search_url = BASE_URL + "/?s=" + quote_plus(query)
    if page > 1:
        search_url += "&page=" + str(page)
    html, _ = fetch(search_url, referer=BASE_URL)
    if not html:
        return []
    items, seen_urls = [], set()
    pattern = (r'<a\s+href="([^"]+)"\s+class="[^"]*show-card[^"]*"'
               r'[^>]*style="[^"]*background-image:\s*url\([^)]+\)[^"]*"'
               r'[^>]*>(.*?)</a>')
    for href, card_content in re.findall(pattern, html, re.DOTALL | re.I):
        full_url = _normalize_url(href)
        if full_url in seen_urls:
            continue
        tm = re.search(r'<p[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</p>', card_content, re.I)
        title = tm.group(1) if tm else href.split('/')[-1]
        seen_urls.add(full_url)
        items.append({"title": _clean_title(title), "url": full_url,
                      "type": "movie", "_action": "details"})
    return items


def get_page(url):
    log("faselhd_rip: get_page {}".format(url))
    html, final_url = fetch(url, referer=BASE_URL)
    if not html:
        return {"title": "Error", "servers": [], "items": [], "type": "movie"}

    post_id = None
    for pat in [r'"post_id":\s*"?(\d+)"?', r'var\s+POST_ID\s*=\s*(\d+)', r'data-post-id=["\'](\d+)["\']']:
        m = re.search(pat, html, re.I)
        if m:
            post_id = m.group(1)
            break
    if post_id:
        log("faselhd_rip: extracted POST_ID = {}".format(post_id))

    title_m = (re.search(r'<h1[^>]*class="[^"]*post-title[^"]*"[^>]*>(.*?)</h1>', html, re.I)
               or re.search(r'<title>([^<]+)</title>', html, re.I))
    title  = _clean_title(title_m.group(1)) if title_m else ""
    pm     = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    poster = _normalize_url(pm.group(1)) if pm else ""
    plotm  = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html)
    plot   = _clean_title(plotm.group(1)) if plotm else ""
    ym     = re.search(r'<span[^>]*class="[^"]*meta-tag[^"]*"[^>]*>📅\s*(\d{4})', html, re.I)
    year   = ym.group(1) if ym else ""
    rm     = re.search(r'<i[^>]*class="fa fa-star"[^>]*></i>\s*([0-9.]+)', html, re.I)
    rating = rm.group(1) if rm else ""
    item_type = "series" if ("/series" in url or "مسلسل" in title or "/anime" in url) else "movie"

    episodes = []
    if item_type == "series":
        for m in re.finditer(
                r'<a[^>]+href="([^"]+)"[^>]*class="[^"]*episode-link[^"]*"[^>]*>.*?الحلقة\s*(\d+)',
                html, re.I):
            episodes.append({"title": "الحلقة {}".format(m.group(2)),
                              "url": _normalize_url(m.group(1)), "type": "episode", "_action": "details"})

    servers, seen_embed = [], set()

    def _add(embed_url):
        embed_url = embed_url.replace('&amp;', '&').strip()
        if embed_url and embed_url not in seen_embed:
            seen_embed.add(embed_url)
            servers.append({"name": "🎬 Server {}".format(len(servers) + 1),
                            "url": embed_url, "type": "embed"})
            log("faselhd_rip: added server {}: {}".format(len(servers), embed_url[:80]))

    if post_id:
        _add("{}/e/{}/".format(GOVID_BASE, post_id))

    if post_id:
        ajax_url = BASE_URL + "/wp-content/themes/timemovies/ajax.php"
        ajax_hdrs = {"Content-Type": "application/x-www-form-urlencoded",
                     "X-Requested-With": "XMLHttpRequest",
                     "Referer": url,
                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        log("faselhd_rip: checking AJAX for additional servers")
        for server_num in range(0, 16):
            if len(servers) > MAX_AJAX_SERVERS:
                log("faselhd_rip: AJAX cap reached, stopping")
                break
            ajax_html, _ = fetch(ajax_url, referer=url,
                                 post_data="post_id={}&server={}".format(post_id, server_num),
                                 extra_headers=ajax_hdrs)
            if not ajax_html:
                continue
            try:
                data = json.loads(ajax_html)
                if data.get("success") and data.get("iframe"):
                    sm = re.search(r'src=["\']([^"\']+)["\']', data["iframe"], re.I)
                    if sm:
                        alt = sm.group(1).replace('&amp;', '&')
                        log("faselhd_rip: found alternative server: {}".format(alt[:80]))
                        _add(alt)
            except Exception as e:
                log("faselhd_rip: AJAX error server {}: {}".format(server_num, e))

    log("faselhd_rip: {} -> {} servers found".format(url, len(servers)))
    return {"url": final_url or url, "title": title, "plot": plot,
            "poster": poster, "year": year, "rating": rating,
            "servers": servers, "items": episodes, "type": item_type}


# ── govid.live stream extraction ───────────────────────────────────────────────

_GOVID_HDRS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
}


def _govid_fetch(url, referer):
    """Fetch a govid.live page with correct browser headers."""
    hdrs = dict(_GOVID_HDRS)
    hdrs["Referer"] = referer
    hdrs["Origin"]  = GOVID_BASE
    return fetch(url, referer=referer, extra_headers=hdrs)


def _scan_page_for_stream(html, page_url):
    """
    Full scan of an HTML page for a govid stream URL.

    Order:
      1. Inline <script> blocks (player config lives here if present)
      2. External <script src> — ANY domain except known CDN noise
         (Previous code only fetched govid.live scripts; the /e/ page may
          load its player from a different domain entirely.)
      3. Raw m3u8 anywhere in the page HTML

    Also returns any /e/{id}/ reference found, so the caller can retry
    with the canonical embed URL.
    """
    if not html:
        return None, None

    # 1 ── inline scripts ─────────────────────────────────────────────────────
    inline_blocks = re.findall(r'<script(?:\s[^>]*)?>(.+?)</script>', html, re.DOTALL | re.I)
    log("faselhd_rip: found {} inline script blocks in {}".format(len(inline_blocks), page_url[:60]))
    # Log first block snippet for debugging if we find nothing
    for i, blk in enumerate(inline_blocks):
        found = _find_m3u8(blk)
        if found:
            log("faselhd_rip: m3u8 in inline script[{}]: {}".format(i, found[:80]))
            return found, None
    if inline_blocks:
        log("faselhd_rip: inline script[0] snippet: {}".format(inline_blocks[0][:300].replace('\n', ' ')))

    # 2 ── external scripts (all domains except noise) ─────────────────────────
    # Use a broad pattern that also catches unquoted src and single-quoted src
    ext_srcs = re.findall(r'<script[^>]+src=["\']?([^"\'>\s]+)["\']?', html, re.I)
    log("faselhd_rip: found {} external scripts in page".format(len(ext_srcs)))
    for src in ext_srcs[:6]:   # limit to 6 to avoid runaway fetching
        if not src.startswith('http'):
            src = GOVID_BASE + '/' + src.lstrip('/')
        if _is_noise_domain(src):
            log("faselhd_rip: skipping noise script: {}".format(src[:60]))
            continue
        log("faselhd_rip: fetching external script: {}".format(src[:80]))
        js, _ = _govid_fetch(src, page_url)
        if not js:
            continue
        found = _find_m3u8(js)
        if found:
            log("faselhd_rip: m3u8 in external script {}: {}".format(src[:60], found[:80]))
            return found, None
        # Look for an API path pattern we can use with the video ID
        api_m = re.search(r'["\']/((?:stream|hls|vod|live|video|play|src)/)["\']', js)
        if api_m:
            return None, api_m.group(1)   # caller will append video_id

    # 3 ── raw m3u8 anywhere in the HTML ──────────────────────────────────────
    found = _find_m3u8(html)
    if found:
        log("faselhd_rip: m3u8 in raw HTML: {}".format(found[:80]))
        return found, None

    # Also surface any /e/{id}/ reference (for /play/ pages)
    id_m = re.search(r'govid\.live/e/(\d+)/?', html)
    if id_m:
        return None, id_m.group(1)   # signals "retry with this ID"

    # Dump first 500 chars for debugging when all else fails
    log("faselhd_rip: page dump (first 500): {}".format(html[:500].replace('\n', ' ')))
    return None, None


def _extract_govid_by_id(video_id, embed_url):
    """
    Resolve a stream from a numeric govid.live video ID.

    What the logs tell us:
      - /e/{id}/ → 3899 bytes, 0 inline scripts, "Arabic Windows" encoding
      - External scripts on that page: unknown domain(s), previously skipped
      - /video-{id}.m3u8 without token → 3 bytes (requires tokenbaseip)
      - All guessed API paths (/api/source/, /api/v1/, /api/media/) → 404

    Strategy:
      A. Fetch canonical /e/{id}/ and scan (inline + external scripts + raw HTML)
      B. Fetch the /play/ URL (if different) and do the same
      C. Give up — log a page dump so we can diagnose next time
    """
    log("faselhd_rip: _extract_govid_by_id id={} embed={}".format(video_id, embed_url[:80]))

    canonical = "{}/e/{}/".format(GOVID_BASE, video_id)
    urls_to_scan = [canonical]
    if embed_url != canonical and "govid.live" in embed_url:
        urls_to_scan.append(embed_url)

    for page_url in urls_to_scan:
        log("faselhd_rip: fetching govid page {}".format(page_url[:80]))
        html, _ = _govid_fetch(page_url, BASE_URL)
        if not html:
            continue

        stream, extra = _scan_page_for_stream(html, page_url)
        if stream:
            quality = "1080p" if "1080" in stream else ("720p" if "720" in stream else "HD")
            return stream, quality, page_url

        # extra can be: an API path fragment or a video ID string
        if extra:
            if extra.isdigit():
                # _scan_page found a different /e/{id}/ reference
                if extra != video_id:
                    log("faselhd_rip: found different video ID {} in page, retrying".format(extra))
                    return _extract_govid_by_id(extra, "{}/e/{}/".format(GOVID_BASE, extra))
            else:
                # API path hint from a JS bundle
                api_url = "{}/{}{}".format(GOVID_BASE, extra, video_id)
                log("faselhd_rip: trying API hint: {}".format(api_url))
                api_resp, _ = _govid_fetch(api_url, canonical)
                if api_resp:
                    stream = _find_m3u8(api_resp)
                    if stream:
                        return stream, "HD", canonical

    log("faselhd_rip: all strategies exhausted for id={}".format(video_id))
    return None, "", embed_url


def _extract_govid_stream(embed_url, page_referer):
    """
    Top-level govid.live handler.

    ID extraction priority:
      1. /e/{id}/  — direct parse (canonical form)
      2. /play/=0TP... — fetch the page and look for /e/{id}/ inside it.
         Do NOT try to guess the ID from the token string; the tokens are
         opaque and do not contain raw digit runs in current govid structure.
    """
    log("faselhd_rip: _extract_govid_stream {}".format(embed_url[:80]))

    # 1 — canonical /e/{id}/
    m = re.search(r'/e/(\d+)/?', embed_url)
    if m:
        return _extract_govid_by_id(m.group(1), embed_url)

    # 2 — /play/ token: fetch the page to find the embedded /e/{id}/ reference
    if '/play/' in embed_url:
        log("faselhd_rip: fetching /play/ page to discover video ID")
        html, _ = _govid_fetch(embed_url, page_referer)
        if html:
            # Look for /e/{id}/ reference embedded anywhere in the page
            id_m = re.search(r'govid\.live/e/(\d+)/?', html)
            if not id_m:
                # Also check for bare numeric ID in common JS patterns
                # e.g.  var id = 208053;  or  "video_id":"208053"
                id_m = re.search(
                    r'(?:video_?id|post_?id|vid|pid)\s*[=:"\']\s*["\']?(\d{4,7})["\']?',
                    html, re.I)
            if id_m:
                video_id = id_m.group(1)
                log("faselhd_rip: found video ID {} in /play/ page".format(video_id))
                return _extract_govid_by_id(video_id, embed_url)

            # No ID found but try a full scan of the /play/ page anyway
            stream, extra = _scan_page_for_stream(html, embed_url)
            if stream:
                quality = "1080p" if "1080" in stream else ("720p" if "720" in stream else "HD")
                return stream, quality, embed_url
            if extra and extra.isdigit():
                return _extract_govid_by_id(extra, embed_url)

    log("faselhd_rip: all govid strategies failed for {}".format(embed_url[:80]))
    return None, "", embed_url


def extract_stream(url):
    log("faselhd_rip extract_stream: {}".format(url[:100]))
    url = url.replace('&amp;', '&').strip()

    if "govid.live" in url:
        if ".m3u8" not in url:
            return _extract_govid_stream(url, BASE_URL)
        quality = "1080p" if "1080" in url else ("720p" if "720" in url else "HD")
        return url, quality, GOVID_BASE

    if ".m3u8" in url:
        quality = "1080p" if "1080" in url else ("720p" if "720" in url else "HD")
        return url, quality, BASE_URL

    stream_url, quality, ref = base_extract_stream(url)
    if stream_url:
        return stream_url, quality, ref

    return None, "", BASE_URL
