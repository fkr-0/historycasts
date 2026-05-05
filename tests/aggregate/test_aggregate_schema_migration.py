from __future__ import annotations

import sqlite3

from podcast_atlas.aggregate.schema import ensure_schema


def test_ensure_schema_adds_episodes_raw_and_backfills_raw_id_for_legacy_rows() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE podcasts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT,
          feed_url TEXT
        );
        CREATE TABLE episodes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          podcast_id INTEGER,
          guid TEXT,
          title TEXT,
          pub_date TEXT,
          page_url TEXT,
          audio_url TEXT,
          duration INTEGER,
          episode_type TEXT,
          kind TEXT,
          narrator TEXT,
          description_raw TEXT,
          description_pure TEXT,
          best_span_id INTEGER,
          best_place_id INTEGER
        );
        INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'p', 'f');
        INSERT INTO episodes
          (id, podcast_id, guid, title, pub_date, page_url, audio_url, duration, episode_type, kind, narrator, description_raw, description_pure)
        VALUES
          (10, 1, 'g-10', 'Episode', '2020-01-01', 'https://e', 'https://a', 60, 'full', 'regular', 'n', '<p>raw</p>', 'raw');
        """
    )

    ensure_schema(conn)

    tables = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert "episodes_raw" in tables

    episode_cols = {r[1] for r in conn.execute("PRAGMA table_info(episodes)").fetchall()}
    assert "raw_id" in episode_cols

    row = conn.execute("SELECT raw_id FROM episodes WHERE id=10").fetchone()
    assert row is not None
    assert row[0] is not None

    raw = conn.execute(
        "SELECT podcast_id, guid, title, pub_date, page_url, audio_url, duration_sec, author, description_raw FROM episodes_raw WHERE id=?",
        (int(row[0]),),
    ).fetchone()
    assert raw is not None
    assert raw[0] == 1
    assert raw[1] == "g-10"
    assert raw[2] == "Episode"
    assert raw[3] == "2020-01-01"
    assert raw[4] == "https://e"
    assert raw[5] == "https://a"
    assert raw[6] == 60
    assert raw[8] == "<p>raw</p>"
    conn.close()
