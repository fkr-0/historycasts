from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from podcast_atlas.provenance import ORIGIN_DET, new_run

from .db_build import (
    DEFAULT_YEAR_MAX,
    _extract_episode_derived,
    _recompute_clusters,
    postprocess_derived_rows,
)
from .extract import clean_description
from .gazetteer import load_gazetteer_csv
from .schema import ensure_schema

_YEAR_TEXT_RE = re.compile(r"\b(?:[1-9]\d{2,3})\b")


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        is not None
    )


def audit_derived_cleanup(db_path: str | Path) -> dict[str, int]:
    """Report how much stored description/override data the new pass will change."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id, description_raw, description_pure FROM episodes ORDER BY id"
    ).fetchall()

    changed = 0
    shortened = 0
    removed_year_values = 0
    removed_characters = 0
    for row in rows:
        old = str(row["description_pure"] or "")
        new = clean_description(str(row["description_raw"] or ""))
        if new != old:
            changed += 1
        if len(new) < len(old):
            shortened += 1
            removed_characters += len(old) - len(new)
            removed_year_values += len(
                set(_YEAR_TEXT_RE.findall(old)) - set(_YEAR_TEXT_RE.findall(new))
            )

    auto_overrides = conn.execute(
        """
        SELECT COUNT(*)
        FROM time_spans ts
        LEFT JOIN runs r ON r.id=ts.run_id
        WHERE ts.review_flag='review-override'
          AND COALESCE(r.tool, '')='aggregate-heuristic-review'
        """
    ).fetchone()[0]
    conn.close()
    return {
        "episodes_total": len(rows),
        "descriptions_changed": changed,
        "descriptions_shortened": shortened,
        "description_characters_removed": removed_characters,
        "distinct_year_values_removed": removed_year_values,
        "auto_review_overrides_to_remove": int(auto_overrides),
    }


def _delete_regenerable_rows(conn: sqlite3.Connection) -> dict[str, int]:
    auto_override_ids = [
        int(row[0])
        for row in conn.execute(
            """
            SELECT ts.id
            FROM time_spans ts
            LEFT JOIN runs r ON r.id=ts.run_id
            WHERE ts.review_flag='review-override'
              AND COALESCE(r.tool, '')='aggregate-heuristic-review'
            """
        ).fetchall()
    ]
    deterministic_span_ids = [
        int(row[0])
        for row in conn.execute(
            "SELECT id FROM time_spans WHERE origin='det' AND COALESCE(locked, 0)=0"
        ).fetchall()
    ]
    span_ids = sorted(set(auto_override_ids + deterministic_span_ids))
    if span_ids:
        placeholders = ",".join("?" for _ in span_ids)
        conn.execute(
            f"UPDATE episodes SET best_span_id=NULL WHERE best_span_id IN ({placeholders})",
            span_ids,
        )
        for link_table in ("span_entity", "span_place"):
            if _table_exists(conn, link_table):
                conn.execute(
                    f"DELETE FROM {link_table} WHERE span_id IN ({placeholders})",
                    span_ids,
                )
        conn.execute(f"DELETE FROM time_spans WHERE id IN ({placeholders})", span_ids)

    counts: dict[str, int] = {
        "auto_review_overrides_removed": len(auto_override_ids),
        "deterministic_spans_removed": len(deterministic_span_ids),
    }
    for table, best_column in (
        ("places", "best_place_id"),
        ("entities", None),
        ("episode_keywords", None),
    ):
        ids = [
            int(row[0])
            for row in conn.execute(
                f"SELECT rowid FROM {table} WHERE origin='det' AND COALESCE(locked, 0)=0"
            ).fetchall()
        ]
        if best_column and ids:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(
                f"UPDATE episodes SET {best_column}=NULL WHERE {best_column} IN ({placeholders})",
                ids,
            )
        conn.execute(f"DELETE FROM {table} WHERE origin='det' AND COALESCE(locked, 0)=0")
        counts[f"deterministic_{table}_removed"] = len(ids)
    return counts


def _refresh_episode_best_refs(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE episodes
        SET best_span_id=(
              SELECT b.id FROM v_best_time_span b WHERE b.episode_id=episodes.id
            ),
            best_place_id=(
              SELECT p.id FROM v_best_place p WHERE p.episode_id=episodes.id
            )
        """
    )


