from __future__ import annotations

import sqlite3


SCHEMA_SQL = r"""
PRAGMA foreign_keys=ON;

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

CREATE TABLE IF NOT EXISTS episodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  podcast_id INTEGER REFERENCES podcasts(id),
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
  episode_id INTEGER REFERENCES episodes(id),
  keyword_id INTEGER REFERENCES keywords(id),
  score REAL,
  PRIMARY KEY (episode_id, keyword_id)
);

CREATE TABLE IF NOT EXISTS clusters (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  podcast_id INTEGER REFERENCES podcasts(id),
  k INTEGER,
  label TEXT,
  centroid_year REAL,
  centroid_lat REAL,
  centroid_lon REAL
);

CREATE TABLE IF NOT EXISTS episode_clusters (
  episode_id INTEGER REFERENCES episodes(id),
  cluster_id INTEGER REFERENCES clusters(id),
  PRIMARY KEY (episode_id, cluster_id)
);

CREATE TABLE IF NOT EXISTS cluster_keywords (
  cluster_id INTEGER REFERENCES clusters(id),
  phrase TEXT,
  score REAL
);

CREATE TABLE IF NOT EXISTS cluster_entities (
  cluster_id INTEGER REFERENCES clusters(id),
  name TEXT,
  kind TEXT,
  score REAL
);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.commit()
