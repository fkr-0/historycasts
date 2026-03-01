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
