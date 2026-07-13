import sqlite3
from collections import Counter

from podcast_atlas.aggregate.cluster import Point, k_for_n, kmeans, merge_small_clusters
from podcast_atlas.aggregate.db_build import (
    _period_label,
    _recompute_clusters,
    _segment_index_column,
    _select_best_place_id,
    apply_heuristic_review_overrides,
)
from podcast_atlas.aggregate.schema import ensure_schema
from podcast_atlas.provenance import ORIGIN_DET, ORIGIN_NONDET, new_run


def test_k_for_n_clamped():
    assert k_for_n(0) == 0
    assert k_for_n(1) == 1
    assert k_for_n(3) == 1
    assert k_for_n(4) == 2
    assert k_for_n(15) == 3
    assert k_for_n(300) <= 16


def test_best_place_prefers_selected_span_segment() -> None:
    candidates = [
        (10, 1, "main", "city", 0),
        (11, 2, "main", "country", 1),
        (12, 3, "caption", "city", 2),
    ]

    assert _select_best_place_id(candidates, best_span_segment_id=2) == 11


def test_best_place_falls_back_to_main_city_and_mention_order() -> None:
    candidates = [
        (10, 1, "outline", "country", 0),
        (11, 2, "main", "city", 1),
        (12, 3, "main", "city", 2),
    ]

    assert _select_best_place_id(candidates, best_span_segment_id=None) == 11


def test_segment_index_column_supports_legacy_name() -> None:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE segments (id INTEGER PRIMARY KEY, episode_id INTEGER, section TEXT, seg_idx INTEGER, text TEXT)"
    )

    assert _segment_index_column(conn) == "seg_idx"
    conn.close()


def test_period_label_handles_ce_and_bce_centuries() -> None:
    assert _period_label(1881) == "19. Jh."
    assert _period_label(536) == "6. Jh."
    assert _period_label(-48) == "1. Jh. v. Chr."


def test_kmeans_deterministic_assignments():
    pts = [
        Point(1, 1000.0, 50.0, 10.0),
        Point(2, 1010.0, 50.1, 10.1),
        Point(3, 1800.0, 48.0, 2.0),
        Point(4, 1810.0, 48.1, 2.1),
        Point(5, 1900.0, 40.0, -74.0),
        Point(6, 1910.0, 40.1, -74.1),
    ]
    cent1, a1 = kmeans(pts, k=3)
    cent2, a2 = kmeans(pts, k=3)
    assert a1 == a2
    assert len(cent1) == 3


def test_merge_small_clusters_absorbs_singletons_and_compacts_ids() -> None:
    points = [
        Point(1, 1800.0, 48.0, 16.0),
        Point(2, 1810.0, 48.1, 16.1),
        Point(3, 1820.0, 48.2, 16.2),
        Point(4, 1900.0, 52.0, 13.0),
        Point(5, 1910.0, 52.1, 13.1),
        Point(6, 250.0, 41.9, 12.5),
    ]
    assignments = {1: 0, 2: 0, 3: 0, 4: 2, 5: 2, 6: 5}

    centroids, merged = merge_small_clusters(points, assignments, min_size=2)

    counts = Counter(merged.values())
    assert sorted(counts) == [0, 1]
    assert min(counts.values()) >= 2
    assert len(centroids) == 2


