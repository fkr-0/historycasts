from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
from pathlib import Path


def export_dataset(db_path: str, out_path: str, *, minify: bool = True) -> str:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    meta = {
        "schema_version": "2026-02-27-static",
        "generated_at_iso": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_db": str(Path(db_path).resolve()),
    }

    podcasts = [dict(r) for r in cur.execute("SELECT id, title, link, language FROM podcasts ORDER BY id").fetchall()]

    episodes = [
        {
            "id": r["id"],
            "podcast_id": r["podcast_id"],
            "title": r["title"],
            "pub_date_iso": r["pub_date"],
            "page_url": r["page_url"],
            "audio_url": r["audio_url"],
            "kind": r["kind"],
            "narrator": r["narrator"],
            "description_pure": r["description_pure"],
            "best_span_id": r["best_span_id"],
            "best_place_id": r["best_place_id"],
        }
        for r in cur.execute(
            "SELECT id,podcast_id,title,pub_date,page_url,audio_url,kind,narrator,description_pure,best_span_id,best_place_id FROM episodes ORDER BY podcast_id,pub_date"
        ).fetchall()
    ]

    spans = [
        {
            "id": r["id"],
            "episode_id": r["episode_id"],
            "start_iso": r["start_iso"],
            "end_iso": r["end_iso"],
            "precision": r["precision"],
            "qualifier": r["qualifier"],
            "score": r["score"],
            "source_section": r["source_section"],
            "source_text": r["source_text"],
        }
        for r in cur.execute(
            "SELECT id,episode_id,start_iso,end_iso,precision,qualifier,score,source_section,source_text FROM time_spans ORDER BY episode_id,score DESC"
        ).fetchall()
    ]

    places = [
        {
            "id": r["id"],
            "episode_id": r["episode_id"],
            "canonical_name": r["canonical_name"],
            "norm_key": r["norm_key"],
            "place_kind": r["place_kind"],
            "lat": r["latitude"],
            "lon": r["longitude"],
            "radius_km": r["radius_km"],
        }
        for r in cur.execute(
            """
            SELECT p.id,p.episode_id,
                   COALESCE(n.canonical_name, p.name_raw) AS canonical_name,
                   COALESCE(n.norm_key, lower(p.name_raw)) AS norm_key,
                   COALESCE(n.place_kind, p.place_kind) AS place_kind,
                   p.latitude,p.longitude,p.radius_km
            FROM places p
            LEFT JOIN places_norm n ON n.id = p.place_norm_id
            ORDER BY p.episode_id
            """
        ).fetchall()
    ]

    entities = [
        {
            "id": r["id"],
            "episode_id": r["episode_id"],
            "name": r["name"],
            "kind": r["kind"],
            "confidence": r["confidence"],
        }
        for r in cur.execute(
            "SELECT id,episode_id,name,kind,confidence FROM entities ORDER BY episode_id,confidence DESC"
        ).fetchall()
    ]

    episode_keywords: dict[str, list[dict]] = {}
    for r in cur.execute(
        """
        SELECT ek.episode_id, k.phrase, ek.score
        FROM episode_keywords ek
        JOIN keywords k ON k.id = ek.keyword_id
        ORDER BY ek.episode_id, ek.score DESC
        """
    ).fetchall():
        episode_keywords.setdefault(str(r["episode_id"]), []).append({"phrase": r["phrase"], "score": r["score"]})

    episode_clusters = {str(r["episode_id"]): r["cluster_id"] for r in cur.execute("SELECT episode_id,cluster_id FROM episode_clusters").fetchall()}

    clusters = [dict(r) for r in cur.execute("SELECT id,podcast_id,k,label,centroid_year,centroid_lat,centroid_lon FROM clusters ORDER BY podcast_id,id").fetchall()]

    # cluster summaries
    cluster_summaries = []
    for c in clusters:
        cid = c["id"]
        n_members = cur.execute("SELECT COUNT(*) FROM episode_clusters WHERE cluster_id=?", (cid,)).fetchone()[0]
        kws = [dict(r) for r in cur.execute("SELECT phrase,score FROM cluster_keywords WHERE cluster_id=? ORDER BY score DESC LIMIT 25", (cid,)).fetchall()]
        ents = [dict(r) for r in cur.execute("SELECT name,kind,score FROM cluster_entities WHERE cluster_id=? ORDER BY score DESC LIMIT 25", (cid,)).fetchall()]
        cluster_summaries.append({
            "cluster": {
                "id": cid,
                "podcast_id": c["podcast_id"],
                "k": c["k"],
                "label": c["label"],
                "centroid_mid_year": c["centroid_year"],
                "centroid_lat": c["centroid_lat"],
                "centroid_lon": c["centroid_lon"],
                "n_members": n_members,
            },
            "top_keywords": kws,
            "top_entities": [{"name": e["name"], "kind": e["kind"], "count": e["score"]} for e in ents],
        })

    payload = {
        "meta": meta,
        "podcasts": podcasts,
        "episodes": episodes,
        "spans": spans,
        "places": places,
        "entities": entities,
        "episode_keywords": episode_keywords,
        "episode_clusters": episode_clusters,
        "clusters": cluster_summaries,
    }

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        if minify:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    conn.close()
    return str(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Export dataset.json for static React app")
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args()
    p = export_dataset(args.db, args.out, minify=not args.pretty)
    print(p)


if __name__ == "__main__":
    main()
