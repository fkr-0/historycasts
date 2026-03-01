from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import Database


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return date.fromisoformat(s)


def _parse_bbox(s: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not s:
        return None
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be minLon,minLat,maxLon,maxLat")
    min_lon, min_lat, max_lon, max_lat = (float(x) for x in parts)
    return (min_lon, min_lat, max_lon, max_lat)


def _episode_out(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "podcast_id": r["podcast_id"],
        "guid": r["guid"],
        "title": r["title"],
        "published_at": r["published_at"],
        "audio_url": r.get("audio_url"),
        "duration_seconds": r.get("duration_seconds"),
        "incident_type": r.get("incident_type") or "other",
        "primary_time": {
            "kind": r.get("primary_time_kind") or "unknown",
            "year": r.get("primary_time_year"),
            "start_year": r.get("primary_time_start_year"),
            "end_year": r.get("primary_time_end_year"),
        },
        "primary_location": (
            {
                "name": r.get("primary_location_name"),
                "country": r.get("primary_location_country"),
                "lat": r.get("primary_location_lat"),
                "lon": r.get("primary_location_lon"),
            }
            if r.get("primary_location_lat") is not None
            and r.get("primary_location_lon") is not None
            else None
        ),
        "persons": json.loads(r.get("persons_json") or "[]"),
        "links": json.loads(r.get("links_json") or "[]"),
        "description": r.get("description", ""),
    }


def create_app(
    db_path: Path,
    *,
    static_dir: Path | None = None,
    static_mount_path: str = "/app",
) -> FastAPI:
    db = Database(Path(db_path))

    app = FastAPI(title="Podcast Atlas API", version="0.1.0")

    # Local dev convenience
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/podcasts")
    def list_podcasts() -> Dict[str, Any]:
        return {"podcasts": db.list_podcasts()}

    @app.get("/api/episodes")
    def list_episodes(
        podcast_id: Optional[str] = None,
        q: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        incident_type: Optional[str] = None,
        bbox: Optional[str] = None,
        limit: int = 2000,
    ) -> Dict[str, Any]:
        ds = _parse_date(date_start)
        de = _parse_date(date_end)
        bb = _parse_bbox(bbox) if bbox else None
        rows = db.query_episodes(
            podcast_id=podcast_id,
            q=q,
            date_start=ds,
            date_end=de,
            incident_type=incident_type,
            bbox=bb,
            limit=limit,
        )
        eps = [_episode_out(r) for r in rows]
        return {"episodes": eps, "count": len(eps)}

    @app.get("/api/facets")
    def facets(
        podcast_id: Optional[str] = None,
        q: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        incident_type: Optional[str] = None,
        bbox: Optional[str] = None,
        location_limit: int = 200,
    ) -> Dict[str, Any]:
        ds = _parse_date(date_start)
        de = _parse_date(date_end)
        bb = _parse_bbox(bbox) if bbox else None
        return db.facets(
            podcast_id=podcast_id,
            q=q,
            date_start=ds,
            date_end=de,
            incident_type=incident_type,
            bbox=bb,
            location_limit=location_limit,
        )

    @app.get("/api/meta")
    def meta() -> Dict[str, Any]:
        rows = db.list_episodes()
        dates = [datetime.fromisoformat(r["published_at"]).date() for r in rows]
        if dates:
            min_date = min(dates).isoformat()
            max_date = max(dates).isoformat()
        else:
            min_date = None
            max_date = None
        incident_types = sorted({(r.get("incident_type") or "other") for r in rows})
        podcasts = db.list_podcasts()
        return {
            "min_date": min_date,
            "max_date": max_date,
            "incident_types": incident_types,
            "podcasts": podcasts,
        }

    if static_dir is not None:
        static_dir = Path(static_dir)
        if not static_dir.exists():
            raise FileNotFoundError(f"Static directory does not exist: {static_dir}")
        app.mount(
            static_mount_path, StaticFiles(directory=str(static_dir), html=True), name="static-app"
        )

    return app
