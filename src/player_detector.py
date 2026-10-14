import json
import os
import shutil
import subprocess
import time

def is_process_running(proc_name):
    try:
        res = subprocess.run(["pgrep", "-x", proc_name], capture_output=True, timeout=0.5)
        return res.returncode == 0
    except Exception:
        return False

def find_nowplaying_cli():
    paths = [
        "/opt/homebrew/bin/nowplaying-cli",
        "/usr/local/bin/nowplaying-cli",
    ]
    for p in paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    which_p = shutil.which("nowplaying-cli")
    if which_p:
        return which_p
    return "/opt/homebrew/bin/nowplaying-cli"

def get_nowplaying_raw():
    cli = find_nowplaying_cli()
    if not os.path.exists(cli) and not shutil.which(cli):
        return None

    try:
        proc = subprocess.run(
            [cli, "get-raw"],
            capture_output=True,
            text=True,
            timeout=1.5,
        )
        stdout = proc.stdout.strip()
        if not stdout or stdout == "null":
            return None
        return json.loads(stdout)
    except Exception:
        return None

def get_ytmusic_direct_stream():
    if not is_process_running("Web App"):
        return None

    script = """
tell application "System Events"
  try
    tell process "Web App"
      set w to window 1
      set winTitle to name of w
      set s to first UI element of w whose role is "AXSplitGroup"
      set tb to first UI element of s whose role is "AXTabGroup"
      set g1 to first UI element of tb whose role is "AXGroup"
      set g2 to first UI element of g1 whose role is "AXGroup"
      set sa to first UI element of g2 whose role is "AXScrollArea"
      set wa to first UI element of sa whose role is "AXWebArea"
      set pb to first UI element of wa whose description is "Player bar"
      set t to title of UI element 12 of pb
      set a to title of UI element 15 of pb
      set tm to value of UI element 10 of pb
      set pp to title of UI element 4 of pb
      return (t & "|||" & a & "|||" & tm & "|||" & pp & "|||" & winTitle)
    end tell
  on error
    return "none"
  end try
end tell
"""
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
        out = res.stdout.strip()
        if "|||" in out:
            parts = out.split("|||")
            title = parts[0].strip()
            artist = parts[1].strip() if len(parts) > 1 else ""
            time_str = parts[2].strip() if len(parts) > 2 else ""
            pp_title = parts[3].strip() if len(parts) > 3 else "Play"
            win_title = parts[4].strip() if len(parts) > 4 else ""

            if not title and " | YouTube Music" in win_title:
                title = win_title.replace(" | YouTube Music", "").strip()

            if not title:
                return None

            elapsed = 0.0
            duration = 0.0
            if " / " in time_str:
                e_str, d_str = time_str.split(" / ", 1)
                try:
                    e_parts = [float(x) for x in e_str.split(":")]
                    elapsed = e_parts[0] * 60 + e_parts[1] if len(e_parts) == 2 else e_parts[0]
                    d_parts = [float(x) for x in d_str.split(":")]
                    duration = d_parts[0] * 60 + d_parts[1] if len(d_parts) == 2 else d_parts[0]
                except Exception:
                    pass

            rate = 1 if pp_title.lower() == "pause" else 0

            return {
                "id": "ytmusic",
                "title": title,
                "artist": artist,
                "album": "",
                "duration": round(duration, 1),
                "elapsed": round(elapsed, 1),
                "rate": rate,
                "bundleId": "com.apple.Safari.WebApp",
                "appName": "YouTube Music",
                "source": "ytmusic",
                "detectedAt": time.time(),
            }
    except Exception:
        pass
    return None

def get_apple_music_stream():
    if not is_process_running("Music"):
        return None
    script = """
tell application "Music"
    if player state is playing or player state is paused then
        set t to name of current track
        set a to artist of current track
        set al to album of current track
        set d to duration of current track
        set e to player position
        set s to player state as string
        return (t & "|||" & a & "|||" & al & "|||" & d & "|||" & e & "|||" & s)
    end if
    return "none"
end tell
"""
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
        out = res.stdout.strip()
        if "|||" in out:
            parts = out.split("|||")
            return {
                "id": "apple_music",
                "title": parts[0].strip(),
                "artist": parts[1].strip() if len(parts) > 1 else "",
                "album": parts[2].strip() if len(parts) > 2 else "",
                "duration": round(float(parts[3]), 1) if len(parts) > 3 and parts[3] else 0.0,
                "elapsed": round(float(parts[4]), 1) if len(parts) > 4 and parts[4] else 0.0,
                "rate": 1 if len(parts) > 5 and parts[5].lower() == "playing" else 0,
                "bundleId": "com.apple.Music",
                "appName": "Apple Music",
                "source": "music",
                "detectedAt": time.time(),
            }
    except Exception:
        pass
    return None

