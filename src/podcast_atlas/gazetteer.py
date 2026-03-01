from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class Place:
    name: str
    kind: str
    country: str
    lat: float
    lon: float
    aliases: Tuple[str, ...] = ()


class Gazetteer:
    """Very small offline gazetteer.

    It is intentionally tiny and deterministic. Users can extend it by editing CSV.
    """

    def __init__(self, places: List[Place]):
        self._places = places
        self._name_to_place: Dict[str, Place] = {}
        self._token_map: Dict[str, Set[str]] = {}

        for p in places:
            for nm in {p.name, *p.aliases}:
                self._name_to_place[nm.lower()] = p
                self._token_map.setdefault(nm.lower(), set()).add(p.name)

    @property
    def places(self) -> List[Place]:
        return list(self._places)

    def lookup(self, name: str) -> Optional[Place]:
        return self._name_to_place.get(name.lower())

    def all_names(self) -> Set[str]:
        return {p.name for p in self._places}

    @classmethod
    def from_csv_path(cls, path: str | Path) -> "Gazetteer":
        import csv

        p = Path(path)
        rows: List[Place] = []
        with p.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                aliases = tuple(a.strip() for a in (r.get("aliases") or "").split(",") if a.strip())
                rows.append(
                    Place(
                        name=r["name"],
                        kind=r.get("kind") or "unknown",
                        country=r.get("country") or "",
                        lat=float(r["lat"]),
                        lon=float(r["lon"]),
                        aliases=aliases,
                    )
                )
        return cls(rows)
