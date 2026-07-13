from __future__ import annotations

import datetime as dt
import re
import sqlite3
from typing import Optional

from ..provenance import ORIGIN_DET, ORIGIN_NONDET, new_run
from .cluster import Point, k_for_n, kmeans, merge_small_clusters
from .extract import (
    clean_description,
    extract_entities,
    extract_places,
    extract_spans,
    rake_phrases,
    segment_text,
)
from .gazetteer import load_gazetteer_csv, norm_key
from .rss_parse import parse_rss
from .schema import ensure_schema

_URL_RE = re.compile(r"https?://\S+")
DEFAULT_YEAR_MAX = dt.datetime.now(dt.timezone.utc).year


def _rowid(cur: sqlite3.Cursor) -> int:
    rowid = cur.lastrowid
    if rowid is None:
        raise RuntimeError("sqlite lastrowid is None after insert")
    return int(rowid)


def _classify_kind(title: str) -> str:
    t = title.lower()
    if "hb" in t and "gag" in t:
        return "book"
    if any(k in t for k in ["bonus", "live", "spezial", "special"]):
        return "special"
    if any(k in t for k in ["ankündigung", "update", "meta", "hinweis"]):
        return "meta"
    return "regular"


def _detect_narrator(author: Optional[str], desc: str) -> Optional[str]:
    # Prefer explicit author
    if author and author.strip():
        return author.strip()
    names = set()
    for m in re.finditer(r"\b(Richard|Daniel)\s+liest\b", desc, re.IGNORECASE):
        names.add(m.group(1).capitalize())
    return ", ".join(sorted(names)) if names else None


def _ensure_place_norm(conn: sqlite3.Connection, canonical: str, kind: str) -> int:
    nk = norm_key(canonical)
    cur = conn.execute("SELECT id FROM places_norm WHERE norm_key=?", (nk,))
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur = conn.execute(
        "INSERT INTO places_norm (norm_key, canonical_name, place_kind) VALUES (?, ?, ?)",
        (nk, canonical, kind),
    )
    return _rowid(cur)


