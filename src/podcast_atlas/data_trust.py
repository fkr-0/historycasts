from __future__ import annotations

import re
import sqlite3
from calendar import monthrange
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class TrustFinding:
    code: str
    severity: Severity
    count: int
    message: str
    samples: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_HTML_TAG_RE = re.compile(r"</?(?:a|br|div|em|li|ol|p|span|strong|ul)\b[^>]*>", re.IGNORECASE)
_HTML_ENTITY_RE = re.compile(r"&(?:nbsp|amp|lt|gt|quot|#\d+|#x[0-9a-f]+);", re.IGNORECASE)
_BOILERPLATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "cross_promotion",
        re.compile(
            r"\bdie\s+passende\s+ausgabe\s+[„“”‚‘’\"']?eine\s+stunde\s+history[„“”‚‘’\"']?",
            re.IGNORECASE,
        ),
    ),
    ("affiliate", re.compile(r"\*?affiliate-link\s*:", re.IGNORECASE)),
    (
        "hosted_footer",
        re.compile(r"hosted\s+on\s+acast|acast\.com/privacy", re.IGNORECASE),
    ),
    (
        "advertising_footer",
        re.compile(r"\b(?:aus\s+unserer\s+werbung|werbepartner)\b", re.IGNORECASE),
    ),
    (
        "tracking_url",
        re.compile(
            r"\b(?:utm_(?:source|medium|campaign)=|linktr\.ee/|campfirefm)\b", re.IGNORECASE
        ),
    ),
)


def _sample_rows(rows: list[sqlite3.Row], *, limit: int = 5) -> list[dict[str, Any]]:
    return [{key: row[key] for key in row.keys()} for row in rows[:limit]]


_HISTORICAL_DATE_RE = re.compile(r"^([+-]?\d+)-(\d{2})-(\d{2})(?:$|T)")


def _parse_iso_date(value: str) -> tuple[int, int, int]:
    value = value.strip()
    if not value:
        raise ValueError("empty date")
    match = _HISTORICAL_DATE_RE.match(value)
    if match is None:
        raise ValueError(f"invalid historical ISO date: {value}")
    year, month, day = (int(part) for part in match.groups())
    if not 1 <= month <= 12:
        raise ValueError(f"invalid month: {month}")
    if not 1 <= day <= monthrange(year, month)[1]:
        raise ValueError(f"invalid day: {day}")
    return year, month, day


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }


def _protected_row_counts(conn: sqlite3.Connection, tables: set[str]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for table in sorted(tables):
        columns = {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if "origin" not in columns and "locked" not in columns:
            continue
        counts: dict[str, int] = {}
        if "origin" in columns:
            counts["nondeterministic"] = int(
                conn.execute(f"SELECT COUNT(*) FROM {table} WHERE origin='nondet'").fetchone()[0]
            )
        if "locked" in columns:
            counts["locked"] = int(
                conn.execute(f"SELECT COUNT(*) FROM {table} WHERE locked<>0").fetchone()[0]
            )
        result[table] = counts
    return result


def audit_data_trust(db_path: Path | str) -> dict[str, Any]:
    """Run a read-only, deterministic trust audit over a podcast-atlas SQLite database."""
    path = Path(db_path).resolve()
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    tables = _table_names(conn)
    findings: list[TrustFinding] = []

    def add_rows(code: str, severity: Severity, message: str, rows: list[sqlite3.Row]) -> None:
        if rows:
            findings.append(TrustFinding(code, severity, len(rows), message, _sample_rows(rows)))

    integrity = [str(row[0]) for row in conn.execute("PRAGMA integrity_check").fetchall()]
    if integrity != ["ok"]:
        findings.append(
            TrustFinding(
                "sqlite_integrity",
                "error",
                len(integrity),
                "SQLite integrity_check did not return exactly 'ok'.",
                [{"result": value} for value in integrity[:5]],
            )
        )

    fk_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
    add_rows(
        "orphan_foreign_keys",
        "error",
        "Foreign-key orphan rows are present.",
        fk_rows,
    )

    if "episodes_raw" in tables:
        add_rows(
            "duplicate_raw_guid",
            "error",
            "A podcast contains duplicate non-empty raw episode GUIDs.",
            conn.execute(
                """
                SELECT podcast_id, guid, COUNT(*) AS duplicate_count
                FROM episodes_raw
                WHERE guid IS NOT NULL AND TRIM(guid)<>''
                GROUP BY podcast_id, guid
                HAVING COUNT(*) > 1
                """
            ).fetchall(),
        )

    if "episodes" in tables:
        add_rows(
            "duplicate_episode_title_pub_date",
            "error",
            "A podcast contains duplicate title/publication-date episode identities.",
            conn.execute(
                """
                SELECT podcast_id, title, pub_date, COUNT(*) AS duplicate_count
                FROM episodes
                WHERE title IS NOT NULL AND pub_date IS NOT NULL
                GROUP BY podcast_id, title, pub_date
                HAVING COUNT(*) > 1
                """
            ).fetchall(),
        )

        if "episodes_raw" in tables:
            add_rows(
                "broken_episode_raw_reference",
                "error",
                "An episode is not linked to the matching raw/source row.",
                conn.execute(
                    """
                    SELECT e.id, e.podcast_id, e.guid, e.raw_id
                    FROM episodes e
                    WHERE e.raw_id IS NULL OR NOT EXISTS (
                      SELECT 1 FROM episodes_raw er
                      WHERE er.id=e.raw_id AND er.podcast_id=e.podcast_id AND er.guid=e.guid
                    )
                    """
                ).fetchall(),
            )

        if "time_spans" in tables:
            add_rows(
                "broken_best_span_reference",
                "error",
                "An episode best_span_id does not resolve to a span owned by that episode.",
                conn.execute(
                    """
                    SELECT e.id AS episode_id, e.best_span_id
                    FROM episodes e
                    WHERE e.best_span_id IS NOT NULL AND NOT EXISTS (
                      SELECT 1 FROM time_spans ts
                      WHERE ts.id=e.best_span_id AND ts.episode_id=e.id
                    )
                    """
                ).fetchall(),
            )

        if "places" in tables:
            add_rows(
                "broken_best_place_reference",
                "error",
                "An episode best_place_id does not resolve to a place owned by that episode.",
                conn.execute(
                    """
                    SELECT e.id AS episode_id, e.best_place_id
                    FROM episodes e
                    WHERE e.best_place_id IS NOT NULL AND NOT EXISTS (
                      SELECT 1 FROM places p
                      WHERE p.id=e.best_place_id AND p.episode_id=e.id
                    )
                    """
                ).fetchall(),
            )

        add_rows(
            "invalid_episode_url",
            "error",
            "Episode page/audio URLs must be HTTP(S) when present.",
            conn.execute(
                """
                SELECT id, page_url, audio_url
                FROM episodes
                WHERE
                  (page_url IS NOT NULL AND TRIM(page_url)<>''
                   AND page_url NOT LIKE 'http://%' AND page_url NOT LIKE 'https://%')
                  OR
                  (audio_url IS NOT NULL AND TRIM(audio_url)<>''
                   AND audio_url NOT LIKE 'http://%' AND audio_url NOT LIKE 'https://%')
                """
            ).fetchall(),
        )

        invalid_pub_dates: list[sqlite3.Row] = []
        for row in conn.execute(
            "SELECT id, pub_date FROM episodes WHERE pub_date IS NOT NULL AND TRIM(pub_date)<>''"
        ).fetchall():
            try:
                _parse_iso_date(str(row["pub_date"]))
            except ValueError:
                invalid_pub_dates.append(row)
        add_rows(
            "invalid_episode_pub_date",
            "error",
            "Episode publication dates must be parseable ISO dates/timestamps.",
            invalid_pub_dates,
        )

        description_rows = conn.execute(
            "SELECT id, podcast_id, title, description_pure FROM episodes WHERE description_pure IS NOT NULL"
        ).fetchall()
        markup_rows = [
            row
            for row in description_rows
            if _HTML_TAG_RE.search(str(row["description_pure"]))
            or _HTML_ENTITY_RE.search(str(row["description_pure"]))
        ]
        add_rows(
            "markup_remnant",
            "warning",
            "Clean descriptions still contain HTML markup/entity remnants.",
            markup_rows,
        )
        for label, pattern in _BOILERPLATE_PATTERNS:
            boilerplate_rows = [
                row for row in description_rows if pattern.search(str(row["description_pure"]))
            ]
            add_rows(
                f"boilerplate_{label}",
                "warning",
                f"Clean descriptions still contain targeted {label.replace('_', ' ')} boilerplate.",
                boilerplate_rows,
            )

    if "links" in tables:
        add_rows(
            "invalid_link_url",
            "error",
            "Stored extracted links must be HTTP(S) when present.",
            conn.execute(
                """
                SELECT id, episode_id, url
                FROM links
                WHERE url IS NOT NULL AND TRIM(url)<>''
                  AND url NOT LIKE 'http://%' AND url NOT LIKE 'https://%'
                """
            ).fetchall(),
        )

    if "time_spans" in tables:
        invalid_span_rows: list[sqlite3.Row] = []
        for row in conn.execute(
            "SELECT id, episode_id, start_iso, end_iso, origin, locked FROM time_spans"
        ).fetchall():
            try:
                start = _parse_iso_date(str(row["start_iso"])) if row["start_iso"] else None
                end = _parse_iso_date(str(row["end_iso"])) if row["end_iso"] else None
                if start is not None and end is not None and start > end:
                    raise ValueError("reversed span")
            except ValueError:
                invalid_span_rows.append(row)
        protected_invalid_spans = [
            row
            for row in invalid_span_rows
            if bool(row["locked"]) or str(row["origin"] or "").lower() == "nondet"
        ]
        deterministic_invalid_spans = [
            row for row in invalid_span_rows if row not in protected_invalid_spans
        ]
        add_rows(
            "invalid_time_span",
            "error",
            "Deterministic time spans must contain parseable, non-reversed date bounds.",
            deterministic_invalid_spans,
        )
        add_rows(
            "protected_invalid_time_span",
            "warning",
            "A locked/nondeterministic time span is structurally invalid and is preserved for manual review.",
            protected_invalid_spans,
        )

    if "places" in tables:
        add_rows(
            "invalid_coordinate",
            "error",
            "Coordinates must be complete pairs in range and radius must be non-negative.",
            conn.execute(
                """
                SELECT id, episode_id, latitude, longitude, radius_km
                FROM places
                WHERE (latitude IS NULL) <> (longitude IS NULL)
                   OR latitude < -90 OR latitude > 90
                   OR longitude < -180 OR longitude > 180
                   OR radius_km < 0
                """
            ).fetchall(),
        )

    summary: dict[str, Any] = {
        "podcasts": int(conn.execute("SELECT COUNT(*) FROM podcasts").fetchone()[0])
        if "podcasts" in tables
        else 0,
        "episodes": int(conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0])
        if "episodes" in tables
        else 0,
        "protected_rows": _protected_row_counts(conn, tables),
    }
    conn.close()

    errors = sum(finding.count for finding in findings if finding.severity == "error")
    warnings = sum(finding.count for finding in findings if finding.severity == "warning")
    return {
        "database": str(path),
        "ok": errors == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": summary,
        "findings": [finding.as_dict() for finding in findings],
    }
