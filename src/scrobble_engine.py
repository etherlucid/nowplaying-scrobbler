import hashlib
import time
from .config import load_config
from .listenbrainz import flush_queue, get_queue_count, submit_listen, submit_playing_now
from .player_detector import get_current_playing_track
from .state_file import write_state

def get_track_key(track):
    if not track:
        return ""
    t = (track.get("title") or "").strip().lower()
    a = (track.get("artist") or "").strip().lower()
    al = (track.get("album") or "").strip().lower()
    raw = f"{t}___{a}___{al}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class ScrobbleEngine:
    def __init__(self, logger=None):
        self.logger = logger or (lambda msg: None)
        self.config = load_config()

        # Current track session state
        self.current_key = None
        self.current_track = None
        self.track_start_time = None
        self.accumulated_seconds = 0.0
        self.last_tick_time = time.time()
        self.playing_now_sent = False
        self.scrobbled = False
        self.scrobbled_at = None
        self.last_error = None
        self.last_queue_flush_time = 0

    def log(self, message):
        self.logger(message)

    def reset_track_session(self, new_track=None):
        self.current_track = new_track
        self.current_key = get_track_key(new_track)
        self.track_start_time = time.time() if new_track else None
        self.accumulated_seconds = 0.0
        self.last_tick_time = time.time()
        self.playing_now_sent = False
        self.scrobbled = False
        self.scrobbled_at = None
        self.last_error = None

    def tick(self):
        now = time.time()
        delta = min(3.0, max(0.0, now - self.last_tick_time))
        self.last_tick_time = now

        # Reload config periodically (picks up token or preference changes)
        self.config = load_config()
        token = self.config.get("listenbrainz_token", "").strip()
        enabled = self.config.get("enabled", True)
        threshold_pct = float(self.config.get("scrobble_threshold_pct", 50))
        max_delay = float(self.config.get("max_scrobble_delay_sec", 240))
        min_duration = float(self.config.get("min_track_duration_sec", 30))
        allowed_sources = [s.lower() for s in self.config.get("allowed_sources", [])]

        if not enabled:
            write_state({
                "connected": bool(token),
                "userName": self.config.get("user_name", ""),
                "enabled": False,
                "status": "disabled",
                "track": None,
                "listenProgressPct": 0,
                "scrobbleThresholdPct": threshold_pct,
                "scrobbled": False,
                "scrobbledAt": None,
                "queueCount": get_queue_count(),
                "lastError": None,
            })
            return

        # 1. Fetch current media track
        track = get_current_playing_track()

        # Check source filter
        if track:
            src = track.get("source", "").lower()
            if allowed_sources and src not in allowed_sources and "mediaremote" not in allowed_sources:
                track = None

        track_key = get_track_key(track)

        # 2. Track Change Detection
        if track_key != self.current_key:
            if self.current_track and self.accumulated_seconds > 0:
                self.log(
                    f"Track ended: {self.current_track.get('title')} "
                    f"(listened {round(self.accumulated_seconds, 1)}s, scrobbled: {self.scrobbled})"
                )
            self.reset_track_session(track)
            if track:
                self.log(
                    f"New track detected: {track.get('title')} - {track.get('artist')} "
                    f"[{track.get('appName')}] (duration: {track.get('duration')}s)"
                )

        # 3. If no track is playing
        if not track:
            status_str = "idle"
            write_state({
                "connected": bool(token),
                "userName": self.config.get("user_name", ""),
                "enabled": True,
                "status": status_str,
                "track": None,
                "listenProgressPct": 0,
                "scrobbleThresholdPct": threshold_pct,
                "scrobbled": False,
                "scrobbledAt": None,
                "queueCount": get_queue_count(),
                "lastError": self.last_error,
            })
            return

        is_playing = track.get("rate", 0) > 0
        duration = float(track.get("duration") or 0)

        # 4. Submit playing_now on start
        if is_playing and not self.playing_now_sent and token:
            self.log(f"-> Submitting 'playing_now' to ListenBrainz: {track.get('title')} - {track.get('artist')}")
            ok, err = submit_playing_now(token, track)
            if ok:
                self.playing_now_sent = True
                self.log("   ✓ 'playing_now' accepted by ListenBrainz.")
            else:
                self.log(f"   ⚠️ 'playing_now' error: {err}")
                self.last_error = err

        # 5. Accumulate playback time (only when playing)
        if is_playing:
            self.accumulated_seconds += delta

        # 6. Calculate scrobble target
        if duration > 0:
            target_seconds = min(duration * (threshold_pct / 100.0), max_delay)
        else:
            # Unknown duration fallback
            target_seconds = max_delay

        progress_pct = 0.0
        if target_seconds > 0:
            progress_pct = min(100.0, (self.accumulated_seconds / target_seconds) * 100.0)

        # 7. Check scrobble trigger
        should_scrobble = (
            not self.scrobbled
            and self.accumulated_seconds >= target_seconds
            and (duration == 0 or duration >= min_duration)
        )

        if should_scrobble:
            self.log(
                f"-> Scrobble threshold reached ({round(self.accumulated_seconds)}s / {round(target_seconds)}s). "
                f"Submitting scrobble to ListenBrainz..."
            )
            listened_at = int(self.track_start_time or time.time())
            ok, err = submit_listen(token, track, listened_at=listened_at, queue_on_failure=True)
            if ok:
                self.scrobbled = True
                self.scrobbled_at = time.time()
                self.log(f"   ✓ Scrobbled successfully! [{track.get('title')} - {track.get('artist')}]")
            else:
                self.log(f"   ⚠️ Scrobble failed: {err}")
                self.last_error = err
                # Mark as scrobbled so we don't spam attempts (it's queued locally)
                self.scrobbled = True
                self.scrobbled_at = time.time()

        # 8. Periodically flush queue (every 60s)
        if token and now - self.last_queue_flush_time > 60:
            self.last_queue_flush_time = now
            flushed = flush_queue(token)
            if flushed > 0:
                self.log(f"Flushed {flushed} queued listen(s) to ListenBrainz.")

        # 9. Update state file
        if self.scrobbled:
            status_str = "scrobbled"
        elif not is_playing:
            status_str = "paused"
        elif self.playing_now_sent:
            status_str = "scrobbling"
        else:
            status_str = "playing"

        write_state({
            "connected": bool(token),
            "userName": self.config.get("user_name", ""),
            "enabled": True,
            "status": status_str,
            "track": track,
            "listenProgressPct": round(progress_pct, 1),
            "scrobbleThresholdPct": threshold_pct,
            "scrobbled": self.scrobbled,
            "scrobbledAt": self.scrobbled_at,
            "queueCount": get_queue_count(),
            "lastError": self.last_error,
        })
