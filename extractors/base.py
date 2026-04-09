# -*- coding: utf-8 -*-
"""
Base extractor — common utilities + video host resolvers
Hosts supported: Streamtape, Doodstream, Vidbom, Upstream, Govid, Uqload, Mixdrop, Voe, etc.
"""

import re
import json
import time
import random  # FIX: moved import to top
import urllib.request
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor, HTTPSHandler
from urllib.parse import urljoin, urlparse, unquote, urlencode  # FIX: export urljoin
from urllib.error import URLError, HTTPError
import http.cookiejar as cookiejar
import ssl
import gzip
import zlib
import io
import sys

try:
    import brotli
except Exception:
    brotli = None

UA      = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 30
ACCEPT_ENCODING = "gzip, deflate, br" if brotli is not None else "gzip, deflate"

# Global session/opener with cookie support
_opener = None

def log(msg):
    """Central logging for device debugging"""
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = "[{}] {}\n".format(ts, msg)
        with open("/tmp/arabicplayer.log", "a") as f:
            f.write(line)
        print("[ArabicPlayer] {}".format(msg))
    except:
        pass

def _get_opener():
    global _opener
    if _opener:
        return _opener
    
    cj = cookiejar.CookieJar()
    
    # SSL context to ignore verification (required for many Arabic streaming sites)
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    except AttributeError:
        ctx = ssl._create_unverified_context()

    _opener = build_opener(
        HTTPCookieProcessor(cj), 
        HTTPSHandler(context=ctx)
    )
    
    return _opener


def _decode_response_body(raw, info):
    # Handle Compression
    ce = info.get('Content-Encoding', '').lower()
    if 'gzip' in ce:
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    elif 'deflate' in ce:
        try:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        except Exception:
            raw = zlib.decompress(raw)
    elif 'br' in ce and brotli is not None:
        raw = brotli.decompress(raw)

    # Handle Encoding
    charset = 'utf-8'
    ctype = info.get('Content-Type', '').lower()
    if 'charset=' in ctype:
        charset = ctype.split('charset=')[-1].split(';')[0].strip()

    try:
        return raw.decode(charset)
    except Exception:
        try:
            return raw.decode('utf-8', errors='ignore')
        except Exception:
            return raw.decode('latin-1', errors='ignore')

