# -*- coding: utf-8 -*-
"""
EgyDead extractor — WordPress site
Domain: https://tv9.egydead.live/
"""

import re
import sys

from .base import fetch, log, extract_stream as base_extract_stream

if sys.version_info[0] == 3:
    from urllib.parse import quote_plus, urljoin, urlencode, urlparse, quote, unquote
    from html import unescape as html_unescape
else:
    from urllib import quote_plus, urlencode
    from urlparse import urljoin
    from HTMLParser import HTMLParser
    html_unescape = HTMLParser().unescape

MAIN_URL = "https://tv10.egydead.live/"

# FIX: MAIN_URL was a single hardcoded domain with no fallback. A fresh
# snapshot's own canonical tag confirms the site has already moved to
# egydead.fyi - the exact same "mirror domain rotated, hardcoded URL now
# dead" pattern that broke every other site in this addon at some point
# (arabseed's asd.pics, topcinema's numeric CDN prefix, wecima's
# wecima.click). "Categories not working" while HTML parsing itself is
# fine (confirmed independently) points squarely at the fetch step
# failing against a stale domain. Ported the same resilient probing
# pattern already working in wecima.py: try each known/likely domain in
# order, verify the response actually looks like this site (not a
# challenge page or unrelated squatted domain), and cache whichever one
# responds. Falls back to the old hardcoded domain only if every
# candidate fails, so this never behaves worse than before.
#
# tv9.egydead.live is this file's own ORIGINAL domain (see the module
# docstring above, never updated when the code moved to tv10) - meaning
# this site has now rotated through at least 3 domains: tv9 -> tv10 ->
# egydead.fyi, a clear numbered-mirror pattern. Kept as a last-resort
# fallback in case tv10 ever goes down and a user's DNS/cache still
# resolves the older one.
DOMAINS = [
    "https://egydead.fyi/",
    "https://tv10.egydead.live/",
    "https://tv9.egydead.live/",
]
VALID_HOST_MARKERS = ("egydead.fyi", "egydead.live", "egydead.com", "egydead")
BLOCKED_HOST_MARKERS = ("alliance4creativity.com",)
_RESOLVED_BASE = None


def _host(url):
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""


def _is_valid_site_url(url):
    # FIX: this was defined (VALID_HOST_MARKERS) but never actually used -
    # content-only validation (_looks_like_egydead_page) is weak on its
    # own, since any page merely mentioning the word "egydead" somewhere
    # would pass. Combine a host check with the content check, matching
    # wecima.py's dual validation, so a redirect to an unrelated domain
    # can't slip through just because the word appears in its text.
    host = _host(url)
    if not host:
        return False
    if any(m in host for m in BLOCKED_HOST_MARKERS):
        return False
    return any(m in host for m in VALID_HOST_MARKERS)


def _is_blocked_page(html, final_url=""):
    text = (html or "").lower()
    final = (final_url or "").lower()
    if not text:
        return True
    if "just a moment" in text and ("cf-chl" in text or "challenge" in text):
        return True
    if "enable javascript and cookies to continue" in text:
        return True
    if any(m in final for m in BLOCKED_HOST_MARKERS):
        return True
    return False


def _looks_like_egydead_page(html):
    text = html or ""
    return (
        "movieItem" in text
        or "BottomTitle" in text
        or "egydead" in text.lower()
    )


def _site_root(url):
    parts = urlparse(url)
    return "{}://{}/".format(parts.scheme or "https", parts.netloc)


def _get_base():
    global MAIN_URL, _RESOLVED_BASE
    if _RESOLVED_BASE:
        return _RESOLVED_BASE
    for domain in DOMAINS:
        log("EgyDead: probing {}".format(domain))
        html, final_url = fetch(domain, referer=domain)
        final_url = final_url or domain
        if not _is_valid_site_url(final_url):
            log("EgyDead: unexpected host after redirect {}".format(final_url))
            continue
        if _is_blocked_page(html, final_url):
            log("EgyDead: blocked {}".format(final_url))
            continue
        if html and _looks_like_egydead_page(html):
            _RESOLVED_BASE = _site_root(final_url)
            MAIN_URL = _RESOLVED_BASE
            log("EgyDead: selected base {}".format(_RESOLVED_BASE))
            return _RESOLVED_BASE
    _RESOLVED_BASE = DOMAINS[0]
    MAIN_URL = _RESOLVED_BASE
    log("EgyDead: all probes failed, falling back to {}".format(_RESOLVED_BASE))
    return _RESOLVED_BASE

