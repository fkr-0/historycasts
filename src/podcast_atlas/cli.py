from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from .aggregate.wiki_enrich import enrich_with_wikidata
from .api import create_app
from .curation import delete_episode_spans
from .db import Database
from .feed_merge import merge_feeds
from .geocode_places import geocode_places
from .ingest import ingest_podcastde_archive, ingest_rss_file
from .metadata_merge import merge_handcrafted_metadata
from .static_build import build_static
from .static_export import export_dataset, write_json


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="podcast-atlas")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ing = sub.add_parser("ingest", help="Ingest an RSS feed from a local XML file into sqlite")
    p_ing.add_argument("--db", required=True, help="SQLite DB path")
    p_ing.add_argument("--podcast-id", required=True, help="Short id for the podcast, e.g. drig")
    p_ing.add_argument("--feed-url", required=True, help="Feed URL (or a label like fixture:drig)")
    p_ing.add_argument("--rss-file", required=True, help="Path to RSS XML file")
    p_ing.add_argument(
        "--overrides", default="data/manual_overrides.yml", help="Manual overrides YAML"
    )

    p_pd = sub.add_parser(
        "ingest-podcastde", help="Ingest from a podcast.de archive by crawling episode pages"
    )
    p_pd.add_argument("--db", required=True, help="SQLite DB path")
    p_pd.add_argument("--podcast-id", required=True, help="Short id for the podcast, e.g. drig")
    p_pd.add_argument("--archive-url", required=True, help="podcast.de archive URL")
    p_pd.add_argument("--feed-url", default="podcast.de", help="Label stored in DB as feed_url")
    p_pd.add_argument("--max-pages", default=10, type=int)
    p_pd.add_argument("--max-episodes", default=500, type=int)
    p_pd.add_argument(
        "--overrides", default="data/manual_overrides.yml", help="Manual overrides YAML"
    )

    p_srv = sub.add_parser("serve", help="Run FastAPI server")
    p_srv.add_argument("--db", required=True, help="SQLite DB path")
    p_srv.add_argument("--host", default="127.0.0.1")
    p_srv.add_argument("--port", default=8000, type=int)
    p_srv.add_argument(
        "--static-dir", default=None, help="Directory with built static web assets to mount"
    )
    p_srv.add_argument("--static-mount-path", default="/app", help="Path prefix for static assets")
    p_srv.add_argument(
        "--build-static", action="store_true", help="Build dataset + web app before serving"
    )
    p_srv.add_argument(
        "--dataset-out", default="static_site/dataset.json", help="Dataset JSON output path"
    )
    p_srv.add_argument(
        "--web-dir", default="frontend", help="Web app directory containing package.json"
    )
    p_srv.add_argument(
        "--skip-web-build", action="store_true", help="Only export dataset, skip pnpm web build"
    )

    p_build = sub.add_parser("build-sample", help="Build sample DB from fixtures (offline demo)")
    p_build.add_argument("--db", default="active.db", help="Output sqlite path")

    p_merge = sub.add_parser(
        "merge-feeds", help="Merge multiple RSS feed files into an existing DB"
    )
    p_merge.add_argument("--db", required=True, help="Path to existing SQLite DB")
    p_merge.add_argument(
        "--rss", action="append", required=True, help="Path to RSS feed file (repeatable)"
    )
    p_merge.add_argument("--out", required=True, help="Output path for merged DB")

    p_export = sub.add_parser("export-static", help="Export a SQLite DB as static dataset JSON")
    p_export.add_argument("--db", required=True, help="Path to SQLite DB")
    p_export.add_argument("--out", required=True, help="Output dataset JSON path")
    p_export.add_argument("--minify", action="store_true", help="Write compact JSON")

    p_build_static = sub.add_parser("build-static", help="Build static dataset and web app bundle")
    p_build_static.add_argument("--db", required=True, help="Path to SQLite DB")
    p_build_static.add_argument("--dataset-out", required=True, help="Output path for dataset JSON")
    p_build_static.add_argument(
        "--web-dir", required=True, help="Web app directory containing package.json"
    )
    p_build_static.add_argument(
        "--skip-web-build", action="store_true", help="Only export dataset JSON"
    )

    p_enrich = sub.add_parser(
        "enrich-wiki", help="Enrich entities with Wikipedia/Wikidata concepts and claims"
    )
    p_enrich.add_argument("--db", required=True, help="Path to SQLite DB")
    p_enrich.add_argument(
        "--max-concepts", type=int, default=400, help="Maximum grouped entities to resolve"
    )
    p_enrich.add_argument(
        "--min-entity-count", type=int, default=2, help="Minimum frequency per entity candidate"
    )
    p_enrich.add_argument(
        "--min-confidence", type=float, default=0.6, help="Minimum average entity confidence"
    )
    p_enrich.add_argument(
        "--languages",
        default="de,en",
        help="Comma-separated language priority for Wikidata search",
    )
    p_enrich.add_argument(
        "--claim-properties",
        default="P31,P279,P17,P131,P361,P527,P569,P570,P571,P580,P582,P585",
        help="Comma-separated Wikidata property ids to extract",
    )
    p_enrich.add_argument(
        "--overwrite", action="store_true", help="Clear existing concepts/mappings before enrich"
    )

    p_delete_spans = sub.add_parser(
        "delete-spans",
        help="Delete time spans for an episode while preserving optional keep-span ids",
    )
    p_delete_spans.add_argument("--db", required=True, help="Path to SQLite DB")
    p_delete_spans.add_argument("--episode-id", required=True, type=int, help="Episode id")
    p_delete_spans.add_argument(
        "--keep-span-id",
        action="append",
        type=int,
        default=[],
        help="Span id to preserve (repeatable)",
    )

    p_merge_meta = sub.add_parser(
        "merge-handcrafted",
        help="Merge handcrafted metadata from res/res.json into SQLite as protected rows",
    )
    p_merge_meta.add_argument("--db", required=True, help="Path to SQLite DB")
    p_merge_meta.add_argument(
        "--res-json",
        default="res/res.json",
        help="Path to handcrafted metadata JSON payload",
    )
    p_merge_meta.add_argument(
        "--no-update-best",
        action="store_true",
        help="Do not update episodes.best_span_id/best_place_id",
    )

    p_geocode = sub.add_parser(
        "geocode-places",
        help="Resolve missing place lat/lon coordinates using online geocoding and update DB places",
    )
    p_geocode.add_argument("--db", required=True, help="Path to SQLite DB")
    p_geocode.add_argument(
        "--cache-path",
        default="data/geocode_cache.json",
        help="JSON cache for geocoder lookups",
    )
    p_geocode.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of unresolved canonical places to geocode (0=all)",
    )
    p_geocode.add_argument(
        "--delay-seconds",
        type=float,
        default=1.0,
        help="Delay between provider requests for rate-limit safety",
    )
    p_geocode.add_argument(
        "--user-agent",
        default="podcast-atlas/1.0 (historycasts geocoder)",
        help="HTTP User-Agent for geocoder requests",
    )
    p_geocode.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and report without writing DB updates",
    )

    return p


