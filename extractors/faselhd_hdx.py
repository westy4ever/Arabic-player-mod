# -*- coding: utf-8 -*-
"""
Extractor for faselhdx.bid (FaselHD CDN variant)
Domains: web51212x / web5106x / web51118x / web5120x.faselhdx.bid

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIRMED FROM REAL HTML FILES (saved pages uploaded by user)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CARD STRUCTURE (id="postList" grid, 24 per page):
  <div class="postDiv ">
    <a href="ITEM_URL">
      <div class="imgdiv-class">
        <img data-src="https://static.faselhdcdn.com/…jpg?resize=400%2C600"
             alt="TITLE">
      </div>
      <div class="postInner">
        <div class="posTop">
          <span class="quality">1080p WEB-DL</span>
          <span class="pImdb"><i class="fa fa-star"></i> 6.4</span>
        </div>
        <div class="h1">TITLE</div>
      </div>
    </a>
  </div>

PAGINATION (Bootstrap, no trailing slash on page N>1):
  <a class="page-link" href="…/movies/">1</a>
  <span class="page-link">2</span>             ← current page (no link)
  <a class="page-link" href="…/movies/page/3">3</a>
  <a class="page-link" href="…/movies/page/3">›</a>

BUG 1 — PAGINATION SHOWS SAME MOVIES:
  Root cause: 44 postDiv cards exist but 20 are in the top SLIDER (same
  featured movies on every page). Only 24 are in id="postList" (real grid).
  The old regex matched ALL 44 → 20 identical slider cards shown each page.
  Fix: scope card extraction to id="postList" only.

BUG 2 — SERVERS NOT EXTRACTED:
  Root cause: onclick uses HTML entity &#39; for quotes, not literal ':
    onclick="player_iframe.location.href = &#39;URL&#39;"
  The old regex used literal ' — never matched live-fetched HTML.
  Fix: regex handles both &#39; and literal ' as delimiters.

BUG 3 — POSTER NOT SHOWN:
  Root cause: og:image meta tag is absent in live-fetched HTML.
  Working sources (confirmed):
    <meta itemprop="image" content="https://static.faselhdcdn.com/…jpg">
    <div class="posterImg"><img src="https://static.faselhdcdn.com/…jpg">

STREAM:
  scdns.io URL = WASM-signed with viewer IP — cannot reproduce server-side.
  Download links (t7meel.site etc.) extracted as fallback servers.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
import json
import sys

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urlparse
else:
    from urllib import quote_plus
    from urlparse import urlparse

from extractors.base import fetch, urljoin, log
from extractors.base import extract_stream as base_extract_stream

# FIX: "web51212x.faselhdx.bid" never appears in ANY of the real saved
# pages (movies.html, recent.html, movie_links.html, episodes.html,
# series_episode.html) - they all consistently use "web7518x.faselhdx.bid"
# for actual content instead, and all their canonical tags point to yet
# another domain, "fasel-hd.cam" (fasel-HD.pro also shows up as an
# outbound link). This site's CDN mirror subdomain clearly rotates its
# numeric prefix, so hardcoding a specific one (old or new) just delays the
# next break. Anchor to the stable canonical domain instead and let
# _update_base() adapt to whatever mirror it actually redirects to.
BASE_URL = "https://www.fasel-hd.cam"

# FIX: matching a fixed list of specific numeric-prefixed subdomains can
# never keep up with rotation (confirmed: 51212x in this list, but real
# pages use 7518x - a prefix that matches NONE of these entries). Match by
# domain suffix instead, which covers any current or future CDN mirror
# subdomain under these known root domains.
_KNOWN_DOMAIN_SUFFIXES = (
    "faselhdx.bid",
    "faselhd.bid",
    "fasel-hd.cam",
    "faselhd.pro",
    "faselhd.life",
)

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/124.0.0.0 Safari/537.36")

_HEADERS = {
    "User-Agent":      _UA,
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
    "DNT":             "1",
}

# Script sources that never contain stream URLs
_SCRIPT_NOISE = {
    "jwpcdn.com", "jwplatform.com",
    "unpkg.com", "cdn.jsdelivr.net", "cdnjs.cloudflare.com",
    "ajax.googleapis.com", "code.jquery.com", "stackpath.bootstrapcdn.com",
    "google-analytics.com", "googletagmanager.com",
    "aclib.net", "acscdn.com", "madurird.com", "browsecoherentunrefined.com",
    "crumpetprankerstench.com",
}

# m3u8 URLs that look real but are actually image CDN endpoints
_FAKE_M3U8_HOSTS = {"img.scdns.io"}


# ── helpers ────────────────────────────────────────────────────────────────────

def _update_base(url):
    global BASE_URL
    p = urlparse(url)
    if p.netloc and any(p.netloc.lower().endswith(suf) for suf in _KNOWN_DOMAIN_SUFFIXES):
        BASE_URL = "{}://{}".format(p.scheme or "https", p.netloc)


def _norm(url):
    if not url:
        return ""
    url = str(url).strip().replace("&amp;", "&")
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return BASE_URL.rstrip("/") + "/" + url.lstrip("/")
    return url


def _clean(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace("&amp;", "&")
    text = text.replace("فاصل إعلاني", "").replace("FaselHD", "")
    text = re.sub(r'\s*[-|]\s*(فاصل\s*إعلاني|FaselHD).*$', '', text, flags=re.I)
    return text.strip()


_EPISODE_URL_PAT = re.compile(r'/(?:[a-z-]*-)?episodes/', re.I)


def _classify_type(item_url, title):
    """Classify a URL/title as 'episode', 'series', or 'movie'.

    FIX: a single shared classifier replaces two separate, subtly
    divergent copies of this logic (one in _extract_cards for category
    listings, one in get_page for detail pages) that both misclassified
    specific, individually-playable episodes as generic "series" -
    causing the app to show an episode picker instead of playing the
    tapped episode directly (same bug found and fixed in arabseed.py).

    Confirmed from real pages: both "/episodes/...-الحلقة-N" (regular
    shows) and "/anime-episodes/...-الحلقة-N" (anime) are dedicated
    single-episode paths, each with its own servers. "/anime/..." and
    "/series/..." (no episode suffix) are hub-style pages that still need
    an episode-selection step.
    """
    if _EPISODE_URL_PAT.search(item_url):
        return "episode"
    if "/series" in item_url or "مسلسل" in title:
        return "series"
    if "/anime" in item_url and "/anime-movies" not in item_url:
        return "series"
    return "movie"


def _get(url, referer=None, extra=None):
    hdrs = dict(_HEADERS)
    hdrs["Referer"] = referer or BASE_URL
    if extra:
        hdrs.update(extra)
    return fetch(url, referer=referer or BASE_URL, extra_headers=hdrs)


def _is_real_m3u8(url):
    host = urlparse(url).netloc.lower()
    if host in _FAKE_M3U8_HOSTS:
        return False
    if re.search(r'\.(jpg|jpeg|png|gif|webp|avif)\.m3u8', urlparse(url).path.lower()):
        return False
    return True


# ── categories ────────────────────────────────────────────────────────────────

def get_categories():
    return [
        {"title": "🆕 المضاف حديثا",            "url": BASE_URL + "/most_recent",         "type": "category", "_action": "category"},
        {"title": "🎬 جميع الافلام",             "url": BASE_URL + "/all-movies",           "type": "category", "_action": "category"},
        {"title": "🎬 افلام اجنبي",              "url": BASE_URL + "/movies",               "type": "category", "_action": "category"},
        {"title": "🎬 افلام مدبلجة",             "url": BASE_URL + "/dubbed-movies",        "type": "category", "_action": "category"},
        {"title": "🎬 افلام هندي",               "url": BASE_URL + "/hindi",                "type": "category", "_action": "category"},
        {"title": "🎬 افلام اسيوي",              "url": BASE_URL + "/asian-movies",         "type": "category", "_action": "category"},
        {"title": "🎬 افلام انمي",               "url": BASE_URL + "/anime-movies",         "type": "category", "_action": "category"},
        {"title": "⭐ الاعلي تصويتا",            "url": BASE_URL + "/movies_top_votes",     "type": "category", "_action": "category"},
        {"title": "👁️ الاعلي مشاهدة",            "url": BASE_URL + "/movies_top_views",     "type": "category", "_action": "category"},
        {"title": "🏆 الاعلي IMDB",              "url": BASE_URL + "/movies_top_imdb",      "type": "category", "_action": "category"},
        {"title": "🏆 جوائز الاوسكار",           "url": BASE_URL + "/oscars-winners",       "type": "category", "_action": "category"},
        {"title": "🎬 سلاسل الافلام",            "url": BASE_URL + "/movies_collections",   "type": "category", "_action": "category"},
        {"title": "📺 جميع المسلسلات",           "url": BASE_URL + "/series",               "type": "category", "_action": "category"},
        {"title": "📺 المضاف حديثا (مسلسلات)",  "url": BASE_URL + "/recent_series",        "type": "category", "_action": "category"},
        {"title": "📺 احدث الحلقات",             "url": BASE_URL + "/episodes",             "type": "category", "_action": "category"},
        {"title": "📺 الاعلي مشاهدة (مسلسلات)", "url": BASE_URL + "/series_top_views",    "type": "category", "_action": "category"},
        {"title": "📺 الاعلي IMDB (مسلسلات)",   "url": BASE_URL + "/series_top_imdb",     "type": "category", "_action": "category"},
        {"title": "📺 المسلسلات القصيرة",        "url": BASE_URL + "/short_series",         "type": "category", "_action": "category"},
        {"title": "📡 جميع البرامج",             "url": BASE_URL + "/tvshows",              "type": "category", "_action": "category"},
        {"title": "📡 المضاف حديثا (برامج)",    "url": BASE_URL + "/recent_tvshows",       "type": "category", "_action": "category"},
        {"title": "📡 احدث الحلقات (برامج)",    "url": BASE_URL + "/tvepisodes",           "type": "category", "_action": "category"},
        {"title": "📡 الاعلي مشاهدة (برامج)",   "url": BASE_URL + "/tvshows_top_views",   "type": "category", "_action": "category"},
        {"title": "🌏 مسلسلات اسيوي",            "url": BASE_URL + "/asian-series",         "type": "category", "_action": "category"},
        {"title": "🌏 المضاف حديثا (اسيوي)",    "url": BASE_URL + "/recent_asian",         "type": "category", "_action": "category"},
        {"title": "🌏 احدث الحلقات (اسيوي)",    "url": BASE_URL + "/asian-episodes",       "type": "category", "_action": "category"},
        {"title": "🌏 الاعلي مشاهدة (اسيوي)",   "url": BASE_URL + "/asian_top_views",     "type": "category", "_action": "category"},
        {"title": "🎌 جميع الانمي",              "url": BASE_URL + "/anime",                "type": "category", "_action": "category"},
        {"title": "🎌 المضاف حديثا (انمي)",     "url": BASE_URL + "/recent_anime",         "type": "category", "_action": "category"},
        {"title": "🎌 احدث الحلقات (انمي)",     "url": BASE_URL + "/anime-episodes",       "type": "category", "_action": "category"},
        {"title": "🎌 الاعلي مشاهدة (انمي)",    "url": BASE_URL + "/anime_top_views",     "type": "category", "_action": "category"},
    ]


# ── card regex ────────────────────────────────────────────────────────────────
# Scoped to the postList grid section to avoid slider duplicates.
# Confirmed card structure from real HTML: postDiv > a > imgdiv-class > img[data-src] + h1
_CARD_PAT = re.compile(
    r'<div[^>]*class="postDiv[^"]*"[^>]*>\s*'
    r'<a\s+href="([^"]+)"[^>]*>'
    r'(?:(?!<div[^>]*class="postDiv).)*?'
    r'data-src="([^"]+)"'
    r'(?:(?!<div[^>]*class="postDiv).)*?'
    r'<div[^>]*class="h1"[^>]*>([^<]+)</div>',
    re.DOTALL | re.I
)

_QUALITY_PAT = re.compile(r'<span[^>]*class="[^"]*quality[^"]*"[^>]*>([^<]+)</span>', re.I)
_IMDB_PAT    = re.compile(r'<span[^>]*class="[^"]*pImdb[^"]*"[^>]*>.*?([\d.]+)', re.I | re.DOTALL)


def _extract_cards(html, max_items=50):
    """
    Extract cards from the id="postList" section only.

    BUG FIX: The page has 44 postDiv cards total, but 20 live in the top
    slider (owl-item) and repeat the same featured movies on every page.
    Only the 24 cards inside id="postList" are unique per page.
    """
    # Scope to the postList div
    post_list_m = re.search(r'<div[^>]+id=["\']postList["\'][^>]*>(.*?)(?=<div[^>]+class="[^"]*subHead|<div[^>]+id="[^"]*footer|</div>\s*</div>\s*</div>\s*</div>\s*<div[^>]+id)', html, re.DOTALL | re.I)
    if post_list_m:
        scope = post_list_m.group(1)
        log("faselhd_hdx: scoped to postList ({} chars)".format(len(scope)))
    else:
        # Fallback: use full HTML but deduplicate aggressively
        scope = html
        log("faselhd_hdx: postList not found, using full HTML")

    items, seen = [], set()
    for m in _CARD_PAT.finditer(scope):
        item_url  = _norm(m.group(1))
        poster    = _norm(m.group(2).split("?")[0])  # strip ?resize=... query
        title     = _clean(m.group(3))
        card_html = m.group(0)

        if not item_url or item_url in seen:
            continue
        if "/page/" in item_url:
            continue

        qm = _QUALITY_PAT.search(card_html)
        im = _IMDB_PAT.search(card_html)

        item_type = _classify_type(item_url, title)

        seen.add(item_url)
        items.append({
            "title":   title,
            "url":     item_url,
            "poster":  poster,
            "thumb":   poster,
            "rating":  im.group(1).strip() if im else "",
            "quality": qm.group(1).strip() if qm else "",
            "year":    "",
            "type":    item_type,
            "_action": "details",
        })
        if len(items) >= max_items:
            break

    return items


# ── category items ────────────────────────────────────────────────────────────

def get_category_items(url, page=1):
    _update_base(url)

    pm = re.search(r'/page/(\d+)/?$', url.rstrip('/'))
    if pm and page == 1:
        page = int(pm.group(1))

    log("faselhd_hdx: get_category_items page={} url={}".format(page, url))

    clean = re.sub(r'/page/\d+/?$', '', url.rstrip('/'))

    # NO trailing slash on page > 1 (server redirects /page/2/ → page 1)
    current_url = "{}/page/{}".format(clean, page) if page > 1 else clean + "/"

    html, final_url = _get(current_url, referer=BASE_URL)
    if not html:
        log("faselhd_hdx: fetch failed: {}".format(current_url))
        return []

    if final_url:
        _update_base(final_url)

    items = _extract_cards(html)
    log("faselhd_hdx: extracted {} items (page {})".format(len(items), page))

    # ── Pagination ─────────────────────────────────────────────────────────────
    # Confirmed: current page is <span class="page-link">N</span> (no link)
    # Next page: <a class="page-link" href="…/page/N+1">N+1</a>
    # Arrow:     <a class="page-link" href="…/page/N+1">›</a>
    next_n = page + 1

    # Strategy 1: numbered next-page link
    nm = re.search(
        r'<a[^>]+class="[^"]*page-link[^"]*"[^>]+href="([^"]+/page/{}(?:[/"?][^"]*)?)"'
        .format(next_n),
        html, re.I
    )
    if nm:
        items.append({
            "title": "➡️ Next Page - Page {}".format(next_n),
            "url":   _norm(nm.group(1).rstrip('/')),
            "type":  "category", "_action": "category",
        })
    else:
        # Strategy 2: › arrow link (confirmed in saved HTML)
        arrow = re.search(
            r'<a[^>]+class="[^"]*page-link[^"]*"[^>]+href="([^"]+)"[^>]*>\s*[›»]\s*</a>',
            html, re.I
        )
        if arrow:
            items.append({
                "title": "➡️ Next Page",
                "url":   _norm(arrow.group(1).rstrip('/')),
                "type":  "category", "_action": "category",
            })
        else:
            # Strategy 3: <link rel="next">
            rel = re.search(
                r'<link[^>]+rel=["\']next["\'][^>]+href=["\']([^"\']+)["\']', html, re.I
            )
            if rel:
                items.append({
                    "title": "➡️ Next Page",
                    "url":   _norm(rel.group(1).rstrip('/')),
                    "type":  "category", "_action": "category",
                })

    return items


# ── search ────────────────────────────────────────────────────────────────────

def search(query, page=1):
    _update_base(BASE_URL)
    url = BASE_URL + "/?s=" + quote_plus(query)
    if page > 1:
        url += "&paged=" + str(page)

    html, final_url = _get(url, referer=BASE_URL)
    if not html:
        return []
    if final_url:
        _update_base(final_url)

    return _extract_cards(html)


# ── detail page ───────────────────────────────────────────────────────────────

def get_page(url):
    _update_base(url)
    log("faselhd_hdx: get_page {}".format(url))

    html, final_url = _get(url, referer=BASE_URL)
    if not html:
        return {"title": "Error", "servers": [], "items": [], "type": "movie"}
    if final_url:
        _update_base(final_url)

    # post_id from body class "postid-298828"
    pid_m = re.search(r'\bpostid-(\d+)\b', html)
    post_id = pid_m.group(1) if pid_m else None
    if post_id:
        log("faselhd_hdx: post_id={}".format(post_id))

    # Title from <div class="h1 title">TITLE<span…rating…>
    title_m = (
        re.search(r'<div[^>]*class="[^"]*h1 title[^"]*"[^>]*>(.*?)(?:<span|</div>)',
                  html, re.I | re.DOTALL) or
        re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
    )
    title = _clean(title_m.group(1)) if title_m else ""

    # Poster — confirmed working sources (og:image absent in live HTML):
    #   1. <meta itemprop="image" content="URL">
    #   2. <div class="posterImg"><img src="https://…">
    #   3. <meta itemprop="thumbnailUrl" content="URL">
    poster = ""
    for pat in [
        r'itemprop=["\']image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<div[^>]*class="[^"]*posterImg[^"]*"[^>]*>.*?<img[^>]+src="(https://[^"]+)"',
        r'itemprop=["\']thumbnailUrl["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]:
        m = re.search(pat, html, re.I | re.DOTALL)
        if m:
            poster = _norm(m.group(1).split("?")[0])
            break

    # Plot — capture inside .singleDesc regardless of <p>
    plotm = re.search(r'class="singleDesc"[^>]*>(.*?)</div>', html, re.I | re.DOTALL)
    plot = _clean(plotm.group(1)) if plotm else ""

    # Year — support both 'سنة الإنتاج' and 'موعد الصدور'
    ym = (
        re.search(r'(?:سنة\s*الإنتاج|موعد الصدور)\s*:.*?(\d{4})', html, re.I | re.DOTALL) or
        re.search(r'\b(20\d{2})\b', title)
    )
    year = ym.group(1) if ym else ""

    # Rating
    rm = (
        re.search(r'class="singleStar"[^>]*>.*?<strong>([\d.]+)</strong>', html, re.I | re.DOTALL) or
        re.search(r'class="pImdb"[^>]*>.*?([\d.]+)', html, re.I | re.DOTALL)
    )
    rating = rm.group(1) if rm else ""

    # FIX: is_tv_content gates whether to look up sibling episodes below
    # (broader - true for both hub pages and specific episode pages), while
    # item_type (via the shared _classify_type, same one used for category
    # items) is what downstream navigation uses to decide "direct-play this
    # episode" vs "show an episode picker" - these need to differ for a
    # specific episode page, which must do both.
    is_tv_content = (
        "/series" in url or "/episodes" in url or
        "مسلسل" in title or "/anime" in url
    )
    item_type = _classify_type(url, title)

    # ── Servers ────────────────────────────────────────────────────────────────
    servers, seen_embed = [], set()

    def _add(embed_url, name=None):
        embed_url = str(embed_url).replace("&amp;", "&").replace("&#39;", "").strip()
        if not embed_url or embed_url in seen_embed:
            return
        seen_embed.add(embed_url)
        label = name or "🎬 Server {}".format(len(servers) + 1)
        servers.append({"name": label, "url": embed_url, "type": "embed"})
        log("faselhd_hdx: server {}: {}".format(len(servers), embed_url[:80]))

    # BUG FIX: onclick uses HTML entity &#39; for single quotes in live HTML:
    #   onclick="player_iframe.location.href = &#39;URL&#39;"
    # Old regex used literal ' — never matched. New regex handles both forms.
    tabs_m = re.search(
        r'<ul[^>]*class="[^"]*tabs-ul[^"]*"[^>]*>(.*?)</ul>',
        html, re.I | re.DOTALL
    )
    if tabs_m:
        tabs_html = tabs_m.group(1)
        # Match onclick with &#39; OR ' OR " as the URL delimiter
        for li_m in re.finditer(
            r'onclick=["\'][^"\']*player_iframe\.location\.href\s*=\s*'
            r'(?:&#39;|["\'])([^"\'&]+(?:&amp;[^"\'&]+)*)(?:&#39;|["\'])',
            tabs_html, re.I
        ):
            raw_url = _norm(li_m.group(1).replace("&amp;", "&"))
            # Get label from <a> text
            snippet = tabs_html[li_m.start():li_m.start() + 300]
            a_m = re.search(r'<a[^>]*>(.*?)</a>', snippet, re.DOTALL | re.I)
            label = "🎬 Server {}".format(len(servers) + 1)
            if a_m:
                raw_label = re.sub(r'<[^>]+>', '', a_m.group(1)).strip()
                if raw_label:
                    label = raw_label
            _add(raw_url, label)

    # Fallback: iframe data-src (confirmed present in HTML)
    ifm = re.search(
        r'<iframe[^>]+name=["\']player_iframe["\'][^>]+data-src=["\']([^"\']+)["\']',
        html, re.I
    )
    if ifm and not servers:
        _add(_norm(ifm.group(1)))

    log("faselhd_hdx: {} servers found".format(len(servers)))

    # ── Episodes (series) ─────────────────────────────────────────────────────
    episodes = []
    if is_tv_content:
        for ep_m in re.finditer(
            r'<a[^>]+href="([^"]+(?:faselhdx|faselhd)[^"]+)"[^>]*>'
            r'[^<]*(?:الحلقة|Episode)\s*(\d+)',
            html, re.I
        ):
            episodes.append({
                "title":   "الحلقة {}".format(ep_m.group(2)),
                "url":     _norm(ep_m.group(1)),
                "type":    "episode",
                "_action": "details",
            })

    return {
        "url":     final_url or url,
        "title":   title,
        "plot":    plot,
        "poster":  poster,
        "thumb":   poster,
        "year":    year,
        "rating":  rating,
        "servers": servers,
        "items":   episodes,
        "type":    item_type,
    }


# ── stream extraction ─────────────────────────────────────────────────────────

def _scan_for_stream(html, referer):
    if not html:
        return None

    # Direct m3u8 (skip img.scdns.io thumbnails)
    for m in re.finditer(
        r'(https?://[^\s"\'<>`\\]+\.m3u8(?:\?[^\s"\'<>`\\]*)?)', html, re.I
    ):
        u = m.group(1).replace("\\/", "/").replace("&amp;", "&")
        if _is_real_m3u8(u):
            return u

    # JS player config patterns
    for pat in [
        r'(?:file|src|url|source|hls)\s*[=:]\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'["\']file["\']\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
    ]:
        m2 = re.search(pat, html, re.I)
        if m2:
            u = m2.group(1).replace("\\/", "/").replace("&amp;", "&")
            if _is_real_m3u8(u):
                return u

    # Real scdns stream host (master.c.scdns.io or r466--xxx.c.scdns.io)
    m3 = re.search(
        r'(https?://(?:master\.|r\d+--)[^\s"\'<>]+\.c\.scdns\.io/[^\s"\'<>]+)',
        html, re.I
    )
    if m3:
        u = m3.group(1).replace("\\/", "/").replace("&amp;", "&")
        if not u.endswith(".m3u8"):
            u = u.split("?")[0] + ".m3u8"
        return u

    # Same-domain external scripts only
    p = urlparse(referer)
    same_host = p.netloc

    ext_srcs = re.findall(r'<script[^>]+src=["\']?([^"\'>\s]+)["\']?', html, re.I)
    for src in ext_srcs[:8]:
        src_l = src.lower()
        if any(d in src_l for d in _SCRIPT_NOISE):
            continue
        if re.match(r'^/[a-z0-9-]+\.[a-z]{2,6}/', src_l):
            continue  # relative ad-injector pattern
        if not src.startswith("http"):
            src = BASE_URL.rstrip("/") + "/" + src.lstrip("/")
        if same_host and urlparse(src).netloc != same_host:
            continue
        log("faselhd_hdx: scanning script: {}".format(src[:80]))
        js, _ = _get(src, referer=referer)
        if not js:
            continue
        for m4 in re.finditer(r'(https?://[^\s"\'<>`\\]+\.m3u8[^\s"\'<>`\\]*)', js, re.I):
            u = m4.group(1).replace("\\/", "/")
            if _is_real_m3u8(u):
                return u

    return None


def extract_stream(url):
    """
    Resolve a faselhdx.bid server URL to a playable stream.

    For video_player?player_token=… URLs:
      1. Fetch the page and scan for any directly-embedded m3u8 (rare, may
         appear in future firmware).
      2. If none found, return the video_player URL itself as a "web" link.
         The app opens it in a WebView, the ZFG/scdns player runs normally
         in the real browser context with the viewer's actual IP — this is
         the correct way to play these streams.

    For download/file links (t7meel site etc.):
      Follow the redirect chain and return the resolved URL.
    """
    log("faselhd_hdx extract_stream: {}".format(url[:100]))
    url = url.replace("&amp;", "&").strip()
    _update_base(url)

    # Already a direct m3u8
    if ".m3u8" in url:
        if not _is_real_m3u8(url):
            log("faselhd_hdx: rejected false-positive m3u8: {}".format(url[:80]))
            return None, "", BASE_URL
        quality = "1080p" if "1080" in url else ("720p" if "720" in url else "HD")
        return url, quality, BASE_URL

    # video_player page — scan first, fall back to returning the page URL itself
    if "video_player" in url or "player_token" in url:
        log("faselhd_hdx: fetching video_player page")
        html, final_url = _get(url, referer=BASE_URL)
        stream = _scan_for_stream(html, url) if html else None
        if stream:
            log("faselhd_hdx: found inline stream: {}".format(stream[:80]))
            quality = "1080p" if "1080" in stream else ("720p" if "720" in stream else "HD")
            return stream, quality, url

        # No inline m3u8 — return the player page URL itself.
        # The app opens this in a WebView and the stream plays normally.
        player_url = (final_url or url).replace("&amp;", "&")
        log("faselhd_hdx: returning player page as web link: {}".format(player_url[:80]))
        return player_url, "HD", BASE_URL

    # Download/file links (t7meel.site, etc.)
    if any(d in url for d in ["t7meel.site", "thmeel", "srvdown", "t7hd"]):
        log("faselhd_hdx: following download link: {}".format(url[:80]))
        try:
            html, final = _get(url, referer=BASE_URL)
            if html:
                stream = _scan_for_stream(html, url)
                if stream:
                    log("faselhd_hdx: found stream via download link: {}".format(stream[:80]))
                    return stream, "HD", url
            # Return the resolved URL after redirect
            resolved = (final or url).replace("&amp;", "&")
            return resolved, "HD", BASE_URL
        except Exception as e:
            log("faselhd_hdx: download link error: {}".format(e))
            return url, "HD", BASE_URL

    # Unknown embed — try base extractor then manual scan
    stream_url, quality, ref = base_extract_stream(url)
    if stream_url:
        return stream_url, quality, ref

    html, _ = _get(url, referer=BASE_URL)
    stream = _scan_for_stream(html, url) if html else None
    if stream:
        return stream, "HD", BASE_URL

    # Last resort — return the URL itself for WebView
    return url, "HD", BASE_URL