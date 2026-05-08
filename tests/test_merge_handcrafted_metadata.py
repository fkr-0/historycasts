from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from podcast_atlas.aggregate.schema import ensure_schema
from podcast_atlas.metadata_merge import merge_handcrafted_metadata


def test_merge_handcrafted_metadata_inserts_protected_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "meta.db"
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    conn.execute("INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'pod', 'fixture:pod')")
    conn.execute(
        """
        INSERT INTO episodes
        (id, podcast_id, guid, title, pub_date, audio_url, kind, narrator, description_pure)
        VALUES (1, 1, 'g1', 'Episode 1', '2020-01-01T00:00:00Z', 'https://a', 'regular', 'n', 'desc')
        """
    )
    conn.commit()
    conn.close()

    payload = {
        "1": {
            "clean_description": "A handcrafted summary",
            "timespans": [
                {
                    "granularity": "range",
                    "start": "1914-01-01",
                    "end": "1918-12-31",
                    "display": "WW1",
                    "evidence": "world war one",
                    "confidence": 0.95,
                }
            ],
            "places": [
                {"name_raw": "Paris", "normalized": "Paris", "kind": "city", "confidence": 0.9}
            ],
            "people": [{"name": "Ada Lovelace", "role": "historical", "confidence": 0.9}],
            "hosts": [{"name": "Host A", "confidence": 0.8}],
            "guests": [],
        }
    }
    res_json = tmp_path / "res.json"
    res_json.write_text(json.dumps(payload), encoding="utf-8")

    stats = merge_handcrafted_metadata(db_path=db_path, res_json_path=res_json)
    assert stats["timespans_inserted"] == 1
    assert stats["places_inserted"] == 1
    assert stats["entities_inserted"] == 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ts = conn.execute(
        "SELECT origin, locked, review_flag FROM time_spans WHERE episode_id=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert ts is not None
    assert ts["origin"] == "nondet"
    assert ts["locked"] == 1
    assert ts["review_flag"] == "handcrafted-res-json"

    pl = conn.execute(
        "SELECT origin, locked, name_raw FROM places WHERE episode_id=1 ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert pl is not None
    assert pl["origin"] == "nondet"
    assert pl["locked"] == 1
    assert pl["name_raw"] == "Paris"

    ent_count = conn.execute(
        "SELECT COUNT(*) FROM entities WHERE episode_id=1 AND origin='nondet' AND locked=1"
    ).fetchone()[0]
    assert ent_count == 2

    ep = conn.execute("SELECT best_span_id, best_place_id FROM episodes WHERE id=1").fetchone()
    assert ep["best_span_id"] is not None
    assert ep["best_place_id"] is not None
    conn.close()