def test_recompute_clusters_preserves_nondet_rows() -> None:
    conn = sqlite3.connect(":memory:")
    ensure_schema(conn)
    det_run = new_run(conn, origin=ORIGIN_DET, tool="det", params={})
    nd_run = new_run(conn, origin=ORIGIN_NONDET, tool="manual", params={})

    conn.execute("INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'p', 'f')")
    # Existing nondet curated cluster
    conn.execute(
        """
        INSERT INTO clusters (id, run_id, origin, podcast_id, k, label, centroid_year, centroid_lat, centroid_lon)
        VALUES (100, ?, 'nondet', 1, 4, 'CURATED', 1900, 48, 2)
        """,
        (nd_run,),
    )
    conn.execute(
        """
        INSERT INTO cluster_keywords (run_id, origin, locked, cluster_id, phrase, score)
        VALUES (?, 'nondet', 1, 100, 'curated', 1.0)
        """,
        (nd_run,),
    )
    conn.execute(
        """
        INSERT INTO cluster_entities (run_id, origin, locked, cluster_id, name, kind, score)
        VALUES (?, 'nondet', 1, 100, 'Ada Lovelace', 'person', 1.0)
        """,
        (nd_run,),
    )
    # Existing deterministic cluster to be pruned
    conn.execute(
        """
        INSERT INTO clusters (id, run_id, origin, podcast_id, k, label, centroid_year, centroid_lat, centroid_lon)
        VALUES (101, ?, 'det', 1, 4, 'DET', 1900, 48, 2)
        """,
        (det_run,),
    )
    conn.commit()

    _recompute_clusters(conn, run_id=det_run)

    nd_cnt = conn.execute("SELECT COUNT(*) FROM clusters WHERE origin='nondet'").fetchone()[0]
    det_cnt = conn.execute("SELECT COUNT(*) FROM clusters WHERE origin='det'").fetchone()[0]
    assert nd_cnt == 1
    assert det_cnt == 0
    conn.close()


def test_recompute_clusters_uses_geocoded_candidate_when_best_place_is_unresolved() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    det_run = new_run(conn, origin=ORIGIN_DET, tool="det", params={})
    nd_run = new_run(conn, origin=ORIGIN_NONDET, tool="curated", params={})
    conn.execute("INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'p', 'f')")
    for episode_id, year in enumerate((1800, 1810, 1900, 1910), start=1):
        conn.execute(
            "INSERT INTO episodes (id, podcast_id, guid, title) VALUES (?, 1, ?, ?)",
            (episode_id, f"g{episode_id}", f"t{episode_id}"),
        )
        conn.execute(
            "INSERT INTO segments (id, episode_id, section, idx, text) VALUES (?, ?, 'main', 0, ?)",
            (episode_id, episode_id, f"Im Jahr {year} in Wien"),
        )
        span_id = 100 + episode_id
        conn.execute(
            """
            INSERT INTO time_spans
            (id, run_id, origin, locked, episode_id, segment_id, start_iso, end_iso,
             precision, qualifier, source_text, source_section, source_context, score)
            VALUES (?, ?, 'det', 0, ?, ?, ?, ?, 'year', 'year', ?, 'main', ?, 8)
            """,
            (
                span_id,
                det_run,
                episode_id,
                episode_id,
                f"{year}-01-01",
                f"{year}-12-31",
                str(year),
                f"Im Jahr {year} in Wien",
            ),
        )
        unresolved_id = 200 + episode_id
        conn.execute(
            """
            INSERT INTO places
            (id, run_id, origin, locked, episode_id, segment_id, name_raw, place_kind,
             latitude, longitude, radius_km)
            VALUES (?, ?, 'nondet', 1, ?, NULL, 'Curated unresolved', 'city', NULL, NULL, 25)
            """,
            (unresolved_id, nd_run, episode_id),
        )
        conn.execute(
            """
            INSERT INTO places
            (id, run_id, origin, locked, episode_id, segment_id, name_raw, place_kind,
             latitude, longitude, radius_km)
            VALUES (?, ?, 'det', 0, ?, ?, 'Wien', 'city', 48.2, 16.3, 25)
            """,
            (300 + episode_id, det_run, episode_id, episode_id),
        )
        conn.execute(
            "UPDATE episodes SET best_span_id=?, best_place_id=? WHERE id=?",
            (span_id, unresolved_id, episode_id),
        )
    conn.commit()

    _recompute_clusters(conn, run_id=det_run)

    assert conn.execute("SELECT COUNT(*) FROM episode_clusters").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM clusters").fetchone()[0] == 2
    assert all(
        "Jh." in row[0] and "Wien" in row[0]
        for row in conn.execute("SELECT label FROM clusters").fetchall()
    )
    conn.close()


