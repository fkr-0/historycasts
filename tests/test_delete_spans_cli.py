from __future__ import annotations

import pytest

from podcast_atlas import cli


def test_parser_supports_delete_spans_subcommand() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(
        [
            "delete-spans",
            "--db",
            "active.db",
            "--episode-id",
            "109",
            "--keep-span-id",
            "444",
            "--keep-span-id",
            "500",
        ]
    )

    assert ns.cmd == "delete-spans"
    assert ns.db == "active.db"
    assert ns.episode_id == 109
    assert ns.keep_span_id == [444, 500]


def test_delete_spans_command_executes_curation(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_delete_episode_spans(
        db_path: str, *, episode_id: int, keep_span_ids: list[int]
    ) -> dict[str, object]:
        called["db_path"] = db_path
        called["episode_id"] = episode_id
        called["keep_span_ids"] = keep_span_ids
        return {
            "episode_id": episode_id,
            "kept_span_ids": keep_span_ids,
            "missing_keep_span_ids": [],
            "deleted_span_ids": [445, 446],
            "deleted_span_count": 2,
            "deleted_span_entity_count": 2,
            "deleted_span_place_count": 2,
            "best_span_cleared": False,
        }

    monkeypatch.setattr(cli, "delete_episode_spans", fake_delete_episode_spans)

    rc = cli.main(
        [
            "delete-spans",
            "--db",
            "active.db",
            "--episode-id",
            "109",
            "--keep-span-id",
            "444",
        ]
    )

    assert rc == 0
    assert called["db_path"] == "active.db"
    assert called["episode_id"] == 109
    assert called["keep_span_ids"] == [444]
