from __future__ import annotations

import pytest

from podcast_atlas import cli


def test_parser_supports_enrich_wiki_subcommand() -> None:
    parser = cli.build_parser()
    ns = parser.parse_args(
        [
            "enrich-wiki",
            "--db",
            "dbs/in.db",
            "--max-concepts",
            "120",
            "--min-entity-count",
            "3",
            "--min-confidence",
            "0.7",
            "--languages",
            "de,en",
            "--claim-properties",
            "P31,P17",
            "--overwrite",
        ]
    )

    assert ns.cmd == "enrich-wiki"
    assert ns.db == "dbs/in.db"
    assert ns.max_concepts == 120
    assert ns.min_entity_count == 3
    assert ns.min_confidence == 0.7
    assert ns.languages == "de,en"
    assert ns.claim_properties == "P31,P17"
    assert ns.overwrite is True


def test_enrich_wiki_command_executes_enricher(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_enrich(
        db_path: str,
        *,
        max_concepts: int,
        min_entity_count: int,
        min_confidence: float,
        languages: list[str],
        claim_properties: list[str],
        overwrite: bool,
    ) -> dict[str, int]:
        called["db_path"] = db_path
        called["max_concepts"] = max_concepts
        called["min_entity_count"] = min_entity_count
        called["min_confidence"] = min_confidence
        called["languages"] = languages
        called["claim_properties"] = claim_properties
        called["overwrite"] = overwrite
        return {
            "candidates": 0,
            "concepts_upserted": 0,
            "episode_links_upserted": 0,
            "claims_upserted": 0,
        }

    monkeypatch.setattr(cli, "enrich_with_wikidata", fake_enrich)

    rc = cli.main(
        [
            "enrich-wiki",
            "--db",
            "dbs/in.db",
            "--max-concepts",
            "120",
            "--min-entity-count",
            "3",
            "--min-confidence",
            "0.7",
            "--languages",
            "de,en",
            "--claim-properties",
            "P31,P17",
            "--overwrite",
        ]
    )

    assert rc == 0
    assert called["db_path"] == "dbs/in.db"
    assert called["max_concepts"] == 120
    assert called["min_entity_count"] == 3
    assert called["min_confidence"] == 0.7
    assert called["languages"] == ["de", "en"]
    assert called["claim_properties"] == ["P31", "P17"]
    assert called["overwrite"] is True
