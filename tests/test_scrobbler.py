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

    def test_build_payload_with_mbids(self):
        track = {
            "title": "Belize",
            "artist": "Danger Mouse & Black Thought",
            "album": "Cheat Codes",
            "duration": 234.0,
            "recording_mbid": "6683a6fa-5549-48b5-beb3-f09ab93ff94e",
            "release_mbid": "80a62cc0-1872-4c68-ba48-73d63c208ac3",
            "artist_mbids": ["4b356f05-bcc2-4544-925b-fd9a1bf708be"],
        }
        payload = _build_payload(track, "single", listened_at=1700000000)
        add_info = payload["payload"][0]["track_metadata"]["additional_info"]
        self.assertEqual(add_info["recording_mbid"], "6683a6fa-5549-48b5-beb3-f09ab93ff94e")
        self.assertEqual(add_info["release_mbid"], "80a62cc0-1872-4c68-ba48-73d63c208ac3")
        self.assertEqual(add_info["artist_mbids"], ["4b356f05-bcc2-4544-925b-fd9a1bf708be"])

    def test_metadata_cleaning(self):
        from src.metadata_filter import clean_artist_name, clean_track_title, split_artist_track

        self.assertEqual(clean_track_title("Belize (Official Music Video)"), "Belize")
        self.assertEqual(clean_track_title("Song Name [Official Audio]"), "Song Name")
        self.assertEqual(clean_track_title("Track (Remastered 2021)"), "Track")
        self.assertEqual(clean_track_title("Live Track (Live at Wembley)"), "Live Track")
        self.assertEqual(clean_artist_name("Danger Mouse - Topic"), "Danger Mouse")

        a, t = split_artist_track("Mos Def - Ms. Fat Booty")
        self.assertEqual(a, "Mos Def")
        self.assertEqual(t, "Ms. Fat Booty")

if __name__ == "__main__":
    unittest.main()