def _upsert_podcast(conn: sqlite3.Connection, info) -> int:
    row = conn.execute("SELECT id FROM podcasts WHERE feed_url=?", (info.feed_url,)).fetchone()
    if row:
        return int(row[0])
    cur = conn.execute(
        """
        INSERT INTO podcasts (title, description, language, link, image_url, feed_url, feed_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            info.title,
            info.description,
            info.language,
            info.link,
            info.image_url,
            info.feed_url,
            info.feed_type,
        ),
    )
    conn.commit()
    return _rowid(cur)


def _insert_episode(
    conn: sqlite3.Connection, podcast_id: int, item, *, limit_existing: bool = True
) -> Optional[int]:
    # guid unique
    if limit_existing:
        row = conn.execute("SELECT id FROM episodes WHERE guid=?", (item.guid,)).fetchone()
        if row:
            return None
    kind = _classify_kind(item.title)
    pure = clean_description(item.description_raw)
    narrator = _detect_narrator(item.author, pure)
    cur_raw = conn.execute(
        """
        INSERT OR IGNORE INTO episodes_raw
        (podcast_id, guid, title, pub_date, page_url, audio_url, duration_sec, author, description_raw)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            podcast_id,
            item.guid,
            item.title,
            item.pub_date.isoformat(),
            item.page_url,
            item.audio_url,
            item.duration_sec,
            item.author,
            item.description_raw,
        ),
    )
    raw_id = (
        _rowid(cur_raw)
        if cur_raw.lastrowid is not None
        else int(
            conn.execute(
                "SELECT id FROM episodes_raw WHERE podcast_id=? AND guid=?",
                (podcast_id, item.guid),
            ).fetchone()[0]
        )
    )

    cur = conn.execute(
        """
        INSERT INTO episodes
        (podcast_id, raw_id, guid, page_url, title, pub_date, duration, audio_url, episode_type, kind, narrator, description_raw, description_pure)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            podcast_id,
            raw_id,
            item.guid,
            item.page_url,
            item.title,
            item.pub_date.isoformat(),
            item.duration_sec,
            item.audio_url,
            item.episode_type,
            kind,
            narrator,
            item.description_raw,
            pure,
        ),
    )
    conn.commit()
    return _rowid(cur)


def _insert_links(conn: sqlite3.Connection, episode_id: int, raw: str, page_url: str) -> None:
    urls = [u.rstrip('.,);"') for u in _URL_RE.findall(raw or "")]
    if not urls:
        return
    internal_dom = None
    if page_url:
        m = re.match(r"https?://([^/]+)/", page_url)
        internal_dom = m.group(1) if m else None

    rows = []
    for u in urls:
        lt = "external"
        if internal_dom and internal_dom in u:
            lt = "internal"
        if any(
            x in u.lower()
            for x in ["instagram", "tiktok", "facebook", "linktr", "seven.one", "ardsoundsfestival"]
        ):
            lt = "advert"
        rows.append((episode_id, u, lt))
    conn.executemany("INSERT INTO links (episode_id, url, link_type) VALUES (?, ?, ?)", rows)
    conn.commit()


def _mid_year(start_iso: str, end_iso: str) -> Optional[float]:
    try:
        s = dt.date.fromisoformat(start_iso[:10])
        e = dt.date.fromisoformat(end_iso[:10])
        mid = s + (e - s) / 2
        return mid.year + (mid.timetuple().tm_yday / 366.0)
    except Exception:
        return None


def _select_best_place_id(
    candidates: list[tuple[int, int, str, str, int]],
    *,
    best_span_segment_id: int | None,
) -> int | None:
    """Choose the place supported by the strongest available narrative context.

    Candidate tuples contain ``(place_id, segment_id, section, kind, order)``.
    A place mentioned in the same segment as the selected historical span is
    substantially preferable to an incidental place elsewhere in the notes.
    """
    if not candidates:
        return None

    section_weight = {"title": 4.0, "main": 3.0, "outline": 2.0, "caption": 0.0}
    kind_weight = {"city": 0.4, "region": 0.3, "country": 0.15, "unknown": 0.0}

    def score(row: tuple[int, int, str, str, int]) -> tuple[float, int]:
        place_id, segment_id, section, kind, order = row
        same_segment = 5.0 if best_span_segment_id == segment_id else 0.0
        value = (
            same_segment
            + section_weight.get(section, 1.0)
            + kind_weight.get(kind, 0.0)
            - min(order, 50) * 0.01
        )
        # Negated id gives deterministic preference to the earlier insertion.
        return value, -place_id

    return max(candidates, key=score)[0]


def _segment_index_column(conn: sqlite3.Connection) -> str:
    columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(segments)").fetchall()}
    if "idx" in columns:
        return "idx"
    if "seg_idx" in columns:
        return "seg_idx"
    raise RuntimeError("segments table has neither idx nor seg_idx column")


def _period_label(mid_year: float) -> str:
    year = int(round(mid_year))
    if year < 0:
        century = ((abs(year) - 1) // 100) + 1
        return f"{century}. Jh. v. Chr."
    if year == 0:
        return "Zeitenwende"
    century = ((year - 1) // 100) + 1
    return f"{century}. Jh."


def _dominant_cluster_place(conn: sqlite3.Connection, episode_ids: list[int]) -> str | None:
    if not episode_ids:
        return None
    placeholders = ",".join("?" for _ in episode_ids)
    row = conn.execute(
        f"""
        WITH ranked AS (
          SELECT
            e.id AS episode_id,
            COALESCE(NULLIF(pn.canonical_name, ''), NULLIF(p.name_raw, '')) AS place_name,
            ROW_NUMBER() OVER (
              PARTITION BY e.id
              ORDER BY
                CASE WHEN p.segment_id = ts.segment_id THEN 1 ELSE 0 END DESC,
                COALESCE(p.locked, 0) DESC,
                CASE COALESCE(p.origin, 'det') WHEN 'nondet' THEN 1 ELSE 0 END DESC,
                CASE p.place_kind WHEN 'city' THEN 3 WHEN 'region' THEN 2 WHEN 'country' THEN 1 ELSE 0 END DESC,
                COALESCE(p.run_id, 0) DESC,
                p.id DESC
            ) AS rn
          FROM episodes e
          JOIN time_spans ts ON ts.id=e.best_span_id
          JOIN places p ON p.episode_id=e.id
          LEFT JOIN places_norm pn ON pn.id=p.place_norm_id
          WHERE e.id IN ({placeholders})
            AND p.latitude IS NOT NULL
            AND p.longitude IS NOT NULL
        )
        SELECT place_name, COUNT(*) AS support
        FROM ranked
        WHERE rn=1 AND place_name IS NOT NULL
        GROUP BY place_name
        ORDER BY support DESC, place_name ASC
        LIMIT 1
        """,
        episode_ids,
    ).fetchone()
    return str(row["place_name"]) if row is not None else None


def _extract_episode_derived(
    conn: sqlite3.Connection,
    *,
    run_id: int,
    episode_id: int,
    title: str,
    description_pure: str,
    gaz,
) -> tuple[int | None, int | None]:
    """Insert deterministic segments and extracted rows for one episode."""
    description_segments = segment_text(description_pure)
    # The title is high-signal evidence (for example "Das Jahr 536") and
    # participates in date/place extraction without polluting the keyword corpus.
    segs = [("title", title.strip()), *description_segments]
    best_span_id = None
    best_span_score = -1.0
    best_span_segment_id = None
    place_candidates: list[tuple[int, int, str, str, int]] = []
    place_order = 0
    segment_index_column = _segment_index_column(conn)

    for idx, (section, txt) in enumerate(segs):
        if not txt:
            continue
        cur = conn.execute(
            f"INSERT INTO segments (episode_id, section, {segment_index_column}, text) VALUES (?, ?, ?, ?)",
            (episode_id, section, idx, txt),
        )
        seg_id = _rowid(cur)

        for sp in extract_spans(txt, section):
            cur2 = conn.execute(
                """
                INSERT INTO time_spans
                (run_id, origin, locked, episode_id, segment_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score, review_flag)
                VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    ORIGIN_DET,
                    episode_id,
                    seg_id,
                    sp.start.isoformat() if sp.start else None,
                    sp.end.isoformat() if sp.end else None,
                    sp.precision,
                    sp.qualifier,
                    sp.source_text,
                    section,
                    txt[:500],
                    float(sp.score),
                    sp.review_flag,
                ),
            )
            sp_id = _rowid(cur2)
            if sp.score > best_span_score:
                best_span_score = sp.score
                best_span_id = sp_id
                best_span_segment_id = seg_id

        for canon, kind, lat, lon, radius in extract_places(txt, gaz):
            pnid = _ensure_place_norm(conn, canon, kind)
            cur3 = conn.execute(
                """
                INSERT INTO places
                (run_id, origin, locked, episode_id, segment_id, place_norm_id, name_raw, place_kind, latitude, longitude, radius_km)
                VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, ORIGIN_DET, episode_id, seg_id, pnid, canon, kind, lat, lon, radius),
            )
            pl_id = _rowid(cur3)
            place_candidates.append((pl_id, seg_id, section, kind, place_order))
            place_order += 1

        for name, kind, conf, src in extract_entities(txt):
            conn.execute(
                "INSERT INTO entities (run_id, origin, locked, episode_id, segment_id, name, kind, confidence, source_text) VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?)",
                (run_id, ORIGIN_DET, episode_id, seg_id, name, kind, float(conf), src),
            )

        if section == "main":
            for phrase, score in rake_phrases(txt, max_phrases=25):
                row = conn.execute("SELECT id FROM keywords WHERE phrase=?", (phrase,)).fetchone()
                if row:
                    kid = int(row[0])
                else:
                    curk = conn.execute("INSERT INTO keywords (phrase) VALUES (?)", (phrase,))
                    kid = _rowid(curk)
                conn.execute(
                    "INSERT OR REPLACE INTO episode_keywords (run_id, origin, locked, episode_id, keyword_id, score) VALUES (?, ?, 0, ?, ?, ?)",
                    (run_id, ORIGIN_DET, episode_id, kid, float(score)),
                )

    best_place_id = _select_best_place_id(
        place_candidates,
        best_span_segment_id=best_span_segment_id,
    )
    return best_span_id, best_place_id


def build_db(
    db_path: str,
    rss_paths: list[str],
    gazetteer_csv: str,
    *,
    limit: int = 0,
    year_max: int = DEFAULT_YEAR_MAX,
    enable_heuristic_review: bool = True,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    run_id = new_run(
        conn,
        origin=ORIGIN_DET,
        tool="aggregate-build-db",
        params={
            "rss_paths": rss_paths,
            "limit": int(limit),
            "year_max": int(year_max),
            "enable_heuristic_review": bool(enable_heuristic_review),
        },
    )

    gaz = load_gazetteer_csv(gazetteer_csv)

    for rss in rss_paths:
        info, items = parse_rss(rss)
        pid = _upsert_podcast(conn, info)

        count = 0
        for it in items:
            if limit and count >= limit:
                break
            eid = _insert_episode(conn, pid, it)
            if eid is None:
                continue

            _insert_links(conn, eid, it.description_raw, it.page_url)

            pure = conn.execute(
                "SELECT description_pure FROM episodes WHERE id=?", (eid,)
            ).fetchone()[0]
            best_span_id, best_place_id = _extract_episode_derived(
                conn,
                run_id=run_id,
                episode_id=eid,
                title=it.title,
                description_pure=pure,
                gaz=gaz,
            )
            conn.execute(
                "UPDATE episodes SET best_span_id=?, best_place_id=? WHERE id=?",
                (best_span_id, best_place_id, eid),
            )
            conn.commit()

            count += 1

    postprocess_derived_rows(
        conn,
        year_max=year_max,
        enable_heuristic_review=enable_heuristic_review,
    )

    # clusters per podcast
    _recompute_clusters(conn, run_id=run_id)

    conn.close()


def _recompute_clusters(conn: sqlite3.Connection, *, run_id: int) -> None:
    # clear only deterministic cluster artifacts; preserve locked/nondet curation.
    conn.execute("DELETE FROM episode_clusters WHERE origin='det'")
    conn.execute("DELETE FROM cluster_keywords WHERE origin='det'")
    conn.execute("DELETE FROM cluster_entities WHERE origin='det'")
    conn.execute("DELETE FROM clusters WHERE origin='det'")
    conn.commit()

    podcasts = conn.execute("SELECT id FROM podcasts ORDER BY id").fetchall()
    for (pid,) in podcasts:
        # build points for episodes with best span+place
        eps = conn.execute(
            """
            WITH candidates AS (
              SELECT
                e.id,
                e.podcast_id,
                ts.start_iso,
                ts.end_iso,
                p.latitude,
                p.longitude,
                ROW_NUMBER() OVER (
                  PARTITION BY e.id
                  ORDER BY
                    CASE WHEN p.segment_id = ts.segment_id THEN 1 ELSE 0 END DESC,
                    COALESCE(p.locked, 0) DESC,
                    CASE COALESCE(p.origin, 'det') WHEN 'nondet' THEN 1 ELSE 0 END DESC,
                    CASE p.place_kind WHEN 'city' THEN 3 WHEN 'region' THEN 2 WHEN 'country' THEN 1 ELSE 0 END DESC,
                    COALESCE(p.run_id, 0) DESC,
                    p.id DESC
                ) AS rn
              FROM episodes e
              JOIN time_spans ts ON ts.id = e.best_span_id
              JOIN places p ON p.episode_id = e.id
              WHERE e.podcast_id = ?
                AND ts.start_iso IS NOT NULL AND ts.end_iso IS NOT NULL
                AND p.latitude IS NOT NULL AND p.longitude IS NOT NULL
            )
            SELECT id, start_iso, end_iso, latitude, longitude
            FROM candidates
            WHERE rn=1
            """,
            (pid,),
        ).fetchall()

        points: list[Point] = []
        for eid, siso, eiso, lat, lon in eps:
            my = _mid_year(siso, eiso)
            if my is None:
                continue
            points.append(Point(int(eid), float(my), float(lat), float(lon)))

        if len(points) < 4:
            continue

        k = k_for_n(len(points))
        centroids, assign = kmeans(points, k)
        centroids, assign = merge_small_clusters(points, assign, min_size=2)
        actual_k = len(centroids)

        cluster_ids: list[int] = []
        for j, (cy, clat, clon) in enumerate(centroids):
            cur = conn.execute(
                "INSERT INTO clusters (run_id, origin, podcast_id, k, label, centroid_year, centroid_lat, centroid_lon) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    ORIGIN_DET,
                    pid,
                    actual_k,
                    f"C{j + 1}",
                    float(cy),
                    float(clat),
                    float(clon),
                ),
            )
            cluster_ids.append(_rowid(cur))

        for eid, j in assign.items():
            conn.execute(
                "INSERT INTO episode_clusters (run_id, origin, episode_id, cluster_id) VALUES (?, ?, ?, ?)",
                (run_id, ORIGIN_DET, eid, cluster_ids[int(j)]),
            )

        conn.commit()

        # summaries: top keywords and entities per cluster
        for cid in cluster_ids:
            ep_ids = [
                r[0]
                for r in conn.execute(
                    "SELECT episode_id FROM episode_clusters WHERE cluster_id=?", (cid,)
                ).fetchall()
            ]
            if not ep_ids:
                continue

            centroid_year = float(
                conn.execute("SELECT centroid_year FROM clusters WHERE id=?", (cid,)).fetchone()[0]
            )
            place_label = _dominant_cluster_place(conn, ep_ids)
            label = _period_label(centroid_year)
            if place_label:
                label = f"{label} · {place_label}"
            conn.execute("UPDATE clusters SET label=? WHERE id=?", (label, cid))

            # keywords aggregate
            kw = conn.execute(
                f"""
                SELECT k.phrase, SUM(ek.score) AS s
                FROM episode_keywords ek
                JOIN keywords k ON k.id = ek.keyword_id
                WHERE ek.episode_id IN ({",".join("?" * len(ep_ids))})
                GROUP BY k.phrase
                ORDER BY s DESC
                LIMIT 25
                """,
                ep_ids,
            ).fetchall()
            conn.executemany(
                "INSERT INTO cluster_keywords (run_id, origin, locked, cluster_id, phrase, score) VALUES (?, ?, 0, ?, ?, ?)",
                [(run_id, ORIGIN_DET, cid, phrase, float(s)) for phrase, s in kw],
            )

            ent = conn.execute(
                f"""
                SELECT name, kind, COUNT(*) AS c
                FROM entities
                WHERE episode_id IN ({",".join("?" * len(ep_ids))})
                GROUP BY name, kind
                ORDER BY c DESC
                LIMIT 25
                """,
                ep_ids,
            ).fetchall()
            conn.executemany(
                "INSERT INTO cluster_entities (run_id, origin, locked, cluster_id, name, kind, score) VALUES (?, ?, 0, ?, ?, ?, ?)",
                [(run_id, ORIGIN_DET, cid, name, kind, float(c)) for name, kind, c in ent],
            )
            conn.commit()


def cleanup_future_spans(conn: sqlite3.Connection, *, year_max: int) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM time_spans
        WHERE (start_iso IS NOT NULL AND CAST(substr(start_iso,1,4) AS INT) > ?)
           OR (end_iso IS NOT NULL AND CAST(substr(end_iso,1,4) AS INT) > ?)
        """,
        (int(year_max), int(year_max)),
    ).fetchone()
    delete_count = int(row["c"] if row is not None else 0)
    if delete_count <= 0:
        return 0
    conn.execute(
        """
        DELETE FROM time_spans
        WHERE (start_iso IS NOT NULL AND CAST(substr(start_iso,1,4) AS INT) > ?)
           OR (end_iso IS NOT NULL AND CAST(substr(end_iso,1,4) AS INT) > ?)
        """,
        (int(year_max), int(year_max)),
    )
    conn.execute(
        """
        UPDATE episodes
        SET best_span_id = NULL
        WHERE best_span_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM time_spans ts WHERE ts.id = episodes.best_span_id)
        """
    )
    conn.commit()
    return delete_count


