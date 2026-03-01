from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest


@pytest.fixture()
def fx_bayern_html() -> str:
    return Path("tests/fixtures/podcastde_episode_bayern.html").read_text(encoding="utf-8")


@pytest.fixture()
def fx_westsahara_html() -> str:
    return Path("tests/fixtures/podcastde_episode_westsahara.html").read_text(encoding="utf-8")


def test_parse_podcastde_episode_extracts_core_fields(fx_bayern_html: str):
    from podcast_atlas.podcastde import parse_episode_page

    ep = parse_episode_page(fx_bayern_html, default_guid="podcastde:701243987")

    assert ep.guid == "podcastde:701243987"
    assert ep.title == "Bayern - Warum gibt es die CSU?"
    assert ep.audio_url and ep.audio_url.startswith("https://podcast-mp3.dradio.de/")
    assert ep.duration_seconds == 51 * 60
    assert ep.published_date == date(2026, 2, 26)
    assert "CSU" in ep.description


def test_parse_podcastde_episode_handles_missing_pub_date_by_deriving_from_audio_url(
    fx_westsahara_html: str,
):
    from podcast_atlas.podcastde import parse_episode_page

    # Remove the explicit pub date from the fixture to ensure URL-based fallback works.
    html = fx_westsahara_html.replace("20.02.2026", "---")
    ep = parse_episode_page(html, default_guid="podcastde:699612289")

    assert ep.published_date == date(2026, 2, 20)
    assert ep.duration_seconds == 46 * 60
    assert "Westsahara" in ep.description


def test_parse_podcastde_archive_extracts_episode_urls_and_next_page():
    from podcast_atlas.podcastde import parse_archive_page

    html = Path("tests/fixtures/podcastde_archive_page1.html").read_text(encoding="utf-8")
    out = parse_archive_page(html)

    assert (
        "https://www.podcast.de/episode/701243987/bayern-warum-gibt-es-die-csu" in out.episode_urls
    )
    assert (
        "https://www.podcast.de/episode/699612289/verhinderter-staat-die-ausrufung-der-demokratischen-arabischen-republik-sahara"
        in out.episode_urls
    )
    assert out.next_page_url == "https://www.podcast.de/podcast/3205118/archiv?page=2"
