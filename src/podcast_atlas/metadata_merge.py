from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .provenance import ORIGIN_NONDET, ensure_provenance_schema, new_run

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _norm_key(value: str) -> str:
    return _NON_ALNUM.sub(" ", value.lower()).strip()


def _row_exists(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> bool:
    row = conn.execute(sql, params).fetchone()
    return row is not None


def _timespan_fields(span: dict[str, Any]) -> tuple[str, str]:
    gran = str(span.get("granularity") or "").lower()
    if gran == "date":
        return "day", "exact"
    if gran == "range":
        return "year", "range"
    if gran == "year":
        return "year", "year"
    return "unknown", gran or "unknown"


def merge_handcrafted_metadata(
    *,
    db_path: Path | str,
    res_json_path: Path | str,
    update_episode_best_refs: bool = True,
) -> dict[str, int]:
    db_path = Path(db_path)
    res_json_path = Path(res_json_path)
    payload = json.loads(res_json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("res metadata payload must be a JSON object keyed by episode id")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        ensure_provenance_schema(conn)
        run_id = new_run(
            conn,
            origin=ORIGIN_NONDET,
            tool="merge-res-metadata",
            params={"source": str(res_json_path)},
        )

        counters = {
            "episodes_seen": 0,
            "episodes_missing": 0,
            "timespans_inserted": 0,
            "places_inserted": 0,
            "entities_inserted": 0,
        }

        for raw_episode_id, meta in payload.items():
            if not isinstance(meta, dict):
                continue
            try:
                episode_id = int(raw_episode_id)
            except (TypeError, ValueError):
                continue

            counters["episodes_seen"] += 1
            row = conn.execute("SELECT id, best_span_id, best_place_id FROM episodes WHERE id=?", (episode_id,)).fetchone()
            if row is None:
                counters["episodes_missing"] += 1
                continue

            best_span_id = row["best_span_id"]
            best_place_id = row["best_place_id"]

            clean_description = str(meta.get("clean_description") or "")

            for ts in meta.get("timespans") or []:
                if not isinstance(ts, dict):
                    continue
                start_iso = ts.get("start")
                end_iso = ts.get("end")
                if not start_iso and not end_iso:
                    continue
                precision, qualifier = _timespan_fields(ts)
                score = float(ts.get("confidence") or 1.0)
                source_text = str(ts.get("display") or ts.get("evidence") or start_iso or end_iso or "")
                source_context = str(ts.get("evidence") or clean_description or source_text)

                exists = _row_exists(
                    conn,
                    """
                    SELECT 1
                    FROM time_spans
                    WHERE episode_id=?
                      AND COALESCE(start_iso, '')=COALESCE(?, '')
                      AND COALESCE(end_iso, '')=COALESCE(?, '')
                      AND precision=?
                      AND qualifier=?
                      AND source_text=?
                      AND origin='nondet'
                    LIMIT 1
                    """,
                    (episode_id, start_iso, end_iso, precision, qualifier, source_text),
                )
                if exists:
                    continue

                cur = conn.execute(
                    """
                    INSERT INTO time_spans
                    (run_id, origin, locked, episode_id, segment_id, start_iso, end_iso, precision, qualifier,
                     source_text, source_section, source_context, score, review_flag)
                    VALUES (?, 'nondet', 1, ?, NULL, ?, ?, ?, ?, ?, 'description', ?, ?, 'handcrafted-res-json')
                    """,
                    (run_id, episode_id, start_iso, end_iso, precision, qualifier, source_text, source_context[:500], score),
                )
                counters["timespans_inserted"] += 1
                if update_episode_best_refs and best_span_id is None:
                    best_span_id = int(cur.lastrowid)

            for pl in meta.get("places") or []:
                if not isinstance(pl, dict):
                    continue
                canonical_name = str(pl.get("normalized") or pl.get("name_raw") or "").strip()
                if not canonical_name:
                    continue
                place_kind = str(pl.get("kind") or "unknown")
                name_raw = str(pl.get("name_raw") or canonical_name)

                nk = _norm_key(canonical_name)
                pn_row = conn.execute(
                    "SELECT id FROM places_norm WHERE norm_key=?",
                    (nk,),
                ).fetchone()
                if pn_row is None:
                    cur = conn.execute(
                        "INSERT INTO places_norm (norm_key, canonical_name, place_kind) VALUES (?, ?, ?)",
                        (nk, canonical_name, place_kind),
                    )
                    place_norm_id = int(cur.lastrowid)
                else:
                    place_norm_id = int(pn_row[0])

                exists = _row_exists(
                    conn,
                    """
                    SELECT 1
                    FROM places
                    WHERE episode_id=?
                      AND place_norm_id=?
                      AND name_raw=?
                      AND COALESCE(origin, 'det')='nondet'
                    LIMIT 1
                    """,
                    (episode_id, place_norm_id, name_raw),
                )
                if exists:
                    continue

                cur = conn.execute(
                    """
                    INSERT INTO places
                    (run_id, origin, locked, episode_id, segment_id, place_norm_id, name_raw, place_kind, latitude, longitude, radius_km)
                    VALUES (?, 'nondet', 1, ?, NULL, ?, ?, ?, NULL, NULL, NULL)
                    """,
                    (run_id, episode_id, place_norm_id, name_raw, place_kind),
                )
                counters["places_inserted"] += 1
                if update_episode_best_refs and best_place_id is None:
                    best_place_id = int(cur.lastrowid)

            seen_entities: set[tuple[str, str]] = set()
            for key in ("people", "hosts", "guests"):
                entries = meta.get(key) or []
                for person in entries:
                    if not isinstance(person, dict):
                        continue
                    name = str(person.get("name") or "").strip()
                    if not name:
                        continue
                    role = str(person.get("role") or "")
                    kind = "org" if role == "org" else "person"
                    identity = (name, kind)
                    if identity in seen_entities:
                        continue
                    seen_entities.add(identity)
                    confidence = float(person.get("confidence") or 1.0)

                    exists = _row_exists(
                        conn,
                        """
                        SELECT 1 FROM entities
                        WHERE episode_id=? AND name=? AND kind=? AND COALESCE(origin, 'det')='nondet'
                        LIMIT 1
                        """,
                        (episode_id, name, kind),
                    )
                    if exists:
                        continue

                    conn.execute(
                        """
                        INSERT INTO entities
                        (run_id, origin, locked, episode_id, segment_id, name, kind, confidence, source_text)
                        VALUES (?, 'nondet', 1, ?, NULL, ?, ?, ?, ?)
                        """,
                        (run_id, episode_id, name, kind, confidence, f"handcrafted:{role or key}"),
                    )
                    counters["entities_inserted"] += 1

            if update_episode_best_refs:
                conn.execute(
                    "UPDATE episodes SET best_span_id=COALESCE(?, best_span_id), best_place_id=COALESCE(?, best_place_id) WHERE id=?",
                    (best_span_id, best_place_id, episode_id),
                )

        conn.commit()
        return counters
    finally:
        conn.close()
