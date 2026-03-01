from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class GazetteerEntry:
    canonical_name: str
    kind: str  # city|region|country|unknown
    lat: float
    lon: float
    radius_km: float
    aliases: tuple[str, ...]


def norm_key(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[\s\-_/]+", " ", s)
    s = re.sub(r"[^a-z0-9äöüß ]+", "", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s


class Gazetteer:
    def __init__(self, entries: Iterable[GazetteerEntry]):
        self._by_key: dict[str, GazetteerEntry] = {}
        for e in entries:
            self._by_key[norm_key(e.canonical_name)] = e
            for a in e.aliases:
                if a.strip():
                    self._by_key[norm_key(a)] = e

    def lookup(self, name: str) -> Optional[GazetteerEntry]:
        return self._by_key.get(norm_key(name))


def load_gazetteer_csv(path: str) -> Gazetteer:
    p = Path(path)
    entries: list[GazetteerEntry] = []
    with p.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            kind = (row.get("kind") or "unknown").strip() or "unknown"
            lat = float(row.get("lat") or 0.0)
            lon = float(row.get("lon") or 0.0)
            radius = float(row.get("radius_km") or 50.0)
            aliases = tuple((row.get("aliases") or "").split("|"))
            entries.append(GazetteerEntry(name, kind, lat, lon, radius, aliases))
    return Gazetteer(entries)
