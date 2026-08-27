# Datasets

## Canonical DB

- Path: `./active.db`
- Purpose: single source-of-truth SQLite DB for local runs and first-phase CI pages/release flows.
- Versioning policy (phase 1): commit `active.db` to git.
- Typical lifecycle:
  1. copy/import your chosen full DB to `active.db`
  2. after extraction-rule changes, audit and run `podcast-atlas reprocess-derived`
     against `active.db` (the write pass creates a backup by default)
  3. run enrichment/build/export commands against `active.db`
  4. let CI derive `static_site/dataset.json` and `pages/` artifacts from `active.db`

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

`active.db` is the canonical database authority. A production `dataset.json` is always generated
from an explicitly selected SQLite database; it is not a checked-in frontend public asset.

The canonical build is:

```bash
uv run podcast-atlas build-static --db active.db --dataset-out static_site/dataset.json --web-dir frontend
```

That command records the source SQLite SHA-256 in dataset metadata, fails closed if the database
changes during export/build, and copies the exact exported bytes to `frontend/dist/dataset.json`.
The generated build report records both hashes and whether the two dataset artifacts match.

`frontend/public/dataset.json` is intentionally forbidden. A plain `pnpm build` therefore builds
the application shell without inventing or silently bundling a stale dataset; use the canonical
Python build above when a deployable dataset is required.

For a read-only trust audit of a database before export:

```bash
uv run podcast-atlas audit-trust --db active.db
```

The audit checks SQLite/FK integrity, episode identities and source linkage, best-reference
ownership, URL/date/span/coordinate structure, markup remnants, and narrowly targeted recurring
boilerplate. Locked/nondeterministic rows are reported rather than rewritten.

## Future Migration Path

When DB size/update frequency makes versioning heavy:
- remove `active.db` from git history for new snapshots,
- publish DB as release asset or store in object storage,
- fetch DB in CI before `podcast-atlas build-static`,
- keep output paths unchanged (`static_site/dataset.json`, `pages/`).
