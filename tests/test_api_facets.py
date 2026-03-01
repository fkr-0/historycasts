import json
from pathlib import Path

import jsonschema
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


def test_api_facets_schema_and_basic_counts(tmp_path: Path):
    db_path = _mk_db(tmp_path)
    app = create_app(db_path)
    c = TestClient(app)

    r = c.get("/api/facets")
    assert r.status_code == 200
    data = r.json()

    schema = json.loads(Path("schemas/api_facets.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=schema)

    it = {x["incident_type"]: x["count"] for x in data["incident_types"]}
    assert it["revolution"] == 2
    assert it["battle"] == 1
    assert it["assassination"] == 1

    decades = {x["decade"]: x["count"] for x in data["decades"]}
    assert decades[1910] == 1
    assert decades[1780] == 1
    assert decades[-40] == 1


def test_api_facets_respects_filters(tmp_path: Path):
    db_path = _mk_db(tmp_path)
    app = create_app(db_path)
    c = TestClient(app)

    # Filter to only revolution episodes
    r = c.get("/api/facets", params={"incident_type": "revolution"})
    assert r.status_code == 200
    data = r.json()

    it = {x["incident_type"]: x["count"] for x in data["incident_types"]}
    assert it == {"revolution": 2}

    locs = {x["name"]: x["count"] for x in data["locations"] if x["name"] is not None}
    assert locs.get("Paris") == 1
    assert locs.get("Kairo") == 1
