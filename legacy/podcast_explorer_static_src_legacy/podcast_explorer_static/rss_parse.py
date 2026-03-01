from __future__ import annotations

import datetime as dt
import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional, Iterator

try:
    from dateutil import parser as du_parser  # type: ignore
except Exception:
    du_parser = None


NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "media": "http://search.yahoo.com/mrss/",
}


@dataclass
class PodcastInfo:
    title: str
    description: str
    language: str
    link: str
    image_url: str
    feed_url: str
    feed_type: str


@dataclass
class EpisodeItem:
    guid: str
    page_url: str
    title: str
    pub_date: dt.datetime
    duration_sec: Optional[int]
    audio_url: Optional[str]
    episode_type: Optional[str]
    author: Optional[str]
    description_raw: str


_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_P_RE = re.compile(r"</p\s*>", re.IGNORECASE)


def _text(elem: Optional[ET.Element]) -> str:
    return (elem.text or "").strip() if elem is not None else ""


def _parse_pubdate(s: str) -> dt.datetime:
    s = s.strip()
    if not s:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    if du_parser:
        try:
            return du_parser.parse(s)
        except Exception:
            pass
    # best-effort fallback
    for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"]:
        try:
            return dt.datetime.strptime(s, fmt)
        except Exception:
            continue
    return dt.datetime.min.replace(tzinfo=dt.timezone.utc)


def _parse_duration(s: str) -> Optional[int]:
    s = (s or "").strip()
    if not s:
        return None
    if re.fullmatch(r"\d+", s):
        return int(s)
    parts = s.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except Exception:
        return None
    return None


def html_to_text(s: str) -> str:
    """Convert HTML-ish CDATA to readable text with paragraph-ish newlines."""
    if not s:
        return ""
    s = html.unescape(s)
    s = _BR_RE.sub("\n", s)
    s = _P_RE.sub("\n", s)
    s = _TAG_RE.sub("", s)
    # collapse excessive whitespace
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def parse_rss(
    path: str, feed_url: Optional[str] = None
) -> tuple[PodcastInfo, Iterator[EpisodeItem]]:
    tree = ET.parse(path)
    root = tree.getroot()
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS has no channel")

    title = _text(channel.find("title"))
    description = html_to_text(_text(channel.find("description")))
    language = _text(channel.find("language"))
    link = _text(channel.find("link"))
    image_url = _text(channel.find("image/url"))
    if not image_url:
        img = channel.find("itunes:image", NS)
        if img is not None:
            image_url = (img.attrib.get("href") or "").strip()

    # feed_url: prefer atom self
    if feed_url is None:
        atom_self = channel.find("atom:link[@rel='self']", NS)
        feed_url = (atom_self.attrib.get("href") if atom_self is not None else None) or path

    info = PodcastInfo(
        title=title,
        description=description,
        language=language,
        link=link,
        image_url=image_url,
        feed_url=str(feed_url),
        feed_type="rss",
    )

    def _items() -> Iterator[EpisodeItem]:
        for item in channel.findall("item"):
            title_i = _text(item.find("title"))
            page_url = _text(item.find("link"))
            guid = _text(item.find("guid")) or page_url or title_i
            pub_date = _parse_pubdate(_text(item.find("pubDate")))

            # best description: prefer content:encoded when present
            raw = _text(item.find("content:encoded", NS))
            if not raw:
                raw = _text(item.find("description"))

            # enclosure audio url
            audio_url = None
            enc = item.find("enclosure")
            if enc is not None:
                audio_url = (enc.attrib.get("url") or "").strip() or None

            # itunes duration
            duration = _parse_duration(_text(item.find("itunes:duration", NS)))

            episode_type = _text(item.find("itunes:episodeType", NS)) or None
            author = _text(item.find("itunes:author", NS)) or None

            yield EpisodeItem(
                guid=guid,
                page_url=page_url,
                title=title_i,
                pub_date=pub_date,
                duration_sec=duration,
                audio_url=audio_url,
                episode_type=episode_type,
                author=author,
                description_raw=raw,
            )

    return info, _items()
