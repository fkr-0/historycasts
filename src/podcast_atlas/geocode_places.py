from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class GeocodeHit:
    lat: float
    lon: float
    provider: str


Resolver = Callable[[str, str], GeocodeHit | None]
ProgressCallback = Callable[[dict[str, object]], None]


def _nominatim_resolver(*, user_agent: str) -> Resolver:
    def _resolve(query: str, place_kind: str) -> GeocodeHit | None:
        params = {
            "q": query,
            "format": "jsonv2",
            "limit": "1",
            "addressdetails": "0",
        }
        if place_kind:
            params["featuretype"] = place_kind
        url = f"https://nominatim.openstreetmap.org/search?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
        with urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not payload:
            return None
        hit = payload[0]
        return GeocodeHit(lat=float(hit["lat"]), lon=float(hit["lon"]), provider="nominatim")

    return _resolve


def _load_cache(path: Path) -> dict[str, dict[str, float | str] | None]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        return {}
    return {}


def _save_cache(path: Path, cache: dict[str, dict[str, float | str] | None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def _list_candidates(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    rows = conn.execute(
        """
        SELECT
          COALESCE(n.norm_key, LOWER(TRIM(p.name_raw))) AS norm_key,
          COALESCE(n.canonical_name, p.name_raw) AS canonical_name,
          COALESCE(n.place_kind, p.place_kind, 'unknown') AS canonical_kind,
          COUNT(*) AS n_rows
        FROM places p
        LEFT JOIN places_norm n ON n.id = p.place_norm_id
        WHERE (p.latitude IS NULL OR p.longitude IS NULL)
        GROUP BY norm_key, canonical_name, canonical_kind
        ORDER BY n_rows DESC, canonical_name ASC
        """
    ).fetchall()
    out: list[tuple[str, str, str]] = []
    for norm_key, canonical_name, place_kind, _ in rows:
        if not canonical_name:
            continue
        out.append(
            (
                str(norm_key or "").strip(),
                str(canonical_name).strip(),
                str(place_kind or "unknown").strip(),
            )
        )
    return out


def _update_places_for_norm_key(
    conn: sqlite3.Connection, norm_key: str, lat: float, lon: float
) -> int:
    cur = conn.execute(
        """
        UPDATE places
        SET latitude = ?, longitude = ?
        WHERE id IN (
          SELECT p.id
          FROM places p
          LEFT JOIN places_norm n ON n.id = p.place_norm_id
          WHERE (p.latitude IS NULL OR p.longitude IS NULL)
            AND COALESCE(n.norm_key, LOWER(TRIM(p.name_raw))) = ?
        )
        """,
        (float(lat), float(lon), norm_key),
    )
    return int(cur.rowcount if cur.rowcount is not None else 0)


def _refresh_best_place_ids(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """
        UPDATE episodes
        SET best_place_id = (
          SELECT p2.id
          FROM places p2
          WHERE p2.episode_id = episodes.id
            AND p2.latitude IS NOT NULL
            AND p2.longitude IS NOT NULL
          ORDER BY p2.id
          LIMIT 1
        )
        WHERE EXISTS (
          SELECT 1
          FROM places p
          WHERE p.episode_id = episodes.id
            AND p.latitude IS NOT NULL
            AND p.longitude IS NOT NULL
        )
        AND (
          best_place_id IS NULL
          OR EXISTS (
            SELECT 1
            FROM places bp
            WHERE bp.id = best_place_id
              AND (bp.latitude IS NULL OR bp.longitude IS NULL)
          )
        )
        """
    )
    return int(cur.rowcount if cur.rowcount is not None else 0)


def enrich_missing_place_coordinates(
    *,
    db_path: Path | str,
    resolver: Resolver,
    cache_path: Path | str = Path("data/geocode_cache.json"),
    delay_seconds: float = 1.0,
    dry_run: bool = False,
    limit: int = 0,
    progress: ProgressCallback | None = None,
) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    try:
        cache_file = Path(cache_path)
        cache = _load_cache(cache_file)
        candidates = _list_candidates(conn)
        if limit > 0:
            candidates = candidates[: int(limit)]

        if progress:
            progress(
                {
                    "event": "start",
                    "total_candidates": len(candidates),
                    "dry_run": bool(dry_run),
                }
            )

        resolved = 0
        unresolved = 0
        updated_rows = 0
        refreshed = 0
        cache_hits = 0

        total = len(candidates)
        for idx, (norm_key, canonical_name, place_kind) in enumerate(candidates, start=1):
            cache_key = f"{norm_key}|{canonical_name}|{place_kind}"
            hit: GeocodeHit | None = None
            from_cache = False

            if cache_key in cache:
                cache_hits += 1
                from_cache = True
                cached = cache[cache_key]
                if isinstance(cached, dict) and "lat" in cached and "lon" in cached:
                    hit = GeocodeHit(
                        lat=float(cached["lat"]),
                        lon=float(cached["lon"]),
                        provider=str(cached.get("provider") or "cache"),
                    )
            else:
                hit = resolver(canonical_name, place_kind)
                if hit:
                    cache[cache_key] = {
                        "lat": float(hit.lat),
                        "lon": float(hit.lon),
                        "provider": hit.provider,
                    }
                else:
                    cache[cache_key] = None
                if delay_seconds > 0:
                    time.sleep(delay_seconds)

            if not hit:
                unresolved += 1
                if progress and (idx == 1 or idx % 25 == 0 or idx == total):
                    progress(
                        {
                            "event": "progress",
                            "index": idx,
                            "total": total,
                            "name": canonical_name,
                            "status": "unresolved",
                            "from_cache": from_cache,
                            "resolved": resolved,
                            "unresolved": unresolved,
                        }
                    )
                continue

            resolved += 1
            if not dry_run:
                updated_rows += _update_places_for_norm_key(conn, norm_key, hit.lat, hit.lon)
            if progress and (idx == 1 or idx % 25 == 0 or idx == total):
                progress(
                    {
                        "event": "progress",
                        "index": idx,
                        "total": total,
                        "name": canonical_name,
                        "status": "resolved",
                        "from_cache": from_cache,
                        "resolved": resolved,
                        "unresolved": unresolved,
                    }
                )

        if not dry_run:
            refreshed = _refresh_best_place_ids(conn)
            conn.commit()

        _save_cache(cache_file, cache)

        stats = {
            "candidates": len(candidates),
            "resolved": resolved,
            "unresolved": unresolved,
            "updated_rows": updated_rows,
            "best_place_updated": refreshed,
            "cache_hits": cache_hits,
        }
        if progress:
            progress({"event": "done", **stats})
        return stats
    finally:
        conn.close()


def geocode_places(
    *,
    db_path: Path,
    cache_path: Path,
    limit: int = 0,
    delay_seconds: float = 1.0,
    dry_run: bool = False,
    user_agent: str = "podcast-atlas/1.0 (historycasts geocoder)",
    progress: ProgressCallback | None = None,
) -> dict[str, int]:
    resolver = _nominatim_resolver(user_agent=user_agent)
    return enrich_missing_place_coordinates(
        db_path=db_path,
        resolver=resolver,
        cache_path=cache_path,
        delay_seconds=delay_seconds,
        dry_run=dry_run,
        limit=limit,
        progress=progress,
    )
