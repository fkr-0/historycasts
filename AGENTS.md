# AGENTS

## Project focus
This repository has two major tracks:
1. Python analysis + extraction pipeline (ingest RSS/HTML, enrich episode context, store/query SQLite).
2. Web server/client prototyping (FastAPI + JS UI) and static deliverable generation.

Current priority: stabilize the Python/SQLite/export path and static rendering inputs with a single frontend location.

## Active source-of-truth paths
- `src/podcast_atlas/`: core orchestrator package (`ingest`, `db`, `api`, `cli`)
  - `src/podcast_atlas/aggregate/`: canonical extraction/cluster/db-build primitives
  - `src/podcast_atlas/export/`: canonical dataset/static-render bundle helpers
- `frontend/`: Vite + React + Biome webapp
- `scripts/`: operational scripts (`build_demo_db.py`, `merge_feeds_into_db.py`, `unified_export.py`, `export_review.py`)
- `schemas/`: API schema contracts
- `tests/`: Python tests and fixtures
- `active.db`: canonical working SQLite database (repo root)
- `data/`: feed snapshots + curation inputs
- `dbs/`: alternate DB variants and experiments
- `static_site/`: static export artifacts

Dataset path conventions are documented in `DATASETS.md`.

## Archive policy
- Historical tarballs are not active inputs.
- All root-level `.tgz` snapshots were moved to `legacy/archives/`.
- Archive analysis and rationale are documented in `legacy/ARCHIVE_AUDIT.md`.

## Safe execution path (current)
1. Build or merge SQLite DB from feeds and fixtures.
2. Run extraction/enrichment through Python pipeline.
3. Validate with `pytest` and schema checks.
4. Export static JSON from full SQLite using `podcast-atlas export-static`.
5. Build static site assets from exported dataset via `podcast-atlas build-static`.
6. Optionally serve API + static app together from FastAPI (`--build-static`, `--static-dir`, `--static-mount-path`).

## Commands
```bash
# install project and dev dependencies
uv sync --group dev

# build demo DB
uv run podcast-atlas build-sample --db active.db

# merge additional feeds into an existing DB
uv run podcast-atlas merge-feeds --db active.db --rss feeds/a.rss --rss feeds/b.rss --out active.db

# run API server against a DB
uv run podcast-atlas serve --db active.db --host 127.0.0.1 --port 8000

# export full DB to static JSON
uv run podcast-atlas export-static --db active.db --out static_site/dataset.json

# build static dataset + web bundle (pnpm)
uv run podcast-atlas build-static --db active.db --dataset-out static_site/dataset.json --web-dir frontend

# serve API with integrated static build and static mount
uv run podcast-atlas serve --db active.db --build-static --dataset-out static_site/dataset.json --web-dir frontend

# tests
uv run pytest

# quality
make lint
make lintfix
make coverage
```

## Deferred for separate pass
- Additional UX redesign beyond current merged frontend location.
