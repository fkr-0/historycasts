from __future__ import annotations

from podcast_atlas.export.cluster_metrics import compute_cluster_metrics


def test_compute_cluster_metrics_returns_expected_sections() -> None:
    payload = {
        "episodes": [
            {"id": 1, "podcast_id": 10, "pub_date_iso": "2020-01-01T00:00:00Z"},
            {"id": 2, "podcast_id": 10, "pub_date_iso": "2021-01-01T00:00:00Z"},
            {"id": 3, "podcast_id": 11, "pub_date_iso": "2022-01-01T00:00:00Z"},
        ],
        "spans": [
            {"episode_id": 1, "start_iso": "1910-01-01", "end_iso": "1912-12-31", "score": 0.8},
            {"episode_id": 2, "start_iso": "1920-01-01", "end_iso": "1921-12-31", "score": 0.9},
            {"episode_id": 3, "start_iso": "1911-01-01", "end_iso": "1914-12-31", "score": 0.7},
        ],
        "places": [
            {"episode_id": 1, "canonical_name": "Paris", "lat": 48.8, "lon": 2.3},
            {"episode_id": 2, "canonical_name": "Berlin", "lat": 52.5, "lon": 13.4},
            {"episode_id": 3, "canonical_name": "Paris", "lat": 48.8, "lon": 2.3},
        ],
        "entities": [
            {"episode_id": 1, "name": "Entity A", "kind": "person"},
            {"episode_id": 2, "name": "Entity A", "kind": "person"},
            {"episode_id": 3, "name": "Entity B", "kind": "org"},
        ],
        "episode_keywords": {
            "1": [{"phrase": "revolution", "score": 4.0}],
            "2": [{"phrase": "revolution", "score": 3.0}, {"phrase": "europe", "score": 2.0}],
            "3": [{"phrase": "europe", "score": 5.0}],
        },
        "episode_clusters": {"1": 100, "2": 100, "3": 101},
        "clusters": [
            {
                "cluster": {"id": 100},
                "top_keywords": [{"phrase": "revolution", "score": 4.0}, {"phrase": "europe", "score": 2.0}],
            },
            {"cluster": {"id": 101}, "top_keywords": [{"phrase": "europe", "score": 5.0}]},
        ],
    }

    result = compute_cluster_metrics(payload)
    assert set(result.keys()) == {
        "cluster_stats",
        "cluster_term_metrics",
        "cluster_correlations",
        "cluster_entity_stats",
        "cluster_place_stats",
        "cluster_timeline_histogram",
        "cluster_next_steps",
    }
    assert len(result["cluster_stats"]) == 2
    assert any(r["cluster_id"] == 100 for r in result["cluster_term_metrics"])
    assert any(r["cluster_id"] == 100 for r in result["cluster_timeline_histogram"])
    assert any(r["cluster_id"] == 100 for r in result["cluster_next_steps"])
