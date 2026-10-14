import re

# Regex rules ported from Web Scrobbler's @web-scrobbler/metadata-filter
# and YouTube video title parser

YOUTUBE_NOISE_PATTERNS = [
    # (Official Video), (Official Music Video), [Official Audio], etc.
    re.compile(r"[\(\[\{]\s*(?:official\s*(?:music\s*)?video|official\s*audio|official|music\s*video|audio|mv|pv|visualizer|lyrics?|lyric\s*video|hd|4k)\s*[\)\]\}]", re.IGNORECASE),
    # Ending MV / PV tags
    re.compile(r"\s+(?:official\s*video|music\s*video|mv|pv)$", re.IGNORECASE),
    # [Genre] or 【Genre】 prefix
    re.compile(r"^(?:\[[^\]]+\]|【[^】]+】)\s*-*\s*", re.IGNORECASE),
]

REMASTER_PATTERNS = [
    re.compile(r"[\(\[\{]\s*(?:\d{4}\s*)?remaster(?:ed)?(?:\s*\d{4})?\s*[\)\]\}]", re.IGNORECASE),
    re.compile(r"[\(\[\{]\s*(?:deluxe|anniversary|expanded|special)\s*(?:edition|version)?\s*[\)\]\}]", re.IGNORECASE),
]

VERSION_PATTERNS = [
    re.compile(r"[\(\[\{]\s*(?:album\s*version|radio\s*edit|single\s*version|original\s*mix)\s*[\)\]\}]", re.IGNORECASE),
]

LIVE_PATTERNS = [
    re.compile(r"[\(\[\{]\s*live(?:\s+at[^)\]\}]+)?\s*[\)\]\}]", re.IGNORECASE),
]

def clean_track_title(title):
    if not title:
        return ""
    t = str(title).strip()

    # Apply noise filters
    for p in YOUTUBE_NOISE_PATTERNS:
        t = p.sub("", t)
    for p in REMASTER_PATTERNS:
        t = p.sub("", t)
    for p in VERSION_PATTERNS:
        t = p.sub("", t)
    for p in LIVE_PATTERNS:
        t = p.sub("", t)

    # Collapse multiple spaces and clean dangling separators
    t = re.sub(r"\s+", " ", t).strip(" \t\n\r-\"\'")
    return t

def clean_artist_name(artist):
    if not artist:
        return ""
    a = str(artist).strip()
    # Strip " - Topic" appended by YouTube auto-generated artist channels
    a = re.sub(r"\s+-\s*topic$", "", a, flags=re.IGNORECASE)
    # Collapse multiple spaces
    a = re.sub(r"\s+", " ", a).strip(" \t\n\r-\"\'")
    return a

def clean_album_name(album):
    if not album:
        return ""
    al = str(album).strip()
    for p in REMASTER_PATTERNS:
        al = p.sub("", al)
    al = re.sub(r"\s+", " ", al).strip(" \t\n\r-\"\'")
    return al

def split_artist_track(title):
    """
    If title is in 'Artist - Track' format (common in raw YouTube videos),
    attempts to split it into artist and track.
    """
    if not title or " - " not in title:
        return None, title
    parts = title.split(" - ", 1)
    return parts[0].strip(), parts[1].strip()