def fetch(url, referer=None, extra_headers=None, post_data=None):
    """Stable fetch: robust headers for ACE/Bot bypass and SSL handle"""
    try:
        opener = _get_opener()
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not referer:
            if "wecima" in domain or "mycima" in domain: referer = "https://wecima.click/"
            elif "fasel" in domain: referer = "https://www.faselhd.cam/"
            elif "topcinema" in domain: referer = "https://topcinemaa.com/"
            elif "shaheed" in domain: referer = "https://shaheeid4u.net/"
            elif "egydead" in domain or "x7k9f.sbs" in domain: referer = "https://x7k9f.sbs/"
            else: referer = "{}://{}/".format(parsed.scheme, domain)

        headers = {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ar,en-US,en;q=0.9",
            "Accept-Encoding": ACCEPT_ENCODING,
            "Connection": "keep-alive",
            "Referer": referer,
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        if any(x in url.lower() for x in ["ajax", "get__watch", "api/"]):
            headers.update({
                "X-Requested-With": "XMLHttpRequest", 
                "Accept": "application/json, text/javascript, */*; q=0.01", 
                "Sec-Fetch-Dest": "empty", 
                "Sec-Fetch-Mode": "cors"
            })
        if extra_headers: headers.update(extra_headers)
        
        data = post_data
        if data and isinstance(data, dict):
            data = urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif data and isinstance(data, str):
            data = data.encode("utf-8")

        log("Fetching: {}".format(url))
        req = Request(url, headers=headers, data=data)
        with opener.open(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            final_url = resp.geturl()
            info = resp.info()
            
            # ACE Redirection Check
            if "alliance4creativity.com" in final_url.lower() or "watch-it-legally" in final_url.lower():
                log("!!! ALERT: ACE Redirect detected for {} !!!".format(url))
                return None, final_url
            html = _decode_response_body(raw, info)
            
            log("Fetch Success: {} ({} bytes)".format(final_url, len(html)))
            return html, final_url
    except HTTPError as e:
        try:
            raw = e.read()
            html = _decode_response_body(raw, e.info()) if raw else ""
            log("Fetch HTTPError: {} -> {} {} ({} bytes)".format(url, e.code, e.reason, len(html)))
        except Exception:
            log("Fetch HTTPError: {} -> {} {}".format(url, getattr(e, "code", "?"), getattr(e, "reason", e)))
        return None, url
    except URLError as e:
        log("Fetch URLError: {} -> {}".format(url, e))
        global _opener
        _opener = None  # rebuild SSL context on next request
        return None, url
    except Exception as e:
        log("Fetch Error: {} -> {}".format(url, e))
        return None, url


def extract_iframes(html, base_url=""):
    """Return list of iframe src URLs from HTML"""
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    result = []
    for src in iframes:
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            parsed = urlparse(base_url)
            src = parsed.scheme + "://" + parsed.netloc + src
        if src.startswith("http"):
            result.append(src)
    return result


def find_m3u8(html):
    """Find m3u8 URL in page source with robust patterns"""
    if not html: return None
    patterns = [
        r'["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'source\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'hls\.loadSource\(["\']([^"\']+)["\']',
        r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'data-url=["\']([^"\']+\.m3u8[^"\']*)["\']',
        r'data-src=["\']([^"\']+\.m3u8[^"\']*)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").strip()
            if url.startswith("//"): url = "https:" + url
            if url.startswith("http") and ".m3u8" in url:
                return url
    return None


def find_mp4(html):
    """Find mp4 URL in page source with robust patterns"""
    if not html: return None
    patterns = [
        r'["\']([^"\']+\.mp4[^"\']*)["\']',
        r'file\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']',
        r'data-url=["\']([^"\']+\.mp4[^"\']*)["\']',
    ]
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            url = m.group(1).replace("\\/", "/").replace("&amp;", "&").strip()
            if url.startswith("//"): url = "https:" + url
            if url.startswith("http") and ".mp4" in url:
                return url
    return None


def _best_media_url(text):
    """Pick the best visible video source from plain or unpacked JS."""
    candidates = []
    seen = set()
    patterns = [
        r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)',
        r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)',
    ]

    def score(url):
        lowered = url.lower()
        if "2160" in lowered or "4k" in lowered:
            return 5000
        if "1080" in lowered or "fhd" in lowered:
            return 4000
        if "720" in lowered or "hd" in lowered:
            return 3000
        if "480" in lowered:
            return 2000
        if "360" in lowered:
            return 1000
        if "240" in lowered or "sd" in lowered:
            return 500
        if ".m3u8" in lowered:
            return 3500
        return 100

    for pat in patterns:
        for match in re.findall(pat, text or "", re.I):
            url = match.replace("\\/", "/").replace("&amp;", "&")
            if url in seen:
                continue
            seen.add(url)
            candidates.append((score(url), url))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _extract_packer_blocks(html):
    """Return likely Dean Edwards packer blocks even when regex would stop early."""
    blocks = []
    marker = "eval(function(p,a,c,k,e,d){"
    tail = ".split('|')))"
    pos = 0
    while True:
        start = (html or "").find(marker, pos)
        if start == -1:
            break
        end = (html or "").find(tail, start)
        if end == -1:
            break
        blocks.append(html[start:end + len(tail)])
        pos = end + len(tail)
    return blocks


def decode_packer(packed):
    """Decodes Dean Edwards Packer compressed JS"""
    try:
        def read_js_string(text, start_idx):
            quote = text[start_idx]
            i = start_idx + 1
            out = []
            while i < len(text):
                ch = text[i]
                if ch == "\\" and i + 1 < len(text):
                    out.append(text[i + 1])
                    i += 2
                    continue
                if ch == quote:
                    return "".join(out), i + 1
                out.append(ch)
                i += 1
            return "", -1

        start = packed.find("}(")
        if start == -1:
            return ""
        idx = start + 2
        while idx < len(packed) and packed[idx] in " \t\r\n":
            idx += 1
        if idx >= len(packed) or packed[idx] not in ("'", '"'):
            return ""

        p, idx = read_js_string(packed, idx)
        if idx == -1:
            return ""

        nums = re.match(r"\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*", packed[idx:], re.S)
        if not nums:
            return ""
        a, c = nums.group(1), nums.group(2)
        idx += nums.end()
        if idx >= len(packed) or packed[idx] not in ("'", '"'):
            return ""

        k, idx = read_js_string(packed, idx)
        if idx == -1:
            return ""

        a, c = int(a), int(c)
        k = k.split("|")
        
        def e(c):
            result = ""
            while True:
                result = "0123456789abcdefghijklmnopqrstuvwxyz"[c % a] + result
                c = c // a
                if c == 0:
                    break
            return result
        
        d = {}
        for i in range(c):
            d[e(i)] = k[i] or e(i)
            
        return re.sub(r'\b(\w+)\b', lambda x: d.get(x.group(1), x.group(1)), p)
    except:
        return ""


