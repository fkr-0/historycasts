# Architecture

## Top-level model

- `podcast_atlas` is the orchestrator package and CLI surface.
- `podcast_atlas.aggregate` contains ingestion/extraction/database-population primitives.
- `podcast_atlas.export` contains dataset/static-site rendering/bundling primitives.

## Package roles

### `podcast_atlas.aggregate`

- RSS parsing and text normalization (`rss_parse.py`).
- Gazetteer normalization/lookup (`gazetteer.py`).
- Time/place/entity/keyword extraction (`extract.py`).
- DB schema and DB build pipeline (`schema.py`, `db_build.py`).
- Clustering helpers (`cluster.py`).

### `podcast_atlas.export`

- Static dataset extraction (`dataset.py`).
- Static bundle build (`site.py`):
  - write dataset JSON
  - run `pnpm build` for webapp
  - render documentation pages from `README.md`, `CHANGELOG.md`, optional `ARCHITECTURE.md` into `frontend/dist/docs`

### `podcast_atlas` (orchestration)

- CLI command routing (`cli.py`).
- API server and live UX serving (`api.py`).
- DB query model used by API (`db.py`).
- Ingest pipeline for feed/podcast.de into runtime DB (`ingest.py`).
- Static build orchestration delegating to export subsystem (`static_build.py`).

## Migration note

Legacy `podcast_explorer_static` shim modules were removed after importer migration.
Use `podcast_atlas.aggregate.*` and `podcast_atlas.export.*` directly.

## Build flow

1. Aggregate subsystem ingests/extracts/enriches SQLite.
2. Orchestrator chooses runtime behavior (`serve`, `build-static`, `export-static`, etc.).
3. Export subsystem transforms DB → dataset JSON + static web artifacts + docs pages.

## Frontend cluster exploration flow

- Center area provides two fixed top-level tabs:
  - `Explore` (timeline/map workflow)
  - `Clusters` (sortable cluster index by size/cohesion/novelty/spread)
- Cluster selection opens/focuses a dedicated center tab (`cluster-{id}`).
- Cluster detail consumes precomputed export payloads:
  - `cluster_stats`
  - `cluster_term_metrics`
  - `cluster_correlations`
  - `cluster_entity_stats`
  - `cluster_place_stats`
  - `cluster_timeline_histogram`
  - `cluster_next_steps`
- Local scoped state in cluster detail synchronizes:
  - active term (chips/table/term-graph)
  - active year interval (graph slider + timeline bins)
  - derived episode subset table
- Cluster scope is URL-persisted and shareable via query params:
  - `clusterTerm`
  - `clusterYearMin`
  - `clusterYearMax`
  - `clusterSort`
- Related clusters and next-step cards can pivot directly into another cluster tab.
