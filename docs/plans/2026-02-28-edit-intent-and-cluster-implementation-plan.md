# Editing Intent + Cluster Exploration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement (1) a local intent-edit operation layer and (2) a high-utility cluster exploration workflow, end-to-end from SQLite export through frontend UX.

**Architecture:** Keep backend as offline/precompute exporter (`sqlite -> dataset.json`) and keep frontend as deterministic client-state UI. Editing intent is modeled as local operation queue (not immediate DB write), with reconciliation against dataset state. Cluster UX is driven by exported precomputed metrics and synchronized scoped filters.

**Tech Stack:** Python (`podcast_atlas` export pipeline), SQLite, React + TypeScript + Vite + Biome, localStorage, D3/Plotly components already in repo.

## Progress update (2026-02-28)

- Phase 1 backend export extensions are implemented (`dataset_revision`, row fingerprints, cluster metric payloads, queue-to-sql utility) with Python tests.
- Phase 2 and Phase 3 intent queue + operation builders are implemented and wired in UI.
- Phase 4 cluster UX is implemented for Axis A:
  - done: dedicated `Clusters` index tab with sortable metrics (size/cohesion/novelty/spread).
  - done: cluster detail tab with term/time synchronized filtering, term graph, related clusters, next-step cards, and entity/place lift tables.
  - done: cluster scope URL persistence (`clusterTerm`, `clusterYearMin`, `clusterYearMax`, `clusterSort`) and explicit scope export/copy UI.

## Phase 0: Baseline and Guardrails

### Task 0.1: Create feature branch checklist doc
**Files:**
- Create: `docs/plans/2026-02-28-edit-intent-and-cluster-checklist.md`

**Step 1: Write checklist skeleton**
Include sections: backend schema/export, frontend intent queue, frontend cluster views, tests, QA scenarios.

**Step 2: Commit**
`git add docs/plans/2026-02-28-edit-intent-and-cluster-checklist.md && git commit -m "docs: add edit-intent+cluster implementation checklist"`

## Phase 1: Backend Export Extensions (Cluster + Reconciliation Metadata)

### Task 1.1: Extend export models
**Files:**
- Modify: `src/podcast_atlas/models.py`
- Test: `tests/test_models.py`

**Step 1: Add new model fields/types**
Add optional/new fields for:
- `ExportMeta.dataset_revision`
- record-level optional `row_fingerprint` on editable rows
- cluster structures:
  - `cluster_stats`
  - `cluster_term_metrics`
  - `cluster_correlations`
  - `cluster_entity_stats`
  - `cluster_place_stats`
  - `cluster_timeline_histogram`
  - `cluster_next_steps`

**Step 2: Add failing model tests**
Validate parsing/serialization for each new payload structure.

**Step 3: Run tests**
`uv run pytest -q tests/test_models.py`

**Step 4: Commit**

### Task 1.2: Implement cluster metric computation helpers
**Files:**
- Create: `src/podcast_atlas/export/cluster_metrics.py`
- Modify: `src/podcast_atlas/export/__init__.py`
- Test: `tests/test_cluster_metrics_export.py`

**Step 1: Add failing tests for deterministic outputs**
Use tiny synthetic payload fixtures and assert exact metric values (or bounded tolerances).

**Step 2: Implement helper functions**
Compute:
- per-cluster summary stats
- term lift / support / drop-impact approximation
- pairwise cluster similarity edges
- timeline bins
- entity/place lift stats
- next-step suggestions

**Step 3: Run tests**
`uv run pytest -q tests/test_cluster_metrics_export.py`

**Step 4: Commit**

### Task 1.3: Wire metrics into static export
**Files:**
- Modify: `src/podcast_atlas/static_export.py`
- Modify: `src/podcast_atlas/export/dataset.py` (if needed)
- Test: `tests/test_static_export_clusters.py`

**Step 1: Add failing export tests**
Assert new cluster fields exist and align with source cluster IDs.

**Step 2: Add `dataset_revision` and row fingerprints**
Include stable revision string and optional fingerprint generation.

**Step 3: Integrate metric helper output into payload**

**Step 4: Run tests**
`uv run pytest -q tests/test_static_export_clusters.py tests/test_static_build_pipeline.py`

**Step 5: Commit**

### Task 1.4: Add operation queue -> SQL compiler utility
**Files:**
- Create: `scripts/queue_to_sql.py`
- Test: `tests/test_queue_to_sql.py`

**Step 1: Add failing snapshot tests**
Input operation JSON -> deterministic SQL script.

**Step 2: Implement compiler**
Wrap in transaction, preserve op order, emit precondition comments/guards.

**Step 3: Run tests**
`uv run pytest -q tests/test_queue_to_sql.py`

**Step 4: Commit**

## Phase 2: Frontend Intent Queue Foundation