_CLEAN_WORDS = [
    "مشاهدة فيلم", "مشاهدة", "فيلم", "مسلسل",
    "مترجمة اون لاين", "مترجم اون لاين",
    "مترجمة", "مترجم", "اون لاين", "أون لاين",
    "مدبلجة", "مدبلج", "كرتون", "انمي",
    "بالمصري", "سلسلة افلام", "عرض", "برنامج", "جميع مواسم",
]


def _strip_tags(text):
    text = html_unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_title(title):
    title = _strip_tags(title)
    for word in _CLEAN_WORDS:
        title = title.replace(word, "")
    title = re.sub(r"\s*\|\s*$", "", title)
    title = re.sub(r"\s*\-\s*$", "", title)
    return re.sub(r"\s+", " ", title).strip(" -|")


def _full_url(path):
    if not path:
        return ""
    path = html_unescape(path.strip())
    if path.startswith("//"):
        path = "https:" + path
    elif not path.startswith("http"):
        path = urljoin(_get_base(), path)
    try:
        path = quote(unquote(path), safe=':/?&=#+')
    except Exception:
        pass
    return path


def _pick_real_image(html_chunk):
    """
    Find the most likely REAL image URL within a chunk of HTML, robust to
    lazy-load setups that put an identical placeholder in one attribute
    for every single image (only swapping in the real URL via JS later -
    trusting one attribute name blindly can end up picking the same
    placeholder for every item on a page). Checks every common lazy-load
    attribute plus plain src on each <img> tag - all of them, not just
    whichever is present first - and prefers whichever candidate actually
    looks like a real uploaded image (/wp-content/uploads/) over a
    same-for-every-item theme placeholder.
    """
    best = None
    for img_tag in re.findall(r'<img[^>]+>', html_chunk, re.I):
        tag_candidates = []
        for attr in ('data-src', 'data-lazy-src', 'data-original', 'data-lazy', 'src'):
            m = re.search(attr + r'=["\']([^"\']+)["\']', img_tag, re.I)
            if m:
                tag_candidates.append(m.group(1))
        for c in tag_candidates:
            if '/wp-content/uploads/' in c:
                return c
        if best is None and tag_candidates:
            best = tag_candidates[0]
    return best


def _encode_arabic_url(url):
    try:
        parsed = urlparse(url)
        path_segments = []
        for segment in parsed.path.split('/'):
            if segment:
                if any(ord(c) > 127 for c in segment):
                    path_segments.append(quote_plus(segment.encode('utf-8')))
                else:
                    path_segments.append(segment)
            else:
                path_segments.append('')
        encoded_path = '/'.join(path_segments)
        if not encoded_path.startswith('/'):
            encoded_path = '/' + encoded_path
        
        encoded_query = ''
        if parsed.query:
            try:
                query_parts = []
                for part in parsed.query.split('&'):
                    if '=' in part:
                        key, val = part.split('=', 1)
                        if any(ord(c) > 127 for c in val):
                            query_parts.append(key + '=' + quote_plus(val.encode('utf-8')))
                        else:
                            query_parts.append(part)
                    else:
                        query_parts.append(part)
                encoded_query = '&'.join(query_parts)
            except Exception:
                encoded_query = parsed.query
        
        encoded_url = parsed._replace(path=encoded_path, query=encoded_query).geturl()
        return encoded_url
    except Exception:
        return url


