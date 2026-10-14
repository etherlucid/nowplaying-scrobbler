import json
import os
import time

STATE_FILE = "/tmp/nowplaying_scrobbler_state.json"

def write_state(state_dict):
    state_dict["updatedAt"] = time.time()
    tmp_path = f"{STATE_FILE}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2)
        os.replace(tmp_path, STATE_FILE)
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

def read_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None
