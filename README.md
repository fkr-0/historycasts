# historycasts

Python-first pipeline for building and enriching a classified database of history podcast episodes, then exporting static JSON for client-side exploration.

## Current scope
- Ingest podcast feeds into SQLite.
- Extract and normalize episode context (time/place/entities/keywords).
- Serve query API for prototyping.
- Export full SQLite data to static JSON for a client-only web deliverable.

## Repository layout
- `src/podcast_atlas/`: orchestrator package (API, CLI, runtime integration)
  - `src/podcast_atlas/aggregate/`: ingestion + extraction + DB population primitives
  - `src/podcast_atlas/export/`: dataset/static rendering + bundling primitives
- `scripts/`: DB build/merge/export utilities
- `schemas/`: response schema definitions
- `tests/`: regression tests and fixtures
- `frontend/`: Vite + React + Biome + Tailwind webapp
- `active.db`: canonical working SQLite database (repo root)
- `data/`: feed snapshots + curation inputs
- `dbs/`: alternate DB variants and experiments
- `static_site/`: static export artifacts
- `legacy/`: archived `.tgz` snapshots + retired legacy layouts (not active source)

See `DATASETS.md` for canonical DB path and dataset lifecycle rules.

## Quickstart
```bash
uv sync --group dev
uv run podcast-atlas serve --db active.db --host 127.0.0.1 --port 8000
```

## Merge feeds and export static JSON
```bash
uv run podcast-atlas merge-feeds --db active.db --rss feeds/feed1.xml --rss feeds/feed2.xml --out active.db
uv run podcast-atlas export-static --db active.db --out static_site/dataset.json
```

## Optional Wikipedia/Wikidata enrichment
```bash
uv run podcast-atlas enrich-wiki --db active.db --max-concepts 300 --min-entity-count 3 --min-confidence 0.6 --overwrite
```
This creates/updates `concepts`, `episode_concepts`, and `concept_claims` tables from extracted entities.

## Build static dataset + web bundle
```bash
uv run podcast-atlas build-static --db active.db --dataset-out static_site/dataset.json --web-dir frontend
```

Run server and trigger static build in the same flow:
```bash
uv run podcast-atlas serve --db active.db --build-static --dataset-out static_site/dataset.json --web-dir frontend
```
Static assets are mounted at `/app` by default (configurable with `--static-mount-path`).
`build-static` also renders documentation pages from `README.md`, `CHANGELOG.md`, and optional `ARCHITECTURE.md` into `frontend/dist/docs/`.

## Test
```bash
uv run pytest
```

## Developer targets
```bash
make install
make test
make lint
make format-check
make lintfix
make coverage
make static
make live-static
```

## Live static mode (watch + serve)
```bash
# rebuild static artifacts on file changes and serve frontend/dist
make live-static
```

- Serves with `python -m http.server` on `http://127.0.0.1:8088` by default.
- Uses `inotifywait` when available; otherwise falls back to polling.
- After each rebuild it syncs `static_site/dataset.json` to `frontend/dist/dataset.json`.

Optional overrides:
```bash
HOST=0.0.0.0 PORT=8090 SERVE_DIR=frontend/dist make live-static
```

## Archive cleanup
Root-level `.tgz` files were analyzed and moved into `legacy/archives/`.
See `legacy/ARCHIVE_AUDIT.md` for inventory and disposition.

## GitHub Actions + Pages
- Workflow: `.github/workflows/ci-pages.yml`
- Runs lint, format check, tests, and coverage.
- First-phase publish model:
  - committed root DB: `active.db`
  - CI derives all publish artifacts from that DB
- On `main`, builds:
  - static dataset (`static_site/dataset.json`)
  - webapp bundle (`frontend/dist`)
  - Pages bundle with:
    - `/app` (webapp)
    - `/static` (static site artifacts)
    - `/data/dataset.json`
    - `/reports/build-report.html`
    - `/reports/build-stats.json`
- On tag pushes matching `v*`, also creates a GitHub Release asset archive:
  - `historycasts-<tag>-artifacts.tar.gz`
  - includes SQLite DB, dataset JSON, static site bundle, and Pages report bundle.

### Planned follow-up
- If `active.db` grows too large or changes too frequently, move the DB out of git and fetch it in CI from a release artifact or object storage.
- Keep the extraction command stable (`podcast-atlas build-static`) so only DB source location changes.