def _fetch(url, referer=None, post_data=None):
    extra = {}
    if post_data:
        extra["Content-Type"] = "application/x-www-form-urlencoded"
        extra["X-Requested-With"] = "XMLHttpRequest"
    
    # Add browser-like headers
    extra["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    extra["Accept-Language"] = "ar-EG,ar;q=0.9,en;q=0.8"
    extra["Cache-Control"] = "no-cache"
    extra["Pragma"] = "no-cache"
    extra["Sec-Fetch-Dest"] = "document"
    extra["Sec-Fetch-Mode"] = "navigate"
    extra["Sec-Fetch-Site"] = "none"
    extra["Sec-Fetch-User"] = "?1"
    extra["Upgrade-Insecure-Requests"] = "1"
    
    encoded_url = _encode_arabic_url(url)
    
    return fetch(
        encoded_url,
        referer=referer or _get_base(),
        extra_headers=extra if extra else None,
        post_data=post_data,
    )


def _parse_category_list(html):
    """Parse category page with movie items"""
    items = []
    seen = set()

    # Find all movie items - look for li with class containing "movieItem"
    pattern = r'<li[^>]*class=["\'][^"\']*(?:movieItem|post-item)[^"\']*["\'][^>]*>(.*?)</li>'
    for li in re.findall(pattern, html, re.S | re.I):
        
        # Extract URL - look for the post link
        url_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\']', li)
        if not url_match:
            continue
        
        url = _full_url(url_match.group(1))
        if not url or url in seen:
            continue
        seen.add(url)
        
        # Skip pagination links
        if any(x in url for x in ("/page/", "page=", "category")):
            continue
        
        # Extract title
        title = ""
        title_match = (
            re.search(r'<h[1-3][^>]*class=["\'][^"\']*BottomTitle[^"\']*["\'][^>]*>(.*?)</h[1-3]>', li, re.S | re.I) or
            re.search(r'<h[1-3][^>]*>(.*?)</h[1-3]>', li, re.S | re.I) or
            re.search(r'<img[^>]+alt=["\']([^"\']+)["\']', li) or
            re.search(r'<a[^>]+title=["\']([^"\']+)["\']', li)
        )
        if title_match:
            title = _clean_title(title_match.group(1))
        
        # Extract poster. Rather than trusting one specific attribute
        # (some lazy-load implementations put an *identical* placeholder
        # URL in data-src for every image, only swapping in the real one
        # via JS later - trusting data-src blindly can end up picking the
        # same placeholder for every single item), gather every
        # image-URL-bearing attribute found here and prefer whichever one
        # actually looks like a real uploaded image.
        poster = _pick_real_image(li)
        if poster:
            poster = _full_url(poster)
            # Remove size suffix (e.g., -225x280.jpg -> .jpg)
            poster = re.sub(r'-\d+x\d+(?=\.\w+$)', '', poster)
        else:
            poster = ""
        
        # Extract quality/category label (kept in "plot" for context, no
        # longer appended to the displayed title - a plain title reads
        # better than "Title [مسلسلات اجنبي]" repeated on every item in a
        # category that's already all one category).
        quality = ""
        cat_match = re.search(r'<span[^>]*class=["\'][^"\']*cat_name[^"\']*["\'][^>]*>(.*?)</span>', li, re.S | re.I)
        if cat_match:
            quality = _strip_tags(cat_match.group(1))

        # Detect series vs movie from the item's own URL/raw title rather
        # than hardcoding "movie" for everything - series episodes always
        # live under /episode/, /season/, or /serie/ regardless of which
        # category listing they appear in, and Arabic titles usually lead
        # with "مسلسل" (series) before _clean_title strips it.
        raw_title_text = title_match.group(1) if title_match else ""
        url_low = url.lower()
        if any(x in url_low for x in ("/episode/", "/season/", "/serie/", "/series-category/")) or "مسلسل" in raw_title_text:
            item_type = "series"
        else:
            item_type = "movie"

        if title:
            items.append({
                "title": title,
                "url": url,
                "poster": poster,
                "plot": quality,
                "type": item_type,
                "_action": "details",
            })
    
    return items


def _parse_pagination(html, current_url):
    """Return next page item if available"""
    # Look for next page link
    next_match = re.search(
        r'<a[^>]+class=["\'][^"\']*next[^"\']*(?:page-numbers)?["\'][^>]+href=["\']([^"\']+)["\']',
        html, re.I
    )
    if next_match:
        raw_href = html_unescape(next_match.group(1).strip())
        # IMPORTANT: resolve relative to the page the link was actually
        # found on (current_url), NOT the site root (which is what
        # _full_url() always does). This theme is inconsistent - most
        # category pages emit an absolute pagination URL, but at least one
        # (English movies, confirmed via a real production log) emits a
        # bare relative href like "?page=2/". Resolving that against the
        # site root silently drops the category path, bouncing navigation
        # to the homepage's own page 2 instead of staying in the category
        # - which is exactly why mixed movies/series and wrong servers
        # showed up.
        if raw_href.startswith("http"):
            next_url = raw_href
        elif raw_href.startswith("//"):
            next_url = "https:" + raw_href
        else:
            next_url = urljoin(current_url, raw_href)
        if next_url and next_url != current_url:
            return {
                "title": "➡️ Next Page",
                "url": next_url,
                "type": "category",
                "_action": "category",
            }
    return None


