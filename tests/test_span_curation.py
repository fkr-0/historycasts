from __future__ import annotations

import sqlite3
from pathlib import Path

from podcast_atlas.aggregate.schema import ensure_schema
from podcast_atlas.curation import delete_episode_spans


def _seed(path: Path) -> None:
    conn = sqlite3.connect(path)
    ensure_schema(conn)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS span_entity (
          span_id INTEGER NOT NULL REFERENCES time_spans(id),
          entity_id INTEGER NOT NULL REFERENCES entities(id),
          PRIMARY KEY(span_id, entity_id)
        );
        CREATE TABLE IF NOT EXISTS span_place (
          span_id INTEGER NOT NULL REFERENCES time_spans(id),
          place_id INTEGER NOT NULL REFERENCES places(id),
          PRIMARY KEY(span_id, place_id)
        );
        INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'p', 'f');
        INSERT INTO episodes (id, podcast_id, guid, title, pub_date, best_span_id) VALUES
          (109, 1, 'g109', 'Episode 109', '2020-01-01', 444);
        INSERT INTO time_spans (id, episode_id, start_iso, end_iso, precision, qualifier) VALUES
          (444, 109, '1868-01-01', '1868-12-31', 'year', 'range'),
          (445, 109, '0708-01-01', '7019-12-31', 'year', 'range'),
          (446, 109, '0160-01-01', '1679-12-31', 'year', 'range');
        INSERT INTO entities (id, episode_id, name, kind) VALUES (1, 109, 'E', 'person');
        INSERT INTO places_norm (id, norm_key, canonical_name, place_kind) VALUES (1, 'x', 'X', 'city');
        INSERT INTO places (id, episode_id, place_norm_id, name_raw) VALUES (1, 109, 1, 'X');
        INSERT INTO span_entity (span_id, entity_id) VALUES (445, 1), (446, 1);
        INSERT INTO span_place (span_id, place_id) VALUES (445, 1), (446, 1);
        """
    )
    conn.commit()
    conn.close()


def test_delete_episode_spans_preserves_keep_id_and_removes_fk_links(tmp_path: Path) -> None:
    db_path = tmp_path / "curation.db"
    _seed(db_path)

    result = delete_episode_spans(db_path, episode_id=109, keep_span_ids=[444])

    assert result["deleted_span_count"] == 2
    assert result["kept_span_ids"] == [444]
    assert result["deleted_span_entity_count"] == 2
    assert result["deleted_span_place_count"] == 2

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    assert cur.execute("SELECT COUNT(*) FROM time_spans WHERE episode_id=109").fetchone()[0] == 1
    assert cur.execute("SELECT id FROM time_spans WHERE episode_id=109").fetchone()[0] == 444
    assert cur.execute("SELECT COUNT(*) FROM span_entity").fetchone()[0] == 0
    assert cur.execute("SELECT COUNT(*) FROM span_place").fetchone()[0] == 0
    conn.close()