def cmd_ingest(ns: argparse.Namespace) -> int:
    db = Database.create(Path(ns.db))
    ingest_rss_file(
        db,
        rss_path=Path(ns.rss_file),
        podcast_id=ns.podcast_id,
        feed_url=ns.feed_url,
        overrides_path=Path(ns.overrides) if ns.overrides else None,
    )
    return 0


def cmd_ingest_podcastde(ns: argparse.Namespace) -> int:
    db = Database.create(Path(ns.db))
    ingest_podcastde_archive(
        db,
        podcast_id=ns.podcast_id,
        feed_url=str(ns.feed_url),
        archive_url=str(ns.archive_url),
        overrides_path=Path(ns.overrides) if ns.overrides else None,
        max_pages=int(ns.max_pages),
        max_episodes=int(ns.max_episodes),
    )
    return 0


def cmd_serve(ns: argparse.Namespace) -> int:
    static_dir: Path | None = Path(ns.static_dir) if ns.static_dir else None

    if ns.build_static:
        web_dir = Path(ns.web_dir)
        dataset_out = Path(ns.dataset_out)
        build_static(
            db_path=Path(ns.db),
            dataset_out=dataset_out,
            web_dir=web_dir,
            skip_web_build=bool(ns.skip_web_build),
        )
        if static_dir is None and not ns.skip_web_build:
            static_dir = web_dir / "dist"

    app = create_app(Path(ns.db), static_dir=static_dir, static_mount_path=ns.static_mount_path)
    uvicorn.run(app, host=ns.host, port=int(ns.port), log_level="info")
    return 0


def cmd_build_sample(ns: argparse.Namespace) -> int:
    out = Path(ns.db)
    out.parent.mkdir(parents=True, exist_ok=True)
    db = Database.create(out)

    ingest_rss_file(
        db,
        rss_path=Path("tests/fixtures/der_rest_ist_geschichte.rss.xml"),
        podcast_id="drig",
        feed_url="fixture:drig",
        overrides_path=Path("data/manual_overrides.yml"),
    )
    ingest_rss_file(
        db,
        rss_path=Path("tests/fixtures/eine_stunde_history.rss.xml"),
        podcast_id="esh",
        feed_url="fixture:esh",
        overrides_path=Path("data/manual_overrides.yml"),
    )
    return 0


def cmd_merge_feeds(ns: argparse.Namespace) -> int:
    merge_feeds(db_path=Path(ns.db), rss_paths=[Path(p) for p in ns.rss], out_path=Path(ns.out))
    return 0


def cmd_export_static(ns: argparse.Namespace) -> int:
    payload = export_dataset(Path(ns.db))
    write_json(payload, Path(ns.out), minify=bool(ns.minify))
    return 0


def cmd_build_static(ns: argparse.Namespace) -> int:
    build_static(
        db_path=Path(ns.db),
        dataset_out=Path(ns.dataset_out),
        web_dir=Path(ns.web_dir),
        skip_web_build=bool(ns.skip_web_build),
    )
    return 0