def find_packed_links(html):
    """Find video links inside Packer-obfuscated JS"""
    evals = _extract_packer_blocks(html)
    if not evals:
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
    for ev in evals:
        dec = decode_packer(ev)
        if dec:
            res = find_m3u8(dec) or find_mp4(dec)
            if res: return res
    return None


# ─── Video Host Resolvers ────────────────────────────────────────────────────

def resolve_streamtape(url):
    """Extract from streamtape.com"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        # Streamtape obfuscates the link in two parts
        m = re.search(r"robotlink\)\.innerHTML = '([^']+)'\s*\+\s*'([^']+)'", html)
        if m:
            link = m.group(1) + m.group(2)
            link = link.replace("//streamtape.com", "https://streamtape.com")
            if not link.startswith("http"):
                link = "https:" + link
            return link
        # Alternative pattern
        m = re.search(r'(/get_video\?[^"\'&\s]+)', html)
        if m:
            return "https://streamtape.com" + m.group(1)
    except Exception:
        pass
    return None


def resolve_doodstream(url):
    """Extract from dood.* / doodstream / dsvplay and variants"""
    try:
        # Normalize dood domains to dood.re
        dood_base = "https://dood.re"
        # Try multiple domain patterns
        for pat, domain in [
            (r'dood\.[a-z]+', 'dood.re'),
            (r'dsvplay\.[a-z]+', 'dood.re'),
            (r'd0o0d\.[a-z]+', 'dood.re'),
        ]:
            url_try = re.sub(pat, domain, url)
            html, final_url = fetch(url_try)
            if html:
                break
        else:
            html, final_url = fetch(url)
        if not html:
            return None

        m = re.search(r'\$\.get\(["\'](/pass_md5/[^"\']+)["\']', html)
        if not m:
            m = re.search(r'pass_md5/([^"\'\.\s&]+)', html)
            if m:
                pass_path = "/pass_md5/" + m.group(1)
            else:
                return None
        else:
            pass_path = m.group(1)

        pass_url = dood_base + pass_path
        token_html, _ = fetch(pass_url, referer=url)
        if not token_html:
            return None
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        rand = "".join(random.choice(chars) for _ in range(10))  # FIX: use top-level random
        return token_html.strip() + rand + "?token=" + pass_path.split("/")[-1] + "&expiry=" + str(int(time.time() * 1000))
    except Exception:
        pass
    return None


def resolve_vidbom(url):
    """Extract from vidbom.com / vidshare.tv and similar"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        m3u8 = find_m3u8(html)
        if m3u8:
            return m3u8
        mp4 = find_mp4(html)
        return mp4
    except Exception:
        pass
    return None