def _extract_detail_meta(html):
    """Extract title, poster, plot, year from item page"""
    # Title from og:title
    title = ""
    title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if title_match:
        title = _clean_title(title_match.group(1))
    
    if not title:
        title_match = re.search(r'<title>(.*?)</title>', html, re.I)
        if title_match:
            title = _clean_title(title_match.group(1).split('|')[0])
    
    # Poster from og:image
    poster = ""
    poster_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if poster_match and '/wp-content/uploads/' in poster_match.group(1):
        poster = _full_url(poster_match.group(1))
        poster = re.sub(r'-\d+x\d+(?=\.\w+$)', '', poster)

    # Fallback: if og:image is missing or didn't look like a real
    # uploaded image (some pages have it point at a generic site logo
    # instead), search the page body directly using the same robust,
    # multi-attribute image picker used for category listings.
    if not poster:
        # Prefer an image near a "poster"-classed element if one exists,
        # otherwise fall back to whatever the picker finds first.
        poster_area_match = re.search(r'<div[^>]+class=["\'][^"\']*[Pp]oster[^"\']*["\'][^>]*>(.*?)</div>', html, re.S | re.I)
        found = _pick_real_image(poster_area_match.group(1)) if poster_area_match else None
        if not found:
            found = _pick_real_image(html)
        if found:
            poster = _full_url(found)
            poster = re.sub(r'-\d+x\d+(?=\.\w+$)', '', poster)
    
    # Description
    plot = ""
    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if desc_match:
        plot = _strip_tags(desc_match.group(1))
    
    # Try to get plot from singleStory div
    if not plot:
        story_match = re.search(r'<div[^>]*class=["\'][^"\']*singleStory[^"\']*["\'][^>]*>(.*?)</div>', html, re.S | re.I)
        if story_match:
            plot = _strip_tags(story_match.group(1))
    
    # Year
    year = ""
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', title + " " + plot)
    if year_match:
        year = year_match.group(1)
    
    return title, poster, plot, year


def _extract_watch_servers(html, page_url):
    """
    Extract video streaming servers from EgyDead page.
    The watch servers are in <ul class="serversList"> with li elements having data-link attribute.
    """
    servers = []
    seen = set()
    
    # Find serversList ul
    servers_html = _find_servers_html(html)
    
    # Parse servers from serversList
    if servers_html:
        # Find all li elements with data-link attribute
        for li_match in re.finditer(r'<li[^>]*data-link=["\']([^"\']+)["\'][^>]*>(.*?)</li>', servers_html, re.S | re.I):
            video_url = html_unescape(li_match.group(1).strip())
            li_content = li_match.group(2)
            
            if not video_url or video_url in seen:
                continue
            
            if video_url.startswith("//"):
                video_url = "https:" + video_url
            seen.add(video_url)
            
            # Extract server name
            name_match = re.search(r'<span[^>]*><p[^>]*>(.*?)</p></span>', li_content, re.I) or \
                        re.search(r'<p[^>]*>(.*?)</p>', li_content, re.I) or \
                        re.search(r'<span[^>]*>(.*?)</span>', li_content, re.I)
            
            name = _strip_tags(name_match.group(1)) if name_match else f"Watch Server {len(servers) + 1}"
            
            servers.append({"name": name.strip(), "url": video_url, "type": "embed"})
    
    # If no servers found in HTML, try checking for direct iframe
    if not servers:
        # Check for video iframe
        iframe_match = re.search(r'<iframe[^>]+id=["\']videoIframe["\'][^>]+src=["\']([^"\']+)["\']', html, re.I)
        if iframe_match:
            video_url = iframe_match.group(1)
            if video_url and video_url not in seen:
                seen.add(video_url)
                servers.append({"name": "Video Player", "url": video_url, "type": "embed"})
    
    log(f"EgyDead: Found {len(servers)} watch servers for {page_url}")
    return servers


