from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

ORIGIN_DET = "det"
ORIGIN_NONDET = "nondet"
VALID_ORIGINS = {ORIGIN_DET, ORIGIN_NONDET}

_DERIVED_TABLES = (
    "time_spans",
    "places",
    "entities",
    "episode_keywords",
    "clusters",
    "episode_clusters",
    "cluster_keywords",
    "cluster_entities",
)

_VIEWS_SQL = """
CREATE VIEW IF NOT EXISTS v_best_time_span AS
  WITH ranked AS (
    SELECT ts.*,
           ROW_NUMBER() OVER (
             PARTITION BY ts.episode_id
             ORDER BY COALESCE(ts.locked, 0) DESC,
                      CASE COALESCE(ts.origin, 'det') WHEN 'nondet' THEN 1 ELSE 0 END DESC,
                      ts.score DESC,
                      COALESCE(ts.run_id, 0) DESC,
                      ts.id DESC
           ) AS rn
    FROM time_spans ts
  )
  SELECT * FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_best_place AS
  WITH ranked AS (
    SELECT p.*,
           ROW_NUMBER() OVER (
             PARTITION BY p.episode_id
             ORDER BY COALESCE(p.locked, 0) DESC,
                      CASE COALESCE(p.origin, 'det') WHEN 'nondet' THEN 1 ELSE 0 END DESC,
                      (p.latitude IS NOT NULL) DESC,
                      CASE p.place_kind WHEN 'city' THEN 3 WHEN 'region' THEN 2 WHEN 'country' THEN 1 ELSE 0 END DESC,
                      COALESCE(p.run_id, 0) DESC,
                      p.id DESC
           ) AS rn
    FROM places p
  )
  SELECT * FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_entities_preferred AS
  WITH ranked AS (
    SELECT e.*,
           ROW_NUMBER() OVER (
             PARTITION BY e.episode_id, e.name, e.kind
             ORDER BY COALESCE(e.locked, 0) DESC,
                      CASE COALESCE(e.origin, 'det') WHEN 'nondet' THEN 1 ELSE 0 END DESC,
                      e.confidence DESC,
                      COALESCE(e.run_id, 0) DESC,
                      e.id DESC
           ) AS rn
    FROM entities e
  )
  SELECT * FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_episode_keywords_best AS
  WITH ranked AS (
    SELECT ek.*,
           ROW_NUMBER() OVER (
             PARTITION BY ek.episode_id, ek.keyword_id
             ORDER BY COALESCE(ek.locked, 0) DESC,
                      CASE COALESCE(ek.origin, 'det') WHEN 'nondet' THEN 1 ELSE 0 END DESC,
                      ek.score DESC,
                      COALESCE(ek.run_id, 0) DESC
           ) AS rn
    FROM episode_keywords ek
  )
  SELECT * FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_episode_cluster_best AS
  WITH ranked AS (
    SELECT ec.*,
           ROW_NUMBER() OVER (
             PARTITION BY ec.episode_id
             ORDER BY CASE COALESCE(ec.origin, 'det') WHEN 'nondet' THEN 1 ELSE 0 END DESC,
                      COALESCE(ec.run_id, 0) DESC
           ) AS rn
    FROM episode_clusters ec
  )
  SELECT * FROM ranked WHERE rn = 1;

CREATE VIEW IF NOT EXISTS v_ui_episodes AS
  SELECT
    e.id AS episode_id,
    e.podcast_id,
    e.guid,
    e.title,
    e.pub_date,
    e.page_url,
    e.audio_url,
    e.duration,
    e.kind,
    e.narrator,
    e.description_pure,
    bts.id AS best_span_id,
    bp.id AS best_place_id
  FROM episodes e
  LEFT JOIN v_best_time_span bts ON bts.episode_id = e.id
  LEFT JOIN v_best_place bp ON bp.episode_id = e.id;

CREATE VIEW IF NOT EXISTS v_ui_entities AS
  SELECT * FROM v_entities_preferred;

CREATE VIEW IF NOT EXISTS v_ui_episode_keywords AS
  SELECT * FROM v_episode_keywords_best;

CREATE VIEW IF NOT EXISTS v_ui_clusters AS
  WITH ranked AS (
    SELECT c.*,
           ROW_NUMBER() OVER (
             PARTITION BY c.podcast_id, c.label
             ORDER BY CASE COALESCE(c.origin, 'det') WHEN 'nondet' THEN 1 ELSE 0 END DESC,
                      COALESCE(c.run_id, 0) DESC,
                      c.id DESC
           ) AS rn
    FROM clusters c
  )
  SELECT * FROM ranked WHERE rn = 1;
"""


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r[1]) for r in rows}


def _add_column_if_missing(
    conn: sqlite3.Connection, table: str, col_sql: str, col_name: str
) -> None:
    cols = _column_names(conn, table)
    if col_name in cols:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_sql}")


def new_run(
    conn: sqlite3.Connection,
    *,
    origin: str,
    tool: str,
    params: dict[str, Any] | None = None,
) -> int:
    if origin not in VALID_ORIGINS:
        raise ValueError(f"invalid origin: {origin}")
    cur = conn.execute(
        "INSERT INTO runs(created_at, origin, tool, params_json) VALUES (?, ?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            origin,
            tool,
            json.dumps(params or {}, ensure_ascii=False, sort_keys=True),
        ),
    )
    rowid = cur.lastrowid
    if rowid is None:
        raise RuntimeError("sqlite lastrowid is None after runs insert")
    run_id = int(rowid)
    conn.commit()
    return run_id


def ensure_provenance_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL,
          origin TEXT NOT NULL CHECK(origin IN ('det','nondet')),
          tool TEXT NOT NULL,
          params_json TEXT
        )
        """
    )

    for table in _DERIVED_TABLES:
        if not _table_exists(conn, table):
            continue
        _add_column_if_missing(conn, table, "run_id INTEGER REFERENCES runs(id)", "run_id")
        _add_column_if_missing(
            conn,
            table,
            "origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet'))",
            "origin",
        )
        _add_column_if_missing(conn, table, "locked INTEGER NOT NULL DEFAULT 0", "locked")

    # Bootstrap existing rows to deterministic run if no run_id is present yet.
    run_row = conn.execute("SELECT id FROM runs WHERE origin='det' ORDER BY id LIMIT 1").fetchone()
    det_run_id = int(run_row[0]) if run_row is not None else None

    for table in _DERIVED_TABLES:
        if not _table_exists(conn, table):
            continue
        cols = _column_names(conn, table)
        if "run_id" not in cols:
            continue
        null_count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id IS NULL").fetchone()[
            0
        ]
        if int(null_count) <= 0:
            continue
        if det_run_id is None:
            det_run_id = new_run(conn, origin=ORIGIN_DET, tool="provenance-bootstrap", params={})
        conn.execute(f"UPDATE {table} SET run_id=? WHERE run_id IS NULL", (det_run_id,))

    conn.executescript(_VIEWS_SQL)
    conn.commit()


def prune_origin_rows(conn: sqlite3.Connection, *, table: str, origin: str) -> int:
    if origin not in VALID_ORIGINS:
        raise ValueError(f"invalid origin: {origin}")
    if not _table_exists(conn, table):
        return 0
    cols = _column_names(conn, table)
    if "origin" not in cols:
        return 0
    cur = conn.execute(f"DELETE FROM {table} WHERE origin=?", (origin,))
    deleted = int(cur.rowcount if cur.rowcount is not None and cur.rowcount > 0 else 0)
    conn.commit()
    return deleted
