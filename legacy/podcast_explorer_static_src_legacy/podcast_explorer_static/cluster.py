from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


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
        out.append((p.episode_id, ((p.mid_year - y0) / yr, (p.lat - la0) / lar, (p.lon - lo0) / lor)))
    return out


def k_for_n(n: int) -> int:
    if n <= 0:
        return 0
    return max(4, min(16, int(round(math.sqrt(n)))))


def kmeans(points: list[Point], k: int, iters: int = 25) -> tuple[list[tuple[float,float,float]], dict[int,int]]:
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

    def dist(a,b):
        return (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2

    assign: dict[int,int] = {}
    for _ in range(iters):
        changed = False
        # assign
        for eid, v in scaled:
            best = min(range(k), key=lambda j: dist(v, centroids[j]))
            if assign.get(eid) != best:
                assign[eid] = best
                changed = True
        # recompute
        sums = [(0.0,0.0,0.0,0) for _ in range(k)]
        sums = [list(s) for s in sums]
        for eid, v in scaled:
            j = assign[eid]
            sums[j][0] += v[0]; sums[j][1] += v[1]; sums[j][2] += v[2]; sums[j][3] += 1
        for j in range(k):
            if sums[j][3] == 0:
                continue
            centroids[j] = (sums[j][0]/sums[j][3], sums[j][1]/sums[j][3], sums[j][2]/sums[j][3])
        if not changed:
            break

    # Return centroids in original units (approx) by recomputing mean from original points per cluster
    clusters: list[list[Point]] = [[] for _ in range(k)]
    for p in points:
        clusters[assign[p.episode_id]].append(p)
    centroids_orig: list[tuple[float,float,float]] = []
    for pts in clusters:
        if not pts:
            centroids_orig.append((0.0,0.0,0.0))
            continue
        centroids_orig.append((
            sum(p.mid_year for p in pts)/len(pts),
            sum(p.lat for p in pts)/len(pts),
            sum(p.lon for p in pts)/len(pts),
        ))
    return centroids_orig, assign
