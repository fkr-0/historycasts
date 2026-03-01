import json
from pathlib import Path

import jsonschema
from fastapi.testclient import TestClient

from podcast_atlas.api import create_app
from podcast_atlas.db import Database
from podcast_atlas.ingest import ingest_rss_file


def test_api_episodes_schema(tmp_path: Path):
    db_path = tmp_path / "atlas.sqlite"
    db = Database.create(db_path)
    ingest_rss_file(
        db,
        rss_path=Path("tests/fixtures/der_rest_ist_geschichte.rss.xml"),
        podcast_id="drig",
        feed_url="fixture:drig",
        overrides_path=Path("data/manual_overrides.yml"),
    )

    app = create_app(db_path)
    c = TestClient(app)
    r = c.get("/api/episodes")
    assert r.status_code == 200

    schema = json.loads(Path("schemas/api_episodes.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=r.json(), schema=schema)
