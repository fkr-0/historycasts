from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .export.cluster_metrics import compute_cluster_metrics
from .models import (
    ClusterRow,
    ClusterSummary,
    EntityRow,
    EpisodeRow,
    ExportMeta,
    KeywordRow,
    PlaceRow,
    PodcastRow,
    SpanRow,
)

FINGERPRINT_FIELDS_EPISODE = (
    "id",
    "podcast_id",
    "title",
    "pub_date_iso",
    "kind",
    "narrator",
    "best_span_id",
    "best_place_id",
)
FINGERPRINT_FIELDS_SPAN = (
    "id",
    "episode_id",
    "start_iso",
    "end_iso",
    "precision",
    "qualifier",
    "score",
)
FINGERPRINT_FIELDS_PLACE = (
    "id",
    "episode_id",
    "canonical_name",
    "norm_key",
    "place_kind",
    "lat",
    "lon",
)
FINGERPRINT_FIELDS_ENTITY = (
    "id",
    "episode_id",
    "name",
    "kind",
    "confidence",
)
FINGERPRINT_FIELDS_CLUSTER = (
    "id",
    "podcast_id",
    "k",
    "centroid_mid_year",
    "centroid_lat",
    "centroid_lon",
    "n_members",
    "label",
)


def _dataset_revision(db_path: Path | str) -> str:
    p = Path(db_path)
    if not p.exists():
        return "missing-db"
    st = p.stat()
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}:{int(st.st_mtime)}:{st.st_size}"


def _fingerprint(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    data = {k: row.get(k) for k in keys}
    blob = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _table_names(cur: sqlite3.Cursor) -> set[str]:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cur.fetchall()}


def _table_columns(cur: sqlite3.Cursor, table: str) -> set[str]:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def _col_or_null(cols: set[str], name: str, alias: str | None = None) -> str:
    if name in cols:
        return name
    return f"NULL AS {alias or name}"


def detect_enrichment(cur: sqlite3.Cursor) -> Tuple[bool, bool]:
    tables = _table_names(cur)
    wiki_enriched = "concepts" in tables or "episode_concepts" in tables
    wikidata_enriched = "concept_claims" in tables or "cluster_entities" in tables
    return wiki_enriched, wikidata_enriched


