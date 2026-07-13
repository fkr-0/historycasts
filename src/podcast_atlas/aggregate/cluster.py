from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass


@dataclass
class Point:
    episode_id: int
    mid_year: float
    lat: float
    lon: float


def _scale(points: list[Point]) -> list[tuple[int, tuple[float, float, float]]]:
    ys = [p.mid_year for p in points]
    lats = [p.lat for p in points]
    lons = [p.lon for p in points]

    def rng(vs):
        mn, mx = min(vs), max(vs)
        return mn, mx, (mx - mn) if mx != mn else 1.0

    y0, _, yr = rng(ys)
    la0, _, lar = rng(lats)
    lo0, _, lor = rng(lons)

    out = []
    for p in points:
        out.append(
            (p.episode_id, ((p.mid_year - y0) / yr, (p.lat - la0) / lar, (p.lon - lo0) / lor))
        )
    return out


def k_for_n(n: int) -> int:
    if n <= 0:
        return 0
    if n < 4:
        return 1
    # A plain sqrt(n) rule over-fragments the relatively small per-podcast
    # datasets used here and regularly produces singleton clusters. Target a
    # somewhat larger typical cluster while retaining a conservative cap.
    return min(16, max(2, int(round(math.sqrt(n / 2.0)))))


def kmeans(
    points: list[Point], k: int, iters: int = 25
) -> tuple[list[tuple[float, float, float]], dict[int, int]]:
    """Deterministic k-means: seeds evenly spaced in year-sorted order."""
    if k <= 0 or not points:
        return [], {}
    if k > len(points):
        k = len(points)

    scaled = _scale(points)
    # sort by first coord (scaled year)
    scaled_sorted = sorted(scaled, key=lambda x: x[1][0])

    # seeds: evenly spaced indices
    seeds_idx = [int(round(i * (len(scaled_sorted) - 1) / max(1, k - 1))) for i in range(k)]
    centroids = [scaled_sorted[i][1] for i in seeds_idx]

    def dist(a, b):
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2

    assign: dict[int, int] = {}
    sums: list[list[float]]
    for _ in range(iters):
        changed = False
        # assign
        for eid, v in scaled:
            best = min(range(k), key=lambda j: dist(v, centroids[j]))
            if assign.get(eid) != best:
                assign[eid] = best
                changed = True
        # recompute
        sums = [[0.0, 0.0, 0.0, 0.0] for _ in range(k)]
        for eid, v in scaled:
            j = assign[eid]
            sums[j][0] += v[0]
            sums[j][1] += v[1]
            sums[j][2] += v[2]
            sums[j][3] += 1
        for j in range(k):
            if sums[j][3] == 0:
                continue
            centroids[j] = (
                sums[j][0] / sums[j][3],
                sums[j][1] / sums[j][3],
                sums[j][2] / sums[j][3],
            )
        if not changed:
            break

    # Return centroids in original units (approx) by recomputing mean from original points per cluster
    clusters: list[list[Point]] = [[] for _ in range(k)]
    for p in points:
        clusters[assign[p.episode_id]].append(p)
    centroids_orig: list[tuple[float, float, float]] = []
    for pts in clusters:
        if not pts:
            centroids_orig.append((0.0, 0.0, 0.0))
            continue
        centroids_orig.append(
            (
                sum(p.mid_year for p in pts) / len(pts),
                sum(p.lat for p in pts) / len(pts),
                sum(p.lon for p in pts) / len(pts),
            )
        )
    return centroids_orig, assign


def merge_small_clusters(
    points: list[Point],
    assignments: dict[int, int],
    *,
    min_size: int = 2,
) -> tuple[list[tuple[float, float, float]], dict[int, int]]:
    """Merge singleton/tiny clusters into the nearest stable cluster.

    K-means can isolate a geographic or temporal outlier as a one-episode
    cluster. Such clusters are visually prominent but analytically weak. This
    pass keeps clusters with at least ``min_size`` members and reassigns smaller
    groups using the same normalized feature space as k-means.
    """
    if not points or not assignments:
        return [], {}

    counts = Counter(assignments.values())
    stable = sorted(cluster_id for cluster_id, count in counts.items() if count >= min_size)
    if not stable:
        # Deterministically retain the largest original group and absorb the rest.
        stable = [min(counts, key=lambda cluster_id: (-counts[cluster_id], cluster_id))]

    scaled_by_episode = dict(_scale(points))

    def scaled_centroid(cluster_id: int) -> tuple[float, float, float]:
        members = [
            scaled_by_episode[point.episode_id]
            for point in points
            if assignments[point.episode_id] == cluster_id
        ]
        return (
            sum(values[0] for values in members) / len(members),
            sum(values[1] for values in members) / len(members),
            sum(values[2] for values in members) / len(members),
        )

    stable_centroids = {cluster_id: scaled_centroid(cluster_id) for cluster_id in stable}

    def distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
        return sum((left[index] - right[index]) ** 2 for index in range(3))

    reassigned = assignments.copy()
    for point in points:
        current = assignments[point.episode_id]
        if current in stable:
            continue
        value = scaled_by_episode[point.episode_id]
        reassigned[point.episode_id] = min(
            stable,
            key=lambda cluster_id: (distance(value, stable_centroids[cluster_id]), cluster_id),
        )

    active = sorted(set(reassigned.values()))
    compact = {old_id: new_id for new_id, old_id in enumerate(active)}
    compact_assignments = {
        episode_id: compact[cluster_id] for episode_id, cluster_id in reassigned.items()
    }

    clusters: list[list[Point]] = [[] for _ in active]
    for point in points:
        clusters[compact_assignments[point.episode_id]].append(point)
    centroids = [
        (
            sum(point.mid_year for point in members) / len(members),
            sum(point.lat for point in members) / len(members),
            sum(point.lon for point in members) / len(members),
        )
        for members in clusters
    ]
    return centroids, compact_assignments
