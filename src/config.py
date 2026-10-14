import os
import json

CONFIG_DIR = os.path.expanduser("~/.config/nowplaying-scrobbler")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
QUEUE_DB = os.path.join(CONFIG_DIR, "queue.db")

DEFAULT_CONFIG = {
    "listenbrainz_token": "",
    "user_name": "",
    "scrobble_threshold_pct": 50,
    "max_scrobble_delay_sec": 240,
    "min_track_duration_sec": 30,
    "filter_ads": True,
    "poll_interval_sec": 1.0,
    "allowed_sources": ["ytmusic", "safari", "music", "spotify", "mediaremote"],
    "enabled": True,
}

def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
        except Exception:
            pass

def load_config():
    ensure_config_dir()
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    config.update(saved)
        except Exception:
            pass
    return config

def save_config(config):
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        os.chmod(CONFIG_FILE, 0o600)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