### Task 2.1: Add intent operation types and storage API
**Files:**
- Create: `frontend/src/intent/types.ts`
- Create: `frontend/src/intent/storage.ts`
- Create: `frontend/src/intent/reconcile.ts`
- Test: `frontend/src/intent/reconcile.test.ts`
- Test: `frontend/src/intent/storage.test.ts`

**Step 1: Define operation schema and statuses**
`queued | applied | invalid | cancelled`.

**Step 2: Add failing tests for persistence + reconciliation rules**

**Step 3: Implement storage + reconciliation engine**

**Step 4: Run tests**
`cd frontend && pnpm test -- --run src/intent/storage.test.ts src/intent/reconcile.test.ts`

**Step 5: Commit**

### Task 2.2: Add intent queue hook/store
**Files:**
- Create: `frontend/src/intent/useIntentQueue.ts`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/App.integration.test.tsx`

**Step 1: Add failing integration test for queue count badge states**

**Step 2: Implement hook with derived counts + actions**
Actions: add/cancel/remove/cleanup/reconcile/export/copy.

**Step 3: Wire into app root state**

**Step 4: Run test**
`cd frontend && pnpm test -- --run src/App.integration.test.tsx`

**Step 5: Commit**

### Task 2.3: Build operation modal + top-right button
**Files:**
- Create: `frontend/src/components/intent/IntentQueueButton.tsx`
- Create: `frontend/src/components/intent/IntentQueueModal.tsx`
- Create: `frontend/src/components/intent/IntentQueueTable.tsx`
- Modify: `frontend/src/components/app/HeaderBar.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/components/intent/IntentQueueModal.test.tsx`

**Step 1: Add failing component tests**
- button color/state rules
- cleanup confirmation
- cancel/remove actions

**Step 2: Implement components + wiring**

**Step 3: Add export/copy actions**
- JSON download
- SQL download
- clipboard copy

**Step 4: Run tests + lint**
`cd frontend && pnpm test -- --run src/components/intent/IntentQueueModal.test.tsx && pnpm lint`

**Step 5: Commit**

## Phase 3: Frontend Edit Entry Points (Create Operations)

### Task 3.1: Episode-level operation creators
**Files:**
- Create: `frontend/src/intent/opBuilders/episodeOps.ts`
- Modify: `frontend/src/components/EpisodeDetail.tsx`
- Test: `frontend/src/intent/opBuilders/episodeOps.test.ts`

**Step 1: Add failing tests for generated operation payloads**

**Step 2: Implement builders + UI controls**
- title/narrator/kind update intents

**Step 3: Run tests**

**Step 4: Commit**

### Task 3.2: Span/entity/cluster operation creators
**Files:**
- Create: `frontend/src/intent/opBuilders/spanOps.ts`
- Create: `frontend/src/intent/opBuilders/entityOps.ts`
- Create: `frontend/src/intent/opBuilders/clusterOps.ts`
- Modify: `frontend/src/components/EpisodeDetail.tsx`
- Modify: `frontend/src/components/ClusterPanel.tsx`
- Test: corresponding `*.test.ts`

**Step 1: Add failing tests for each op builder**

**Step 2: Implement creation actions in UI**
- span edits
- entity kind/rename
- cluster relabel/include/exclude episode intent

**Step 3: Run tests + lint**

**Step 4: Commit**

## Phase 4: Cluster UX Core (Axis A)

### Task 4.1: Extend frontend dataset types
**Files:**
- Modify: `frontend/src/types.ts`
- Test: `frontend/src/state/clusterSelectors.test.ts`

**Step 1: Add types for new cluster payload sections**

**Step 2: Create selectors module**
- Create: `frontend/src/state/clusterSelectors.ts`

**Step 3: Add failing selector tests and implement**

**Step 4: Run tests**

**Step 5: Commit**

### Task 4.2: Create cluster index view
**Files:**
- Create: `frontend/src/components/clusters/ClusterIndexView.tsx`
- Create: `frontend/src/components/clusters/ClusterCard.tsx`
- Modify: `frontend/src/components/app/RightPanel.tsx` (or app routing slot)
- Test: `frontend/src/components/clusters/ClusterIndexView.test.tsx`

**Step 1: Add failing tests for sorting and selection behavior**

**Step 2: Implement sortable index (size/cohesion/novelty/spread)**

**Step 3: Run tests + lint**

**Step 4: Commit**

### Task 4.3: Create cluster detail view
**Files:**
- Create: `frontend/src/components/clusters/ClusterDetailView.tsx`
- Create: `frontend/src/components/clusters/ClusterTermCloud.tsx`
- Create: `frontend/src/components/clusters/ClusterTimelineChart.tsx`
- Create: `frontend/src/components/clusters/ClusterEpisodesTable.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/components/clusters/ClusterDetailView.test.tsx`

**Step 1: Add failing tests for term click -> scoped episode list sync**

**Step 2: Implement detail panels + shared scope state**

**Step 3: Implement reset controls + breadcrumb**

**Step 4: Run tests + lint**

**Step 5: Commit**

## Phase 5: Cluster UX Vision Features (Axis B)

### Task 5.1: Add drop-impact/lift interaction
**Files:**
- Modify: `frontend/src/components/clusters/ClusterDetailView.tsx`
- Create: `frontend/src/components/clusters/ClusterCoherenceGauge.tsx`
- Test: `frontend/src/components/clusters/ClusterCoherenceGauge.test.tsx`

**Step 1: Add failing tests for simulation toggle effects**

**Step 2: Implement term removal simulation UI using precomputed metrics**

**Step 3: Run tests**

**Step 4: Commit**

### Task 5.2: Add cluster relation graph + next-step cards
**Files:**
- Create: `frontend/src/components/clusters/ClusterRelationGraph.tsx`
- Create: `frontend/src/components/clusters/ClusterNextSteps.tsx`
- Modify: `frontend/src/components/clusters/ClusterDetailView.tsx`
- Test: `frontend/src/components/clusters/ClusterNextSteps.test.tsx`

**Step 1: Add failing tests for suggestion card apply behavior**

**Step 2: Implement graph and card interactions**

**Step 3: Run tests + lint**

**Step 4: Commit**

### Task 5.3: Add scope export features
**Files:**
- Create: `frontend/src/components/clusters/ClusterScopeExport.tsx`
- Modify: `frontend/src/state/clusterSelectors.ts`
- Test: `frontend/src/components/clusters/ClusterScopeExport.test.tsx`

**Step 1: Add failing tests for CSV/PNG export triggers and query-spec serialization**

**Step 2: Implement scope export + query-spec badge**

**Step 3: Run tests**

**Step 4: Commit**

## Phase 6: URL State and Navigation Consistency

### Task 6.1: Add cluster scope URL persistence
**Files:**
- Modify: `frontend/src/urlState.ts`
- Modify: `frontend/src/app/useUrlFilters.tsx`
- Test: `frontend/src/urlState.cluster.test.ts`

**Step 1: Add failing roundtrip tests for cluster scope filters**

**Step 2: Implement encode/decode for cluster id, selected terms, year brush, geo scope**

**Step 3: Run tests**

**Step 4: Commit**

## Phase 7: Documentation + QA Scenarios

### Task 7.1: Update architecture and user docs
**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `README.md`
- Create: `docs/UX_ACCEPTANCE_EDIT_INTENT_AND_CLUSTERS.md`

**Step 1: Document data flow and UX contracts**

**Step 2: Add manual QA scripts matching 8 stories + intent queue lifecycle**

**Step 3: Commit**

## Phase 8: Verification and Release Readiness

### Task 8.1: Full automated verification
**Files:** none

**Step 1: Run backend checks**
- `uv run ruff check src tests scripts`
- `uv run mypy`
- `uv run pytest`

**Step 2: Run frontend checks**
- `cd frontend && pnpm lint`
- `cd frontend && pnpm test -- --run`
- `cd frontend && pnpm build`

**Step 3: Run static build with canonical DB**
- `uv run podcast-atlas build-static --db active.db --dataset-out static_site/dataset.json --web-dir frontend`

**Step 4: Validate generated dataset sections**
Assert new keys exist in `static_site/dataset.json`:
- `cluster_stats`
- `cluster_term_metrics`
- `cluster_correlations`
- `cluster_next_steps`

**Step 5: Commit final integration changes**

---

## Test Checklist (Definition of Done)
- [ ] Export includes dataset revision and row fingerprints for editable rows.
- [ ] Intent queue persists in localStorage, supports cancel/remove/cleanup.
- [ ] Reconciliation marks queued/applied/invalid correctly.
- [ ] Intent modal exports JSON and SQL and supports clipboard copy.
- [ ] At least 4 edit entry points create valid queue operations.
- [ ] Cluster index sortable by at least 4 metrics.
- [ ] Cluster detail has synchronized term/time/map/table filters.
- [ ] Drop-impact and lift visible and interactive.
- [ ] Relation graph and next-step cards navigable.
- [ ] URL state restores cluster scope correctly.
- [ ] All backend + frontend lint/tests/build pass.

## Suggested Commit Strategy
1. `feat(export): add cluster metric payload structures`
2. `feat(intent): add local operation queue model and reconcile`
3. `feat(intent-ui): add queue button and modal actions`
4. `feat(intent-actions): add episode/span/entity/cluster op creators`
5. `feat(cluster-ui): add cluster index and detail synced filtering`
6. `feat(cluster-insights): add drop-impact, relation graph, next steps`
7. `feat(cluster-export): add scope export and URL persistence`
8. `docs: update architecture, README, and UX acceptance guide`