def apply_heuristic_review_overrides(conn: sqlite3.Connection, *, year_max: int) -> int:
    review_run = new_run(
        conn,
        origin=ORIGIN_NONDET,
        tool="aggregate-heuristic-review",
        params={"year_max": int(year_max)},
    )
    rows = conn.execute(
        """
        SELECT e.id AS episode_id
        FROM episodes e
        JOIN v_best_time_span b ON b.episode_id = e.id
        WHERE b.review_flag IN ('caption-folgenbild', 'caption-portrait-year')
        """
    ).fetchall()

    inserted = 0
    for row in rows:
        episode_id = int(row["episode_id"])
        cand = conn.execute(
            """
            SELECT ts.*
            FROM time_spans ts
            JOIN segments s ON s.id = ts.segment_id
            WHERE ts.episode_id=? AND s.section='main'
            ORDER BY ts.score DESC, ts.id DESC
            LIMIT 1
            """,
            (episode_id,),
        ).fetchone()
        if cand is None:
            continue

        exists = conn.execute(
            """
            SELECT 1
            FROM time_spans
            WHERE episode_id=?
              AND origin='nondet'
              AND locked=1
              AND review_flag='review-override'
              AND COALESCE(start_iso, '')=COALESCE(?, '')
              AND COALESCE(end_iso, '')=COALESCE(?, '')
              AND precision=?
              AND qualifier=?
              AND source_text=?
            LIMIT 1
            """,
            (
                episode_id,
                cand["start_iso"],
                cand["end_iso"],
                cand["precision"],
                cand["qualifier"],
                cand["source_text"],
            ),
        ).fetchone()
        if exists is not None:
            continue

        cur = conn.execute(
            """
            INSERT INTO time_spans
            (run_id, origin, locked, episode_id, segment_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score, review_flag)
            VALUES (?, 'nondet', 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'review-override')
            """,
            (
                review_run,
                cand["episode_id"],
                cand["segment_id"],
                cand["start_iso"],
                cand["end_iso"],
                cand["precision"],
                cand["qualifier"],
                cand["source_text"],
                cand["source_section"],
                cand["source_context"],
                float(cand["score"]) + 0.01,
            ),
        )
        conn.execute("UPDATE episodes SET best_span_id=? WHERE id=?", (_rowid(cur), episode_id))
        inserted += 1
    conn.commit()
    return inserted


def postprocess_derived_rows(
    conn: sqlite3.Connection,
    *,
    year_max: int = DEFAULT_YEAR_MAX,
    enable_heuristic_review: bool = True,
) -> dict[str, int]:
    deleted_future = cleanup_future_spans(conn, year_max=year_max)
    inserted_overrides = (
        apply_heuristic_review_overrides(conn, year_max=year_max) if enable_heuristic_review else 0
    )
    return {
        "future_spans_deleted": deleted_future,
        "heuristic_overrides_inserted": inserted_overrides,
    }