def _find_servers_html(html):
    """Extract content of <ul class="serversList"> or <ul id="watch"> from html"""
    m = re.search(
        r'<ul[^>]+class=["\'][^"\']*serversList[^"\']*["\'][^>]*>(.*?)</ul>',
        html, re.S | re.I
    )
    if not m:
        # Try with id="watch"
        m = re.search(r'<ul[^>]*id=["\']watch["\'][^>]*>(.*?)</ul>', html, re.S | re.I)
    return m.group(1) if m else ""


def get_categories(mtype="movie"):
    """Return category list for egydead.lat"""
    if mtype == "movie":
        return [
            {"title": "🎬 English Movies",        "url": _full_url("/category/english-movies/"),      "type": "category", "_action": "category"},
            {"title": "🇪🇬 Arabic Movies",          "url": _full_url("/category/افلام-عربي/"),       "type": "category", "_action": "category"},
            {"title": "🌏 Asian Movies",           "url": _full_url("/category/افلام-اسيوية/"),     "type": "category", "_action": "category"},
            {"title": "🇹🇷 Turkish Movies",         "url": _full_url("/category/افلام-تركية/"),      "type": "category", "_action": "category"},
            {"title": "🇮🇳 Indian Movies",          "url": _full_url("/category/افلام-هندي/"),       "type": "category", "_action": "category"},
            {"title": "🎭 Cartoon Movies",         "url": _full_url("/category/افلام-كرتون/"),      "type": "category", "_action": "category"},
            {"title": "🎌 Anime Movies",           "url": _full_url("/category/افلام-انمي/"),       "type": "category", "_action": "category"},
            {"title": "📽️ Documentary Movies",    "url": _full_url("/category/افلام-وثائقية/"),    "type": "category", "_action": "category"},
        ]
    # series - these live under /series-category/ (a different taxonomy
    # than movies' /category/), and use English slugs, confirmed directly
    # from the site's own navigation menu. The old URLs here used the
    # movie taxonomy path with Arabic slugs, which don't exist under
    # /series-category/ at all - explaining why every series category
    # produced the same wrong (redirected) content.
    return [
        {"title": "📺 English Series",        "url": _full_url("/series-category/english-series/"),    "type": "category", "_action": "category"},
        {"title": "🇪🇬 Arabic Series",         "url": _full_url("/series-category/arabic-series/"),     "type": "category", "_action": "category"},
        {"title": "🇹🇷 Turkish Series",       "url": _full_url("/series-category/turkish-series/"),    "type": "category", "_action": "category"},
        {"title": "🌏 Asian Series",          "url": _full_url("/series-category/asian-series/"),      "type": "category", "_action": "category"},
        {"title": "🎌 Anime Series",          "url": _full_url("/series-category/anime-series/"),      "type": "category", "_action": "category"},
        {"title": "🎠 Cartoon Series",        "url": _full_url("/series-category/cartoon-series/"),    "type": "category", "_action": "category"},
        {"title": "🇮🇳 Indian Series",         "url": _full_url("/series-category/indian-series/"),     "type": "category", "_action": "category"},
        {"title": "📽️ Documentary Series",    "url": _full_url("/series-category/documentary-series/"), "type": "category", "_action": "category"},
        {"title": "📡 TV Shows",              "url": _full_url("/series-category/tv-shows/"),          "type": "category", "_action": "category"},
    ]


