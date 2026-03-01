from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import yaml

from .db import Database
from .extract import (
    classify_incident_type,
    extract_links,
    extract_locations,
    extract_persons,
    extract_time_mentions,
    pick_primary_location,
    pick_primary_time,
)
from .gazetteer import Gazetteer
from .podcastde import parse_archive_page, parse_episode_page
from .rss import parse_rss


def _int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _apply_overrides(
    *,
    guid: str,
    overrides: Dict[str, Any],
    incident: str,
    persons: list[str],
    links: list[str],
    primary_time: Any,
    primary_loc: Any,
    gaz: Gazetteer,
):
    """Apply manual overrides for a single episode.

    This keeps ingest_* sources consistent.
    """
    ov = overrides.get(guid) or {}
    if "incident_type" in ov:
        incident = str(ov["incident_type"])

    if "persons" in ov:
        persons = [str(x) for x in (ov.get("persons") or [])]

    if "links" in ov:
        links = [str(x) for x in (ov.get("links") or [])]

    if "primary_time" in ov:
        pt = ov["primary_time"] or {}
        kind = pt.get("kind", primary_time.kind)
        if kind == "point":
            primary_time = type(primary_time)(kind="point", year=_int_or_default(pt.get("year"), 0))
        elif kind == "range":
            primary_time = type(primary_time)(
                kind="range",
                start_year=_int_or_default(pt.get("start_year"), 0),
                end_year=_int_or_default(pt.get("end_year"), 0),
            )

    if "primary_location" in ov:
        pl = ov["primary_location"] or {}
        nm = pl.get("name")
        if nm:
            place = gaz.lookup(nm)
            if place:
                primary_loc = type(primary_loc)(
                    name=place.name,
                    kind=place.kind,
                    country=place.country,
                    lat=place.lat,
                    lon=place.lon,
                    start=0,
                    end=0,
                )

    return incident, persons, links, primary_time, primary_loc


def _ingest_episode(
    db: Database,
    *,
    podcast_id: str,
    feed_url: str,
    guid: str,
    title: str,
    published_at: datetime,
    description: str,
    audio_url: Optional[str],
    audio_length: Optional[int],
    duration_raw: Optional[str],
    gaz: Gazetteer,
    overrides: Dict[str, Any],
):
    text = f"{title}\n\n{description}".strip()

    time_mentions = extract_time_mentions(text)
    primary_time = pick_primary_time(time_mentions)

    locs = extract_locations(text, gaz)
    primary_loc = pick_primary_location(locs, text=text)

    persons = extract_persons(text)
    links = extract_links(description)

    incident = classify_incident_type(text)

    incident, persons, links, primary_time, primary_loc = _apply_overrides(
        guid=guid,
        overrides=overrides,
        incident=incident,
        persons=persons,
        links=links,
        primary_time=primary_time,
        primary_loc=primary_loc,
        gaz=gaz,
    )

    row: Dict[str, Any] = {
        "podcast_id": podcast_id,
        "guid": guid,
        "title": title,
        "published_at": published_at.astimezone().isoformat(),
        "description": description,
        "audio_url": audio_url,
        "audio_length": audio_length,
        "duration_seconds": _duration_to_seconds(duration_raw),
        "incident_type": incident,
        "primary_time_kind": primary_time.kind,
        "primary_time_year": primary_time.year,
        "primary_time_start_year": primary_time.start_year,
        "primary_time_end_year": primary_time.end_year,
        "primary_location_name": getattr(primary_loc, "name", None) if primary_loc else None,
        "primary_location_country": getattr(primary_loc, "country", None) if primary_loc else None,
        "primary_location_lat": getattr(primary_loc, "lat", None) if primary_loc else None,
        "primary_location_lon": getattr(primary_loc, "lon", None) if primary_loc else None,
        "persons_json": json.dumps(persons, ensure_ascii=False),
        "links_json": json.dumps(links, ensure_ascii=False),
    }
    db.upsert_episode(row=row)


