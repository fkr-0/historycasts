from __future__ import annotations

from pathlib import Path

import httpx

from podcast_atlas.db import Database
from podcast_atlas.ingest import ingest_podcastde_archive


def test_ingest_podcastde_archive_with_mock_http(tmp_path: Path):
    # Arrange: a tiny mock world.
    archive_url = "https://www.podcast.de/podcast/3205118/archiv"
    ep1_url = "https://www.podcast.de/episode/701243987/bayern-warum-gibt-es-die-csu"
    ep2_url = "https://www.podcast.de/episode/699612289/verhinderter-staat-die-ausrufung-der-demokratischen-arabischen-republik-sahara"

    archive_html = Path("tests/fixtures/podcastde_archive_page1.html").read_text(encoding="utf-8")
    ep1_html = Path("tests/fixtures/podcastde_episode_bayern.html").read_text(encoding="utf-8")
    ep2_html = Path("tests/fixtures/podcastde_episode_westsahara.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == archive_url:
            return httpx.Response(200, text=archive_html)
        if str(request.url) == ep1_url:
            return httpx.Response(200, text=ep1_html)
        if str(request.url) == ep2_url:
            return httpx.Response(200, text=ep2_html)
        raise AssertionError(f"unexpected url {request.url!s}")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    db_path = tmp_path / "atlas.sqlite"
    db = Database.create(db_path)

    # Act
    ingest_podcastde_archive(
        db,
        podcast_id="mix",
        feed_url="podcast.de:mock",
        archive_url=archive_url,
        overrides_path=None,
        max_pages=1,
        max_episodes=10,
        http_client=client,
    )

    # Assert
    eps = db.list_episodes()
    assert len(eps) == 2

    e1 = db.get_episode_by_guid("podcastde:701243987")
    assert e1["primary_location_name"] == "Bayern"
    assert e1["duration_seconds"] == 51 * 60

    e2 = db.get_episode_by_guid("podcastde:699612289")
    assert e2["primary_location_name"] == "Westsahara"
    assert e2["primary_time_year"] == 1975
