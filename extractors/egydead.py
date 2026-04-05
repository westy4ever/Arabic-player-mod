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

