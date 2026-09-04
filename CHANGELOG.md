# Changelog

## [Unreleased]

### Added
- Added a read-only `podcast-atlas audit-trust` gate for SQLite/FK integrity, episode/source identity, best-reference ownership, URL/date/span/coordinate structure, targeted boilerplate, and protected-row reporting.
- Added compact dataset provenance/coverage metadata, including the exact source DB SHA-256 and mapped/unmapped/clustered episode coverage.

### Changed
- Made `dataset.json` generated-only for the frontend: removed the stale checked-in `frontend/public/dataset.json`, made plain frontend builds fail if it reappears, and strengthened `build-static` to prove the exported dataset and `frontend/dist/dataset.json` are byte-identical and tied to one unchanged DB revision.
- Narrowed description cleanup to catch the recurring truncated `Die passende Ausgabe “Eine Stunde History”` cross-promo while preserving ordinary natural-language references to the show.

### Fixed
- Made `reprocess-derived --dry-run` genuinely read-only by opening SQLite in read-only URI mode instead of running schema migration/initialization code during an audit.

## [0.3.6] - 2026-05-10

### Added
- Added the `HISTORYCASTS v0.3.6` release marker to the application header.

### Changed
- Enlarged the exploration map area and adjusted timeline/map sizing so the center pane gives the map substantially more room.

### Fixed
- Restored collapsible side-panel resizing by driving expand/collapse through panel handles while retaining normal resizable min/max constraints.

## [0.3.5] - 2026-05-10

### Fixed
- Fixed three-pane divider behavior in `AppFrame` by using numeric panel sizes and rebalancing min/default widths so left/right panes are practically resizable and no longer squeezed.

## [0.3.4] - 2026-05-10

### Added
- Added static build report artifacts at `frontend/dist/docs/build-report.html` and `build-report.json` during `podcast-atlas build-static`.
- Added a `BUILD REPORT` header link in the web app next to `CHANGELOG`.

### Changed
- Changed GitHub Pages deployment to publish `frontend/dist` directly (web app only), instead of the custom multi-folder `pages/` bundle.
- Changed Pages web build base path from `/<repo>/app/` to `/<repo>/` for direct dist hosting.

### Fixed
- Fixed dataset loading in the web app to resolve `dataset.json` from the deployed base path.
- Fixed docs modal iframe URLs to resolve from the deployed base path (project Pages compatible).

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
