from __future__ import annotations

"""podcast.de HTML helpers.

Why this module exists:

Some publishers expose RSS feeds that are difficult to fetch from automated
environments (WAFs, header requirements, etc.). podcast.de often mirrors those
shows and exposes stable episode pages containing:

* A direct MP3 download link (usually on podcast-mp3.dradio.de for DLF shows)
* Human-readable duration ("45 Minuten")
* A description block

This module provides:

* Parsing helpers (pure functions, easy to test)
* A tiny scraper (optional) that can be used in a CLI command on a machine
  with network access.
"""

import re
from dataclasses import dataclass
from datetime import date
from html import unescape
from typing import List, Optional

_MP3_RE = re.compile(
    r"https://podcast-mp3\.dradio\.de/[^\s\"'>]+?\.mp3(?:\?[^\s\"'>]+)?",
    flags=re.IGNORECASE,
)

_EP_URL_RE = re.compile(r"https://www\.podcast\.de/episode/\d+/[^\s\"'>]+", flags=re.IGNORECASE)

_NEXT_RE = re.compile(r"<a[^>]+rel=\"next\"[^>]+href=\"(?P<href>[^\"]+)\"", flags=re.IGNORECASE)

_H1_RE = re.compile(r"<h1[^>]*>(?P<t>.*?)</h1>", flags=re.IGNORECASE | re.DOTALL)

_OG_TITLE_RE = re.compile(
    r"<meta[^>]+property=\"og:title\"[^>]+content=\"(?P<t>[^\"]+)\"",
    flags=re.IGNORECASE,
)

_OG_DESC_RE = re.compile(
    r"<meta[^>]+property=\"og:description\"[^>]+content=\"(?P<d>[^\"]+)\"",
    flags=re.IGNORECASE,
)

_DESC_DIV_RE = re.compile(
    r"<div[^>]+class=\"desc\"[^>]*>(?P<d>.*?)</div>", flags=re.IGNORECASE | re.DOTALL
)

_DDMMYYYY_RE = re.compile(r"\b(?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4})\b")

_MINUTES_RE = re.compile(r"\b(?P<m>\d{1,3})\s*Minuten\b", flags=re.IGNORECASE)

_URL_DATE_RE = re.compile(r"/podcast/(?P<y>\d{4})/(?P<m>\d{2})/(?P<d>\d{2})/", flags=re.IGNORECASE)


def _strip_tags(s: str) -> str:
    # Minimal tag stripper for our small fixtures; we keep it conservative.
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass(frozen=True)
class PodcastDeEpisode:
    guid: str
    title: str
    published_date: Optional[date]
    duration_seconds: Optional[int]
    description: str
    audio_url: Optional[str]


@dataclass(frozen=True)
class PodcastDeArchivePage:
    episode_urls: List[str]
    next_page_url: Optional[str]


def parse_episode_page(html: str, *, default_guid: str) -> PodcastDeEpisode:
    """Parse a podcast.de episode HTML page.

    The parser is intentionally resilient and uses simple fallbacks:
    - Title: og:title -> first h1 -> "(unknown)"
    - Description: og:description -> stripped first 2000 chars of body
    - Published date: dd.mm.yyyy anywhere in page -> derive from MP3 URL path
    - Audio URL: first podcast-mp3.dradio.de mp3 match
    - Duration: "NN Minuten" -> seconds
    """

    m = _OG_TITLE_RE.search(html)
    if m:
        title = m.group("t").strip()
    else:
        mh1 = _H1_RE.search(html)
        title = _strip_tags(mh1.group("t")) if mh1 else "(unknown)"

    # Description: prefer explicit description blocks if present.
    mdv = _DESC_DIV_RE.search(html)
    if mdv:
        desc = _strip_tags(mdv.group("d"))
    else:
        md = _OG_DESC_RE.search(html)
        if md:
            desc = md.group("d").strip()
        else:
            # fallback: strip tags from full page (bounded)
            desc = _strip_tags(html)[:2000]

    mp3 = None
    mm = _MP3_RE.search(html)
    if mm:
        mp3 = mm.group(0)

    # Duration
    dur_s: Optional[int] = None
    dm = _MINUTES_RE.search(html)
    if dm:
        dur_s = int(dm.group("m")) * 60

    # Published date
    pub: Optional[date] = None
    pd = _DDMMYYYY_RE.search(html)
    if pd:
        pub = date(int(pd.group("y")), int(pd.group("m")), int(pd.group("d")))
    else:
        if mp3:
            mdp = _URL_DATE_RE.search(mp3)
            if mdp:
                pub = date(int(mdp.group("y")), int(mdp.group("m")), int(mdp.group("d")))

    return PodcastDeEpisode(
        guid=default_guid,
        title=title,
        published_date=pub,
        duration_seconds=dur_s,
        description=desc,
        audio_url=mp3,
    )


def parse_archive_page(html: str) -> PodcastDeArchivePage:
    episode_urls = sorted(set(_EP_URL_RE.findall(html)))

    next_page = None
    m = _NEXT_RE.search(html)
    if m:
        next_page = unescape(m.group("href"))

    return PodcastDeArchivePage(episode_urls=episode_urls, next_page_url=next_page)
