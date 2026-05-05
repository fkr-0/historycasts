from __future__ import annotations

import sqlite3

from ..provenance import ensure_provenance_schema

SCHEMA_VERSION = 2

SCHEMA_SQL = r"""
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  origin TEXT NOT NULL CHECK(origin IN ('det','nondet')),
  tool TEXT NOT NULL,
  params_json TEXT
);

CREATE TABLE IF NOT EXISTS podcasts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT,
  description TEXT,
  language TEXT,
  link TEXT,
  image_url TEXT,
  feed_url TEXT UNIQUE,
  feed_type TEXT
);

CREATE TABLE IF NOT EXISTS episodes_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  podcast_id INTEGER NOT NULL REFERENCES podcasts(id),
  guid TEXT NOT NULL,
  title TEXT,
  pub_date TEXT,
  page_url TEXT,
  audio_url TEXT,
  duration_sec INTEGER,
  author TEXT,
  description_raw TEXT,
  UNIQUE(podcast_id, guid)
);

CREATE TABLE IF NOT EXISTS episodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  podcast_id INTEGER REFERENCES podcasts(id),
  raw_id INTEGER REFERENCES episodes_raw(id),
  guid TEXT UNIQUE,
  page_url TEXT,
  title TEXT,
  pub_date TEXT,
  duration INTEGER,
  audio_url TEXT,
  episode_type TEXT,
  kind TEXT,
  narrator TEXT,
  description_raw TEXT,
  description_pure TEXT,
  best_span_id INTEGER,
  best_place_id INTEGER
);

CREATE TABLE IF NOT EXISTS links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  episode_id INTEGER REFERENCES episodes(id),
  url TEXT,
  link_type TEXT
);

CREATE TABLE IF NOT EXISTS segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  episode_id INTEGER REFERENCES episodes(id),
  section TEXT,
  idx INTEGER,
  text TEXT
);

CREATE TABLE IF NOT EXISTS time_spans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER REFERENCES runs(id),
  origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet')),
  locked INTEGER NOT NULL DEFAULT 0,
  episode_id INTEGER REFERENCES episodes(id),
  segment_id INTEGER REFERENCES segments(id),
  start_iso TEXT,
  end_iso TEXT,
  precision TEXT,
  qualifier TEXT,
  source_text TEXT,
  source_section TEXT,
  source_context TEXT,
  score REAL,
  review_flag TEXT
);

CREATE TABLE IF NOT EXISTS places_norm (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  norm_key TEXT UNIQUE,
  canonical_name TEXT,
  place_kind TEXT
);

CREATE TABLE IF NOT EXISTS places (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER REFERENCES runs(id),
  origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet')),
  locked INTEGER NOT NULL DEFAULT 0,
  episode_id INTEGER REFERENCES episodes(id),
  segment_id INTEGER REFERENCES segments(id),
  place_norm_id INTEGER REFERENCES places_norm(id),
  name_raw TEXT,
  place_kind TEXT,
  latitude REAL,
  longitude REAL,
  radius_km REAL
);

CREATE TABLE IF NOT EXISTS entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER REFERENCES runs(id),
  origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet')),
  locked INTEGER NOT NULL DEFAULT 0,
  episode_id INTEGER REFERENCES episodes(id),
  segment_id INTEGER REFERENCES segments(id),
  name TEXT,
  kind TEXT,
  confidence REAL,
  source_text TEXT
);

CREATE TABLE IF NOT EXISTS keywords (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  phrase TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS episode_keywords (
  run_id INTEGER REFERENCES runs(id),
  origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet')),
  locked INTEGER NOT NULL DEFAULT 0,
  episode_id INTEGER REFERENCES episodes(id),
  keyword_id INTEGER REFERENCES keywords(id),
  score REAL,
  PRIMARY KEY (episode_id, keyword_id)
);

CREATE TABLE IF NOT EXISTS clusters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER REFERENCES runs(id),
  origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet')),
  podcast_id INTEGER REFERENCES podcasts(id),
  k INTEGER,
  label TEXT,
  centroid_year REAL,
  centroid_lat REAL,
  centroid_lon REAL
);

CREATE TABLE IF NOT EXISTS episode_clusters (
  run_id INTEGER REFERENCES runs(id),
  origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet')),
  episode_id INTEGER REFERENCES episodes(id),
  cluster_id INTEGER REFERENCES clusters(id),
  PRIMARY KEY (episode_id, cluster_id)
);

CREATE TABLE IF NOT EXISTS cluster_keywords (
  run_id INTEGER REFERENCES runs(id),
  origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet')),
  locked INTEGER NOT NULL DEFAULT 0,
  cluster_id INTEGER REFERENCES clusters(id),
  phrase TEXT,
  score REAL
);

CREATE TABLE IF NOT EXISTS cluster_entities (
  run_id INTEGER REFERENCES runs(id),
  origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet')),
  locked INTEGER NOT NULL DEFAULT 0,
  cluster_id INTEGER REFERENCES clusters(id),
  name TEXT,
  kind TEXT,
  score REAL
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    _ensure_episodes_raw_split(conn)
    _ensure_cluster_summary_provenance(conn)
    ensure_provenance_schema(conn)
    _ensure_indexes(conn)
    _set_schema_version(conn, SCHEMA_VERSION)
    conn.commit()


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r[1]) for r in rows}


def _ensure_episodes_raw_split(conn: sqlite3.Connection) -> None:
    episode_cols = _table_columns(conn, "episodes")
    if "raw_id" not in episode_cols:
        conn.execute("ALTER TABLE episodes ADD COLUMN raw_id INTEGER REFERENCES episodes_raw(id)")

    conn.execute(
        """
        INSERT OR IGNORE INTO episodes_raw
        (podcast_id, guid, title, pub_date, page_url, audio_url, duration_sec, author, description_raw)
        SELECT
          e.podcast_id,
          e.guid,
          e.title,
          e.pub_date,
          e.page_url,
          e.audio_url,
          e.duration,
          e.narrator,
          e.description_raw
        FROM episodes e
        WHERE e.guid IS NOT NULL
        """
    )
    conn.execute(
        """
        UPDATE episodes
        SET raw_id = (
          SELECT er.id
          FROM episodes_raw er
          WHERE er.podcast_id = episodes.podcast_id
            AND er.guid = episodes.guid
          LIMIT 1
        )
        WHERE raw_id IS NULL AND guid IS NOT NULL
        """
    )


def _ensure_cluster_summary_provenance(conn: sqlite3.Connection) -> None:
    for table in ("cluster_keywords", "cluster_entities"):
        cols = _table_columns(conn, table)
        if "run_id" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN run_id INTEGER REFERENCES runs(id)")
        if "origin" not in cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN origin TEXT NOT NULL DEFAULT 'det' CHECK(origin IN ('det','nondet'))"
            )
        if "locked" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN locked INTEGER NOT NULL DEFAULT 0")


def _ensure_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_episodes_raw_guid ON episodes_raw(podcast_id, guid);
        CREATE INDEX IF NOT EXISTS idx_episodes_raw_id ON episodes(raw_id);
        CREATE INDEX IF NOT EXISTS idx_time_spans_origin_episode ON time_spans(origin, locked, episode_id);
        CREATE INDEX IF NOT EXISTS idx_places_origin_episode ON places(origin, locked, episode_id);
        CREATE INDEX IF NOT EXISTS idx_entities_origin_episode ON entities(origin, locked, episode_id);
        CREATE INDEX IF NOT EXISTS idx_episode_keywords_origin_episode ON episode_keywords(origin, locked, episode_id);
        CREATE INDEX IF NOT EXISTS idx_clusters_origin_podcast ON clusters(origin, podcast_id);
        """
    )


def _set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    cur = conn.execute("PRAGMA user_version")
    current = int(cur.fetchone()[0])
    if current < int(version):
        conn.execute(f"PRAGMA user_version={int(version)}")