def export_dataset(db_path: Path | str) -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = _table_names(cur)
    wiki_enriched, wikidata_enriched = detect_enrichment(cur)

    meta = ExportMeta(
        generated_at_iso=datetime.now(timezone.utc).isoformat(),
        source_db=os.path.abspath(str(db_path)),
        dataset_revision=_dataset_revision(db_path),
        wiki_enriched=wiki_enriched,
        wikidata_enriched=wikidata_enriched,
    ).model_dump()

    podcasts: List[Dict[str, Any]] = []
    podcast_cols = _table_columns(cur, "podcasts")
    cur.execute(
        "SELECT id, title, "
        f"{_col_or_null(podcast_cols, 'description')}, "
        f"{_col_or_null(podcast_cols, 'language')}, "
        f"{_col_or_null(podcast_cols, 'link')}, "
        f"{_col_or_null(podcast_cols, 'image_url')} "
        "FROM podcasts ORDER BY id"
    )
    for row in cur.fetchall():
        podcasts.append(
            PodcastRow(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                language=row["language"],
                link=row["link"],
                image_url=row["image_url"],
            ).model_dump()
        )

    episodes: List[Dict[str, Any]] = []
    episode_cols = _table_columns(cur, "episodes")
    pub_expr = "pub_date" if "pub_date" in episode_cols else "published_at AS pub_date"
    duration_expr = "duration" if "duration" in episode_cols else "duration_seconds AS duration"
    kind_expr = "kind" if "kind" in episode_cols else "incident_type AS kind"
    if "description_pure" in episode_cols:
        desc_expr = "description_pure"
    elif "description" in episode_cols:
        desc_expr = "description AS description_pure"
    else:
        desc_expr = "NULL AS description_pure"

    cur.execute(
        "SELECT id, podcast_id, guid, "
        f"{_col_or_null(episode_cols, 'page_url')}, "
        "title, "
        f"{pub_expr}, "
        f"{duration_expr}, "
        "audio_url, "
        f"{_col_or_null(episode_cols, 'episode_type')}, "
        f"{kind_expr}, "
        f"{_col_or_null(episode_cols, 'narrator')}, "
        f"{desc_expr}, "
        f"{_col_or_null(episode_cols, 'best_span_id')}, "
        f"{_col_or_null(episode_cols, 'best_place_id')} "
        "FROM episodes ORDER BY podcast_id, pub_date"
    )
    for row in cur.fetchall():
        episode = EpisodeRow(
            id=row["id"],
            podcast_id=row["podcast_id"],
            title=row["title"],
            pub_date_iso=row["pub_date"],
            kind=row["kind"],
            narrator=row["narrator"],
            description_pure=row["description_pure"],
            audio_url=row["audio_url"],
            page_url=row["page_url"],
            best_span_id=row["best_span_id"],
            best_place_id=row["best_place_id"],
        ).model_dump()
        episode["row_fingerprint"] = _fingerprint(episode, FINGERPRINT_FIELDS_EPISODE)
        episodes.append(episode)

    spans: List[Dict[str, Any]] = []
    if "time_spans" in tables:
        cur.execute(
            "SELECT id, episode_id, start_iso, end_iso, precision, qualifier, score, "
            "source_section, source_text, source_context FROM time_spans"
        )
        for row in cur.fetchall():
            span = SpanRow(
                id=row["id"],
                episode_id=row["episode_id"],
                start_iso=row["start_iso"],
                end_iso=row["end_iso"],
                precision=row["precision"],
                qualifier=row["qualifier"],
                score=row["score"],
                source_section=row["source_section"],
                source_text=row["source_text"],
                source_context=row["source_context"],
            ).model_dump()
            span["row_fingerprint"] = _fingerprint(span, FINGERPRINT_FIELDS_SPAN)
            spans.append(span)

    places: List[Dict[str, Any]] = []
    if "places" in tables:
        cur.execute(
            "SELECT p.id, p.episode_id, COALESCE(n.canonical_name, p.name_raw) AS canonical_name, "
            "COALESCE(n.norm_key, LOWER(p.name_raw)) AS norm_key, "
            "COALESCE(n.place_kind, p.place_kind) AS place_kind, "
            "p.latitude AS lat, p.longitude AS lon, p.radius_km "
            "FROM places p LEFT JOIN places_norm n ON n.id = p.place_norm_id"
        )
        for row in cur.fetchall():
            place = PlaceRow(
                id=row["id"],
                episode_id=row["episode_id"],
                canonical_name=row["canonical_name"],
                norm_key=row["norm_key"],
                place_kind=row["place_kind"] or "unknown",
                lat=row["lat"],
                lon=row["lon"],
                radius_km=row["radius_km"],
            ).model_dump()
            place["row_fingerprint"] = _fingerprint(place, FINGERPRINT_FIELDS_PLACE)
            places.append(place)

    entities: List[Dict[str, Any]] = []
    if "entities" in tables:
        cur.execute("SELECT id, episode_id, name, kind, confidence, source_text FROM entities")
        for row in cur.fetchall():
            entity = EntityRow(
                id=row["id"],
                episode_id=row["episode_id"],
                name=row["name"],
                kind=row["kind"] or "unknown",
                confidence=row["confidence"],
                source_text=row["source_text"],
            ).model_dump()
            entity["row_fingerprint"] = _fingerprint(entity, FINGERPRINT_FIELDS_ENTITY)
            entities.append(entity)

    episode_keywords: Dict[str, List[Dict[str, Any]]] = {}
    if "keywords" in tables:
        cur.execute("SELECT id, phrase FROM keywords")
        keywords_map = {row["id"]: row["phrase"] for row in cur.fetchall()}
        cur.execute("SELECT episode_id, keyword_id, score FROM episode_keywords")
        for row in cur.fetchall():
            phrase = keywords_map.get(row["keyword_id"])
            if phrase:
                episode_keywords.setdefault(str(row["episode_id"]), []).append(
                    KeywordRow(phrase=phrase, score=row["score"]).model_dump()
                )

    episode_clusters: Dict[str, int] = {}
    if "episode_clusters" in tables:
        cur.execute("SELECT episode_id, cluster_id FROM episode_clusters")
        for row in cur.fetchall():
            episode_clusters[str(row["episode_id"])] = row["cluster_id"]

    clusters: List[Dict[str, Any]] = []
    if "clusters" in tables:
        cur.execute("PRAGMA table_info(clusters)")
        cols = {c[1] for c in cur.fetchall()}
        if "centroid_mid_year" in cols:
            cur.execute(
                "SELECT id, podcast_id, k, centroid_mid_year, centroid_lat, centroid_lon, n_members, label FROM clusters"
            )
        else:
            cur.execute(
                "SELECT id, podcast_id, k, centroid_year AS centroid_mid_year, "
                "centroid_lat, centroid_lon, NULL AS n_members, label FROM clusters"
            )
        raw_clusters = cur.fetchall()

        cluster_keywords: Dict[int, List[Dict[str, Any]]] = {}
        if "cluster_keywords" in tables:
            cur.execute("PRAGMA table_info(cluster_keywords)")
            ccols = {c[1] for c in cur.fetchall()}
            if "keyword_id" in ccols:
                cur.execute(
                    "SELECT ck.cluster_id, k.phrase, ck.score FROM cluster_keywords ck "
                    "JOIN keywords k ON k.id = ck.keyword_id"
                )
            else:
                cur.execute("SELECT cluster_id, phrase, score FROM cluster_keywords")
            for row in cur.fetchall():
                cluster_keywords.setdefault(row["cluster_id"], []).append(
                    KeywordRow(phrase=row["phrase"], score=row["score"]).model_dump()
                )

        cluster_entities: Dict[int, List[Dict[str, Any]]] = {}
        if "cluster_entities" in tables:
            cur.execute("PRAGMA table_info(cluster_entities)")
            ecols = {c[1] for c in cur.fetchall()}
            if "cnt" in ecols:
                cur.execute("SELECT cluster_id, name, kind, cnt FROM cluster_entities")
            else:
                cur.execute("SELECT cluster_id, name, kind, score AS cnt FROM cluster_entities")
            for row in cur.fetchall():
                cluster_entities.setdefault(row["cluster_id"], []).append(
                    {"name": row["name"], "kind": row["kind"], "count": row["cnt"]}
                )

        member_counts: Dict[int, int] = {}
        if not any(c["n_members"] is not None for c in raw_clusters):
            for cid in episode_clusters.values():
                member_counts[cid] = member_counts.get(cid, 0) + 1

        for rc in raw_clusters:
            cid = rc["id"]
            n_members = (
                rc["n_members"] if rc["n_members"] is not None else member_counts.get(rc["id"], 0)
            )
            cluster_row = ClusterRow(
                id=rc["id"],
                podcast_id=rc["podcast_id"],
                k=rc["k"],
                centroid_mid_year=rc["centroid_mid_year"],
                centroid_lat=rc["centroid_lat"],
                centroid_lon=rc["centroid_lon"],
                n_members=n_members,
                label=rc["label"],
            )
            cluster_summary = ClusterSummary(
                cluster=cluster_row,
                top_keywords=[
                    KeywordRow(**kw)
                    for kw in sorted(cluster_keywords.get(cid, []), key=lambda x: -x["score"])[:25]
                ],
                top_entities=sorted(cluster_entities.get(cid, []), key=lambda x: -x["count"])[:25],
            ).model_dump()
            cluster_summary["cluster"]["row_fingerprint"] = _fingerprint(
                cluster_summary["cluster"], FINGERPRINT_FIELDS_CLUSTER
            )
            clusters.append(cluster_summary)

    concepts: List[Dict[str, Any]] = []
    episode_concepts: Dict[str, List[int]] = {}
    if wiki_enriched:
        cur.execute("PRAGMA table_info(concepts)")
        concept_cols = [c[1] for c in cur.fetchall()]
        if "name" in concept_cols:
            concept_select = ", ".join(
                c for c in concept_cols if c in ("id", "name", "url", "qid", "kind")
            )
            cur.execute(f"SELECT {concept_select} FROM concepts")
            for row in cur.fetchall():
                concepts.append(
                    {k: row[k] for k in row.keys() if k in ("id", "name", "url", "qid", "kind")}
                )
        if "episode_concepts" in tables:
            cur.execute("SELECT episode_id, concept_id FROM episode_concepts")
            for row in cur.fetchall():
                episode_concepts.setdefault(str(row["episode_id"]), []).append(row["concept_id"])

    concept_claims: List[Dict[str, Any]] = []
    if wikidata_enriched and "concept_claims" in tables:
        cur.execute("SELECT concept_id, property, value FROM concept_claims")
        for row in cur.fetchall():
            concept_claims.append(
                {
                    "concept_id": row["concept_id"],
                    "property": row["property"],
                    "value": row["value"],
                }
            )

    conn.close()

    payload: Dict[str, Any] = {
        "meta": meta,
        "podcasts": podcasts,
        "episodes": episodes,
        "spans": spans,
        "places": places,
        "entities": entities,
        "episode_keywords": episode_keywords,
        "episode_clusters": episode_clusters,
        "clusters": clusters,
    }

    payload.update(compute_cluster_metrics(payload))

    if wiki_enriched:
        payload["concepts"] = concepts
        payload["episode_concepts"] = episode_concepts
    if wikidata_enriched:
        payload["concept_claims"] = concept_claims
    return payload


def write_json(payload: Dict[str, Any], out_path: Path | str, *, minify: bool = False) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        if minify:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(payload, f, ensure_ascii=False, indent=2)
