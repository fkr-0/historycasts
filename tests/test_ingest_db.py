from pathlib import Path

from podcast_atlas.db import Database
from podcast_atlas.ingest import ingest_rss_file


def test_ingest_fixture_feeds_into_sqlite(tmp_path: Path):
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

    podcasts = db.list_podcasts()
    assert {p["id"] for p in podcasts} == {"drig", "esh"}

    eps = db.list_episodes()
    assert len(eps) == 6

    # Manual override should set primary location and incident type.
    e = db.get_episode_by_guid("drig-002")
    assert e["incident_type"] == "battle"
    assert e["primary_location_name"] == "Verdun"
    assert e["primary_time_year"] == 1916

    e2 = db.get_episode_by_guid("esh-001")
    assert e2["incident_type"] == "assassination"
    assert e2["primary_time_year"] == -44
