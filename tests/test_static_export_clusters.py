from __future__ import annotations

import sqlite3
from pathlib import Path

from podcast_atlas.aggregate.schema import ensure_schema
from podcast_atlas.static_export import export_dataset


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    ensure_schema(conn)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'Test Podcast', 'https://example.test/feed')"
    )
    cur.execute(
        """
        INSERT INTO episodes
        (id, podcast_id, guid, title, pub_date, audio_url, kind, narrator, description_pure)
        VALUES (1, 1, 'g1', 'Episode One', '2020-01-01T00:00:00Z', 'https://a', 'regular', 'N1', 'desc')
        """
    )
    cur.execute(
        """
        INSERT INTO episodes
        (id, podcast_id, guid, title, pub_date, audio_url, kind, narrator, description_pure)
        VALUES (2, 1, 'g2', 'Episode Two', '2021-01-01T00:00:00Z', 'https://b', 'regular', 'N2', 'desc')
        """
    )
    cur.execute(
        """
        INSERT INTO time_spans
        (id, episode_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score)
        VALUES (1, 1, '1910-01-01', '1912-12-31', 'year', 'range', 'span', 'main', 'ctx', 0.9)
        """
    )
    cur.execute(
        """
        INSERT INTO time_spans
        (id, episode_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score)
        VALUES (2, 2, '1920-01-01', '1921-12-31', 'year', 'range', 'span', 'main', 'ctx', 0.8)
        """
    )
    cur.execute(
        "INSERT INTO places_norm (id, norm_key, canonical_name, place_kind) VALUES (1, 'paris', 'Paris', 'city')"
    )
    cur.execute(
        """
        INSERT INTO places (id, episode_id, place_norm_id, name_raw, place_kind, latitude, longitude, radius_km)
        VALUES (1, 1, 1, 'Paris', 'city', 48.8, 2.3, 10.0)
        """
    )
    cur.execute(
        """
        INSERT INTO entities (id, episode_id, name, kind, confidence, source_text)
        VALUES (1, 1, 'Entity A', 'person', 0.8, 'src')
        """
    )
    cur.execute("INSERT INTO keywords (id, phrase) VALUES (1, 'revolution')")
    cur.execute("INSERT INTO episode_keywords (episode_id, keyword_id, score) VALUES (1, 1, 3.0)")
    cur.execute(
        """
        INSERT INTO clusters (id, podcast_id, k, label, centroid_year, centroid_lat, centroid_lon)
        VALUES (10, 1, 2, 'C1', 1911.0, 48.8, 2.3)
        """
    )
    cur.execute("INSERT INTO episode_clusters (episode_id, cluster_id) VALUES (1, 10)")
    cur.execute(
        "INSERT INTO cluster_keywords (cluster_id, phrase, score) VALUES (10, 'revolution', 3.0)"
    )
    cur.execute(
        "INSERT INTO cluster_entities (cluster_id, name, kind, score) VALUES (10, 'Entity A', 'person', 1.0)"
    )
    conn.commit()
    conn.close()


def test_export_dataset_includes_cluster_metric_sections(tmp_path: Path) -> None:
    db_path = tmp_path / "clusters.db"
    _seed_db(db_path)

    payload = export_dataset(db_path)

    assert payload["meta"]["dataset_revision"]
    assert "cluster_stats" in payload
    assert "cluster_term_metrics" in payload
    assert "cluster_correlations" in payload
    assert "cluster_timeline_histogram" in payload
    assert "cluster_next_steps" in payload
    assert payload["episodes"][0]["row_fingerprint"]
    assert payload["clusters"][0]["cluster"]["row_fingerprint"]