def cmd_enrich_wiki(ns: argparse.Namespace) -> int:
    languages = [s.strip() for s in str(ns.languages).split(",") if s.strip()]
    claim_properties = [s.strip() for s in str(ns.claim_properties).split(",") if s.strip()]
    stats = enrich_with_wikidata(
        str(ns.db),
        max_concepts=int(ns.max_concepts),
        min_entity_count=int(ns.min_entity_count),
        min_confidence=float(ns.min_confidence),
        languages=languages or ["de", "en"],
        claim_properties=claim_properties,
        overwrite=bool(ns.overwrite),
    )
    print(
        "enrich-wiki complete: "
        f"candidates={stats['candidates']} "
        f"concepts_upserted={stats['concepts_upserted']} "
        f"episode_links_upserted={stats['episode_links_upserted']} "
        f"claims_upserted={stats['claims_upserted']}"
    )
    return 0


def cmd_delete_spans(ns: argparse.Namespace) -> int:
    result = delete_episode_spans(
        str(ns.db), episode_id=int(ns.episode_id), keep_span_ids=[int(v) for v in ns.keep_span_id]
    )
    print(
        "delete-spans complete: "
        f"episode_id={result['episode_id']} "
        f"deleted_spans={result['deleted_span_count']} "
        f"deleted_span_entity_links={result['deleted_span_entity_count']} "
        f"deleted_span_place_links={result['deleted_span_place_count']} "
        f"kept={result['kept_span_ids']} "
        f"missing_keep={result['missing_keep_span_ids']}"
    )
    return 0


def cmd_merge_handcrafted(ns: argparse.Namespace) -> int:
    stats = merge_handcrafted_metadata(
        db_path=Path(ns.db),
        res_json_path=Path(ns.res_json),
        update_episode_best_refs=not bool(ns.no_update_best),
    )
    print(
        "merge-handcrafted complete: "
        f"episodes_seen={stats['episodes_seen']} "
        f"episodes_missing={stats['episodes_missing']} "
        f"timespans_inserted={stats['timespans_inserted']} "
        f"places_inserted={stats['places_inserted']} "
        f"entities_inserted={stats['entities_inserted']}"
    )
    return 0


def cmd_geocode_places(ns: argparse.Namespace) -> int:
    def _progress(event: dict[str, object]) -> None:
        kind = str(event.get("event") or "")
        if kind == "start":
            print(
                "geocode-places: start "
                f"candidates={event.get('total_candidates', 0)} "
                f"dry_run={event.get('dry_run', False)}"
            )
            return
        if kind == "progress":
            print(
                "geocode-places: progress "
                f"{event.get('index', 0)}/{event.get('total', 0)} "
                f"status={event.get('status', 'unknown')} "
                f"name={event.get('name', '')} "
                f"cache={event.get('from_cache', False)} "
                f"resolved={event.get('resolved', 0)} "
                f"unresolved={event.get('unresolved', 0)}"
            )
            return
        if kind == "done":
            print(
                "geocode-places: done "
                f"candidates={event.get('candidates', 0)} "
                f"resolved={event.get('resolved', 0)} "
                f"unresolved={event.get('unresolved', 0)}"
            )

    stats = geocode_places(
        db_path=Path(ns.db),
        cache_path=Path(ns.cache_path),
        limit=int(ns.limit),
        delay_seconds=float(ns.delay_seconds),
        dry_run=bool(ns.dry_run),
        user_agent=str(ns.user_agent),
        progress=_progress,
    )
    print(f"geocode-places stats: {json.dumps(stats, ensure_ascii=False, sort_keys=True)}")
    print(
        "geocode-places complete: "
        f"candidates={stats.get('candidates', 0)} "
        f"resolved={stats.get('resolved', 0)} "
        f"unresolved={stats.get('unresolved', 0)} "
        f"updated_rows={stats.get('updated_rows', 0)} "
        f"best_place_updated={stats.get('best_place_updated', 0)} "
        f"cache_hits={stats.get('cache_hits', 0)}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    ns = p.parse_args(argv)

    if ns.cmd == "ingest":
        return cmd_ingest(ns)
    if ns.cmd == "ingest-podcastde":
        return cmd_ingest_podcastde(ns)
    if ns.cmd == "serve":
        return cmd_serve(ns)
    if ns.cmd == "build-sample":
        return cmd_build_sample(ns)
    if ns.cmd == "merge-feeds":
        return cmd_merge_feeds(ns)
    if ns.cmd == "export-static":
        return cmd_export_static(ns)
    if ns.cmd == "build-static":
        return cmd_build_static(ns)
    if ns.cmd == "enrich-wiki":
        return cmd_enrich_wiki(ns)
    if ns.cmd == "delete-spans":
        return cmd_delete_spans(ns)
    if ns.cmd == "merge-handcrafted":
        return cmd_merge_handcrafted(ns)
    if ns.cmd == "geocode-places":
        return cmd_geocode_places(ns)

    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main())
