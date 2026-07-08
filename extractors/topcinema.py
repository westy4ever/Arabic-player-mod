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

DOMAINS = ["https://topcinemaa.top"]
MAIN_URL = DOMAINS[0]

def _normalize_url(url):
    if not url:
        return ""
    url = html_unescape(url.strip())
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http"):
        return urljoin(MAIN_URL, url)
    return url

_LEADING_TYPE_WORDS = ("فيلم", "افلام", "مسلسل", "مسلسلات", "انمي", "برنامج", "عرض")
_TITLE_NOISE_PHRASES = (
    "مشاهدة وتحميل", "مشاهدة وتحميل مباشر", "مشاهدة", "تحميل",
    "مترجمة", "مترجم", "مدبلجة", "مدبلج",
    "اون لاين", "اونلاين", "بجودة عالية", "بجودة", "حصريا", "كامل",
)

def _clean_title(title):
    """Strip bracketed tags, leading content-type words (فيلم/مسلسل/انمي/...),
    and common quality/language noise phrases (مترجم, مدبلج, اون لاين, ...)
    for a clean display title, e.g.
    "[فيلم] فيلم Passenger 2026 مترجم اون لاين" -> "Passenger 2026".

    Deliberately leaves season/episode markers (الموسم, الحلقة) untouched -
    those carry real information for series titles.
    """
    title = html_unescape(title or "")
    title = title.replace("&amp;", "&")
    # Strip invisible Unicode formatting chars (RTL/LTR marks, zero-width
    # spaces, BOM) BEFORE anything anchored to end-of-string below - these
    # are invisible when rendered but defeat a trailing "$" regex anchor,
    # which likely explains why the branding-suffix strip below worked
    # inconsistently (confirmed via logs: same page, same code, same
    # session - stripped one time, not stripped a few minutes later).
    title = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]+', '', title)
    # Strip bracketed tags like "[فيلم]"
    title = re.sub(r'\[[^\]]*\]\s*', '', title)
    # Strip site-branding suffix from <title> tag text, e.g.
    # "... مترجمة - توب سينما" -> "... مترجمة". Try the anchored form
    # first (cleaner - removes the separator too), then fall back to a
    # plain substring removal anywhere in the string as a safety net in
    # case some other trailing artifact still defeats the "$" anchor.
    title = re.sub(r'\s*[-|]\s*ت[ةه]?وب\s*سينما\s*$', '', title, flags=re.I)
    title = re.sub(r'ت[ةه]?وب\s*سينما', '', title, flags=re.I)
    # Strip known noise phrases first, so a leading type word that was
    # originally preceded by one (e.g. "مشاهدة وتحميل فيلم ...") becomes
    # the new leading word and gets caught below.
    for phrase in _TITLE_NOISE_PHRASES:
        title = re.sub(r'\s*' + re.escape(phrase) + r'\s*', ' ', title, flags=re.I)
    # Strip a leading content-type word (there may be more than one)
    words = title.split()
    while words and words[0] in _LEADING_TYPE_WORDS:
        words.pop(0)
    return " ".join(words).strip()

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
    """
    Extract movie/series items from listing pages (categories, search, recent, etc.)
    Looks for any <a> with href+title that contains an image with src/data-src.
    Filters out navigation links (/category/, /search/, /page/, /tag/, /author/).
    """
    items = []
    pattern = r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*title=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
    for m in re.finditer(pattern, html, re.I | re.S):
        href = m.group(1)
        title = m.group(2)
        inner = m.group(3)

        # Skip if the link points to a non‑item page (category, search, pagination, etc.)
        if re.search(r'/(?:category|search|page|tag|author)/', href, re.I):
            continue

        # Find image inside the <a>
        img_match = re.search(r'<img[^>]+(?:data-src|src)=["\']([^"\']+)["\']', inner, re.I)
        if not img_match:
            continue
        poster = img_match.group(1)

        # Skip placeholder images
        if not poster or poster.startswith('data:') or 'placeholder' in poster.lower():
            continue

        link = _normalize_url(href)
        poster = _normalize_url(poster)
        # FIX: category-list posters are WordPress-generated resized
        # thumbnail variants (e.g. "...-440x550.jpg"), while the
        # reliably-working detail-page poster (og:image) is always the
        # original full-size upload with no size suffix. WordPress
        # thumbnail regeneration commonly misses a handful of images after
        # theme/plugin changes, leaving just the resized variant 404ing
        # while the original (which WordPress never deletes) still
        # exists - this matches "poster works on the detail page but not
        # in the list" for the same specific items. Strip the suffix to
        # use the same reliable original file everywhere.
        poster = re.sub(r'-\d+x\d+(?=\.\w+(?:\?.*)?$)', '', poster)

        # FIX: type detection must run on the RAW title - _clean_title now
        # strips "مسلسل"/"انمي" as leading content-type words, so checking
        # the cleaned title here would always miss them and everything
        # would default to "movie".
        item_type = "movie"
        if "مسلسل" in title or "حلقة" in title or "انمي" in title:
            item_type = "series"

        title = _clean_title(title)

        items.append({
            "title": title,
            "url": link,
            "poster": poster,
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

    # Pagination: find the » link (next page)
    next_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>»\s*</a>', html, re.I)
    if next_match:
        next_url = _normalize_url(next_match.group(1))
        if next_url:
            items.append({
                "title": "➡️ الصفحة التالية",
                "url": next_url,
                "type": "category",
                "_action": "category"
            })
    return items

def search(query, page=1):
    url = MAIN_URL + "/search/?query=" + quote_plus(query) + "&type=all"
    html, final_url = fetch(url, referer=MAIN_URL)
    return _extract_blocks(html)

def get_page(url):
    html, final_url = fetch(url, referer=MAIN_URL)

    title_m = re.search(r'<title>(.*?)</title>', html, re.I | re.S)
    raw_title = title_m.group(1) if title_m else "Unknown Title"
    title = _clean_title(raw_title)

    poster_m = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    poster = _normalize_url(poster_m.group(1)) if poster_m else ""

    plot_m = re.search(r'class=["\']description["\'][^>]*>(.*?)</', html, re.S | re.I)
    plot = _clean_title(re.sub(r'<[^>]+>', '', plot_m.group(1))) if plot_m else ""

    servers = []
    episodes = []
    item_type = "movie"

    # Try to locate the watch page URL
    watch_url_m = re.search(
        r'<a[^>]+class=["\'][^"\']*watch[^"\']*["\'][^>]+href=["\']([^"\']+/watch/?)[\"\']',
        html, re.I
    )
    watch_page_html = html
    watch_url = final_url
    if watch_url_m:
        watch_url = _normalize_url(watch_url_m.group(1))
        watch_page_html, _ = fetch(watch_url, referer=final_url)
        watch_page_html = watch_page_html or ""

    # Extract post ID (used for server AJAX)
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

    # Server extraction – look for <li> with data-id and data-server
    # FIX: real markup is `<li data-id="X" data-server="N" class="server--item ...">`
    # - data-id/data-server come BEFORE class, but this regex required class
    # first, so it never matched any real page and silently fell through to
    # the generic fallback below every single time. Made attribute order
    # independent using lookaheads so it matches regardless of which
    # attribute comes first.
    server_candidates = []
    li_matches = re.findall(
        r'<li(?=[^>]*class=["\'][^"\']*server--item)(?=[^>]*data-id=["\'](\d+))(?=[^>]*data-server=["\'](\d+))[^>]*>(.*?)</li>',
        watch_page_html, re.I | re.S
    )
    for pid, idx, inner in li_matches:
        name = re.sub(r'<[^>]+>', ' ', inner)
        name = _clean_title(re.sub(r'\s+', ' ', name)).strip()
        if name:
            server_candidates.append((pid, idx, name))

    # Fallback: any element with data-id and data-server
    if not server_candidates:
        generic_matches = re.findall(
            r'<(?:li|a|button|div)[^>]*data-id=["\'](\d+)["\'][^>]*data-server=["\'](\d+)["\'][^>]*>(.*?)</(?:li|a|button|div)>',
            watch_page_html, re.I | re.S
        )
        for pid, idx, inner in generic_matches:
            name = re.sub(r'<[^>]+>', ' ', inner)
            name = _clean_title(re.sub(r'\s+', ' ', name)).strip()
            if name:
                server_candidates.append((pid, idx, name))

    # Last resort: use predefined server names if we have a post_id
    if not server_candidates and post_id:
        known_servers = [
            "متعدد الجودات", "UpDown", "StreamWish", "Doodstream",
            "Filelions", "Streamtape", "LuluStream", "Filemoon",
            "Mixdrop", "VidGuard", "Okru"
        ]
        for i, srv in enumerate(known_servers, 1):
            if re.search(re.escape(srv), watch_page_html, re.I):
                server_candidates.append((post_id, str(i), srv))

    ajax_endpoint = MAIN_URL + "/wp-content/themes/movies2023/Ajaxat/Single/Server.php"
    seen = set()
    for pid, idx, name in server_candidates:
        if not pid or not idx:
            continue
        key = (pid, idx)
        if key in seen:
            continue
        seen.add(key)
        clean_name = _clean_title(name or "").strip()
        if not clean_name:
            continue
        s_url = "topcinema_server|{}|{}|{}|{}".format(
            ajax_endpoint, pid, idx, watch_url
        )
        servers.append({
            "name": "توب سينما " + clean_name,
            "url": s_url,
        })

    # Episodes extraction – only if the page looks like a series
    # FIX: must check raw_title, not the cleaned title - _clean_title now
    # strips "مسلسل" as a leading content-type word, so this would always
    # miss it on the cleaned version.
    is_series_like = (
        "مسلسل" in raw_title or
        "الحلقة" in watch_page_html or
        "episodes" in watch_page_html.lower() or
        "season" in watch_page_html.lower()
    )
    if is_series_like:
        eps_container = ""
        # FIX: the confirmed real container is `<div class="episodes--list--side">`
        # containing a flat list of <a> episode links with no nested divs -
        # try this first with a precise, non-greedy match. The old fallback
        # patterns below still exist for other layouts, but their generic
        # "episodes" alternative was matching the WRONG, OUTER wrapper div
        # (`episodes--side--list`, which nests the season-toggler dropdown
        # before the actual episode links) and the non-greedy `(.*?)</div>`
        # was truncating at that nested div's closing tag - only ever
        # capturing the season selector, never a single actual episode link.
        m = re.search(
            r'<div[^>]+class=["\'][^"\']*episodes--list--side[^"\']*["\'][^>]*>(.*?)</div>',
            watch_page_html, re.S | re.I
        )
        if m:
            eps_container = m.group(1)
        else:
            for container_pat in [
                r'<div[^>]+class=["\'][^"\']*(?:episodes|series-episodes|season-episodes|ep_list|episodes-list|series-list|all-episodes)[^"\']*["\'][^>]*>(.*?)</div>',
                r'<ul[^>]*class=["\'][^"\']*(?:episodes|series-episodes|list-episodes|ep_list)[^"\']*["\'][^>]*>(.*?)</ul>',
                r'<section[^>]*class=["\'][^"\']*(?:episodes|series)[^"\']*["\'][^>]*>(.*?)</section>',
                r'<div[^>]+id=["\'][^"\']*(?:episodes|episodes-list|episodes-all)[^"\']*["\'][^>]*>(.*?)</div>'
            ]:
                m = re.search(container_pat, watch_page_html, re.S | re.I)
                if m:
                    eps_container = m.group(1)
                    break
        if not eps_container:
            eps_container = watch_page_html

        eps_matches = re.findall(
            r'<a[^>]+href=["\']([^"\']+/(?:watch|episode)[^"\']*)["\'][^>]*>(.*?)</a>',
            eps_container, re.DOTALL | re.I
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
        html, _ = fetch(ajax_url, referer=referer_url,
                        extra_headers={"X-Requested-With": "XMLHttpRequest"},
                        post_data=postdata)

        ifr_m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
        if ifr_m:
            v_url = _normalize_url(ifr_m.group(1))
            log("TopCinema: Found iframe '{}'".format(v_url))
            resolved = resolve_iframe_chain(v_url, referer=MAIN_URL)
            if resolved:
                if isinstance(resolved, tuple):
                    return resolved[0], None, (resolved[1] if len(resolved) > 1 and resolved[1] else MAIN_URL)
                return resolved, None, MAIN_URL
            return v_url, None, MAIN_URL

    return url, None, MAIN_URL