def resolve_uqload(url):
    """Extract from uqload.co"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        m = re.search(r'sources:\s*\["([^"]+)"\]', html)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def resolve_govid(url):
    """Extract from govid.me"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_upstream(url):
    """Extract from upstream.to"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None


def resolve_mixdrop(url):
    """Extract from mixdrop.co / .top (handles Packer)"""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        
        # 1. Try plain text first
        m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', html)
        if m:
            link = m.group(1)
            return ("https:" + link) if link.startswith("//") else link
            
        # 2. Try Packer
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
        for ev in evals:
            dec = decode_packer(ev)
            if dec:
                m = re.search(r'MDCore\.wurl\s*=\s*"([^"]+)"', dec)
                if m:
                    link = m.group(1)
                    return ("https:" + link) if link.startswith("//") else link
    except Exception:
        pass
    return None

def resolve_voe(url):
    """Extract from voe.sx — uses obfuscated JS"""
    try:
        html, final = fetch(url, referer="https://x7k9f.sbs/")
        if not html:
            return None
        # Pattern 1: hls key in JS object
        for pat in [r"'hls'\s*:\s*'([^']+)'", r'"hls"\s*:\s*"([^"]+)"',
                    r"sources\s*=\s*\[\s*\{[^}]*file\s*:\s*'([^']+)'"]:
            m = re.search(pat, html)
            if m:
                return m.group(1)
        # Pattern 2: atob encoded
        import base64
        for enc in re.finditer(r"atob\(['\"]([A-Za-z0-9+/=]+)['\"]\)", html):
            try:
                dec = base64.b64decode(enc.group(1) + "==").decode("utf-8", errors="ignore")
                if "http" in dec:
                    mm = re.search(r"(https?://[^\s'\"<>]+\.m3u8[^\s'\"<>]*)", dec)
                    if mm:
                        return mm.group(1)
            except Exception:
                pass
        return find_m3u8(html) or find_mp4(html)
    except Exception:
        pass
    return None

def resolve_streamruby(url):
    """Extract from streamruby.com / stmruby.com"""
    try:
        html, _ = fetch(url)
        if not html: return None
        # Pattern 1: Plain text
        m = find_m3u8(html) or find_mp4(html)
        if m: return m
        # Pattern 2: Packed JS
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
        for ev in evals:
            dec = decode_packer(ev)
            if dec:
                m = find_m3u8(dec) or find_mp4(dec)
                if m: return m
    except: pass
    return None

def resolve_hgcloud(url):
    """Extract from hgcloud.to / masukestin.me"""
    try:
        html, _ = fetch(url)
        if not html: return None
        return find_m3u8(html) or find_mp4(html)
    except: pass
    return None


def resolve_vidtube(url):
    """Extract direct MP4/HLS from vidtube.one embeds."""
    try:
        html, _ = fetch(url)
        if not html:
            return None
        if "restricted for this domain" in html.lower():
            html = None
            for _ in range(2):
                html, _ = fetch(url, referer="https://topcinema.fan/")
                if html:
                    break
            if not html:
                return None

        direct = _best_media_url(html)
        if direct:
            return direct

        for ev in _extract_packer_blocks(html):
            dec = decode_packer(ev)
            if not dec:
                continue
            direct = _best_media_url(dec)
            if direct:
                return direct
    except Exception:
        pass
    return None

HOST_RESOLVERS = {
    "streamtape": resolve_streamtape,
    "dood":       resolve_doodstream,
    "dsvplay":    resolve_doodstream,
    "vidbom":     resolve_vidbom,
    "vidshare":   resolve_vidbom,
    "uqload":     resolve_uqload,
    "govid":      resolve_govid,
    "upstream":   resolve_upstream,
    "mixdrop":    resolve_mixdrop,
    "voe":        resolve_voe,
    "streamruby": resolve_streamruby,
    "hgcloud":    resolve_hgcloud,
    "masukestin": resolve_hgcloud,
    "vidtube":    resolve_vidtube,
}
def resolve_generic_embed(url):
    """Generic resolver for embed hosts — tries m3u8/mp4 directly then iframes"""
    try:
        html, final = fetch(url, referer="https://x7k9f.sbs/")
        if not html:
            return None
        result = find_m3u8(html) or find_mp4(html)
        if result:
            return result
        # Try Packer-obfuscated JS
        evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
        for ev in evals:
            dec = decode_packer(ev)
            if dec:
                result = find_m3u8(dec) or find_mp4(dec)
                if result:
                    return result
        # Follow iframes one level
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        for ifr in iframes:
            if ifr.startswith("//"): ifr = "https:" + ifr
            h2, _ = fetch(ifr, referer=url)
            if h2:
                result = find_m3u8(h2) or find_mp4(h2)
                if result:
                    return result
    except Exception:
        pass
    return None


# ─── Host Dispatcher ─────────────────────────────────────────────────────────

# ─── Multi-Provider Resolvers (TMDB Based) ──────────────────────────────────

def _get_stream_moviesapi(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://moviesapi.club/api/v1/movies/{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://moviesapi.club/api/v1/tv/{}/{}/{}".format(tmdb_id, s, e)
    body, _ = fetch(url, extra_headers={"Accept": "application/json"})
    if not body: return None
    try:
        data = json.loads(body)
        sources = data.get("sources") or []
        for src in sources:
            f = src.get("file") or src.get("url") or ""
            if ".m3u8" in f: return f
        for src in sources:
            f = src.get("file") or src.get("url") or ""
            if f.startswith("http"): return f
    except: pass
    return find_m3u8(body) or find_mp4(body)

def _get_stream_multiembed(tmdb_id, m_type, season=None, episode=None):
    url = "https://multiembed.mov/directstream.php?video_id={}&tmdb=1".format(tmdb_id)
    if season and episode: url += "&s={}&e={}".format(season, episode)
    html, final = fetch(url)
    if not html: return None
    if final != url and final.startswith("http"):
        if ".m3u8" in final: return final
        h2, _ = fetch(final, referer=url)
        if h2:
            m = find_m3u8(h2)
            if m: return m
    return find_m3u8(html) or find_mp4(html)

def _get_stream_superembed(tmdb_id, m_type, season=None, episode=None):
    url = "https://getsuperembed.link/?video_id={}&tmdb=1".format(tmdb_id)
    if season and episode: url += "&s={}&e={}".format(season, episode)
    body, final = fetch(url)
    if not body: return None
    body = body.strip()
    if body.startswith("http") and len(body) < 500:
        h2, _ = fetch(body, referer=url)
        if h2: return find_m3u8(h2) or find_mp4(h2)
        return body
    try:
        data = json.loads(body)
        for k in ["url", "link", "src", "stream"]:
            if k in data and data[k]: return data[k]
    except: pass
    mm = re.search(r'(https?://[^\s"\'<>]{10,})', body)
    return mm.group(1) if mm else None

def _get_stream_2embed(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://www.2embed.cc/embedtmdb/{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://www.2embed.cc/embedtvtmdb/{}&s={}&e={}".format(tmdb_id, s, e)
    html, _ = fetch(url)
    if not html: return None
    for iframe in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I):
        if iframe.startswith("//"): iframe = "https:" + iframe
        if iframe.startswith("http"):
            h2, _ = fetch(iframe, referer=url)
            if h2:
                m = find_m3u8(h2)
                if m: return m
    return find_m3u8(html) or find_mp4(html)

def _get_stream_autoembed(tmdb_id, m_type, season=None, episode=None):
    if m_type == "movie":
        url = "https://autoembed.cc/movie/tmdb-{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://autoembed.cc/tv/tmdb-{}-{}-{}".format(tmdb_id, s, e)
    html, _ = fetch(url)
    if not html: return None
    return find_m3u8(html) or find_mp4(html)

def _get_stream_vidsrc(tmdb_id, m_type, season=None, episode=None):
    """FIX: Added resolver for vidsrc:// scheme"""
    if m_type == "movie":
        url = "https://vidsrc.me/embed/movie/{}".format(tmdb_id)
    else:
        s, e = season or "1", episode or "1"
        url = "https://vidsrc.me/embed/tv/{}/{}/{}".format(tmdb_id, s, e)
    html, _ = fetch(url, referer="https://vidsrc.me/")
    if not html:
        return None
    # Try to find iframe redirect or direct source
    m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
    if m:
        iframe_url = m.group(1)
        if iframe_url.startswith("//"): iframe_url = "https:" + iframe_url
        h2, _ = fetch(iframe_url, referer=url)
        if h2:
            return find_m3u8(h2) or find_mp4(h2)
    return find_m3u8(html) or find_mp4(html)

