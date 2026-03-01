# Repository Inventory

Snapshot generated: 2026-02-27

## Active code and build surface

- `src/podcast_atlas/`: Python package (aggregate + export + API/orchestration).
- `scripts/`: utility scripts used by project workflows.
- `tests/`: Python test suite.
- `frontend/`: Vite/React/Biome/Tailwind web app.
- `static_site/`: generated static export artifacts (`dataset.json`, docs outputs).
- `.github/workflows/`: CI/build/release pages pipelines.

## Data directories

### `data/` (runtime/demo inputs)

- `data/live/*.rss.xml`: current RSS snapshots used as feed input material.
- `data/gazetteer.csv`, `data/manual_overrides.yml`, `data/manual_review.md`: ingest/extraction support files.

### Canonical DB path

- `active.db` (repo root):
  - Canonical working database path for CLI/docs/Makefile/CI.
  - You can copy a full dataset DB (e.g. former `dbs/podcast_latest_0.8.3.db`) to this path.

### `dbs/` (working / variant databases)

- `dbs/podcast_latest_0.8.3.db`:
  - 1,406 episodes, 5,678 entities, 1,207 spans.
  - Includes enrichment tables (`concepts`, `episode_concepts`, `concept_claims`).
  - Currently best candidate for main full dataset.
- `dbs/podcast_latest_enhanced.db`:
  - 722 episodes, similar extraction tables, no concept enrichment tables.
- `dbs/podcast_latest_gazetteer.db`:
  - 722 episodes, similar to above.
- `dbs/podcast_semantic_latest.db`:
  - semantic/fuzzy schema variant (`fuzzy_times`, `topics`), 722 episodes.
- `dbs/podcast_fuzzy_refined.db`:
  - older fuzzy-focused schema variant, 578 episodes.

## Legacy/archive

- `legacy/archives/`: retained historical snapshots and imported `.tgz` content.
- `legacy/*_legacy` trees: preserved legacy source/tests for traceability.
- `legacy/data_snapshots/podcast_explorer_static/`:
  - `podcast_latest_4feeds.db` (990 episodes, 12,900 entities, 1,817 spans).
  - moved out of `data/` to separate active inputs from historical snapshots.
- `legacy/data_snapshots/podcast_atlas.sample.sqlite`:
  - former sample DB at `data/podcast_atlas.sqlite`, moved to keep canonical path unambiguous.
- `legacy` is larger than active outputs and should be treated as non-runtime history unless explicitly revived.

## What is currently wired into automation

- CI/Pages and Makefile currently use: `active.db`.
- Static web build output: `frontend/dist/` + `static_site/dataset.json`.
- No workflow currently targets `legacy/data_snapshots/podcast_explorer_static/podcast_latest_4feeds.db`.

## Suggested normalization direction

1. Keep `active.db` as the only canonical working path.
2. Keep `data/` restricted to feeds/curation input files.
3. Keep snapshot/legacy DBs in `legacy/` or clearly marked `dbs/` variants.
4. Add one small `DATASETS.md` that defines each DB file purpose, owner, and lifecycle (canonical, experimental, archived).
