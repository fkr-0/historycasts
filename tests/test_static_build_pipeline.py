from __future__ import annotations

from pathlib import Path

import pytest

from podcast_atlas.static_build import build_static


def test_build_static_exports_dataset_and_runs_web_build(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "podcasts.db"
    db_path.write_text("placeholder", encoding="utf-8")
    dataset_out = tmp_path / "static" / "dataset.json"
    web_dir = tmp_path / "web"
    web_dir.mkdir(parents=True)

    calls: list[tuple[str, object]] = []

    def fake_export_dataset(path: Path) -> dict[str, object]:
        calls.append(("export_dataset", path))
        return {"meta": {}, "podcasts": [], "episodes": []}

    def fake_write_json(
        payload: dict[str, object], out_path: Path, *, minify: bool = False
    ) -> None:
        calls.append(("write_json", out_path, minify, payload))

    def fake_run(cmd: list[str], *, cwd: Path, check: bool) -> None:
        calls.append(("run", cmd, cwd, check))

    monkeypatch.setattr("podcast_atlas.static_build.export_dataset", fake_export_dataset)
    monkeypatch.setattr("podcast_atlas.static_build.write_json", fake_write_json)
    monkeypatch.setattr("podcast_atlas.static_build.subprocess.run", fake_run)

    build_static(db_path=db_path, dataset_out=dataset_out, web_dir=web_dir, skip_web_build=False)

    assert ("export_dataset", db_path) in calls
    assert any(c[0] == "write_json" and c[1] == dataset_out for c in calls)
    assert any(
        c[0] == "run" and c[1] == ["pnpm", "build"] and c[2] == web_dir and c[3] is True
        for c in calls
    )


def test_build_static_skip_web_build(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "podcasts.db"
    db_path.write_text("placeholder", encoding="utf-8")
    dataset_out = tmp_path / "static" / "dataset.json"
    web_dir = tmp_path / "web"
    web_dir.mkdir(parents=True)

    def fake_export_dataset(path: Path) -> dict[str, object]:
        return {"meta": {}, "podcasts": [], "episodes": []}

    def fake_write_json(
        payload: dict[str, object], out_path: Path, *, minify: bool = False
    ) -> None:
        return None

    def fail_run(*args: object, **kwargs: object) -> None:
        raise AssertionError("web build should be skipped")

    monkeypatch.setattr("podcast_atlas.static_build.export_dataset", fake_export_dataset)
    monkeypatch.setattr("podcast_atlas.static_build.write_json", fake_write_json)
    monkeypatch.setattr("podcast_atlas.static_build.subprocess.run", fail_run)

    build_static(db_path=db_path, dataset_out=dataset_out, web_dir=web_dir, skip_web_build=True)
