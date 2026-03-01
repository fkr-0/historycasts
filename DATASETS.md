# Datasets

## Canonical DB

- Path: `./active.db`
- Purpose: single source-of-truth SQLite DB for local runs and first-phase CI pages/release flows.
- Versioning policy (phase 1): commit `active.db` to git.
- Typical lifecycle:
  1. copy/import your chosen full DB to `active.db`
  2. run enrichment/build/export commands against `active.db`
  3. let CI derive `static_site/dataset.json` and `pages/` artifacts from `active.db`

## Input/Curation Data (`data/`)

`data/` is reserved for non-canonical runtime inputs:
- `data/live/*.rss.xml` feed snapshots
- `data/gazetteer.csv` gazetteer input
- `data/manual_overrides.yml` and `data/manual_review.md`

No canonical SQLite DB should live in `data/`.

## Working Variants (`dbs/`)

These are alternate or historical variants for comparison/experiments:
- `dbs/podcast_latest_0.8.3.db` (largest full extraction DB, enriched)
- `dbs/podcast_latest_enhanced.db`
- `dbs/podcast_latest_gazetteer.db`
- `dbs/podcast_semantic_latest.db`
- `dbs/podcast_fuzzy_refined.db`

## Archived Snapshots (`legacy/data_snapshots/`)

Historical DB snapshots moved out of active data paths:
- `legacy/data_snapshots/podcast_explorer_static/podcast_latest_4feeds.db`
- `legacy/data_snapshots/podcast_atlas.sample.sqlite`

## Build Outputs

- Static dataset export: `static_site/dataset.json`
- Built web app: `frontend/dist/`

These remain outside `data/` because they are build artifacts tied to frontend and release pipelines.

## Future Migration Path

When DB size/update frequency makes versioning heavy:
- remove `active.db` from git history for new snapshots,
- publish DB as release asset or store in object storage,
- fetch DB in CI before `podcast-atlas build-static`,
- keep output paths unchanged (`static_site/dataset.json`, `pages/`).
