from __future__ import annotations

import sys

from podcast_atlas.aggregate import cli


def test_aggregate_cli_passes_year_max_and_review_flag(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_db(db: str, rss: list[str], gazetteer: str, **kwargs) -> None:
        captured["db"] = db
        captured["rss"] = rss
        captured["gazetteer"] = gazetteer
        captured["kwargs"] = kwargs

    monkeypatch.setattr(cli, "build_db", fake_build_db)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "podcast-db",
            "--db",
            "active.db",
            "--rss",
            "a.xml",
            "--rss",
            "b.xml",
            "--gazetteer",
            "g.csv",
            "--year-max",
            "2025",
            "--disable-heuristic-review",
        ],
    )

    cli.main()

    assert captured["db"] == "active.db"
    assert captured["rss"] == ["a.xml", "b.xml"]
    assert captured["gazetteer"] == "g.csv"
    kwargs = captured["kwargs"]
    assert kwargs["year_max"] == 2025
    assert kwargs["enable_heuristic_review"] is False
    assert kwargs["limit"] == 0
