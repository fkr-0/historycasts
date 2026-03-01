from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import median
from typing import Any


def _year_from_iso(iso: str | None) -> int | None:
    if not iso or len(iso) < 4:
        return None
    try:
        return int(iso[:4])
    except ValueError:
        return None


def _safe_div(num: float, den: float) -> float:
    if den == 0:
        return 0.0
    return num / den


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[k] * b[k] for k in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return _safe_div(dot, na * nb)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _stddev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    m = sum(values) / len(values)
    var = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(var)


def _jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 0.0
    return _safe_div(len(a & b), len(a | b))


def compute_cluster_metrics(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    episodes = payload.get("episodes", [])
    spans = payload.get("spans", [])
    places = payload.get("places", [])
    entities = payload.get("entities", [])
    episode_clusters = payload.get("episode_clusters", {})
    episode_keywords = payload.get("episode_keywords", {})
    clusters = payload.get("clusters", [])

    ep_by_id = {int(e["id"]): e for e in episodes}
    cluster_to_episode_ids: dict[int, set[int]] = defaultdict(set)
    for ep_id_str, cid in episode_clusters.items():
        try:
            cluster_to_episode_ids[int(cid)].add(int(ep_id_str))
        except Exception:
            continue

    span_scores_by_ep: dict[int, list[float]] = defaultdict(list)
    span_years_by_ep: dict[int, list[int]] = defaultdict(list)
    for s in spans:
        ep_id = int(s["episode_id"])
        span_scores_by_ep[ep_id].append(float(s.get("score", 0.0)))
        for key in ("start_iso", "end_iso"):
            y = _year_from_iso(s.get(key))
            if y is not None:
                span_years_by_ep[ep_id].append(y)

    places_by_ep: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for p in places:
        places_by_ep[int(p["episode_id"])].append(p)

    entities_by_ep: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for ent in entities:
        entities_by_ep[int(ent["episode_id"])].append(ent)

    global_term_support: Counter[str] = Counter()
    for kws in episode_keywords.values():
        seen: set[str] = set()
        for kw in kws:
            term = str(kw["phrase"])
            if term not in seen:
                global_term_support[term] += 1
                seen.add(term)

    cluster_stats: list[dict[str, Any]] = []
    cluster_term_metrics: list[dict[str, Any]] = []
    cluster_timeline_histogram: list[dict[str, Any]] = []
    cluster_entity_stats: list[dict[str, Any]] = []
    cluster_place_stats: list[dict[str, Any]] = []
    cluster_next_steps: list[dict[str, Any]] = []

    total_episodes = max(1, len(episodes))

    # Extract term vectors from cluster summaries when available.
    cluster_term_vectors: dict[int, dict[str, float]] = {}
    for c in clusters:
        cid = int(c["cluster"]["id"])
        tv: dict[str, float] = {}
        for kw in c.get("top_keywords", []):
            tv[str(kw["phrase"])] = float(kw.get("score", 0.0))
        cluster_term_vectors[cid] = tv

    for cid, ep_ids in sorted(cluster_to_episode_ids.items()):
        member_eps = [ep_by_id[eid] for eid in ep_ids if eid in ep_by_id]
        episode_count = len(member_eps)
        podcast_counts = Counter(int(e.get("podcast_id", -1)) for e in member_eps)
        dominant_podcast_share = _safe_div(max(podcast_counts.values(), default=0), episode_count)
        years = sorted(y for e in member_eps if (y := _year_from_iso(e.get("pub_date_iso"))) is not None)
        median_pub_year = int(median(years)) if years else None

        span_scores: list[float] = []
        mention_years: list[int] = []
        cluster_places: list[dict[str, Any]] = []
        cluster_entities: list[dict[str, Any]] = []
        for eid in ep_ids:
            span_scores.extend(span_scores_by_ep.get(eid, []))
            mention_years.extend(span_years_by_ep.get(eid, []))
            cluster_places.extend(places_by_ep.get(eid, []))
            cluster_entities.extend(entities_by_ep.get(eid, []))

        temporal_span_years = None
        if mention_years:
            temporal_span_years = max(mention_years) - min(mention_years)
        mean_span_confidence = _mean(span_scores)

        lats = [float(p["lat"]) for p in cluster_places if p.get("lat") is not None]
        lons = [float(p["lon"]) for p in cluster_places if p.get("lon") is not None]
        geo_dispersion = None
        if lats and lons and len(lats) == len(lons):
            # Average of coordinate stddevs as a compact dispersion proxy.
            lat_sd = _stddev(lats) or 0.0
            lon_sd = _stddev(lons) or 0.0
            geo_dispersion = (lat_sd + lon_sd) / 2.0

        term_vector = cluster_term_vectors.get(cid, {})
        total_term_weight = sum(term_vector.values())
        cohesion_proxy = None
        if total_term_weight > 0:
            cohesion_proxy = max(term_vector.values()) / total_term_weight

        cluster_stats.append(
            {
                "cluster_id": cid,
                "episode_count": episode_count,
                "unique_podcast_count": len(podcast_counts),
                "dominant_podcast_share": round(dominant_podcast_share, 6),
                "median_pub_year": median_pub_year,
                "temporal_span_years": temporal_span_years,
                "mean_span_confidence": round(mean_span_confidence, 6) if mean_span_confidence is not None else None,
                "geo_dispersion": round(geo_dispersion, 6) if geo_dispersion is not None else None,
                "cohesion_proxy": round(cohesion_proxy, 6) if cohesion_proxy is not None else None,
            }
        )

        # Timeline histogram (10-year bins).
        if mention_years:
            bins: Counter[tuple[int, int]] = Counter()
            for y in mention_years:
                start = (y // 10) * 10
                bins[(start, start + 9)] += 1
            for (start, end), count in sorted(bins.items()):
                cluster_timeline_histogram.append(
                    {"cluster_id": cid, "start_year": start, "end_year": end, "count": count}
                )

        # Term metrics with support/lift/drop-impact approximation.
        for term, tfidf in term_vector.items():
            support = 0
            for eid in ep_ids:
                kws = episode_keywords.get(str(eid), [])
                if any(str(kw.get("phrase")) == term for kw in kws):
                    support += 1
            global_support = int(global_term_support.get(term, 0))
            cluster_rate = _safe_div(support, episode_count)
            global_rate = _safe_div(global_support, total_episodes)
            lift = _safe_div(cluster_rate, global_rate) if global_rate > 0 else 0.0
            drop_impact = abs(tfidf) * lift
            cluster_term_metrics.append(
                {
                    "cluster_id": cid,
                    "term": term,
                    "tfidf": round(float(tfidf), 6),
                    "support": support,
                    "global_support": global_support,
                    "lift": round(lift, 6),
                    "drop_impact": round(drop_impact, 6),
                }
            )

        # Entity and place stats.
        global_entity_counts: Counter[tuple[str, str]] = Counter(
            (str(e.get("name", "")), str(e.get("kind", "unknown"))) for e in entities
        )
        cluster_entity_counts: Counter[tuple[str, str]] = Counter(
            (str(e.get("name", "")), str(e.get("kind", "unknown"))) for e in cluster_entities
        )
        for (name, kind), count in cluster_entity_counts.most_common(50):
            global_count = max(1, global_entity_counts[(name, kind)])
            lift = _safe_div(_safe_div(count, max(1, len(cluster_entities))), _safe_div(global_count, max(1, len(entities))))
            cluster_entity_stats.append(
                {
                    "cluster_id": cid,
                    "name": name,
                    "kind": kind,
                    "count": count,
                    "lift": round(lift, 6),
                }
            )

        global_place_counts: Counter[str] = Counter(str(p.get("canonical_name", "")) for p in places)
        cluster_place_counts: Counter[str] = Counter(str(p.get("canonical_name", "")) for p in cluster_places)
        place_coords: dict[str, tuple[float | None, float | None]] = {}
        for p in cluster_places:
            name = str(p.get("canonical_name", ""))
            if name not in place_coords:
                place_coords[name] = (p.get("lat"), p.get("lon"))
        for name, count in cluster_place_counts.most_common(50):
            global_count = max(1, global_place_counts[name])
            lift = _safe_div(_safe_div(count, max(1, len(cluster_places))), _safe_div(global_count, max(1, len(places))))
            lat, lon = place_coords.get(name, (None, None))
            cluster_place_stats.append(
                {
                    "cluster_id": cid,
                    "canonical_name": name,
                    "count": count,
                    "lift": round(lift, 6),
                    "lat": lat,
                    "lon": lon,
                }
            )

        # Next-step suggestions.
        top_terms = [
            t for t in cluster_term_metrics if t["cluster_id"] == cid
        ]
        top_terms.sort(key=lambda x: x["lift"], reverse=True)
        if top_terms:
            top = top_terms[0]
            cluster_next_steps.append(
                {
                    "cluster_id": cid,
                    "title": f"Investigate high-lift term: {top['term']}",
                    "rationale": "This term is unusually concentrated in this cluster.",
                    "action_type": "apply_term_filter",
                    "action_payload": {"term": top["term"], "cluster_id": cid},
                }
            )

    # Pairwise correlations.
    cluster_ids = sorted(cluster_to_episode_ids.keys())
    cluster_correlations: list[dict[str, Any]] = []
    for i, a in enumerate(cluster_ids):
        for b in cluster_ids[i + 1 :]:
            jaccard = _jaccard(cluster_to_episode_ids[a], cluster_to_episode_ids[b])
            cosine = _cosine_similarity(cluster_term_vectors.get(a, {}), cluster_term_vectors.get(b, {}))
            bridge_terms = sorted(
                set(cluster_term_vectors.get(a, {})) & set(cluster_term_vectors.get(b, {})),
                key=lambda t: (cluster_term_vectors.get(a, {}).get(t, 0.0) + cluster_term_vectors.get(b, {}).get(t, 0.0)),
                reverse=True,
            )[:5]
            if jaccard > 0 or cosine > 0:
                cluster_correlations.append(
                    {
                        "cluster_a": a,
                        "cluster_b": b,
                        "jaccard_episode_overlap": round(jaccard, 6),
                        "cosine_term_similarity": round(cosine, 6),
                        "bridge_terms": bridge_terms,
                    }
                )

    return {
        "cluster_stats": cluster_stats,
        "cluster_term_metrics": cluster_term_metrics,
        "cluster_correlations": cluster_correlations,
        "cluster_entity_stats": cluster_entity_stats,
        "cluster_place_stats": cluster_place_stats,
        "cluster_timeline_histogram": cluster_timeline_histogram,
        "cluster_next_steps": cluster_next_steps,
    }
