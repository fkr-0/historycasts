from podcast_explorer_static.cluster import Point, k_for_n, kmeans


def test_k_for_n_clamped():
    assert k_for_n(1) == 4  # clamped up
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
