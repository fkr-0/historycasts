from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import httpx

WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_ENTITY_DATA_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"


@dataclass(frozen=True)
class EntityCandidate:
    name: str
    kind: str
    entity_count: int
    avg_confidence: float


def _ensure_enrichment_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS concepts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          url TEXT,
          qid TEXT UNIQUE,
          kind TEXT,
          description TEXT,
          entity_count INTEGER,
          avg_confidence REAL
        );

        CREATE TABLE IF NOT EXISTS episode_concepts (
          episode_id INTEGER REFERENCES episodes(id),
          concept_id INTEGER REFERENCES concepts(id),
          score REAL,
          PRIMARY KEY (episode_id, concept_id)
        );

        CREATE TABLE IF NOT EXISTS concept_claims (
          concept_id INTEGER REFERENCES concepts(id),
          property TEXT,
          value TEXT,
          PRIMARY KEY (concept_id, property, value)
        );
        """
    )
    conn.commit()


def _list_entity_candidates(
    conn: sqlite3.Connection,
    *,
    min_entity_count: int,
    min_confidence: float,
    max_concepts: int,
) -> list[EntityCandidate]:
    has_entities = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='entities'"
    ).fetchone()
    if not has_entities or int(has_entities[0]) == 0:
        return []

    rows = conn.execute(
        """
        SELECT
          trim(name) AS name,
          COALESCE(kind, 'unknown') AS kind,
          COUNT(*) AS c,
          AVG(COALESCE(confidence, 0.0)) AS avg_conf
        FROM entities
        WHERE name IS NOT NULL AND trim(name) <> ''
        GROUP BY trim(name), COALESCE(kind, 'unknown')
        HAVING COUNT(*) >= ? AND AVG(COALESCE(confidence, 0.0)) >= ?
        ORDER BY c DESC, avg_conf DESC, name ASC
        LIMIT ?
        """,
        (min_entity_count, min_confidence, max_concepts),
    ).fetchall()

    return [
        EntityCandidate(
            name=str(row[0]),
            kind=str(row[1]),
            entity_count=int(row[2]),
            avg_confidence=float(row[3]),
        )
        for row in rows
    ]


def _search_wikidata_qid(
    client: httpx.Client, *, name: str, languages: Sequence[str]
) -> tuple[str, str | None] | None:
    for lang in languages:
        try:
            response = client.get(
                WIKIDATA_SEARCH_URL,
                params={
                    "action": "wbsearchentities",
                    "search": name,
                    "language": lang,
                    "format": "json",
                    "limit": 1,
                    "type": "item",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            continue

        hits = payload.get("search", [])
        if not hits:
            continue
        first = hits[0]
        qid = first.get("id")
        desc = first.get("description")
        if isinstance(qid, str) and qid.startswith("Q"):
            return qid, desc if isinstance(desc, str) else None
    return None


def _fetch_entity_data(client: httpx.Client, qid: str) -> dict[str, Any] | None:
    try:
        response = client.get(WIKIDATA_ENTITY_DATA_URL.format(qid=qid))
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    entities = payload.get("entities", {})
    entity = entities.get(qid)
    return entity if isinstance(entity, dict) else None


def _format_claim_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, dict):
        if "id" in value and isinstance(value["id"], str):
            return value["id"]
        if "time" in value and isinstance(value["time"], str):
            return value["time"].lstrip("+").split("T", 1)[0]
        if "text" in value and isinstance(value["text"], str):
            return value["text"]
        if "amount" in value and isinstance(value["amount"], str):
            return value["amount"]
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    if isinstance(value, list):
        return json.dumps(value[:4], ensure_ascii=True, separators=(",", ":"))
    return None


def _extract_claim_rows(
    entity: dict[str, Any], *, concept_id: int, property_ids: Iterable[str], max_values: int
) -> list[tuple[int, str, str]]:
    claims = entity.get("claims", {})
    if not isinstance(claims, dict):
        return []

    rows: list[tuple[int, str, str]] = []
    seen: set[tuple[str, str]] = set()

    for prop in property_ids:
        statements = claims.get(prop, [])
        if not isinstance(statements, list):
            continue
        for stmt in statements[:max_values]:
            if not isinstance(stmt, dict):
                continue
            mainsnak = stmt.get("mainsnak", {})
            if not isinstance(mainsnak, dict):
                continue
            if mainsnak.get("snaktype") != "value":
                continue
            datavalue = mainsnak.get("datavalue", {})
            if not isinstance(datavalue, dict):
                continue
            parsed = _format_claim_value(datavalue.get("value"))
            if not parsed:
                continue
            key = (prop, parsed)
            if key in seen:
                continue
            rows.append((concept_id, prop, parsed))
            seen.add(key)

    return rows


def _pick_wikipedia_url(entity: dict[str, Any]) -> str | None:
    sitelinks = entity.get("sitelinks", {})
    if not isinstance(sitelinks, dict):
        return None

    for wiki_key in ("dewiki", "enwiki"):
        site = sitelinks.get(wiki_key, {})
        if not isinstance(site, dict):
            continue
        url = site.get("url")
        if isinstance(url, str) and url:
            return url
    return None


def enrich_with_wikidata(
    db_path: str,
    *,
    max_concepts: int = 400,
    min_entity_count: int = 2,
    min_confidence: float = 0.6,
    languages: Sequence[str] = ("de", "en"),
    claim_properties: Sequence[str] = (
        "P31",
        "P279",
        "P17",
        "P131",
        "P361",
        "P527",
        "P569",
        "P570",
        "P571",
        "P580",
        "P582",
        "P585",
    ),
    overwrite: bool = False,
) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    _ensure_enrichment_schema(conn)
    if overwrite:
        conn.execute("DELETE FROM concept_claims")
        conn.execute("DELETE FROM episode_concepts")
        conn.execute("DELETE FROM concepts")
        conn.commit()

    candidates = _list_entity_candidates(
        conn,
        min_entity_count=min_entity_count,
        min_confidence=min_confidence,
        max_concepts=max_concepts,
    )
    if not candidates:
        conn.close()
        return {
            "candidates": 0,
            "concepts_upserted": 0,
            "episode_links_upserted": 0,
            "claims_upserted": 0,
        }

    concepts_upserted = 0
    episode_links_upserted = 0
    claims_upserted = 0

    with httpx.Client(
        timeout=10.0,
        follow_redirects=True,
        headers={"User-Agent": "historycasts/0.2.0 (https://github.com/example/historycasts)"},
    ) as client:
        for cand in candidates:
            match = _search_wikidata_qid(client, name=cand.name, languages=languages)
            if not match:
                continue
            qid, desc = match
            entity = _fetch_entity_data(client, qid)
            if not entity:
                continue

            wiki_url = _pick_wikipedia_url(entity)
            cur = conn.execute(
                """
                INSERT INTO concepts (name, url, qid, kind, description, entity_count, avg_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(qid) DO UPDATE SET
                  name=excluded.name,
                  url=COALESCE(excluded.url, concepts.url),
                  kind=excluded.kind,
                  description=COALESCE(excluded.description, concepts.description),
                  entity_count=excluded.entity_count,
                  avg_confidence=excluded.avg_confidence
                """,
                (
                    cand.name,
                    wiki_url,
                    qid,
                    cand.kind,
                    desc,
                    cand.entity_count,
                    cand.avg_confidence,
                ),
            )
            concepts_upserted += cur.rowcount if cur.rowcount > 0 else 0

            concept_id_row = conn.execute("SELECT id FROM concepts WHERE qid=?", (qid,)).fetchone()
            if not concept_id_row:
                continue
            concept_id = int(concept_id_row["id"])

            map_cur = conn.execute(
                """
                INSERT OR IGNORE INTO episode_concepts (episode_id, concept_id, score)
                SELECT DISTINCT episode_id, ?, ?
                FROM entities
                WHERE trim(name)=? AND COALESCE(kind, 'unknown')=?
                """,
                (concept_id, cand.avg_confidence, cand.name, cand.kind),
            )
            episode_links_upserted += map_cur.rowcount if map_cur.rowcount > 0 else 0

            claim_rows = _extract_claim_rows(
                entity,
                concept_id=concept_id,
                property_ids=claim_properties,
                max_values=6,
            )
            if claim_rows:
                claims_cur = conn.executemany(
                    """
                    INSERT OR IGNORE INTO concept_claims (concept_id, property, value)
                    VALUES (?, ?, ?)
                    """,
                    claim_rows,
                )
                claims_upserted += claims_cur.rowcount if claims_cur.rowcount > 0 else 0

            conn.commit()

    conn.close()
    return {
        "candidates": len(candidates),
        "concepts_upserted": concepts_upserted,
        "episode_links_upserted": episode_links_upserted,
        "claims_upserted": claims_upserted,
    }