def _remove_orphan_rows(conn: sqlite3.Connection) -> dict[str, int]:
    orphan_segments = int(
        conn.execute(
            """
            SELECT COUNT(*) FROM segments s
            WHERE NOT EXISTS (SELECT 1 FROM time_spans ts WHERE ts.segment_id=s.id)
              AND NOT EXISTS (SELECT 1 FROM places p WHERE p.segment_id=s.id)
              AND NOT EXISTS (SELECT 1 FROM entities e WHERE e.segment_id=s.id)
            """
        ).fetchone()[0]
    )
    conn.execute(
        """
        DELETE FROM segments
        WHERE NOT EXISTS (SELECT 1 FROM time_spans ts WHERE ts.segment_id=segments.id)
          AND NOT EXISTS (SELECT 1 FROM places p WHERE p.segment_id=segments.id)
          AND NOT EXISTS (SELECT 1 FROM entities e WHERE e.segment_id=segments.id)
        """
    )
    orphan_keywords = int(
        conn.execute(
            """
            SELECT COUNT(*) FROM keywords k
            WHERE NOT EXISTS (SELECT 1 FROM episode_keywords ek WHERE ek.keyword_id=k.id)
            """
        ).fetchone()[0]
    )
    conn.execute(
        """
        DELETE FROM keywords
        WHERE NOT EXISTS (SELECT 1 FROM episode_keywords ek WHERE ek.keyword_id=keywords.id)
        """
    )
    return {
        "orphan_segments_removed": orphan_segments,
        "orphan_keywords_removed": orphan_keywords,
    }


def _default_backup_path(db_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return db_path.with_name(f"{db_path.name}.pre-reprocess-{stamp}.bak")


def reprocess_derived_data(
    db_path: str | Path,
    gazetteer_path: str | Path,
    *,
    year_max: int = DEFAULT_YEAR_MAX,
    enable_heuristic_review: bool = True,
    backup: bool = True,
    backup_path: str | Path | None = None,
) -> dict[str, Any]:
    """Regenerate deterministic extraction and clusters from stored raw descriptions."""
    db = Path(db_path)
    gazetteer = load_gazetteer_csv(str(gazetteer_path))
    audit = audit_derived_cleanup(db)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    written_backup: Path | None = None
    if backup:
        written_backup = Path(backup_path) if backup_path else _default_backup_path(db)
        written_backup.parent.mkdir(parents=True, exist_ok=True)
        backup_conn = sqlite3.connect(str(written_backup))
        conn.backup(backup_conn)
        backup_conn.close()

    run_id = new_run(
        conn,
        origin=ORIGIN_DET,
        tool="aggregate-reprocess-derived",
        params={
            "gazetteer": str(gazetteer_path),
            "year_max": int(year_max),
            "cleaner": "terminal-sections-v2",
        },
    )
    removed = _delete_regenerable_rows(conn)
    pre_orphaned = _remove_orphan_rows(conn)
    conn.commit()

    episodes = conn.execute(
        "SELECT id, title, description_raw FROM episodes ORDER BY id"
    ).fetchall()
    episodes_with_span = 0
    episodes_with_place = 0
    for row in episodes:
        episode_id = int(row["id"])
        pure = clean_description(str(row["description_raw"] or ""))
        conn.execute(
            "UPDATE episodes SET description_pure=? WHERE id=?",
            (pure, episode_id),
        )
        span_id, place_id = _extract_episode_derived(
            conn,
            run_id=run_id,
            episode_id=episode_id,
            title=str(row["title"] or ""),
            description_pure=pure,
            gaz=gazetteer,
        )
        episodes_with_span += int(span_id is not None)
        episodes_with_place += int(place_id is not None)

    conn.commit()
    postprocess = postprocess_derived_rows(
        conn,
        year_max=year_max,
        enable_heuristic_review=enable_heuristic_review,
    )
    _refresh_episode_best_refs(conn)
    conn.commit()
    _recompute_clusters(conn, run_id=run_id)
    post_orphaned = _remove_orphan_rows(conn)
    orphaned = {
        key: int(pre_orphaned.get(key, 0)) + int(post_orphaned.get(key, 0))
        for key in set(pre_orphaned) | set(post_orphaned)
    }
    _refresh_episode_best_refs(conn)
    conn.commit()

    result: dict[str, Any] = {
        **audit,
        **removed,
        **postprocess,
        **orphaned,
        "run_id": run_id,
        "episodes_reprocessed": len(episodes),
        "episodes_with_new_deterministic_span": episodes_with_span,
        "episodes_with_new_deterministic_place": episodes_with_place,
        "clusters": int(conn.execute("SELECT COUNT(*) FROM clusters").fetchone()[0]),
        "clustered_episodes": int(
            conn.execute("SELECT COUNT(*) FROM v_episode_cluster_best").fetchone()[0]
        ),
        "backup_path": str(written_backup) if written_backup else None,
    }
    conn.close()
    return result
