import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from .config import CONFIG_DIR, ensure_config_dir
from .metadata_filter import clean_album_name, clean_artist_name, clean_track_title

CACHE_FILE = os.path.join(CONFIG_DIR, "mb_cache.json")
_MEM_CACHE = {}

def _load_cache():
    global _MEM_CACHE
    if _MEM_CACHE:
        return _MEM_CACHE
    ensure_config_dir()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _MEM_CACHE = json.load(f)
        except Exception:
            _MEM_CACHE = {}
    return _MEM_CACHE

def _save_cache():
    ensure_config_dir()
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_MEM_CACHE, f, indent=2)
    except Exception:
        pass

def _make_cache_key(title, artist, album):
    t = (title or "").strip().lower()
    a = (artist or "").strip().lower()
    al = (album or "").strip().lower()
    return f"{t}___{a}___{al}"

def lookup_metadata(token, title, artist, album=""):
    """
    Looks up canonical MusicBrainz MBIDs (recording, release, artists)
    using ListenBrainz metadata lookup service first, with MusicBrainz WS API fallback.
    """
    clean_title = clean_track_title(title)
    clean_artist = clean_artist_name(artist)
    clean_album = clean_album_name(album)

    if not clean_title or not clean_artist:
        return None

    cache = _load_cache()
    ckey = _make_cache_key(clean_title, clean_artist, clean_album)
    if ckey in cache:
        return cache[ckey]

    result = None

    # 1. Primary: ListenBrainz Metadata Lookup API
    if token:
        params = {
            "artist_name": clean_artist,
            "recording_name": clean_title,
        }
        if clean_album:
            params["release_name"] = clean_album

        url = f"https://api.listenbrainz.org/1/metadata/lookup/?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Token {token}",
                "User-Agent": "nowplaying-scrobbler/0.1.0-beta.2 (https://github.com/etherlucid/nowplaying-scrobbler)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                rec_mbid = data.get("recording_mbid")
                if rec_mbid:
                    result = {
                        "recording_mbid": rec_mbid,
                        "release_mbid": data.get("release_mbid"),
                        "artist_mbids": data.get("artist_mbids") or [],
                        "canonical_title": data.get("recording_name") or clean_title,
                        "canonical_artist": data.get("artist_credit_name") or clean_artist,
                        "canonical_album": data.get("release_name") or clean_album,
                        "source": "listenbrainz_lookup",
                    }
        except Exception:
            pass

    # 2. Secondary: Direct MusicBrainz Web Service 2 Search Fallback
    if not result:
        # Quote query terms
        q = f'recording:"{clean_title}" AND artist:"{clean_artist}"'
        url = f"https://musicbrainz.org/ws/2/recording?query={urllib.parse.quote(q)}&fmt=json&limit=1"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "nowplaying-scrobbler/0.1.0-beta.2 (etherlucid@users.noreply.github.com)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                recordings = data.get("recordings", [])
                if recordings:
                    rec = recordings[0]
                    rec_mbid = rec.get("id")
                    artist_mbids = []
                    for ac in rec.get("artist-credit", []):
                        if isinstance(ac, dict) and ac.get("artist", {}).get("id"):
                            artist_mbids.append(ac["artist"]["id"])

                    rel_mbid = None
                    rel_name = clean_album
                    releases = rec.get("releases", [])
                    if releases:
                        rel_mbid = releases[0].get("id")
                        if not rel_name:
                            rel_name = releases[0].get("title", "")

                    if rec_mbid:
                        result = {
                            "recording_mbid": rec_mbid,
                            "release_mbid": rel_mbid,
                            "artist_mbids": artist_mbids,
                            "canonical_title": rec.get("title") or clean_title,
                            "canonical_artist": clean_artist,
                            "canonical_album": rel_name or clean_album,
                            "source": "musicbrainz_search",
                        }
        except Exception:
            pass

    # Cache result (even if None, to avoid re-querying failed lookups constantly)
    cache[ckey] = result
    _save_cache()
    return result
