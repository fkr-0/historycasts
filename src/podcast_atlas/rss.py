from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import List, Optional
from xml.etree import ElementTree as ET


@dataclass(frozen=True)
class RssPodcast:
    title: str
    link: str
    description: str


@dataclass(frozen=True)
class RssEpisode:
    guid: str
    title: str
    published_at: datetime
    description: str
    audio_url: Optional[str]
    audio_length: Optional[int]
    duration_raw: Optional[str]


def _text(el: Optional[ET.Element]) -> str:
    return (el.text or "").strip() if el is not None else ""


def parse_rss(xml_text: str) -> tuple[RssPodcast, List[RssEpisode]]:
    root = ET.fromstring(xml_text)

    ch = root.find("channel")
    if ch is None:
        raise ValueError("not an RSS 2.0 feed (missing channel)")

    pod = RssPodcast(
        title=_text(ch.find("title")),
        link=_text(ch.find("link")),
        description=_text(ch.find("description")),
    )

    itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

    episodes: List[RssEpisode] = []
    for item in ch.findall("item"):
        title = _text(item.find("title"))
        guid = _text(item.find("guid")) or title
        pub = _text(item.find("pubDate"))
        if not pub:
            raise ValueError(f"missing pubDate for item {guid}")
        published_at = parsedate_to_datetime(pub)

        desc_el = item.find("description")
        # CDATA becomes .text
        description = (desc_el.text or "").strip() if desc_el is not None else ""

        enc = item.find("enclosure")
        audio_url = enc.attrib.get("url") if enc is not None else None
        enc_length = enc.attrib.get("length") if enc is not None else None
        audio_length = int(enc_length) if enc_length else None

        dur = item.find(f"{itunes_ns}duration")
        duration_raw = _text(dur) if dur is not None else None

        episodes.append(
            RssEpisode(
                guid=guid,
                title=title,
                published_at=published_at,
                description=description,
                audio_url=audio_url,
                audio_length=audio_length,
                duration_raw=duration_raw,
            )
        )

    return pod, episodes
