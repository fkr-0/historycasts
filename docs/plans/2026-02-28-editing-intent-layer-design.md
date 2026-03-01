# Editing Intent Layer Design

Date: 2026-02-28
Status: Draft for implementation

## 1. Goal
Provide a safe, local-first editing layer for curated podcast data where users express intent as queued operations in browser storage, inspect/export them, and verify whether they are already applied in the live dataset.

This is intentionally not direct live DB mutation from the browser.

## 2. Problem and Constraints
- The current app is static/dataset-driven and optimized for exploration.
- Curation edits need accountability and reversibility.
- We need CRUD-like UX without requiring immediate backend write access.
- Operations must survive refresh and be portable (file export / clipboard).
- UI must clearly distinguish:
  - no operations
  - queued/unapplied operations
  - operations already applied in dataset (reconciled)

## 3. Scope
### In scope
- Local operation queue in `localStorage`.
- Modal for review, cleanup, cancel, export, copy.
- Reconciliation check against currently loaded dataset.
- SQL-script export and JSON export.
- UI entry points to generate operations from common edit actions.

### Out of scope (phase 1)
- Automatic backend apply endpoint.
- Multi-user conflict resolution.
- Real-time collaborative editing.

## 4. Core Architecture
## 4.1 Operation model (canonical)
Store operations as JSON records:
- `op_id`: UUID
- `created_at`
- `actor`: optional local user label
- `entity_type`: `episode | span | place | entity | cluster | keyword | relation`
- `entity_id`: stable id from dataset
- `op_type`: `insert | update | delete | link | unlink`
- `payload`: field-level patch or inserted row values
- `preconditions`: expected old values/hash/version
- `status`: `queued | applied | invalid | cancelled`
- `status_reason`
- `sql_preview`: deterministic SQL text generated client-side or by utility

### Why not SQL-only storage
Custom JSON is required for robust reconciliation and UX filtering. SQL export is derived output.

## 4.2 Local storage keys
- `historycasts.intentQueue.v1` -> array of operations
- `historycasts.intentMeta.v1` -> queue metadata (schema version, last reconcile timestamp, app version)

## 4.3 Reconciliation algorithm
Manual/automatic refresh checks each non-cancelled operation:
1. Locate target row in dataset by `entity_type + entity_id`.
2. Evaluate op semantics:
   - `update`: all target fields already equal desired values -> `applied`.
   - `delete`: target row absent -> `applied`.
   - `insert`: target identifier exists with expected values -> `applied`.
   - mismatch + target missing/shape mismatch -> `invalid`.
3. Recompute and persist `status` + `status_reason`.

## 5. Backend and Export Implications (sqlite -> dataset)
To make reconciliation trustworthy, exported dataset must include stable identity and optional row integrity hints.

Required additions in export payload:
- `meta.dataset_revision` (build timestamp + source DB checksum).
- For editable entities, guarantee stable `id` and include `updated_at` if available.
- Optional `row_fingerprint` per record (hash over canonical fields used for reconciliation).

Python changes:
- Update export models in `src/podcast_atlas/models.py` (optional fingerprint/version fields).
- Update export assembly in `src/podcast_atlas/static_export.py`.
- Add optional utility script to transform queue JSON -> SQL script (`scripts/queue_to_sql.py`).

## 6. Frontend UX Design
## 6.1 Top-right intent button
Label format:
- No ops: `Changes (0)` neutral surface color.
- Unapplied queued > 0: `Changes (N)` warning/accent color.
- Queued 0 and applied>0 remains in queue: success/green color.

Tooltip/subtext:
- `N queued, M applied, K invalid`.

## 6.2 Operations modal sections
- Summary strip: queued/applied/invalid/cancelled counts.
- Action bar:
  - `Refresh status`
  - `Cleanup (remove applied+invalid)`
  - `Cancel selected`
  - `Export SQL`
  - `Export JSON`
  - `Copy to clipboard`
- Operation list table:
  - columns: status, entity, type, created_at, brief diff, reason
  - row expand: full payload + SQL preview
  - bulk select + remove/cancel

## 6.3 UX enforcement rules
- Every operation creation action must show immediate toast + count update.
- No hidden auto-deletions from queue.
- Cancel is reversible until cleanup.
- Cleanup confirmation dialog must show exact remove counts.

## 7. Operation Creation Entry Points (must be implemented)
Minimum set to make feature useful:
1. Episode detail edits:
   - title/narrator/kind correction
   - description annotation notes
2. Span curation:
   - adjust start/end year
   - confidence override
   - mark invalid span
3. Entity curation:
   - rename/merge entity label
   - kind correction
4. Cluster curation:
   - relabel cluster
   - include/exclude episode from cluster (as intent op)

Each action creates queue ops, never direct dataset mutation.

## 8. Export Formats
## 8.1 JSON export (lossless)
- Full queue with metadata.

## 8.2 SQL export (portable)
- Deterministic transaction-wrapped script:
  - `BEGIN;`
  - precondition checks as comments/assert-like guards
  - SQL statements in creation order
  - `COMMIT;`

## 9. Completion Criteria
Feature is complete only if all are true:
1. Queue persists across reload.
2. Button state reflects queue status rules exactly.
3. Reconciliation updates statuses correctly after dataset refresh.
4. Cleanup removes only `applied|invalid` (and optionally `cancelled`) with confirmation.
5. User can remove/cancel queued operations individually and in bulk.
6. Export JSON and SQL both work; clipboard copy works.
7. At least 4 UI edit entry points create valid ops.
8. Unit tests cover queue reducer + reconcile logic.
9. Integration test covers: create op -> refresh -> status update -> cleanup.

## 10. Guarantee Matrix
- If export includes stable IDs + dataset revision and reconcile logic passes tests, then status colors/messages are truthful.
- If each UI mutation path only emits queue ops, then no silent data mutation can occur client-side.
- If SQL export is generated from canonical op JSON and covered by snapshot tests, then exported script faithfully represents intent queue.

## 11. Suggested Implementation Phases
1. Data model + localStorage store + reducer.
2. Modal + summary button + cleanup/cancel/export actions.
3. Reconciliation engine + manual refresh.
4. First 4 operation creation entry points.
5. SQL compiler + optional backend utility.
6. Tests + polish.