def get_category_items(url, page=None):
    """Get items from a category page"""
    fetch_url = url
    if page and page > 1:
        # This site has been observed using two different pagination
        # styles: WordPress' usual path style (/page/2/) on some pages,
        # and a query-string style (?page=2/) on others (confirmed via a
        # live snapshot of the front page). If the URL we were given
        # already contains either form, bump the existing number in place
        # rather than assuming a style - that keeps this correct
        # regardless of which one the current page actually uses. Only
        # falls back to appending /page/N/ when neither is present yet
        # (i.e. this is the first page of a category with no page
        # component at all).
        if '/page/' in fetch_url:
            fetch_url = re.sub(r'/page/\d+', f'/page/{page}', fetch_url)
        elif re.search(r'[?&]page=\d+', fetch_url):
            fetch_url = re.sub(r'([?&]page=)\d+', r'\g<1>' + str(page), fetch_url)
        elif fetch_url.endswith('/'):
            fetch_url = f"{fetch_url}page/{page}/"
        else:
            fetch_url = f"{fetch_url}/page/{page}/"
    
    log(f"EgyDead: Fetching category page: {fetch_url}")
    html, final_url = _fetch(fetch_url)
    if not html:
        log(f"EgyDead: get_category_items failed: {fetch_url}")
        return []

    items = _parse_category_list(html)

    if not page or page == 1:
        nxt = _parse_pagination(html, fetch_url)
        if nxt:
            items.append(nxt)

    log(f"EgyDead: category {url} page {page or 1} → {len(items)} items")
    return items


def search(query, page=1):
    """Search for movies/series"""
    search_url = _get_base().rstrip("/") + "/?s=" + quote_plus(query)
    if page > 1:
        search_url += f"&paged={page}"
    
    html, final_url = _fetch(search_url)
    if not html:
        log(f"EgyDead: search failed for '{query}'")
        return []

    items = _parse_category_list(html)

    if page == 1:
        nxt = _parse_pagination(html, search_url)
        if nxt:
            items.append(nxt)

    log(f"EgyDead: search '{query}' → {len(items)} items")
    return items


def get_page(url, m_type=None):
    """Fetch and parse an item page"""
    html, final_url = _fetch(url)
    result = {
        "url": url,
        "title": "",
        "poster": "",
        "plot": "",
        "year": "",
        "rating": "",
        "servers": [],
        "items": [],
        "type": m_type or "movie",
    }

    if not html:
        log(f"EgyDead: get_page failed: {url}")
        return result

    # Extract metadata
    title, poster, plot, year = _extract_detail_meta(html)
    result["title"] = title
    result["poster"] = poster
    result["plot"] = plot
    result["year"] = year

    # Extract WATCH servers (streaming links)
    servers = _extract_watch_servers(html, final_url or url)

    # This site gates the actual server list behind a view-confirmation
    # step: the page's own "watch" form POSTs View=1 back to the exact
    # same URL, and only *that* response includes the populated
    # <ul class="serversList"> (confirmed directly via a real captured
    # network log - the plain GET response has the container present but
    # empty, no data-link attributes at all, until this POST happens).
    # Replicate that exact interaction as a fallback whenever the initial
    # GET comes back with no servers, instead of giving up.
    if not servers:
        log(f"EgyDead: no servers on initial load, retrying with View=1 POST: {url}")
        post_html, post_final_url = _fetch(url, post_data={"View": "1"})
        if post_html:
            servers = _extract_watch_servers(post_html, post_final_url or url)

    result["servers"] = servers

    # Determine type from URL
    low = url.lower()
    if any(x in low for x in ("/episode/", "/series/", "/season/", "/serie/", "مسلسل", "/category/مسلسلات", "/series-category/")):
        result["type"] = "series"
    else:
        result["type"] = m_type or "movie"

    log(f"EgyDead: item type={result['type']}, title={title}, watch_servers={len(servers)}")
    return result


def extract_stream(url):
    """Resolve a server URL to a playable stream"""
    from .base import resolve_streamruby, resolve_host, resolve_mixdrop, resolve_doodstream

    low = (url or "").lower()

    # StreamRuby
    if "stmruby" in low or "streamruby" in low:
        stream = resolve_streamruby(url)
        if stream:
            return (
                stream + "|Referer=https://stmruby.com/&Origin=https://stmruby.com",
                None,
                "https://stmruby.com/",
            )

    # Mixdrop
    if "mixdrop" in low:
        stream = resolve_mixdrop(url)
        if stream:
            return stream, None, None

    # Doodstream
    if "dood" in low or "doodstream" in low:
        stream = resolve_doodstream(url)
        if stream:
            return stream, None, None

    # Govid
    if "govid.live" in low:
        try:
            from .base import resolve_govid
            stream = resolve_govid(url)
            if stream:
                return stream, None, None
        except ImportError:
            pass

    # For other hosts
    return base_extract_stream(url)