_PREMIUM_METHODS = {
    "moviesapi":   _get_stream_moviesapi,
    "multiembed":  _get_stream_multiembed,
    "superembed":  _get_stream_superembed,
    "2embed":      _get_stream_2embed,
    "autoembed":   _get_stream_autoembed,
    "vidsrc":      _get_stream_vidsrc,   # FIX: added vidsrc handler
}

def get_premium_servers(m_type, tmdb_id, season=None, episode=None):
    """Return a list of premium multi-provider servers as dicts"""
    res = []
    suffix = ""
    if season and episode:
        suffix = ":{}:{}".format(season, episode)
    
    res.append({"name": "Premium: AutoEmbed 🚀",  "url": "autoembed://{}:{}{}".format(m_type, tmdb_id, suffix)})
    res.append({"name": "Premium: VidSrc 🔥",     "url": "vidsrc://{}:{}{}".format(m_type, tmdb_id, suffix)})
    return res

# ─── Updated Dispatcher ──────────────────────────────────────────────────────

def resolve_host(url, referer=None):
    """Auto-detect host and resolve to direct stream URL"""
    # 1. Custom URI Schemes
    m = re.match(r'(\w+)://(movie|series|tv|episode):(\d+)(?::(\d+):(\d+))?', url)
    if m:
        method_name, m_type, tmdb_id, season, episode = m.groups()
        m_type = "movie" if m_type in ("movie", "film") else "series"
        if method_name in _PREMIUM_METHODS:
            return _PREMIUM_METHODS[method_name](tmdb_id, m_type, season, episode)
        elif method_name == "auto":
            for name, func in _PREMIUM_METHODS.items():
                try:
                    res = func(tmdb_id, m_type, season, episode)
                    if res: return res
                except: pass
            return None

    # 2. Domain Dispatch
    domain = urlparse(url).netloc.lower()
    log("Resolving host: {} (URL: {})".format(domain, url))
    if "streamruby" in domain:
        return resolve_streamruby(url)
    if "hgcloud" in domain or "masukestin" in domain:
        return resolve_hgcloud(url)

    for key, resolver in HOST_RESOLVERS.items():
        if key in domain:
            log("Using resolver: {}".format(key))
            return resolver(url)
    
    # Generic fallback
    log("Using generic fallback for: {}".format(domain))
    html, final_url = fetch(url, referer=referer or url)
    if not html: 
        log("Generic fallback failed: No HTML")
        return None
    res = find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    if res: 
        log("Generic fallback success: {}".format(res))
        return res
    
    evals = re.findall(r"eval\(function\(p,a,c,k,e,d\).*?}\(.*?\)\)", html, re.S)
    log("Found {} packed scripts".format(len(evals)))
    for ev in evals:
        dec = decode_packer(ev)
        if dec:
            r = find_m3u8(dec) or find_mp4(dec)
            if r: 
                log("Packer success: {}".format(r))
                return r
            
    log("All resolution attempts failed for: {}".format(url))
    return None



