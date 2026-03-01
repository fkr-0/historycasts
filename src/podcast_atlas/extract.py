from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence

from .gazetteer import Gazetteer


@dataclass(frozen=True)
class TimeMention:
    kind: str  # 'year' | 'range_year'
    year: Optional[int] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    start: int = 0
    end: int = 0


@dataclass(frozen=True)
class PrimaryTime:
    kind: str  # 'point' | 'range' | 'unknown'
    year: Optional[int] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None


@dataclass(frozen=True)
class LocationMention:
    name: str
    kind: str
    country: str
    lat: float
    lon: float
    start: int
    end: int


def _expand_range_end(start_year: int, end_raw: int) -> int:
    # 1914-18 -> 1918
    if end_raw < 100:
        century = start_year // 100
        return century * 100 + end_raw
    return end_raw


_RANGE_RE = re.compile(r"(?P<y1>\d{3,4})\s*[\-–—]\s*(?P<y2>\d{2,4})")
_YEAR_RE = re.compile(r"\b(?P<y>\d{3,4})\b")
_BC_RE = re.compile(r"\b(?P<y>\d{1,4})\s*(?:v\.?\s*Chr\.?|BC|BCE)\b", re.IGNORECASE)


def extract_time_mentions(text: str) -> List[TimeMention]:
    """Extract year and year-range mentions.

    This is deliberately conservative and schema-stable.
    """
    mentions: List[TimeMention] = []

    range_spans: List[tuple[int, int]] = []
    for m in _RANGE_RE.finditer(text):
        y1 = int(m.group("y1"))
        y2 = int(m.group("y2"))
        y2 = _expand_range_end(y1, y2)
        mentions.append(
            TimeMention(kind="range_year", start_year=y1, end_year=y2, start=m.start(), end=m.end())
        )
        range_spans.append((m.start(), m.end()))

    # BC years (e.g., 44 v. Chr.)
    for m in _BC_RE.finditer(text):
        y = -int(m.group("y"))
        # Avoid duplicates if part of a range span.
        if any(a <= m.start() < b for a, b in range_spans):
            continue
        mentions.append(TimeMention(kind="year", year=y, start=m.start(), end=m.end()))

    # Plain years not inside a range.
    for m in _YEAR_RE.finditer(text):
        if any(a <= m.start() < b for a, b in range_spans):
            continue
        y = int(m.group("y"))
        mentions.append(TimeMention(kind="year", year=y, start=m.start(), end=m.end()))

    return sorted(mentions, key=lambda x: (x.start, x.end))


def pick_primary_time(mentions: Sequence[TimeMention]) -> PrimaryTime:
    # Prefer standalone year mentions over ranges.
    years = [m for m in mentions if m.kind == "year" and m.year is not None]
    if years:
        # pick the first standalone year mention
        y = years[0].year
        return PrimaryTime(kind="point", year=y)

    ranges = [
        m
        for m in mentions
        if m.kind == "range_year" and m.start_year is not None and m.end_year is not None
    ]
    if ranges:
        r = ranges[0]
        return PrimaryTime(kind="range", start_year=r.start_year, end_year=r.end_year)

    return PrimaryTime(kind="unknown")


def extract_locations(text: str, gazetteer: Gazetteer) -> List[LocationMention]:
    hits: List[LocationMention] = []

    # Prefer longer names first to avoid partial matches.
    names = []
    for p in gazetteer.places:
        names.append((p.name, p))
        for a in p.aliases:
            names.append((a, p))
    names.sort(key=lambda t: len(t[0]), reverse=True)

    used_spans: List[tuple[int, int]] = []
    for nm, place in names:
        # word boundary-ish match; allow diacritics and spaces
        pattern = r"\b" + re.escape(nm) + r"\b"
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            span = (m.start(), m.end())
            # avoid overlapping duplicates
            if any(not (span[1] <= a or span[0] >= b) for a, b in used_spans):
                continue
            used_spans.append(span)
            hits.append(
                LocationMention(
                    name=place.name,
                    kind=place.kind,
                    country=place.country,
                    lat=place.lat,
                    lon=place.lon,
                    start=m.start(),
                    end=m.end(),
                )
            )

    return sorted(hits, key=lambda x: (x.start, -(x.end - x.start)))


def pick_primary_location(
    locs: Sequence[LocationMention], *, text: str
) -> Optional[LocationMention]:
    if not locs:
        return None
    # Smallest start position wins
    return sorted(locs, key=lambda x: (x.start, x.end))[0]


# Heuristic name extraction: sequences of capitalized words + optional particles.
_PERSON_RE = re.compile(
    r"\b([A-ZÄÖÜ][a-zäöüß]+\s+(?:(?:von|van|de|del|der|den|da|di)\s+)?[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){0,2})\b"
)

_PERSON_STOP = {
    "Ort",
    "Zeit",
    "Thema",
    "Personen",
    "Kontext",
    "Mehr",
    "Folge",
    "Jahr",
    "Krieg",
    "Revolution",
    "Politik",
    "Frankreich",
    "Deutschland",
}


def extract_persons(text: str) -> List[str]:
    # Strip common labels that would otherwise glue to the first name.
    cleaned = re.sub(
        r"\b(Personen|Person|Guests|Guest|Mitwirkende)\b\s*:?",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    found: List[str] = []
    for m in _PERSON_RE.finditer(cleaned):
        name = m.group(1).strip()
        if any(tok in _PERSON_STOP for tok in name.split()):
            continue
        found.append(name)

    # Keep order, unique
    out: List[str] = []
    seen = set()
    for n in found:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def classify_incident_type(text: str) -> str:
    t = text.lower()

    battle_kw = ["schlacht", "battle", "verdun"]
    if any(k in t for k in battle_kw):
        return "battle"

    if any(k in t for k in ["attentat", "assassination", "mord"]):
        return "assassination"

    if any(
        k in t for k in ["sturmflut", "katastrophe", "disaster", "flut", "hurricane", "earthquake"]
    ):
        return "disaster"

    if any(k in t for k in ["revolution", "proteste", "aufstand", "frühling"]):
        return "revolution"

    if any(k in t for k in ["mauerfall", "wiedervereinigung"]):
        return "political_change"

    if any(k in t for k in ["konflikt", "krieg", "streit", "invasion", "besatzung"]):
        return "conflict"

    if any(k in t for k in ["politik", "regierung", "parlament"]):
        return "politics"

    return "other"


def extract_links(text: str) -> List[str]:
    # Very light URL extraction.
    url_re = re.compile(r"https?://[^\s\]\)<>\"']+")
    return url_re.findall(text)
