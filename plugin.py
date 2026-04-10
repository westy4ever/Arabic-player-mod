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
from enigma                  import eTimer, ePicLoad, eServiceReference, iPlayableService
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

_PLUGIN_VERSION = "2.0.0"
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

    # Ensure no old emojis are prefixing the title in our metadata
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
            # Preferred format:
            # /stream?url=<encoded_url>&referer=<encoded_url>&ua=<encoded_ua>
            # Legacy format:
            # /https://real-url?params|header=val&...
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

            # Build request headers
            headers = {"User-Agent": SAFE_UA}

            if explicit_ua:
                headers["User-Agent"] = explicit_ua

            # Parse piped headers (e.g. User-Agent=...&Referer=...)
            if piped_headers:
                for part in piped_headers.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        headers[k.strip()] = v.strip()

            # Auto-set Referer from URL domain if not already set
            if explicit_referer:
                headers["Referer"] = explicit_referer
            elif "Referer" not in headers:
                try:
                    parts = stream_url.split("/")
                    headers["Referer"] = parts[0] + "//" + parts[2] + "/"
                except Exception:
                    pass

            # Forward Range header for seeking support
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

            # Forward critical decoder headers
            for key in ("content-type", "content-length",
                        "content-range", "accept-ranges",
                        "last-modified", "etag"):
                if key in resp_hdrs:
                    self.send_header(key.title(), resp_hdrs[key])

            # Always advertise byte-range support
            if "accept-ranges" not in resp_hdrs:
                self.send_header("Accept-Ranges", "bytes")

            self.end_headers()

            if method == "HEAD":
                return

            # Stream body
            try:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    _PROXY_LAST_BYTES += len(chunk)
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except Exception:
                pass  # Client disconnected or decoder stopped reading

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
        self._items  = []  # list of dicts from extractor
        self._page   = 1
        self._source = "home"  # home / categories / search
        self._site   = "egydead" # egydead / akoam / arabseed / wecima
        self._m_type = "movie"
        self._last_query = ""
        self._nav_stack = []  # Navigation stack for proper back behavior
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
        self._nav_stack = []  # Clear stack when going home
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

    # removed duplicate _refreshPreview (the correct version is below at _setList)
    # ── Navigation ────────────────────────────────────────────────────────────
    def _onOk(self):
        idx = self["menu"].getSelectedIndex()
        if idx < 0 or idx >= len(self._items):
            return
        item = self._items[idx]

        # Home menu actions (System actions)
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
            # If _action is "category" or something else, let it fall through to curr_type check

        # Category selection
        # Support both 'type' and legacy '_action'
        curr_type = item.get("type", item.get("_action"))
        my_log("_onOk: type={}, url={}".format(curr_type, item.get("url")))
        
        if curr_type == "category":
            if item.get("_m_type") in ("movie", "series"):
                self._m_type = item.get("_m_type")
            self._loadCategory(item["url"], item["title"])
            return

        # Open movie / series / episode
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

        # Skip separators
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

        # Show poster with debounce (300ms delay to avoid loading during fast scrolling)
        poster_url = item.get("poster") or item.get("image") or ""
        # Do NOT call _get_tmdb_poster here — it makes a live HTTP request
        # on the main Enigma2 thread and will freeze the UI on every scroll.
        # Poster enrichment happens later in ArabicPlayerDetail._bgLoad.

        with self._poster_lock:
            self._requested_poster_url = poster_url

        if poster_url:
            # Check cache first — instant display
            cached = _get_cached_poster(poster_url)
            if cached:
                self._display_poster_from_file(cached)
            else:
                # Debounce: wait 300ms before downloading
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
            # Basic URL normalization
            try:
                from urllib.parse import urlparse, quote, urlunparse
                p = list(urlparse(url))
                p[2] = quote(p[2])
                p[4] = quote(p[4])
                url = urlunparse(p)
            except Exception: pass

            # Check cache first
            cached = _get_cached_poster(url)
            if cached:
                with self._poster_lock:
                    if url != self._requested_poster_url: return
                callInMainThread(self._display_poster_from_file, cached)
                return

            # Download and cache
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
        # Specific for EgyDead style
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

    def __init__(self, session, item, site="egydead", m_type="movie"): # Added m_type
        Screen.__init__(self, session)
        self.session = session
        self._item   = item
        self._site   = site
        self._m_type = m_type # Store m_type
        self._data   = None   # page data from extractor
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

    def _load(self):
        threading.Thread(target=self._bgLoad, args=(self._site, self._item["url"], self._m_type), daemon=True).start() # Pass site, url, m_type

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
        # Remove provider prefix from plot text
        plot_text = re.sub(r"^\[.*?\]\s*|^المصدر:\s*.*?\|\s*", "", plot_text)
        # H: second pass -- strip site names that survived start/end cleaning
        _MID_SITES = (
            "EgyDead", "Wecima", "Akoam", "ArabSeed",
            "TopCinema", "TopCinemaa", "FaselHD", "Shaheed", "Shaheed4u",
        )
        for _ms in _MID_SITES:
            # remove "| SiteName" or "- SiteName" or "SiteName" surrounded by spaces
            plot_text = re.sub(
                r"\s*[|\-]\s*" + re.escape(_ms) + r"[^\u0600-\u06ff\n]{0,25}",
                " ", plot_text, flags=re.I)
            # remove "على موقع SiteName" type phrases
            plot_text = re.sub(
                r"\u0639\u0644\u0649\s+\u0645\u0648\u0642\u0639\s+" + re.escape(_ms)
                + r"[^\u0600-\u06ff\n]{0,30}",
                " ", plot_text, flags=re.I)
        plot_text = re.sub(r"  +", " ", plot_text).strip()
        my_log("Detail plot source: {} | len={}".format(plot_source, len(plot_text)))
        _pt = (plot_text or "").strip()
        if len(_pt) > 500:
            _pt = _pt[:500].rsplit(" ", 1)[0] + "…"
        # G: force RTL paragraph direction for Arabic-dominant text
        _ar_count = sum(1 for _c in _pt[:80] if "؀" <= _c <= "ۿ")
        if _ar_count > int(len(_pt[:80]) * 0.3):
            _pt = "‏" + _pt
        self["plot"].setText(_pt)

        # Build menu
        self._servers = _sort_servers([s for s in data.get("servers", []) if s.get("url")])
        self._episodes = [e for e in data.get("items", []) if e.get("type") == "episode"]
        
        my_log("Detail _onLoaded: servers={}, items={}".format(len(self._servers), len(self._episodes)))

        # Detect if this is a series by checking data type, item type, OR presence of episodes
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

        # Load poster
        poster_url = data.get("poster") or self._item.get("poster", "")
        if poster_url:
            threading.Thread(
                target=self._downloadPoster, args=(poster_url,), daemon=True
            ).start()

    def _status_hint(self, prefix):
        fav_state = "محفوظ" if _is_favorite(self._item.get("url")) else "غير محفوظ"
        tmdb_state = "TMDb مفعل" if _tmdb_enabled() else "TMDb غير مفعل"
        return "{}  |  {}  |  {}".format(prefix, fav_state, tmdb_state)

    def _downloadPoster(self, url):
        try:
            if not url: return
            if url.startswith("//"): url = "https:" + url
            
            # --- Unicode Fix (Arabic Path Encoding) ---
            import urllib.request as urllib2
            try:
                from urllib.parse import urlparse, quote, urlunparse
                # Ensure the URL is a string (Py3) and encode it correctly for Request
                p = list(urlparse(url))
                p[2] = quote(p[2]) # encode path
                p[4] = quote(p[4]) # encode query string
                url = urlunparse(p)
            except Exception: pass
            
            # Use poster cache
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
        if idx < 0: return
        
        # If it's a series, open nested detail for episode
        _is_series = bool(
            self._data and (
                self._data.get("type") in ("series", "show")
                or self._item.get("type") in ("series", "show")
                or self._episodes
            )
        )
        if _is_series:
            if idx >= len(self._episodes): return
            item = self._episodes[idx]
            self.session.open(ArabicPlayerDetail, item, self._site, "episode")
        else:
            # movie / episode: extract and play selected server
            if idx >= len(self._servers): return
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
            
            # Use site-specific extractor via factory
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
            # Only reject if it's clearly an embed/player page with no known media extension
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
            
            # Using synced UA from base.py
            headers = {"User-Agent": SAFE_UA}
            
            # Use the final referer from the extraction process
            if final_ref:
                headers["Referer"] = final_ref
            
            if old_params:
                for p in old_params.split("&"):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        if k not in headers: headers[k] = v
            
            header_str = "&".join(["{}={}".format(k, v) for k, v in headers.items()])
            pure_url = main_url.split("|")[0].strip()
            # Enigma2 uses # mapping for HTTP headers, not |
            url = pure_url + "#" + header_str if header_str else pure_url
            
            _item_url   = self._item.get("url", "")
            _saved_pos  = _get_saved_position(_item_url)
            if _saved_pos > 30:
                _mins_r = _saved_pos // 60
                _secs_r = _saved_pos % 60
                def _on_resume(_ans, _u=url, _t=title, _iu=_item_url, _sp=_saved_pos):
                    if not _ans:
                        # user chose 'from start' -- wipe stale resume point
                        _save_position(_iu, 0)
                    _play(self.session, _u, _t, resume_pos=_sp if _ans else 0, item_url=_iu)
                self["status"].setText("جاري فتح المشغل...")
                self.session.openWithCallback(
                    _on_resume, MessageBox,
                    "Resume from {}:{:02d}?".format(_mins_r, _secs_r),
                    MessageBox.TYPE_YESNO, timeout=8, default=True)
            else:
                self["status"].setText("Opening player...")
                _play(self.session, url, title, resume_pos=0, item_url=_item_url)
            self["overlay_bg"].hide()
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

    # Try the most common Enigma2 backends in a practical order.
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

    # Detect if this is an HLS stream
    is_hls = any(x in plain_url.lower() for x in (".m3u8", "master.txt", "/hls", "/playlist"))

    if is_hls:
        # HLS streams: prioritize 4097 (native HLS on Enigma2 HiSilicon/others)
        add_candidate(4097, plain_url, "4097 مباشر HLS")
        if proxied:
            add_candidate(4097, proxied, "4097 + proxy HLS", True)
        add_candidate(4097, url, "4097 + headers HLS")
        add_candidate(8193, plain_url, "8193 مباشر")
        if proxied:
            add_candidate(8193, proxied, "8193 + proxy", True)
    else:
        # MP4/direct streams: try 5001 first
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


