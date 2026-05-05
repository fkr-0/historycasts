from __future__ import annotations

import sqlite3

from podcast_atlas.provenance import ORIGIN_DET, ORIGIN_NONDET, ensure_provenance_schema, new_run


def test_ensure_provenance_schema_migrates_legacy_tables_and_creates_views() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE episodes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          podcast_id INTEGER,
          guid TEXT,
          title TEXT,
          pub_date TEXT,
          page_url TEXT,
          audio_url TEXT,
          duration INTEGER,
          kind TEXT,
          narrator TEXT,
          description_pure TEXT
        );
        CREATE TABLE time_spans (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          episode_id INTEGER,
          start_iso TEXT,
          end_iso TEXT,
          precision TEXT,
          qualifier TEXT,
          source_text TEXT,
          source_section TEXT,
          source_context TEXT,
          score REAL
        );
        CREATE TABLE places (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          episode_id INTEGER,
          place_norm_id INTEGER,
          name_raw TEXT,
          place_kind TEXT,
          latitude REAL,
          longitude REAL,
          radius_km REAL
        );
        CREATE TABLE entities (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          episode_id INTEGER,
          name TEXT,
          kind TEXT,
          confidence REAL,
          source_text TEXT
        );
        CREATE TABLE keywords (id INTEGER PRIMARY KEY AUTOINCREMENT, phrase TEXT UNIQUE);
        CREATE TABLE episode_keywords (episode_id INTEGER, keyword_id INTEGER, score REAL, PRIMARY KEY (episode_id, keyword_id));
        CREATE TABLE clusters (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          podcast_id INTEGER,
          k INTEGER,
          label TEXT,
          centroid_year REAL,
          centroid_lat REAL,
          centroid_lon REAL
        );
        CREATE TABLE episode_clusters (episode_id INTEGER, cluster_id INTEGER, PRIMARY KEY (episode_id, cluster_id));
        """
    )

    ensure_provenance_schema(conn)

    span_cols = {r[1] for r in conn.execute("PRAGMA table_info(time_spans)").fetchall()}
    assert {"run_id", "origin", "locked"}.issubset(span_cols)

    view_names = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
    }
    assert "v_best_time_span" in view_names
    assert "v_ui_episodes" in view_names

    run_id_det = new_run(conn, origin=ORIGIN_DET, tool="t", params={})
    run_id_nd = new_run(conn, origin=ORIGIN_NONDET, tool="manual", params={})

    eid = conn.execute(
        "INSERT INTO episodes (podcast_id, guid, title, pub_date) VALUES (?, ?, ?, ?)",
        (1, "g1", "ep", "2020-01-01"),
    ).lastrowid
    conn.execute(
        """
        INSERT INTO time_spans
        (run_id, origin, locked, episode_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score)
        VALUES (?, 'det', 0, ?, '1900-01-01', '1900-12-31', 'year', 'year', '1900', 'main', 'ctx', 9.0)
        """,
        (run_id_det, eid),
    )
    conn.execute(
        """
        INSERT INTO time_spans
        (run_id, origin, locked, episode_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score)
        VALUES (?, 'nondet', 1, ?, '1914-01-01', '1918-12-31', 'year', 'range', 'ww1', 'description', 'ctx', 1.0)
        """,
        (run_id_nd, eid),
    )
    conn.commit()

    row = conn.execute(
        "SELECT origin, locked, source_text FROM v_best_time_span WHERE episode_id=?",
        (eid,),
    ).fetchone()
    assert row is not None
    assert row["origin"] == "nondet"
    assert row["locked"] == 1
    assert row["source_text"] == "ww1"
    conn.close()
