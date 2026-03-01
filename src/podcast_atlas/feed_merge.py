from __future__ import annotations

import datetime as dt
import html
import os
import shutil
import sqlite3
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List, Optional


def _parse_pub_date(pub_date: Optional[str]) -> Optional[str]:
    if not pub_date:
        return None
    try:
        dt_obj = parsedate_to_datetime(pub_date)
        if dt_obj.tzinfo:
            dt_obj = dt_obj.astimezone(dt.timezone.utc)
        return dt_obj.isoformat()
    except Exception:
        return None


def _determine_kind(title: str) -> str:
    lower = title.lower()
    if any(k in lower for k in ("spezial", "special", "bonus", "trailer")):
        return "special"
    if any(k in lower for k in ("meta", "update", "ank\u00fcndigung")):
        return "meta"
    return "regular"


def _sanitize_description(text: Optional[str]) -> str:
    if not text:
        return ""
    import re

    unescaped = html.unescape(text)
    cleaned = re.sub(r"<[^>]+>", "", unescaped)
    return cleaned.strip()


def merge_feeds(db_path: Path | str, rss_paths: List[Path | str], out_path: Path | str) -> None:
    """Merge RSS feeds into an existing SQLite DB with podcast/episode dedup."""

    db_path = Path(db_path)
    out_path = Path(out_path)
    normalized_rss = [Path(p) for p in rss_paths]

    if db_path != out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_path, out_path)

    conn = sqlite3.connect(out_path)
    cur = conn.cursor()

    cur.execute("SELECT MAX(id) FROM podcasts")
    max_podcast_id = cur.fetchone()[0] or 0
    cur.execute("SELECT MAX(id) FROM episodes")
    max_episode_id = cur.fetchone()[0] or 0

    cur.execute("SELECT id, feed_url, link, title FROM podcasts")
    podcast_lookup: Dict[str, int] = {}
    for pid, feed_url, link, title in cur.fetchall():
        if feed_url:
            podcast_lookup.setdefault(str(feed_url).strip(), int(pid))
        if link:
            podcast_lookup.setdefault(str(link).strip(), int(pid))
        if title:
            podcast_lookup.setdefault(str(title).strip().lower(), int(pid))

    cur.execute("SELECT guid FROM episodes")
    existing_guids = {row[0] for row in cur.fetchall() if row[0]}

    for rss_path in normalized_rss:
        tree = ET.parse(rss_path)
        root = tree.getroot()
        channel = root.find("channel") or root

        title_elem = channel.find("title")
        desc_elem = channel.find("description")
        link_elem = channel.find("link")
        language_elem = channel.find("language")
        image_elem = channel.find("image")

        podcast_title = (
            title_elem.text.strip() if title_elem is not None and title_elem.text else None
        )
        podcast_desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
        podcast_link = link_elem.text.strip() if link_elem is not None and link_elem.text else None
        podcast_language = (
            language_elem.text.strip() if language_elem is not None and language_elem.text else None
        )

        image_url = None
        if image_elem is not None:
            url_elem = image_elem.find("url")
            if url_elem is not None and url_elem.text:
                image_url = url_elem.text.strip()

        feed_type = os.path.splitext(os.path.basename(rss_path))[-1].lstrip(".")
        existing_pid = None
        for key in [podcast_link, podcast_title.lower() if podcast_title else None, str(rss_path)]:
            if key and key in podcast_lookup:
                existing_pid = podcast_lookup[key]
                break

        if existing_pid is None:
            max_podcast_id += 1
            existing_pid = max_podcast_id
            cur.execute(
                "INSERT INTO podcasts (id, title, description, language, link, image_url, feed_url, feed_type)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (
                    existing_pid,
                    podcast_title or f"Podcast {existing_pid}",
                    podcast_desc,
                    podcast_language,
                    podcast_link,
                    image_url,
                    str(rss_path),
                    feed_type,
                ),
            )
            podcast_lookup[(podcast_title or f"Podcast {existing_pid}").lower()] = existing_pid
            if podcast_link:
                podcast_lookup[podcast_link] = existing_pid
            podcast_lookup[str(rss_path)] = existing_pid

        items = channel.findall("item")
        for item in items:
            guid_elem = item.find("guid")
            guid = guid_elem.text.strip() if guid_elem is not None and guid_elem.text else None
            if guid is None:
                guid = item.findtext("{*}guid")
            if guid is None:
                guid = (item.findtext("link") or "") + (item.findtext("title") or "")
            if guid in existing_guids:
                continue

            existing_guids.add(guid)
            max_episode_id += 1
            title_text = item.findtext("title") or f"Episode {max_episode_id}"
            pub_date_iso = _parse_pub_date(item.findtext("pubDate"))
            description_raw = item.findtext("description") or ""
            description_pure = _sanitize_description(description_raw)

            audio_url = None
            enclosure = item.find("enclosure")
            if enclosure is not None and enclosure.attrib.get("type", "").startswith("audio/"):
                audio_url = enclosure.attrib.get("url")
            media = item.find("{http://search.yahoo.com/mrss/}content")
            if (
                not audio_url
                and media is not None
                and media.attrib.get("type", "").startswith("audio/")
            ):
                audio_url = media.attrib.get("url")

            episode_type = item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}episodeType")
            kind = _determine_kind(title_text)

            cur.execute(
                "INSERT INTO episodes (id, podcast_id, guid, page_url, title, pub_date, duration, audio_url, "
                "episode_type, kind, narrator, description_raw, description_pure, best_span_id, best_place_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    max_episode_id,
                    existing_pid,
                    guid,
                    item.findtext("link"),
                    title_text,
                    pub_date_iso,
                    None,
                    audio_url,
                    episode_type,
                    kind,
                    None,
                    description_raw,
                    description_pure,
                    None,
                    None,
                ),
            )

        conn.commit()

    conn.close()
