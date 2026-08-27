from __future__ import annotations

import hashlib
import json
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
    source_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()

    def fake_export_dataset(path: Path) -> dict[str, object]:
        calls.append(("export_dataset", path))
        return {"meta": {"source_db_sha256": source_hash}, "podcasts": [], "episodes": []}

    def fake_write_json(
        payload: dict[str, object], out_path: Path, *, minify: bool = False
    ) -> None:
        calls.append(("write_json", out_path, minify, payload))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

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
    assert (web_dir / "dist" / "dataset.json").read_bytes() == dataset_out.read_bytes()
    report = json.loads((web_dir / "dist" / "docs" / "build-report.json").read_text())
    assert report["dataset_matches_dist"] is True
    assert report["dataset_sha256"] == hashlib.sha256(dataset_out.read_bytes()).hexdigest()
    assert report["dist_dataset_sha256"] == report["dataset_sha256"]
    assert report["source_db_sha256"] == source_hash
    assert report["dataset_source_db_sha256"] == source_hash


def test_build_static_skip_web_build(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = tmp_path / "podcasts.db"
    db_path.write_text("placeholder", encoding="utf-8")
    dataset_out = tmp_path / "static" / "dataset.json"
    web_dir = tmp_path / "web"
    web_dir.mkdir(parents=True)
    source_hash = hashlib.sha256(db_path.read_bytes()).hexdigest()

    def fake_export_dataset(path: Path) -> dict[str, object]:
        return {"meta": {"source_db_sha256": source_hash}, "podcasts": [], "episodes": []}

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


def test_build_static_writes_build_report_docs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "podcasts.db"
    db_path.write_text("placeholder", encoding="utf-8")
    dataset_out = tmp_path / "static" / "dataset.json"
    web_dir = tmp_path / "web"
    web_dir.mkdir(parents=True)

    payload = {
        "meta": {"source_db_sha256": hashlib.sha256(db_path.read_bytes()).hexdigest()},
        "podcasts": [{"id": 1}],
        "episodes": [{"id": 1}, {"id": 2}],
        "spans": [{"id": 1}],
        "places": [],
        "entities": [],
        "clusters": [{"id": 1}],
        "concepts": [],
        "concept_claims": [],
    }

    def fake_export_dataset(path: Path) -> dict[str, object]:
        return payload

    def fake_write_json(
        payload_obj: dict[str, object], out_path: Path, *, minify: bool = False
    ) -> None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload_obj), encoding="utf-8")

    monkeypatch.setattr("podcast_atlas.static_build.export_dataset", fake_export_dataset)
    monkeypatch.setattr("podcast_atlas.static_build.write_json", fake_write_json)

    build_static(db_path=db_path, dataset_out=dataset_out, web_dir=web_dir, skip_web_build=True)

    assert (web_dir / "dist" / "docs" / "build-report.html").exists()
    assert (web_dir / "dist" / "docs" / "build-report.json").exists()


def test_build_static_rejects_stale_public_dataset_before_export(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "podcasts.db"
    db_path.write_text("placeholder", encoding="utf-8")
    dataset_out = tmp_path / "static" / "dataset.json"
    web_dir = tmp_path / "web"
    public_dir = web_dir / "public"
    public_dir.mkdir(parents=True)
    (public_dir / "dataset.json").write_text('{"stale": true}', encoding="utf-8")

    def fail_export(_path: Path) -> dict[str, object]:
        raise AssertionError("stale public dataset must fail before canonical export")

    monkeypatch.setattr("podcast_atlas.static_build.export_dataset", fail_export)

    with pytest.raises(RuntimeError, match="frontend/public/dataset.json is forbidden"):
        build_static(db_path=db_path, dataset_out=dataset_out, web_dir=web_dir)

    assert not dataset_out.exists()


def test_build_static_rejects_export_from_different_database_revision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db_path = tmp_path / "podcasts.db"
    db_path.write_text("current database", encoding="utf-8")
    dataset_out = tmp_path / "static" / "dataset.json"
    web_dir = tmp_path / "web"
    web_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "podcast_atlas.static_build.export_dataset",
        lambda _path: {
            "meta": {"source_db_sha256": "0" * 64},
            "podcasts": [],
            "episodes": [],
        },
    )

    with pytest.raises(RuntimeError, match="source SQLite revision changed during export"):
        build_static(
            db_path=db_path,
            dataset_out=dataset_out,
            web_dir=web_dir,
            skip_web_build=True,
        )

    assert not dataset_out.exists()
