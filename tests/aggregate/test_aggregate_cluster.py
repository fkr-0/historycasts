import sqlite3

from podcast_atlas.aggregate.cluster import Point, k_for_n, kmeans
from podcast_atlas.aggregate.db_build import _recompute_clusters
from podcast_atlas.aggregate.schema import ensure_schema
from podcast_atlas.provenance import ORIGIN_DET, ORIGIN_NONDET, new_run


def test_k_for_n_clamped():
    assert k_for_n(0) == 0
    assert k_for_n(1) == 1
    assert k_for_n(3) == 1
    assert k_for_n(4) == 2
    assert k_for_n(300) <= 16


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
