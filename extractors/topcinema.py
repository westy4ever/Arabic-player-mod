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

    watch_page_html = html
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

