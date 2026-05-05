from __future__ import annotations

import sqlite3
from pathlib import Path

from podcast_atlas.aggregate.schema import ensure_schema
from podcast_atlas.geocode_places import GeocodeHit, enrich_missing_place_coordinates


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    ensure_schema(conn)
    conn.execute("INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'pod', 'fixture:pod')")
    conn.execute(
        """
        INSERT INTO episodes
        (id, podcast_id, guid, title, pub_date, audio_url, kind, narrator, description_pure, best_place_id)
        VALUES
        (1, 1, 'g1', 'Episode 1', '2020-01-01T00:00:00Z', 'https://a', 'regular', 'n', 'desc', 1),
        (2, 1, 'g2', 'Episode 2', '2020-01-02T00:00:00Z', 'https://b', 'regular', 'n', 'desc', NULL)
        """
    )
    conn.execute(
        """
        INSERT INTO places_norm (id, norm_key, canonical_name, place_kind)
        VALUES
        (1, 'paris', 'Paris', 'city'),
        (2, 'berlin', 'Berlin', 'city')
        """
    )
    conn.execute(
        """
        INSERT INTO places
        (id, run_id, origin, locked, episode_id, segment_id, place_norm_id, name_raw, place_kind, latitude, longitude, radius_km)
        VALUES
        (1, NULL, 'det', 0, 1, NULL, 1, 'Paris', 'city', NULL, NULL, NULL),
        (2, NULL, 'det', 0, 1, NULL, 1, 'Paris', 'city', NULL, NULL, NULL),
        (3, NULL, 'det', 0, 2, NULL, 2, 'Berlin', 'city', NULL, NULL, NULL)
        """
    )
    conn.commit()
    conn.close()


def test_enrich_missing_place_coordinates_updates_rows_and_best_place(tmp_path: Path) -> None:
    db_path = tmp_path / "geo.db"
    _make_db(db_path)

    calls: list[str] = []

    def resolver(query: str, place_kind: str) -> GeocodeHit | None:
        calls.append(f"{query}|{place_kind}")
        if query == "Paris":
            return GeocodeHit(lat=48.8566, lon=2.3522, provider="test")
        if query == "Berlin":
            return GeocodeHit(lat=52.52, lon=13.405, provider="test")
        return None

    stats = enrich_missing_place_coordinates(
        db_path=db_path,
        resolver=resolver,
        dry_run=False,
        delay_seconds=0.0,
        cache_path=tmp_path / "cache.json",
    )

    assert stats["candidates"] == 2
    assert stats["resolved"] == 2
    assert stats["updated_rows"] == 3
    assert stats["best_place_updated"] == 1
    assert calls == ["Paris|city", "Berlin|city"]

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT id, latitude, longitude FROM places ORDER BY id"
    ).fetchall()
    assert rows == [
        (1, 48.8566, 2.3522),
        (2, 48.8566, 2.3522),
        (3, 52.52, 13.405),
    ]
    best_rows = conn.execute(
        "SELECT id, best_place_id FROM episodes ORDER BY id"
    ).fetchall()
    assert best_rows == [(1, 1), (2, 3)]
    conn.close()
