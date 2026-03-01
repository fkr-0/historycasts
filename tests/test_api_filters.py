from pathlib import Path

from fastapi.testclient import TestClient

from podcast_atlas.api import create_app
from podcast_atlas.db import Database
from podcast_atlas.ingest import ingest_rss_file


def _mk_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "atlas.sqlite"
    db = Database.create(db_path)
    ingest_rss_file(
        db,
        rss_path=Path("tests/fixtures/der_rest_ist_geschichte.rss.xml"),
        podcast_id="drig",
        feed_url="fixture:drig",
        overrides_path=Path("data/manual_overrides.yml"),
    )
    ingest_rss_file(
        db,
        rss_path=Path("tests/fixtures/eine_stunde_history.rss.xml"),
        podcast_id="esh",
        feed_url="fixture:esh",
        overrides_path=Path("data/manual_overrides.yml"),
    )
    return db_path


def test_api_filters_by_date_range(tmp_path: Path):
    db_path = _mk_db(tmp_path)
    app = create_app(db_path)
    c = TestClient(app)

    # Only 2023 Nov 06..13 should include drig-001 and drig-002 (fixture dates)
    r = c.get("/api/episodes", params={"date_start": "2023-11-06", "date_end": "2023-11-13"})
    assert r.status_code == 200
    data = r.json()
    guids = {e["guid"] for e in data["episodes"]}
    assert "drig-001" in guids
    assert "drig-002" in guids
    assert "drig-003" not in guids


def test_api_filters_by_bbox(tmp_path: Path):
    db_path = _mk_db(tmp_path)
    app = create_app(db_path)
    c = TestClient(app)

    # BBox around Germany should include Berlin + Hamburg episodes
    r = c.get("/api/episodes", params={"bbox": "5.0,47.0,15.5,55.5"})
    assert r.status_code == 200
    guids = {e["guid"] for e in r.json()["episodes"]}
    assert "drig-001" in guids  # Berlin
    assert "esh-002" in guids  # Hamburg
    assert "esh-003" not in guids  # Kairo


def test_api_filters_by_incident_type(tmp_path: Path):
    db_path = _mk_db(tmp_path)
    app = create_app(db_path)
    c = TestClient(app)

    r = c.get("/api/episodes", params={"incident_type": "revolution"})
    assert r.status_code == 200
    guids = {e["guid"] for e in r.json()["episodes"]}
    assert "drig-003" in guids
    assert "esh-003" in guids
    assert "drig-002" not in guids
