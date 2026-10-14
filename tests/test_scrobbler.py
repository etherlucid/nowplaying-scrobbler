import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.listenbrainz import _build_payload, validate_token
from src.player_detector import is_ad
from src.scrobble_engine import get_track_key

class TestScrobbler(unittest.TestCase):
    def test_build_payload_playing_now(self):
        track = {
            "title": "Belize",
            "artist": "Danger Mouse & Black Thought",
            "album": "Cheat Codes",
            "duration": 234.0,
            "appName": "YouTube Music",
        }
        payload = _build_payload(track, "playing_now")
        self.assertEqual(payload["listen_type"], "playing_now")
        meta = payload["payload"][0]["track_metadata"]
        self.assertEqual(meta["track_name"], "Belize")
        self.assertEqual(meta["artist_name"], "Danger Mouse & Black Thought")
        self.assertEqual(meta["release_name"], "Cheat Codes")
        self.assertEqual(meta["additional_info"]["duration_ms"], 234000)
        self.assertEqual(meta["additional_info"]["media_player"], "YouTube Music")

    def test_build_payload_single(self):
        track = {
            "title": "Song",
            "artist": "Artist",
            "duration": 180.0,
        }
        payload = _build_payload(track, "single", listened_at=1700000000)
        self.assertEqual(payload["listen_type"], "single")
        self.assertEqual(payload["payload"][0]["listened_at"], 1700000000)

    def test_ad_detection(self):
        self.assertTrue(is_ad({"title": "Advertisement", "duration": 30}))
        self.assertTrue(is_ad({"title": "audio ad", "duration": 15}))
        self.assertTrue(is_ad({"title": "Promo", "artist": "", "duration": 10}))
        self.assertTrue(is_ad({"title": "Short Clip", "duration": 3}))
        self.assertFalse(is_ad({"title": "Real Song", "artist": "Real Artist", "duration": 200}))

    def test_track_key_stability(self):
        k1 = get_track_key({"title": "Song", "artist": "Artist", "album": "Album"})
        k2 = get_track_key({"title": "song ", "artist": " artist", "album": "album"})
        self.assertEqual(k1, k2)

if __name__ == "__main__":
    unittest.main()
