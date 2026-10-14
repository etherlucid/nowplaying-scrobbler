# nowplaying-scrobbler

> Real-time desktop scrobbler for [ListenBrainz](https://listenbrainz.org/), designed for macOS **YouTube Music Safari PWAs** and system-wide **MediaRemote** playback.

Works where browser extension scrobblers (like Web Scrobbler) fail due to Safari 17/18 PWA sandboxing.

---

## Features

- **Safari PWA First**: Detects and scrobbles music directly from YouTube Music Safari PWAs (`Web App.app`) and WebKit audio sessions.
- **System-Wide Fallback**: Supports Apple Music, Spotify, and any player reporting to macOS `MediaRemote`.
- **ListenBrainz API v1**: Submits `playing_now` on track start and `single` listens upon reaching the standard 50% or 4-minute listen threshold.
- **Ad & Promo Filtering**: Automatically skips YouTube ads, promos, and short non-music audio.
- **Offline Queue**: Safely queues listens locally in SQLite if offline or if ListenBrainz is temporarily unreachable, flushing automatically upon reconnection.
- **Übersicht Widget Integration**: Emits live scrobble state to `/tmp/nowplaying_scrobbler_state.json` for desktop widgets (such as [`uebersicht-now-playing`](https://github.com/etherlucid/uebersicht-now-playing)).
- **Zero Dependencies**: Pure Python 3 standard library. No `pip` or virtualenv requirements.

---

## Installation via Homebrew

```bash
brew tap etherlucid/tap
brew install nowplaying-scrobbler
```

### Background Service (`launchd`)

To start `nowplaying-scrobbler` as an automatic background daemon on login:

```bash
brew services start etherlucid/tap/nowplaying-scrobbler
```

To stop:
```bash
brew services stop etherlucid/tap/nowplaying-scrobbler
```

---

## Quickstart

### 1. Authenticate with ListenBrainz
Grab your User Token from your [ListenBrainz Profile](https://listenbrainz.org/profile/):

```bash
nowplaying-scrobbler auth <YOUR_TOKEN>
```

### 2. Check Status
```bash
nowplaying-scrobbler status
```

Example output:
```text
nowplaying-scrobbler v0.1.0-beta.1
----------------------------------------
ListenBrainz: Connected as @etherlucid ✓
Offline Queue: 0 pending listens (clean)
----------------------------------------
▶ Now Playing: Belize
  Artist:     Danger Mouse & Black Thought
  Album:      Cheat Codes
  Player:     YouTube Music
  Position:   1:45 / 3:54
  Progress:   [========>           ] 45% (target: 50%)
----------------------------------------
```

### 3. Run Manually (Foreground)
```bash
nowplaying-scrobbler run
```

---

## Configuration

Configuration is stored at `~/.config/nowplaying-scrobbler/config.json`:

```json
{
  "listenbrainz_token": "...",
  "user_name": "...",
  "scrobble_threshold_pct": 50,
  "max_scrobble_delay_sec": 240,
  "min_track_duration_sec": 30,
  "filter_ads": true,
  "poll_interval_sec": 1.0,
  "allowed_sources": ["ytmusic", "safari", "music", "spotify", "mediaremote"]
}
```

---

## License

MIT © [etherlucid](https://github.com/etherlucid)