def _duration_to_seconds(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    raw = raw.strip()
    # itunes duration can be HH:MM:SS or MM:SS or seconds
    if raw.isdigit():
        return int(raw)
    parts = raw.split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 3:
        h, m, s = nums
        return h * 3600 + m * 60 + s
    if len(nums) == 2:
        m, s = nums
        return m * 60 + s
    return None


def _load_overrides(path: Optional[Path]) -> Dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def ingest_rss_file(
    db: Database,
    *,
    rss_path: Path,
    podcast_id: str,
    feed_url: str,
    overrides_path: Optional[Path] = None,
    gazetteer_path: Path = Path("data/gazetteer.csv"),
) -> None:
    gaz = Gazetteer.from_csv_path(gazetteer_path)
    overrides = _load_overrides(overrides_path)

    xml_text = Path(rss_path).read_text(encoding="utf-8")
    pod, episodes = parse_rss(xml_text)

    db.upsert_podcast(podcast_id=podcast_id, title=pod.title, feed_url=feed_url, link=pod.link)

    for ep in episodes:
        _ingest_episode(
            db,
            podcast_id=podcast_id,
            feed_url=feed_url,
            guid=ep.guid,
            title=ep.title,
            published_at=ep.published_at,
            description=ep.description,
            audio_url=ep.audio_url,
            audio_length=ep.audio_length,
            duration_raw=ep.duration_raw,
            gaz=gaz,
            overrides=overrides,
        )


def _episode_guid_from_url(url: str) -> str:
    m = re.search(r"/episode/(?P<id>\d+)/", url)
    if not m:
        # fall back to a stable hash
        import hashlib

        return "podcastde:" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"podcastde:{m.group('id')}"


def ingest_podcastde_archive(
    db: Database,
    *,
    podcast_id: str,
    feed_url: str,
    archive_url: str,
    overrides_path: Optional[Path] = None,
    gazetteer_path: Path = Path("data/gazetteer.csv"),
    max_pages: int = 10,
    max_episodes: int = 500,
    http_client: Optional[httpx.Client] = None,
) -> None:
    """Ingest episodes by crawling a podcast.de archive page.

    This is intended for *interactive* use on a machine with network access.
    Tests can pass a MockTransport-based client.
    """
    gaz = Gazetteer.from_csv_path(gazetteer_path)
    overrides = _load_overrides(overrides_path)

    close_client = False
    if http_client is None:
        close_client = True
        http_client = httpx.Client(
            headers={
                "User-Agent": "podcast-atlas/0.1 (+https://example.invalid)",
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
        )

    try:
        # We store a very small placeholder podcast record; users can edit later.
        db.upsert_podcast(
            podcast_id=podcast_id, title=podcast_id, feed_url=feed_url, link=archive_url
        )

        page_url = archive_url
        seen_pages = set()
        collected: list[str] = []

        for _ in range(max_pages):
            if page_url in seen_pages:
                break
            seen_pages.add(page_url)
            r = http_client.get(page_url)
            r.raise_for_status()
            pg = parse_archive_page(r.text)
            for u in pg.episode_urls:
                if u not in collected:
                    collected.append(u)
                if len(collected) >= max_episodes:
                    break
            if len(collected) >= max_episodes:
                break
            if not pg.next_page_url:
                break
            page_url = pg.next_page_url

        for u in collected:
            r = http_client.get(u)
            r.raise_for_status()
            guid = _episode_guid_from_url(u)
            ep = parse_episode_page(r.text, default_guid=guid)

            # Map date -> datetime; keep it stable and timezone-aware.
            if ep.published_date is None:
                # fall back to "now"
                published_at = datetime.now().astimezone()
            else:
                published_at = datetime(
                    ep.published_date.year, ep.published_date.month, ep.published_date.day, 12, 0, 0
                ).astimezone()

            _ingest_episode(
                db,
                podcast_id=podcast_id,
                feed_url=feed_url,
                guid=ep.guid,
                title=ep.title,
                published_at=published_at,
                description=ep.description,
                audio_url=ep.audio_url,
                audio_length=None,
                duration_raw=str(ep.duration_seconds) if ep.duration_seconds is not None else None,
                gaz=gaz,
                overrides=overrides,
            )
    finally:
        if close_client:
            http_client.close()
