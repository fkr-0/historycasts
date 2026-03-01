# Changelog

## [Unreleased]

## [0.3.0] - 2026-03-01

### Added
- Added `podcast-atlas delete-spans` CLI command for FK-safe time span cleanup per episode.
- Added `podcast_atlas.curation.delete_episode_spans` helper and `scripts/delete_episode_spans.py`.
- Added cluster detail center-tab UX with synchronized term/year filtering and cluster-scoped episodes table.
- Added term co-occurrence mini graph with clickable term nodes that apply scope filtering.
- Added cluster entity/place lift tables with sortable ranking controls.
- Added dedicated `Clusters` center tab with sortable index cards (size/cohesion/novelty/spread).
- Added URL-persisted cluster scope query and scope-export copy control in cluster detail.
- Added frontend tests for cluster detail interactions (`frontend/src/components/ClusterDetail.test.tsx`).
- Added frontend tests for URL scope round-trip and cluster index behaviors.

### Changed
- Reinitialized repository history with a sane `.gitignore` and committed `active.db` as phase-1 CI source.
- Updated GitHub Pages workflow to derive dataset and web artifacts directly from committed `active.db`.
- Added Pages base-path support via `VITE_BASE_PATH` in `frontend/vite.config.ts`.
- Cluster selection from filters/search now opens and focuses dedicated cluster tabs instead of only setting a passive filter.
- Extended integration coverage for cluster drill-down behavior in `frontend/src/App.integration.test.tsx`.
- Updated architecture and implementation-plan docs for current intent queue + cluster exploration progress.

### Fixed
- Fixed panel-resize constraints by using percentage sizes in `AppFrame` with `react-resizable-panels`.
- Fixed docs modal rendering/theme and fenced code block output (language labels, no leading blank line, block code styling).
- Fixed Ruff lint violations in export/test modules and restored clean `make lint` checks.

## [0.2.0] - 2026-02-27

### Added
- Added GitHub Actions workflow `.github/workflows/ci-pages.yml` for lint/format/test/coverage and GitHub Pages deployment.
- Added tag-based release publishing job that bundles DB/dataset/static artifacts into a GitHub Release asset archive.
- Added `scripts/build_pages_bundle.py` to assemble published artifacts and generate build/database/dataset reports.
- Added `AGENTS.md` with project operating rules, safe pipeline sequence, and deferred webapp boundary.
- Added `README.md` describing the Python-first ingest/extract/query/export workflow.
- Added `legacy/ARCHIVE_AUDIT.md` with archive hashes, classification, and disposition notes.
- Added package modules `podcast_atlas.feed_merge` and `podcast_atlas.static_export` to centralize DB merge/export logic.
- Added package module `podcast_atlas.static_build` for static dataset + web bundle build orchestration.
- Added CLI commands `merge-feeds` and `export-static` to keep merge/export in one canonical interface.
- Added CLI command `build-static` and extended `serve` with static build/mount options.
- Added `.gitignore` for Python/Node/generated artifact hygiene.
- Added `Makefile` targets: `test`, `lint`, `lintfix`, `coverage`, `static`.
- Added `Makefile` target `format-check`.

### Changed
- Moved all root `.tgz` snapshot archives into `legacy/archives/` to reduce root clutter and avoid snapshot-vs-source ambiguity.
- Switched project workflow documentation from ad-hoc `python`/`PYTHONPATH` commands to `uv sync` + `uv run`.
- Refactored `scripts/merge_feeds_into_db.py` and `scripts/unified_export.py` into thin wrappers over package code.
- Updated `pyproject.toml` for `README.md`, uv packaging mode, and a `dependency-groups.dev` configuration including `ruff`, `mypy`, and `pytest-cov`.
- Switched static web build invocation to `pnpm build`.

## Historical commits

### 2026-02-27
- Added Biome for linting and formatting.
- Added Tailwind CSS for styling.
- Added D3.js v7 for data visualization.
- Added data transformation utilities for stacked timeline.
- Added D3 scale utilities for timeline.