def get_spotify_stream():
    if not is_process_running("Spotify"):
        return None
    script = """
tell application "Spotify"
    if player state is playing or player state is paused then
        set t to name of current track
        set a to artist of current track
        set al to album of current track
        set d to (duration of current track) / 1000
        set e to player position
        set s to player state as string
        return (t & "|||" & a & "|||" & al & "|||" & d & "|||" & e & "|||" & s)
    end if
    return "none"
end tell
"""
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1.5)
        out = res.stdout.strip()
        if "|||" in out:
            parts = out.split("|||")
            return {
                "id": "spotify",
                "title": parts[0].strip(),
                "artist": parts[1].strip() if len(parts) > 1 else "",
                "album": parts[2].strip() if len(parts) > 2 else "",
                "duration": round(float(parts[3]), 1) if len(parts) > 3 and parts[3] else 0.0,
                "elapsed": round(float(parts[4]), 1) if len(parts) > 4 and parts[4] else 0.0,
                "rate": 1 if len(parts) > 5 and parts[5].lower() == "playing" else 0,
                "bundleId": "com.spotify.client",
                "appName": "Spotify",
                "source": "spotify",
                "detectedAt": time.time(),
            }
    except Exception:
        pass
    return None

def is_ad(track):
    if not track:
        return False
    title = (track.get("title") or "").strip().lower()
    artist = (track.get("artist") or "").strip().lower()
    dur = track.get("duration") or 0

    if title in ("advertisement", "ad", "audio ad"):
        return True
    if dur > 0 and dur < 5:
        return True
    # YouTube video ad titles often have no artist or generic names
    if not artist and ("advertisement" in title or "promo" in title):
        return True
    return False

def get_current_playing_track():
    """
    Returns the currently active playing track, prioritizing YouTube Music Safari PWA
    and MediaRemote, with Apple Music and Spotify fallbacks.
    """
    # 1. Primary: MediaRemote via nowplaying-cli
    mr_data = get_nowplaying_raw()
    if mr_data:
        title = (mr_data.get("kMRMediaRemoteNowPlayingInfoTitle") or "").strip()
        artist = (mr_data.get("kMRMediaRemoteNowPlayingInfoArtist") or "").strip()
        album = (mr_data.get("kMRMediaRemoteNowPlayingInfoAlbum") or "").strip()
        duration = float(mr_data.get("kMRMediaRemoteNowPlayingInfoDuration") or 0)
        elapsed = float(mr_data.get("kMRMediaRemoteNowPlayingInfoElapsedTime") or 0)
        rate = int(mr_data.get("kMRMediaRemoteNowPlayingInfoPlaybackRate") or 0)
        bundle_id = (mr_data.get("kMRMediaRemoteNowPlayingInfoClientBundleIdentifier") or "").strip()

        b_lower = bundle_id.lower()
        if "safari.webapp" in b_lower or ("webkit" in b_lower and is_process_running("Web App")):
            app_name = "YouTube Music"
            source_id = "ytmusic"
        elif "apple.music" in b_lower:
            app_name = "Apple Music"
            source_id = "music"
        elif "spotify" in b_lower:
            app_name = "Spotify"
            source_id = "spotify"
        elif "safari" in b_lower:
            app_name = "Safari"
            source_id = "safari"
        elif "chrome" in b_lower:
            app_name = "Google Chrome"
            source_id = "chrome"
        else:
            app_name = bundle_id or "Media Player"
            source_id = "mediaremote"

        if title:
            track = {
                "id": source_id,
                "title": title,
                "artist": artist,
                "album": album,
                "duration": round(duration, 1),
                "elapsed": round(elapsed, 1),
                "rate": rate,
                "bundleId": bundle_id,
                "appName": app_name,
                "source": source_id,
                "detectedAt": time.time(),
            }
            if not is_ad(track):
                return track

    # 2. Fallback: YouTube Music direct accessibility extraction if MediaRemote was empty
    yt_direct = get_ytmusic_direct_stream()
    if yt_direct and yt_direct.get("title") and not is_ad(yt_direct):
        return yt_direct

    # 3. Fallback: Spotify AppleScript
    spot = get_spotify_stream()
    if spot and spot.get("title") and not is_ad(spot):
        return spot

    # 4. Fallback: Apple Music AppleScript
    am = get_apple_music_stream()
    if am and am.get("title") and not is_ad(am):
        return am

    return None
