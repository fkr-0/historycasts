from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from podcast_atlas.aggregate.schema import ensure_schema
from podcast_atlas.data_trust import audit_data_trust


def _seed_valid_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO podcasts (id, title, feed_url) VALUES (1, 'Test', 'https://example.test/feed')"
    )
    conn.execute(
        """
        INSERT INTO episodes_raw
          (id, podcast_id, guid, title, pub_date, page_url, audio_url, description_raw)
        VALUES
          (1, 1, 'guid-1', 'Ancient episode', '2020-01-01T00:00:00Z',
           'https://example.test/e/1', 'https://example.test/a/1.mp3', 'raw source text')
        """
    )
    conn.execute(
        """
        INSERT INTO episodes
          (id, podcast_id, guid, title, pub_date, page_url, audio_url, description_raw,
           description_pure, raw_id)
        VALUES
          (1, 1, 'guid-1', 'Ancient episode', '2020-01-01T00:00:00Z',
           'https://example.test/e/1', 'https://example.test/a/1.mp3', 'raw source text',
           'A discussion of antiquity.', 1)
        """
    )
    conn.execute(
        """
        INSERT INTO time_spans
          (id, episode_id, start_iso, end_iso, precision, qualifier, source_text,
           source_section, source_context, score, origin, locked)
        VALUES
          (1, 1, '-0401-01-01', '-0401-12-31', 'year', 'exact', '401 BCE',
           'main', 'ctx', 0.9, 'nondet', 1)
        """
    )
    conn.execute("UPDATE episodes SET best_span_id=1 WHERE id=1")
    conn.commit()
    conn.close()


def test_audit_data_trust_accepts_valid_bce_and_reports_protected_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "valid.db"
    _seed_valid_db(db_path)
    before = hashlib.sha256(db_path.read_bytes()).hexdigest()

    report = audit_data_trust(db_path)
    after = hashlib.sha256(db_path.read_bytes()).hexdigest()

    assert report["ok"] is True
    assert after == before
    assert report["errors"] == 0
    assert report["warnings"] == 0
    assert report["summary"]["protected_rows"]["time_spans"] == {
        "nondeterministic": 1,
        "locked": 1,
    }


def test_audit_data_trust_flags_structural_and_targeted_sanitation_failures(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "invalid.db"
    _seed_valid_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        UPDATE episodes
        SET page_url='file:///not-public',
            description_pure='Useful history. Hosted on Acast. See acast.com/privacy.'
        WHERE id=1
        """
    )
    conn.execute(
        """
        INSERT INTO places
          (id, episode_id, name_raw, place_kind, latitude, longitude, radius_km, origin, locked)
        VALUES (1, 1, 'Impossible', 'city', 95.0, 181.0, -1.0, 'det', 0)
        """
    )
    conn.execute(
        """
        INSERT INTO time_spans
          (id, episode_id, start_iso, end_iso, precision, qualifier, source_text,
           source_section, source_context, score, origin, locked)
        VALUES
          (2, 1, '-0100-01-01', '-0200-12-31', 'year', 'range', 'reversed',
           'main', 'ctx', 0.5, 'det', 0)
        """
    )
    conn.execute(
        "INSERT INTO episode_keywords (episode_id, keyword_id, score) VALUES (1, 999, 1.0)"
    )
    conn.commit()
    conn.close()

    report = audit_data_trust(db_path)
    codes = {finding["code"] for finding in report["findings"]}

    assert report["ok"] is False
    assert "invalid_episode_url" in codes
    assert "invalid_coordinate" in codes
    assert "invalid_time_span" in codes
    assert "orphan_foreign_keys" in codes
    assert "boilerplate_hosted_footer" in codes
