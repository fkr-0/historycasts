from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple


def _dt_to_iso(dt: datetime) -> str:
    # store as ISO date-time with timezone if present
    return dt.astimezone().isoformat()


def _iso_to_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


@dataclass
class Database:
    path: Path

    @classmethod
    def create(cls, path: Path) -> "Database":
        path = Path(path)
        db = cls(path)
        db._init()
        return db

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def _init(self) -> None:
        with self.connect() as con:
            con.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS podcasts (
                  id TEXT PRIMARY KEY,
                  title TEXT NOT NULL,
                  feed_url TEXT NOT NULL,
                  link TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS episodes (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  podcast_id TEXT NOT NULL,
                  guid TEXT NOT NULL UNIQUE,
                  title TEXT NOT NULL,
                  published_at TEXT NOT NULL,
                  description TEXT NOT NULL,
                  audio_url TEXT,
                  audio_length INTEGER,
                  duration_seconds INTEGER,

                  incident_type TEXT,

                  primary_time_kind TEXT,
                  primary_time_year INTEGER,
                  primary_time_start_year INTEGER,
                  primary_time_end_year INTEGER,

                  primary_location_name TEXT,
                  primary_location_country TEXT,
                  primary_location_lat REAL,
                  primary_location_lon REAL,

                  persons_json TEXT NOT NULL DEFAULT '[]',
                  links_json TEXT NOT NULL DEFAULT '[]',

                  FOREIGN KEY(podcast_id) REFERENCES podcasts(id)
                );

                CREATE INDEX IF NOT EXISTS idx_episodes_pub ON episodes(published_at);
                CREATE INDEX IF NOT EXISTS idx_episodes_inc ON episodes(incident_type);
                CREATE INDEX IF NOT EXISTS idx_episodes_loc ON episodes(primary_location_lat, primary_location_lon);
                """
            )

    def upsert_podcast(self, *, podcast_id: str, title: str, feed_url: str, link: str) -> None:
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO podcasts(id, title, feed_url, link)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  title=excluded.title,
                  feed_url=excluded.feed_url,
                  link=excluded.link
                """,
                (podcast_id, title, feed_url, link),
            )

    def upsert_episode(self, *, row: Dict[str, Any]) -> None:
        cols = [
            "podcast_id",
            "guid",
            "title",
            "published_at",
            "description",
            "audio_url",
            "audio_length",
            "duration_seconds",
            "incident_type",
            "primary_time_kind",
            "primary_time_year",
            "primary_time_start_year",
            "primary_time_end_year",
            "primary_location_name",
            "primary_location_country",
            "primary_location_lat",
            "primary_location_lon",
            "persons_json",
            "links_json",
        ]
        vals = [row.get(c) for c in cols]
        with self.connect() as con:
            con.execute(
                f"""
                INSERT INTO episodes({", ".join(cols)})
                VALUES ({", ".join("?" for _ in cols)})
                ON CONFLICT(guid) DO UPDATE SET
                  podcast_id=excluded.podcast_id,
                  title=excluded.title,
                  published_at=excluded.published_at,
                  description=excluded.description,
                  audio_url=excluded.audio_url,
                  audio_length=excluded.audio_length,
                  duration_seconds=excluded.duration_seconds,
                  incident_type=excluded.incident_type,
                  primary_time_kind=excluded.primary_time_kind,
                  primary_time_year=excluded.primary_time_year,
                  primary_time_start_year=excluded.primary_time_start_year,
                  primary_time_end_year=excluded.primary_time_end_year,
                  primary_location_name=excluded.primary_location_name,
                  primary_location_country=excluded.primary_location_country,
                  primary_location_lat=excluded.primary_location_lat,
                  primary_location_lon=excluded.primary_location_lon,
                  persons_json=excluded.persons_json,
                  links_json=excluded.links_json
                """,
                vals,
            )

    def list_podcasts(self) -> List[Dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM podcasts ORDER BY id").fetchall()
            return [dict(r) for r in rows]

    def list_episodes(self) -> List[Dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM episodes ORDER BY published_at").fetchall()
            return [dict(r) for r in rows]

    def get_episode_by_guid(self, guid: str) -> Dict[str, Any]:
        with self.connect() as con:
            row = con.execute("SELECT * FROM episodes WHERE guid=?", (guid,)).fetchone()
            if row is None:
                raise KeyError(guid)
            return dict(row)

    def query_episodes(
        self,
        *,
        podcast_id: Optional[str] = None,
        q: Optional[str] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        incident_type: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        limit: int = 2000,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM episodes"
        where_sql, params = self._build_where(
            podcast_id=podcast_id,
            q=q,
            date_start=date_start,
            date_end=date_end,
            incident_type=incident_type,
            bbox=bbox,
        )
        sql += where_sql
        sql += " ORDER BY published_at LIMIT ?"
        params.append(int(limit))

        with self.connect() as con:
            rows = con.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def facets(
        self,
        *,
        podcast_id: Optional[str] = None,
        q: Optional[str] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        incident_type: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        location_limit: int = 200,
    ) -> Dict[str, Any]:
        """Compute faceted counts for the given filter set."""

        where_sql, params = self._build_where(
            podcast_id=podcast_id,
            q=q,
            date_start=date_start,
            date_end=date_end,
            incident_type=incident_type,
            bbox=bbox,
        )

        # Helper: because where_sql can be empty, we need to append extra
        # constraints with WHERE or AND correctly.
        def _append(extra_predicate: str) -> str:
            return where_sql + (" AND " if where_sql else " WHERE ") + extra_predicate

        with self.connect() as con:
            total = con.execute(
                f"SELECT COUNT(*) AS c FROM episodes{where_sql}", params
            ).fetchone()["c"]

            inc_rows = con.execute(
                f"""
                SELECT COALESCE(incident_type, 'other') AS incident_type, COUNT(*) AS count
                FROM episodes{where_sql}
                GROUP BY COALESCE(incident_type, 'other')
                ORDER BY count DESC, incident_type ASC
                """,
                params,
            ).fetchall()

            loc_rows = con.execute(
                f"""
                SELECT primary_location_name AS name,
                       primary_location_country AS country,
                       primary_location_lat AS lat,
                       primary_location_lon AS lon,
                       COUNT(*) AS count
                FROM episodes{_append("primary_location_lat IS NOT NULL AND primary_location_lon IS NOT NULL")}
                GROUP BY name, country, lat, lon
                ORDER BY count DESC, name ASC
                LIMIT ?
                """,
                [*params, int(location_limit)],
            ).fetchall()

            unk_loc = con.execute(
                f"""
                SELECT COUNT(*) AS c
                FROM episodes{_append("(primary_location_lat IS NULL OR primary_location_lon IS NULL)")}
                """,
                params,
            ).fetchone()["c"]

            dec_rows = con.execute(
                f"""
                SELECT
                  CASE
                    WHEN COALESCE(primary_time_year, primary_time_start_year, primary_time_end_year) IS NULL
                      THEN NULL
                    ELSE (CAST(COALESCE(primary_time_year, primary_time_start_year, primary_time_end_year) / 10 AS INT) * 10)
                  END AS decade,
                  COUNT(*) AS count
                FROM episodes{where_sql}
                GROUP BY decade
                ORDER BY count DESC, decade ASC
                """,
                params,
            ).fetchall()

        locations = [dict(r) for r in loc_rows]
        if unk_loc:
            locations.append(
                {"name": None, "country": None, "lat": None, "lon": None, "count": int(unk_loc)}
            )

        return {
            "total_count": int(total),
            "incident_types": [dict(r) for r in inc_rows],
            "locations": locations,
            "decades": [dict(r) for r in dec_rows],
        }

    def _build_where(
        self,
        *,
        podcast_id: Optional[str],
        q: Optional[str],
        date_start: Optional[date],
        date_end: Optional[date],
        incident_type: Optional[str],
        bbox: Optional[Tuple[float, float, float, float]],
    ) -> Tuple[str, List[Any]]:
        """Return (where_sql, params).

        where_sql is either an empty string or a string beginning with " WHERE ...".
        """

        where: List[str] = []
        params: List[Any] = []

        if podcast_id:
            where.append("podcast_id = ?")
            params.append(podcast_id)

        if q:
            where.append("(title LIKE ? OR description LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])

        if date_start:
            where.append("date(published_at) >= date(?)")
            params.append(date_start.isoformat())

        if date_end:
            where.append("date(published_at) <= date(?)")
            params.append(date_end.isoformat())

        if incident_type:
            where.append("incident_type = ?")
            params.append(incident_type)

        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            where.append("primary_location_lat IS NOT NULL AND primary_location_lon IS NOT NULL")
            where.append("primary_location_lat BETWEEN ? AND ?")
            where.append("primary_location_lon BETWEEN ? AND ?")
            params.extend([min_lat, max_lat, min_lon, max_lon])

        if where:
            return " WHERE " + " AND ".join(where), params
        return "", params
