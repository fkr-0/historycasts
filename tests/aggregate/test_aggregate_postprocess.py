from __future__ import annotations

import sqlite3

from podcast_atlas.aggregate.db_build import postprocess_derived_rows
from podcast_atlas.aggregate.schema import ensure_schema
from podcast_atlas.provenance import ORIGIN_DET, ORIGIN_NONDET, new_run


def test_postprocess_prunes_future_spans_and_inserts_heuristic_locked_override() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    det_run = new_run(conn, origin=ORIGIN_DET, tool="test", params={})

    conn.execute("INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'pod', 'feed')")
    conn.execute(
        """
        INSERT INTO episodes_raw
        (id, podcast_id, guid, title, pub_date, page_url, audio_url, duration_sec, author, description_raw)
        VALUES (1, 1, 'g1', 'E1', '2020-01-01', 'https://e', 'https://a', 10, 'n', 'raw')
        """
    )
    conn.execute(
        """
        INSERT INTO episodes
        (id, podcast_id, raw_id, guid, title, pub_date, page_url, audio_url, duration, kind, narrator, description_raw, description_pure)
        VALUES (1, 1, 1, 'g1', 'E1', '2020-01-01', 'https://e', 'https://a', 10, 'regular', 'n', 'raw', 'pure')
        """
    )
    conn.execute("INSERT INTO segments (id, episode_id, section, idx, text) VALUES (1, 1, 'caption', 0, 'cap')")
    conn.execute("INSERT INTO segments (id, episode_id, section, idx, text) VALUES (2, 1, 'main', 1, 'main')")

    # Caption span is currently best and flagged for review.
    caption_id = conn.execute(
        """
        INSERT INTO time_spans
        (run_id, origin, locked, episode_id, segment_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES (?, 'det', 0, 1, 1, '1930-01-01', '1930-12-31', 'year', 'year', '1930', 'caption', 'ctx', 2.0, 'caption-folgenbild')
        """,
        (det_run,),
    ).lastrowid
    # Main span candidate (lower score, should still become locked override).
    conn.execute(
        """
        INSERT INTO time_spans
        (run_id, origin, locked, episode_id, segment_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES (?, 'det', 0, 1, 2, '1712-01-01', '1712-12-31', 'year', 'year', '1712', 'main', 'ctx', 1.0, NULL)
        """,
        (det_run,),
    )
    # Future span should be deleted by policy.
    conn.execute(
        """
        INSERT INTO time_spans
        (run_id, origin, locked, episode_id, segment_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES (?, 'det', 0, 1, 2, '3000-01-01', '3000-12-31', 'year', 'year', '3000', 'main', 'ctx', 9.0, NULL)
        """,
        (det_run,),
    )
    conn.execute("UPDATE episodes SET best_span_id=? WHERE id=1", (caption_id,))
    conn.commit()

    postprocess_derived_rows(conn, year_max=2026)

    future_count = conn.execute(
        "SELECT COUNT(*) FROM time_spans WHERE start_iso LIKE '3000-%' OR end_iso LIKE '3000-%'"
    ).fetchone()[0]
    assert future_count == 0

    override = conn.execute(
        """
        SELECT origin, locked, source_section, review_flag
        FROM time_spans
        WHERE episode_id=1 AND origin='nondet' AND locked=1
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    assert override is not None
    assert override["origin"] == ORIGIN_NONDET
    assert override["locked"] == 1
    assert override["source_section"] == "main"
    assert override["review_flag"] == "review-override"

    conn.close()


def test_postprocess_heuristic_override_is_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    det_run = new_run(conn, origin=ORIGIN_DET, tool="test", params={})

    conn.execute("INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'pod', 'feed')")
    conn.execute(
        "INSERT INTO episodes_raw (id, podcast_id, guid, title) VALUES (1, 1, 'g1', 'E1')"
    )
    conn.execute(
        "INSERT INTO episodes (id, podcast_id, raw_id, guid, title, pub_date) VALUES (1, 1, 1, 'g1', 'E1', '2020-01-01')"
    )
    conn.execute("INSERT INTO segments (id, episode_id, section, idx, text) VALUES (1, 1, 'caption', 0, 'cap')")
    conn.execute("INSERT INTO segments (id, episode_id, section, idx, text) VALUES (2, 1, 'main', 1, 'main')")
    caption_id = conn.execute(
        """
        INSERT INTO time_spans
        (run_id, origin, locked, episode_id, segment_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES (?, 'det', 0, 1, 1, '1930-01-01', '1930-12-31', 'year', 'year', '1930', 'caption', 'ctx', 2.0, 'caption-folgenbild')
        """,
        (det_run,),
    ).lastrowid
    conn.execute(
        """
        INSERT INTO time_spans
        (run_id, origin, locked, episode_id, segment_id, start_iso, end_iso, precision, qualifier, source_text, source_section, source_context, score, review_flag)
        VALUES (?, 'det', 0, 1, 2, '1712-01-01', '1712-12-31', 'year', 'year', '1712', 'main', 'ctx', 1.0, NULL)
        """,
        (det_run,),
    )
    conn.execute("UPDATE episodes SET best_span_id=? WHERE id=1", (caption_id,))
    conn.commit()

    first = postprocess_derived_rows(conn, year_max=2026)
    second = postprocess_derived_rows(conn, year_max=2026)
    assert first["heuristic_overrides_inserted"] == 1
    assert second["heuristic_overrides_inserted"] == 0

    cnt = conn.execute(
        "SELECT COUNT(*) FROM time_spans WHERE origin='nondet' AND locked=1 AND review_flag='review-override'"
    ).fetchone()[0]
    assert cnt == 1
    conn.close()
