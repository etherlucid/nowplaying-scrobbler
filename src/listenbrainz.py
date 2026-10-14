import json
import sqlite3
import time
import urllib.error
import urllib.request
from .config import QUEUE_DB, ensure_config_dir

API_BASE = "https://api.listenbrainz.org/1"
CLIENT_NAME = "nowplaying-scrobbler"
CLIENT_VERSION = "0.1.0-beta.2"

def validate_token(token):
    token = (token or "").strip()
    if not token:
        return False, "", "Token is empty."

    url = f"{API_BASE}/validate-token"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Token {token}",
            "User-Agent": f"{CLIENT_NAME}/{CLIENT_VERSION}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=6.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("valid") is True:
                return True, data.get("user_name", ""), "Token valid."
            return False, "", data.get("message", "Invalid token.")
    except urllib.error.HTTPError as e:
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            return False, "", err_data.get("message", f"HTTP {e.code}")
        except Exception:
            return False, "", f"HTTP {e.code}"
    except Exception as e:
        return False, "", f"Network error: {e}"

def _build_payload(track, listen_type, listened_at=None):
    album = track.get("album") or track.get("canonical_album") or ""
    metadata = {
        "artist_name": track.get("artist") or "Unknown Artist",
        "track_name": track.get("title") or "Unknown Title",
    }
    if album:
        metadata["release_name"] = album

    additional_info = {
        "submission_client": CLIENT_NAME,
        "submission_client_version": CLIENT_VERSION,
        "media_player": track.get("appName") or "YouTube Music",
        "music_service_name": track.get("appName") or "YouTube Music",
    }
    dur = track.get("duration")
    if dur and dur > 0:
        additional_info["duration_ms"] = int(round(dur * 1000))

    if track.get("recording_mbid"):
        additional_info["recording_mbid"] = track["recording_mbid"]
    if track.get("release_mbid"):
        additional_info["release_mbid"] = track["release_mbid"]
    if track.get("artist_mbids"):
        additional_info["artist_mbids"] = track["artist_mbids"]
    if track.get("origin_url"):
        additional_info["origin_url"] = track["origin_url"]

    metadata["additional_info"] = additional_info

    item = {"track_metadata": metadata}
    if listen_type == "single" and listened_at is not None:
        item["listened_at"] = int(listened_at)

    return {
        "listen_type": listen_type,
        "payload": [item],
    }

def _send_request(token, payload_dict):
    url = f"{API_BASE}/submit-listens"
    body = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{CLIENT_NAME}/{CLIENT_VERSION}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            if resp.status in (200, 201):
                return True, ""
            return False, f"Unexpected status {resp.status}"
    except urllib.error.HTTPError as e:
        msg = f"HTTP {e.code}"
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            msg = err_body.get("error", err_body.get("message", msg))
        except Exception:
            pass
        return False, msg
    except Exception as e:
        return False, str(e)

def submit_playing_now(token, track):
    if not token:
        return False, "No token"
    payload = _build_payload(track, "playing_now")
    return _send_request(token, payload)

def submit_listen(token, track, listened_at=None, queue_on_failure=True):
    if listened_at is None:
        listened_at = int(time.time())

    payload = _build_payload(track, "single", listened_at=listened_at)
    if not token:
        if queue_on_failure:
            enqueue_listen(payload)
        return False, "No token provided, queued locally."

    success, err = _send_request(token, payload)
    if not success:
        if queue_on_failure:
            enqueue_listen(payload)
        return False, err
    return True, ""

# Local SQLite Queue for offline handling
def _get_db():
    ensure_config_dir()
    conn = sqlite3.connect(QUEUE_DB)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_listens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL,
            attempts INTEGER DEFAULT 0
        )
        """
    )
    return conn

def enqueue_listen(payload_dict):
    try:
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO pending_listens (payload, created_at, attempts) VALUES (?, ?, 0)",
                (json.dumps(payload_dict), time.time()),
            )
            conn.commit()
    except Exception as e:
        print(f"Error enqueuing listen: {e}")

def get_queue_count():
    try:
        with _get_db() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM pending_listens")
            row = cur.fetchone()
            return row[0] if row else 0
    except Exception:
        return 0

def flush_queue(token, max_items=25):
    if not token:
        return 0
    flushed = 0
    try:
        with _get_db() as conn:
            cur = conn.execute(
                "SELECT id, payload, attempts FROM pending_listens ORDER BY id ASC LIMIT ?",
                (max_items,),
            )
            rows = cur.fetchall()
            for row_id, payload_str, attempts in rows:
                try:
                    payload = json.loads(payload_str)
                    success, err = _send_request(token, payload)
                    if success:
                        conn.execute("DELETE FROM pending_listens WHERE id = ?", (row_id,))
                        flushed += 1
                    else:
                        if "invalid" in err.lower() or "malformed" in err.lower():
                            # Corrupted or unprocessable, remove so it won't block the queue
                            conn.execute("DELETE FROM pending_listens WHERE id = ?", (row_id,))
                        else:
                            conn.execute(
                                "UPDATE pending_listens SET attempts = attempts + 1 WHERE id = ?",
                                (row_id,),
                            )
                            # Network still down or rate-limited; stop flushing this round
                            break
                except Exception:
                    conn.execute("DELETE FROM pending_listens WHERE id = ?", (row_id,))
            conn.commit()
    except Exception as e:
        print(f"Error flushing queue: {e}")
    return flushed
