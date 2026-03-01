from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    row = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def delete_episode_spans(
    db_path: str | Path, *, episode_id: int, keep_span_ids: Iterable[int] = ()
) -> dict[str, Any]:
    keep_ids = sorted({int(v) for v in keep_span_ids})
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")

        rows = cur.execute(
            "SELECT id FROM time_spans WHERE episode_id=? ORDER BY id",
            (int(episode_id),),
        ).fetchall()
        all_span_ids = [int(r[0]) for r in rows]
        delete_span_ids = [sid for sid in all_span_ids if sid not in set(keep_ids)]
        missing_keep_ids = [sid for sid in keep_ids if sid not in all_span_ids]

        deleted_span_entity_count = 0
        deleted_span_place_count = 0
        deleted_span_count = 0
        best_span_cleared = False

        if delete_span_ids:
            placeholders = ",".join("?" for _ in delete_span_ids)
            with con:
                if _table_exists(cur, "span_entity"):
                    cur.execute(
                        f"DELETE FROM span_entity WHERE span_id IN ({placeholders})",
                        delete_span_ids,
                    )
                    deleted_span_entity_count = int(cur.rowcount if cur.rowcount > 0 else 0)

                if _table_exists(cur, "span_place"):
                    cur.execute(
                        f"DELETE FROM span_place WHERE span_id IN ({placeholders})",
                        delete_span_ids,
                    )
                    deleted_span_place_count = int(cur.rowcount if cur.rowcount > 0 else 0)

                cur.execute(
                    f"DELETE FROM time_spans WHERE id IN ({placeholders})",
                    delete_span_ids,
                )
                deleted_span_count = int(cur.rowcount if cur.rowcount > 0 else 0)

                cur.execute(
                    f"UPDATE episodes SET best_span_id=NULL WHERE id=? AND best_span_id IN ({placeholders})",
                    [int(episode_id), *delete_span_ids],
                )
                best_span_cleared = (cur.rowcount or 0) > 0

        return {
            "episode_id": int(episode_id),
            "all_span_ids": all_span_ids,
            "kept_span_ids": [sid for sid in keep_ids if sid in all_span_ids],
            "missing_keep_span_ids": missing_keep_ids,
            "deleted_span_ids": delete_span_ids,
            "deleted_span_count": deleted_span_count,
            "deleted_span_entity_count": deleted_span_entity_count,
            "deleted_span_place_count": deleted_span_place_count,
            "best_span_cleared": best_span_cleared,
        }
    finally:
        con.close()