def test_heuristic_review_does_not_override_handcrafted_span() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    det_run = new_run(conn, origin=ORIGIN_DET, tool="det", params={})
    nd_run = new_run(conn, origin=ORIGIN_NONDET, tool="handcrafted", params={})
    conn.execute("INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'p', 'f')")
    conn.execute("INSERT INTO episodes (id, podcast_id, guid, title) VALUES (1, 1, 'g', 't')")
    conn.execute(
        "INSERT INTO segments (id, episode_id, section, idx, text) VALUES (1, 1, 'main', 0, 'Im Jahr 1881')"
    )
    conn.execute(
        """
        INSERT INTO time_spans
        (id, run_id, origin, locked, episode_id, segment_id, start_iso, end_iso,
         precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES (1, ?, 'nondet', 1, 1, NULL, '1801-01-01', '1900-12-31',
                'century', 'handcrafted', '19. Jahrhundert', 'description', 'curated', 20,
                'handcrafted-res-json')
        """,
        (nd_run,),
    )
    conn.execute(
        """
        INSERT INTO time_spans
        (id, run_id, origin, locked, episode_id, segment_id, start_iso, end_iso,
         precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES (2, ?, 'det', 0, 1, 1, '1881-01-01', '1881-12-31',
                'year', 'year', '1881', 'main', 'Im Jahr 1881', 6, NULL)
        """,
        (det_run,),
    )
    conn.execute("UPDATE episodes SET best_span_id=1 WHERE id=1")
    conn.commit()

    inserted = apply_heuristic_review_overrides(conn, year_max=2026)

    assert inserted == 0
    assert conn.execute("SELECT best_span_id FROM episodes WHERE id=1").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM time_spans").fetchone()[0] == 2
    conn.close()


def test_heuristic_review_replaces_caption_warning_with_main_span() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    det_run = new_run(conn, origin=ORIGIN_DET, tool="det", params={})
    conn.execute("INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'p', 'f')")
    conn.execute("INSERT INTO episodes (id, podcast_id, guid, title) VALUES (1, 1, 'g', 't')")
    conn.execute(
        "INSERT INTO segments (id, episode_id, section, idx, text) VALUES (1, 1, 'caption', 0, 'Bild 2023')"
    )
    conn.execute(
        "INSERT INTO segments (id, episode_id, section, idx, text) VALUES (2, 1, 'main', 1, 'Im Jahr 1881')"
    )
    conn.execute(
        """
        INSERT INTO time_spans
        (id, run_id, origin, locked, episode_id, segment_id, start_iso, end_iso,
         precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES (1, ?, 'det', 0, 1, 1, '2023-01-01', '2023-12-31',
                'year', 'year', '2023', 'caption', 'Bild 2023', 7, 'caption-folgenbild')
        """,
        (det_run,),
    )
    conn.execute(
        """
        INSERT INTO time_spans
        (id, run_id, origin, locked, episode_id, segment_id, start_iso, end_iso,
         precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES (2, ?, 'det', 0, 1, 2, '1881-01-01', '1881-12-31',
                'year', 'year', '1881', 'main', 'Im Jahr 1881', 6, NULL)
        """,
        (det_run,),
    )
    conn.execute("UPDATE episodes SET best_span_id=1 WHERE id=1")
    conn.commit()

    inserted = apply_heuristic_review_overrides(conn, year_max=2026)

    assert inserted == 1
    best = conn.execute(
        "SELECT ts.origin, ts.locked, ts.start_iso, ts.review_flag "
        "FROM episodes e JOIN time_spans ts ON ts.id=e.best_span_id WHERE e.id=1"
    ).fetchone()
    assert tuple(best) == ("nondet", 1, "1881-01-01", "review-override")
    conn.close()
