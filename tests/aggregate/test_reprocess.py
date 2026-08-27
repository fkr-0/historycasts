from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from podcast_atlas.aggregate.reprocess import audit_derived_cleanup, reprocess_derived_data
from podcast_atlas.aggregate.schema import ensure_schema
from podcast_atlas.provenance import ORIGIN_DET, ORIGIN_NONDET, new_run


def _write_gazetteer(path: Path) -> None:
    path.write_text(
        "name,kind,lat,lon,radius_km,aliases\nWien,city,48.2082,16.3738,25,Vienna\n",
        encoding="utf-8",
    )


def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    det_run = new_run(conn, origin=ORIGIN_DET, tool="old-det", params={})
    review_run = new_run(
        conn,
        origin=ORIGIN_NONDET,
        tool="aggregate-heuristic-review",
        params={},
    )
    handcrafted_run = new_run(
        conn,
        origin=ORIGIN_NONDET,
        tool="handcrafted",
        params={},
    )
    conn.execute("INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'Podcast', 'feed')")
    conn.execute(
        """
        INSERT INTO episodes
        (id, podcast_id, guid, title, description_raw, description_pure)
        VALUES
        (1, 1, 'g1', 'Die Glühlampe 1881',
         'Im Dezember 1881 brennt das Ringtheater in Wien.\n\n// Literatur\nBuch, 2023.',
         'Im Dezember 1881 brennt das Ringtheater in Wien.\nBuch, 2023.'),
        (2, 1, 'g2', 'Beethoven und die Eroica',
         'Beethoven arbeitet zu Beginn des 19. Jahrhunderts in Wien.',
         'Beethoven arbeitet zu Beginn des 19. Jahrhunderts in Wien.')
        """
    )
    conn.execute(
        "INSERT INTO segments (id, episode_id, section, idx, text) VALUES (1, 1, 'main', 0, 'Buch, 2023.')"
    )
    conn.execute(
        """
        INSERT INTO time_spans
        (id, run_id, origin, locked, episode_id, segment_id, start_iso, end_iso,
         precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES
        (1, ?, 'det', 0, 1, 1, '2023-01-01', '2023-12-31',
         'year', 'year', '2023', 'main', 'Buch, 2023.', 6, NULL),
        (2, ?, 'nondet', 1, 1, 1, '2023-01-01', '2023-12-31',
         'year', 'year', '2023', 'main', 'Buch, 2023.', 6.01, 'review-override'),
        (3, ?, 'nondet', 1, 2, NULL, '1801-01-01', '1900-12-31',
         'century', 'handcrafted', '19. Jahrhundert', 'description', 'curated', 20,
         'handcrafted-res-json')
        """,
        (det_run, review_run, handcrafted_run),
    )
    conn.execute("UPDATE episodes SET best_span_id=2 WHERE id=1")
    conn.execute("UPDATE episodes SET best_span_id=3 WHERE id=2")
    conn.commit()
    conn.close()


def test_reprocess_removes_generated_override_and_preserves_handcrafted(tmp_path: Path) -> None:
    db = tmp_path / "atlas.db"
    gazetteer = tmp_path / "gazetteer.csv"
    _seed_db(db)
    _write_gazetteer(gazetteer)

    before_audit = hashlib.sha256(db.read_bytes()).hexdigest()
    audit = audit_derived_cleanup(db)
    after_audit = hashlib.sha256(db.read_bytes()).hexdigest()
    assert after_audit == before_audit
    assert audit["descriptions_changed"] == 1
    assert audit["auto_review_overrides_to_remove"] == 1

    stats = reprocess_derived_data(db, gazetteer, backup=False)

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    episode_1 = conn.execute(
        """
        SELECT e.description_pure, ts.start_iso, ts.origin, ts.review_flag
        FROM episodes e JOIN time_spans ts ON ts.id=e.best_span_id
        WHERE e.id=1
        """
    ).fetchone()
    assert "2023" not in episode_1["description_pure"]
    assert episode_1["start_iso"] == "1881-01-01"
    assert episode_1["origin"] == "det"
    assert episode_1["review_flag"] is None

    episode_2 = conn.execute(
        """
        SELECT ts.start_iso, ts.origin, ts.review_flag
        FROM episodes e JOIN time_spans ts ON ts.id=e.best_span_id
        WHERE e.id=2
        """
    ).fetchone()
    assert tuple(episode_2) == ("1801-01-01", "nondet", "handcrafted-res-json")
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM time_spans WHERE review_flag='review-override'"
        ).fetchone()[0]
        == 0
    )
    conn.close()

    assert stats["episodes_reprocessed"] == 2
    assert stats["auto_review_overrides_removed"] == 1
    assert stats["backup_path"] is None
