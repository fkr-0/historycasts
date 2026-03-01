from __future__ import annotations

import datetime as dt
import re
import sqlite3
from typing import Optional

from .cluster import Point, k_for_n, kmeans
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
    conn.commit()
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

    cur = conn.execute(
        """
        INSERT INTO episodes
        (podcast_id, guid, page_url, title, pub_date, duration, audio_url, episode_type, kind, narrator, description_raw, description_pure)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            podcast_id,
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


def build_db(db_path: str, rss_paths: list[str], gazetteer_csv: str, *, limit: int = 0) -> None:
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)

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

            # segments + extraction
            segs = segment_text(
                conn.execute("SELECT description_pure FROM episodes WHERE id=?", (eid,)).fetchone()[
                    0
                ]
            )
            best_span_id = None
            best_span_score = -1.0
            best_place_id = None

            for idx, (section, txt) in enumerate(segs):
                cur = conn.execute(
                    "INSERT INTO segments (episode_id, section, idx, text) VALUES (?, ?, ?, ?)",
                    (eid, section, idx, txt),
                )
                seg_id = _rowid(cur)

                # spans
                spans = extract_spans(txt, section)
                for sp in spans:
                    cur2 = conn.execute(
                        """
                        INSERT INTO time_spans
                        (episode_id, segment_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score, review_flag)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            eid,
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

                # places
                places = extract_places(txt, gaz)
                for canon, kind, lat, lon, radius in places:
                    pnid = _ensure_place_norm(conn, canon, kind)
                    cur3 = conn.execute(
                        """
                        INSERT INTO places
                        (episode_id, segment_id, place_norm_id, name_raw, place_kind, latitude, longitude, radius_km)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (eid, seg_id, pnid, canon, kind, lat, lon, radius),
                    )
                    pl_id = _rowid(cur3)
                    # choose first geocoded place as best
                    if best_place_id is None:
                        best_place_id = pl_id

                # entities
                for name, kind, conf, src in extract_entities(txt):
                    conn.execute(
                        "INSERT INTO entities (episode_id, segment_id, name, kind, confidence, source_text) VALUES (?, ?, ?, ?, ?, ?)",
                        (eid, seg_id, name, kind, float(conf), src),
                    )

                # keywords only from main section
                if section == "main":
                    for phrase, score in rake_phrases(txt, max_phrases=25):
                        # insert keyword
                        row = conn.execute(
                            "SELECT id FROM keywords WHERE phrase=?", (phrase,)
                        ).fetchone()
                        if row:
                            kid = int(row[0])
                        else:
                            curk = conn.execute(
                                "INSERT INTO keywords (phrase) VALUES (?)", (phrase,)
                            )
                            kid = _rowid(curk)
                        conn.execute(
                            "INSERT OR REPLACE INTO episode_keywords (episode_id, keyword_id, score) VALUES (?, ?, ?)",
                            (eid, kid, float(score)),
                        )

            # set best ids
            conn.execute(
                "UPDATE episodes SET best_span_id=?, best_place_id=? WHERE id=?",
                (best_span_id, best_place_id, eid),
            )
            conn.commit()

            count += 1

    # clusters per podcast
    _recompute_clusters(conn)

    conn.close()


def _recompute_clusters(conn: sqlite3.Connection) -> None:
    # clear old clusters
    conn.execute("DELETE FROM episode_clusters")
    conn.execute("DELETE FROM cluster_keywords")
    conn.execute("DELETE FROM cluster_entities")
    conn.execute("DELETE FROM clusters")
    conn.commit()

    podcasts = conn.execute("SELECT id FROM podcasts ORDER BY id").fetchall()
    for (pid,) in podcasts:
        # build points for episodes with best span+place
        eps = conn.execute(
            """
            SELECT e.id, ts.start_iso, ts.end_iso, p.latitude, p.longitude
            FROM episodes e
            JOIN time_spans ts ON ts.id = e.best_span_id
            JOIN places p ON p.id = e.best_place_id
            WHERE e.podcast_id = ?
              AND ts.start_iso IS NOT NULL AND ts.end_iso IS NOT NULL
              AND p.latitude IS NOT NULL AND p.longitude IS NOT NULL
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

        cluster_ids: list[int] = []
        for j, (cy, clat, clon) in enumerate(centroids):
            cur = conn.execute(
                "INSERT INTO clusters (podcast_id, k, label, centroid_year, centroid_lat, centroid_lon) VALUES (?, ?, ?, ?, ?, ?)",
                (pid, k, f"C{j + 1}", float(cy), float(clat), float(clon)),
            )
            cluster_ids.append(_rowid(cur))

        for eid, j in assign.items():
            conn.execute(
                "INSERT INTO episode_clusters (episode_id, cluster_id) VALUES (?, ?)",
                (eid, cluster_ids[int(j)]),
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
                "INSERT INTO cluster_keywords (cluster_id, phrase, score) VALUES (?, ?, ?)",
                [(cid, phrase, float(s)) for phrase, s in kw],
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
                "INSERT INTO cluster_entities (cluster_id, name, kind, score) VALUES (?, ?, ?, ?)",
                [(cid, name, kind, float(c)) for name, kind, c in ent],
            )
            conn.commit()
