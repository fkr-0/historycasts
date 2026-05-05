from __future__ import annotations

from pathlib import Path

import pytest

from podcast_atlas import cli


def test_parser_supports_build_static_subcommand() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(
        [
            "build-static",
            "--db",
            "dbs/in.db",
            "--dataset-out",
            "static_site/dataset.json",
            "--web-dir",
            "web",
            "--skip-web-build",
        ]
    )

    assert ns.cmd == "build-static"
    assert ns.db == "dbs/in.db"
    assert ns.dataset_out == "static_site/dataset.json"
    assert ns.web_dir == "web"
    assert ns.skip_web_build is True


def test_build_static_command_executes_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_build_static(
        *, db_path: Path, dataset_out: Path, web_dir: Path, skip_web_build: bool
    ) -> None:
        called["db_path"] = db_path
        called["dataset_out"] = dataset_out
        called["web_dir"] = web_dir
        called["skip_web_build"] = skip_web_build

    monkeypatch.setattr(cli, "build_static", fake_build_static)

    rc = cli.main(
        [
            "build-static",
            "--db",
            "dbs/in.db",
            "--dataset-out",
            "static_site/dataset.json",
            "--web-dir",
            "web",
            "--skip-web-build",
        ]
    )

    assert rc == 0
    assert called["db_path"] == Path("dbs/in.db")
    assert called["dataset_out"] == Path("static_site/dataset.json")
    assert called["web_dir"] == Path("web")
    assert called["skip_web_build"] is True


def test_parser_supports_geocode_places_subcommand() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(
        [
            "geocode-places",
            "--db",
            "active.db",
            "--cache-path",
            "data/geocode_cache.json",
            "--limit",
            "25",
            "--dry-run",
        ]
    )

    assert ns.cmd == "geocode-places"
    assert ns.db == "active.db"
    assert ns.cache_path == "data/geocode_cache.json"
    assert ns.limit == 25
    assert ns.dry_run is True


def test_geocode_places_command_executes_enricher(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_geocode_places(
        *,
        db_path: Path,
        cache_path: Path,
        limit: int,
        delay_seconds: float,
        dry_run: bool,
        user_agent: str,
        progress,
    ) -> dict[str, int]:
        called["db_path"] = db_path
        called["cache_path"] = cache_path
        called["limit"] = limit
        called["delay_seconds"] = delay_seconds
        called["dry_run"] = dry_run
        called["user_agent"] = user_agent
        called["progress"] = progress
        progress({"event": "start", "total_candidates": 1, "dry_run": False})
        progress(
            {
                "event": "progress",
                "index": 1,
                "total": 1,
                "status": "resolved",
                "name": "Paris",
                "from_cache": False,
                "resolved": 1,
                "unresolved": 0,
            }
        )
        progress({"event": "done", "candidates": 1, "resolved": 1, "unresolved": 0})
        return {
            "candidates": 1,
            "resolved": 1,
            "unresolved": 0,
            "updated_rows": 2,
            "best_place_updated": 1,
            "cache_hits": 0,
        }

    monkeypatch.setattr(cli, "geocode_places", fake_geocode_places)

    rc = cli.main(
        [
            "geocode-places",
            "--db",
            "active.db",
            "--cache-path",
            "data/geocode_cache.json",
            "--limit",
            "15",
            "--delay-seconds",
            "0.2",
            "--user-agent",
            "historycasts-test/1.0",
        ]
    )

    assert rc == 0
    assert called["db_path"] == Path("active.db")
    assert called["cache_path"] == Path("data/geocode_cache.json")
    assert called["limit"] == 15
    assert called["delay_seconds"] == 0.2
    assert called["dry_run"] is False
    assert called["user_agent"] == "historycasts-test/1.0"
    assert callable(called["progress"])