def resolve_iframe_chain(url, referer=None, depth=0, max_depth=6):
    """
    Follows a chain of iframes/redirects to find a playable stream.
    Supports src, data-src, data-url attributes.
    """
    if depth > max_depth: return None, ""
    
    html, final_url = fetch(url, referer=referer)
    if not html: return None, ""
    
    domain = urlparse(final_url or url).netloc.lower()
    
    # 1. Check for stream in current HTML
    stream = find_m3u8(html) or find_mp4(html) or find_packed_links(html)
    if stream: return stream, domain
    
    # 2. Look for iframes (src, data-src, data-url)
    iframes = re.findall(r'<(?:iframe|embed|frame)[^>]+(?:src|data-src|data-url)=["\']([^"\']+)["\']', html, re.I)
    for iframe in iframes:
        if iframe.startswith("//"): iframe = "https:" + iframe
        if not iframe.startswith("http"):
            if iframe.startswith("/"):
                p = urlparse(final_url or url)
                iframe = "{}://{}{}".format(p.scheme, p.netloc, iframe)
            else:
                continue
        
        # Avoid common ad iframes or social trackers
        if any(x in iframe.lower() for x in ["facebook", "twitter", "googletag", "ads", "analytics", "doubleclick"]):
            continue
            
        res, h = resolve_iframe_chain(iframe, referer=url, depth=depth+1, max_depth=max_depth)
        if res: return res, h
        
    return None, ""


def extract_stream(url):
    """Standard wrapper for plugin to get (URL, Quality, FinalReferer)"""
    log("--- Starting Extraction for: {} ---".format(url))
    raw_url = (url or "").strip()
    if not raw_url:
        return None, "", url

    piped_headers = {}
    main_url = raw_url
    if "|" in raw_url:
        main_url, raw_headers = raw_url.split("|", 1)
        for part in raw_headers.split("&"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            piped_headers[key.strip()] = value.strip()

    lower_main_url = main_url.lower()
    if main_url.startswith("http") and any(ext in lower_main_url for ext in (".m3u8", ".mp4", ".mkv", ".mp3")):
        referer = piped_headers.get("Referer")
        if not referer:
            parsed = urlparse(main_url)
            referer = "{}://{}/".format(parsed.scheme, parsed.netloc)
        log("Extraction DIRECT URL shortcut: {}".format(main_url))
        q = "1080p" if "1080" in lower_main_url else ("720p" if "720" in lower_main_url else "HD")
        return raw_url, q, referer

    # 1. Resolve host with redirection tracking
    _, final_referer = fetch(main_url, referer=piped_headers.get("Referer"))
    if not final_referer: # Check if fetch itself failed to get a final URL
        return None, "", main_url # Return original URL as referer if no final_referer
        
    stream = resolve_host(main_url, referer=piped_headers.get("Referer"))
    if not stream:
        log("Initial resolve_host failed, trying resolve_iframe_chain")
        # Try recursive chain if domain dispatch failed
        stream, h = resolve_iframe_chain(main_url, referer=piped_headers.get("Referer"), depth=0)
        
    if stream:
        log("Extraction SUCCESS: {}".format(stream))
        q = "1080p" if "1080" in stream else ("720p" if "720" in stream else "HD")
        return stream, q, final_referer
    
    log("Extraction FINAL FAILURE for: {}".format(main_url))
    return None, "", final_referer