# ─── Simple Player Fallback ─────────────────────────────────────────────────
class ArabicPlayerSimplePlayer(Screen):
    skin = """
    <screen name="ArabicPlayerSimplePlayer" position="0,0" size="1920,1080" flags="wfNoBorder" backgroundColor="transparent">

        <!-- ── Shadow layer (slightly larger, softer) ── -->
        <widget name="osd_shadow"   position="148,856" size="1624,230" backgroundColor="#000000" zPosition="9" />

        <!-- ── Main OSD card (1600×210, centered, 160px margins) ── -->
        <widget name="overlay_bg"   position="160,860" size="1600,210" backgroundColor="#0A0E14" zPosition="10" />

        <!-- ── Top accent line (cyan, full card width) ── -->
        <widget name="osd_topline"  position="160,860" size="1600,3" backgroundColor="#00E5FF" zPosition="11" />

        <!-- ROW 1: Title + duration  (y=863, h=46) ── -->
        <widget name="osd_titlebar" position="160,860" size="1600,52" backgroundColor="#0D1520" zPosition="11" />
        <widget name="osd_title"    position="180,868" size="1180,38" font="Regular;30" foregroundColor="#00E5FF" transparent="1" zPosition="12" />
        <widget name="osd_durtext"  position="1380,868" size="360,38" font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="12" halign="right" />

        <!-- ROW 2: Progress bar track + fill + glow head (y=912, h=20) ── -->
        <widget name="prog_bg"      position="160,912" size="1600,20" backgroundColor="#1C2333" zPosition="11" />
        <widget name="prog_fill"    position="160,912" size="2,20" backgroundColor="#00B4D8" zPosition="12" />
        <widget name="prog_head"    position="160,910" size="4,24" backgroundColor="#00E5FF" zPosition="13" />
        <widget name="prog_pct"     position="160,912" size="1600,20" font="Regular;16" foregroundColor="#FFFFFF" transparent="1" zPosition="14" halign="center" />

        <!-- ROW 3: Elapsed | Status center | Seek hint (y=932, h=54) ── -->
        <widget name="osd_elapsed"  position="180,938" size="320,44" font="Regular;36" foregroundColor="#FFD740" transparent="1" zPosition="12" />
        <widget name="status"       position="640,938" size="640,44" font="Regular;36" foregroundColor="#39D98A" transparent="1" zPosition="12" halign="center" />
        <widget name="osd_hints"    position="1220,938" size="520,44" font="Regular;26" foregroundColor="#8B949E" transparent="1" zPosition="12" halign="right" />

        <!-- ROW 4: Divider + key-hint bar (y=982, h=48) ── -->
        <widget name="osd_divider"  position="160,982" size="1600,2" backgroundColor="#1C2333" zPosition="11" />
        <widget name="osd_keybar"   position="160,984" size="1600,46" backgroundColor="#0D1520" zPosition="11" />
        <widget name="osd_keys"     position="180,992" size="1560,34" font="Regular;24" foregroundColor="#484F58" transparent="1" zPosition="12" halign="center" />

        <!-- ── Bottom accent line ── -->
        <widget name="osd_botline"  position="160,1027" size="1600,3" backgroundColor="#0A2040" zPosition="11" />

    </screen>
    """

    def __init__(self, session, title, candidates, previous_service=None, resume_pos=0, item_url=""):
        Screen.__init__(self, session)
        self["overlay_bg"]   = Label("")
        self["status"]       = Label("جاري التشغيل...")
        # OSD widgets required by v7 skin
        self["osd_shadow"]   = Label("")
        self["osd_titlebar"] = Label("")
        self["osd_title"]    = Label("")
        self["osd_durtext"]  = Label("")
        self["osd_durtext2"] = Label("")
        self["osd_topline"]  = Label("")
        self["prog_bg"]      = Label("")
        self["prog_fill"]    = Label("")
        self["prog_head"]    = Label("")
        self["prog_pct"]     = Label("")
        self["osd_elapsed"]  = Label("")
        self["osd_hints"]    = Label("")
        self["osd_divider"]  = Label("")
        self["osd_keybar"]   = Label("")
        self["osd_keybar2"]  = Label("")
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
        self._hide_timer = eTimer()
        self._hide_timer.callback.append(self.__hideOSD)
        self._osd_update_timer = eTimer()
        self._osd_update_timer.callback.append(self.__updateOSD)
        self._osd_visible = False
        self._total_secs  = 0
        self._osd_auto_hide_secs = 4
        self._osd_update_timer = eTimer()
        self._osd_update_timer.callback.append(self.__updateOSD)
        self._osd_visible = False
        self._total_secs  = 0
        self._osd_update_timer = eTimer()
        self._osd_update_timer.callback.append(self.__updateOSD)
        self._osd_visible = False
        self._total_secs  = 0
        self._osd_update_timer = eTimer()
        self._osd_update_timer.callback.append(self.__updateOSD)
        self._osd_visible = False
        self._total_secs  = 0
        # new OSD widget references
        self["osd_titlebar"] = Label("")
        self["osd_title"]    = Label("")
        self["osd_durtext"]  = Label("")
        self["prog_bg"]      = Label("")
        self["prog_fill"]    = Label("")
        self["prog_pct"]     = Label("")
        self["osd_elapsed"]  = Label("")
        self["osd_hints"]    = Label("")
        self["osd_keybar"]   = Label("")
        self["osd_keys"]     = Label("")
        self._paused = False
        self["actions"] = ActionMap(
            ["OkCancelActions", "MediaPlayerActions", "InfobarSeekActions", "DirectionActions"],
            {
                "cancel":           self.__onExit,
                "stop":             self.__onExit,
                "ok":               self.__togglePause,
                "playpauseService": self.__togglePause,
                "right":            lambda: self.__seek(+10),
                "left":             lambda: self.__seek(-10),
                "seekFwd":          lambda: self.__seek(+60),
                "seekBack":         lambda: self.__seek(-60),
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

    # ── OSD helpers ──────────────────────────────────────────────
    _OSD_WIDGETS = [
        "osd_shadow","overlay_bg","osd_topline","osd_botline",
        "osd_titlebar","osd_title","osd_durtext","osd_durtext2",
        "prog_bg","prog_fill","prog_head","prog_pct","osd_elapsed",
        "status","osd_hints","osd_divider",
        "osd_keybar","osd_keybar2","osd_keys",
    ]

    def __initOSD(self):
        for _w in self._OSD_WIDGETS:
            try: self[_w].hide()
            except Exception: pass

    def __hideOSD(self):
        self._osd_visible = False
        try: self._osd_update_timer.stop()
        except Exception: pass
        for _w in self._OSD_WIDGETS:
            try: self[_w].hide()
            except Exception: pass

    def __showOSD(self, auto_hide=True):
        self._osd_visible = True
        for _w in self._OSD_WIDGETS:
            try: self[_w].show()
            except Exception: pass
        self.__updateOSD()
        try: self._osd_update_timer.start(1000, False)
        except Exception: pass
        if auto_hide:
            try:
                secs = getattr(self, "_osd_auto_hide_secs", 4)
                self._hide_timer.stop()
                self._hide_timer.start(secs * 1000, True)
            except Exception: pass

    def __updateOSD(self):
        if not getattr(self, "_osd_visible", False):
            try: self._osd_update_timer.stop()
            except Exception: pass
            return
        try:
            wall = _GLOBAL_PLAY_START_WALL
            base = _GLOBAL_PLAY_START_POS
            elapsed = max(0, int((time.time() - wall) + base)) if wall else 0
            he = elapsed // 3600; me = (elapsed % 3600) // 60; se = elapsed % 60
            self["osd_elapsed"].setText("{:02d}:{:02d}:{:02d}".format(he, me, se))
            total = getattr(self, "_total_secs", 0)
            if not total:
                try:
                    svc  = self.session.nav.getCurrentService()
                    seek = svc and svc.seek()
                    if seek:
                        r = seek.getLength()
                        if r and r[0] == 0 and r[1] > 0:
                            total = r[1] // 90000
                            self._total_secs = total
                except Exception: pass
            if total > 0:
                rem = max(0, total - elapsed)
                pct = min(1.0, float(elapsed) / float(total))
                hr=rem//3600; mr=(rem%3600)//60; sr=rem%60
                ht=total//3600; mt=(total%3600)//60; st=total%60
                self["osd_durtext"].setText(
                    "-{:02d}:{:02d}:{:02d}  {:02d}:{:02d}:{:02d}".format(hr,mr,sr,ht,mt,st))
                self["prog_pct"].setText("{:.1f}%".format(pct*100))
                rem = max(0, total - elapsed)
                pct = min(1.0, float(elapsed) / float(total))
                hr=rem//3600; mr=(rem%3600)//60; sr=rem%60
                ht=total//3600; mt=(total%3600)//60; st=total%60
                self["osd_hints"].setText("-{:02d}:{:02d}:{:02d}".format(hr,mr,sr))
                self["osd_durtext2"].setText("{:02d}:{:02d}:{:02d}".format(ht,mt,st))
                self["osd_durtext"].setText("")
                self["prog_pct"].setText("{:.1f} %".format(pct*100))
                fw = max(2, int(1920 * pct))
            else:
                self["osd_hints"].setText("")
                self["osd_durtext"].setText("")
                self["osd_durtext2"].setText("")
                self["prog_pct"].setText("")
                fw = 2
            try:
                from enigma import eSize, ePoint
                self["prog_fill"].instance.setSize(eSize(fw, 24))
                self["prog_head"].instance.move(ePoint(max(0,fw-2), 929))
            except Exception: pass
            self["osd_keys"].setText("OK=Pause  << -10s  +10s >>  <<< -60s  +60s >>>")
            self["osd_keybar2"].setText("Stop = Save & Exit")
        except Exception as e:
            my_log("updateOSD error: {}".format(e))

    # ── playback ─────────────────────────────────────────────────
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
        except Exception:
            pass
        try:
            self.session.nav.playService(self.sref)
            self._retry_timer.start(12000, True)
        except Exception as e:
            my_log("SimplePlayer fallback error: {}".format(e))
            self.__playNext()

    def __onConfirmed(self):
        self._play_confirmed = True
        try:
            self._retry_timer.stop()
        except Exception:
            pass
        my_log("Play confirmed: {}".format(self._candidate_label))
        _start_pos_tracker(self.session, self._item_url, start_pos=self._resume_pos)
        if self._resume_pos > 30:
            self._seek_timer.start(2000, True)
        # Show OSD briefly then auto-hide
        self["osd_title"].setText(self.title)
        self["status"].setText(u"▶ Playing")
        self._total_secs = 0
        self.__showOSD()  # auto-hides after 4s

    def __togglePause(self):
        try:
            svc = self.session.nav.getCurrentService()
            if not svc:
                self.__showOSD(); self._hide_timer.start(2000, True); return
            p = svc.pause()
            if not p:
                self.__showOSD(); self._hide_timer.start(2000, True); return
            if self._paused:
                p.unpause()
                self._paused = False
                self["status"].setText(u"▶ Playing")
            else:
                p.pause()
                self._paused = True
                self["status"].setText(u"⏸ Paused")
            self.__showOSD()  # auto-hides after 4s
        except Exception as e:
            my_log("togglePause error: {}".format(e))
            self.__showOSD()

    def __seek(self, delta_secs):
        try:
            svc = self.session.nav.getCurrentService()
            if not svc: return
            sk = svc.seek()
            if not sk: return
            # compute absolute target from current wall-clock estimate
            global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
            global _GLOBAL_LAST_SEEK_TARGET
            _wall = _GLOBAL_PLAY_START_WALL
            _base = _GLOBAL_PLAY_START_POS
            if _wall:
                elapsed = time.time() - _wall
            else:
                elapsed = 0
            current_est = int(_base + elapsed)
            target      = max(0, current_est + int(delta_secs))
            # clamp to total duration if known
            _tot = getattr(self, "_total_secs", 0)
            if _tot > 0:
                target = min(target, _tot - 3)
            # use absolute seekTo -- reliable on HiSilicon
            # seekRelative is unreliable for large jumps on this SoC
            sk.seekTo(target * 90000)
            _GLOBAL_LAST_SEEK_TARGET = target
            # set base to target immediately; decoder takes ~2s to reach
            # it so we subtract 2s allowance so display stays behind video
            _GLOBAL_PLAY_START_POS  = max(0, target - 2)
            _GLOBAL_PLAY_START_WALL = time.time()
            self._total_secs = 0
            _th = target // 3600; _tm = (target % 3600) // 60; _ts = target % 60
            _arr = u"➡" if delta_secs > 0 else u"⬅"
            self["status"].setText(u"{} {:02d}:{:02d}:{:02d}".format(_arr, _th, _tm, _ts))
            self.__showOSD()
            # auto-hide after 2.5s (gives time to see where we landed)
            self._hide_timer.start(2500, True)
        except Exception as e:
            my_log("seek error: {}".format(e))

    def __hideStatus(self):
        self["osd_title"].setText(self.title)
        self["osd_keys"].setText(
            u"OK = Pause/Play   ⬅ -10s   +10s ➡   ⬅⬅ -60s   +60s ➡➡   Stop = Save & Exit")
        self["status"].setText(u"▶ Playing")
        self._total_secs = 0
        self.__showOSD()
        self._hide_timer.start(3000, True)

    def __onExit(self):
        """Stop/Back/OK: save accurate position then close."""
        try:
            if self._item_url and _GLOBAL_PLAY_START_WALL > 0:
                elapsed = time.time() - _GLOBAL_PLAY_START_WALL
                secs    = int(_GLOBAL_PLAY_START_POS + elapsed)
                # sanity-check: position must be > 30s and
                # not exceed total duration by more than 60s
                _tot = getattr(self, "_total_secs", 0)
                if _tot > 0:
                    secs = min(secs, _tot - 5)
                secs = max(0, secs)
                if secs > 30:
                    _save_position(self._item_url, secs)
                    my_log("Exit save: {}s (wall-clock)".format(secs))
                else:
                    my_log("Exit save skipped: pos={}s".format(secs))
        except Exception as e:
            my_log("Exit save error: {}".format(e))
        _stop_pos_tracker()
        self.close()

    def __onFailed(self):
        if self._play_confirmed:
            return
        try:
            self._retry_timer.stop()
        except Exception:
            pass
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
            svc  = self.session.nav.getCurrentService()
            seek = svc and svc.seek()
            if seek:
                seek.seekTo(self._resume_pos * 90000)
                my_log("Resume seekTo: {}s".format(self._resume_pos))
                global _GLOBAL_PLAY_START_WALL, _GLOBAL_PLAY_START_POS
                global _GLOBAL_LAST_SEEK_TARGET
                _GLOBAL_LAST_SEEK_TARGET = self._resume_pos
                # base = target - 2s decoder buffer
                # wall starts from NOW so estimate increments from here
                _GLOBAL_PLAY_START_POS  = max(0, self._resume_pos - 2)
                _GLOBAL_PLAY_START_WALL = time.time()
                # update OSD immediately to show correct position
                self._total_secs = 0
                if getattr(self, "_osd_visible", False):
                    self.__updateOSD()
            else:
                my_log("doSeek: no seek interface")
        except Exception as e:
            my_log("doSeek failed: {}".format(e))

    def __stop(self):
        self.__hideOSD()
        if self._handoff:
            return
        _stop_pos_tracker()
        for _t in ("_seek_timer","_retry_timer","_hide_timer","_osd_update_timer"):
            try: getattr(self, _t).stop()
            except Exception: pass
        try: self.session.nav.stopService()
        except Exception: pass
        # small delay before restoring previous service reduces
        # the single-frame flicker on black background
        try:
            from enigma import eCallLater
            eCallLater(80, self.__restorePrevious)
        except Exception:
            self.__restorePrevious()

    def __restorePrevious(self):
        if self._restored_previous:
            return
        self._restored_previous = True
        _restore_previous_service(self.session, self.previous_service)

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