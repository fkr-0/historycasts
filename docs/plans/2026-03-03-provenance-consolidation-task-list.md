# Provenance Consolidation Task List

## Status Summary (from prior 1-12 list)

1. Unify year policy: **Partially complete**
   - `build_db` now takes `year_max`, CLI exposes `--year-max`.
   - Cleanup + heuristic postprocess use this policy.
   - Remaining: centralize constant into a single shared policy module and remove ad-hoc year cutoffs.

2. CLI postprocess controls: **Complete**
   - Added `podcast-db --year-max` and `--disable-heuristic-review`.

3. Provenance on cluster summary tables: **Complete**
   - Added `run_id`, `origin`, `locked` to `cluster_keywords`, `cluster_entities`.
   - Builder writes deterministic provenance into both tables.

4. Stop destructive cluster reset: **Complete**
   - `_recompute_clusters` now deletes only `origin='det'` rows.
   - Nondet/locked curated cluster rows are preserved.

5. Deterministic prune helper workflow: **Partially complete**
   - Added generic `prune_origin_rows(...)` helper.
   - Remaining: integrate scoped deterministic pruning for rerun workflows per feed/episode without harming nondet links.

6. Schema versioning: **Complete (baseline)**
   - Added `PRAGMA user_version` management in schema bootstrap (`SCHEMA_VERSION=2`).
   - Remaining: explicit migration registry/functions for future incompatible changes.

7. Index coverage for provenance paths: **Complete**
   - Added indices for `episodes_raw`, provenance filters on derived tables, and cluster provenance querying.

8. Export preferred-only data sections: **Complete (additive)**
   - Added `spans_preferred`, `places_preferred`, `entities_preferred`.
   - Existing payload sections preserved for backward compatibility.

9. Regression tests for rerun safety/idempotence: **Partially complete**
   - Added idempotence test for heuristic overrides.
   - Added nondet cluster preservation test.
   - Remaining: full rerun test matrix (mixed det/nondet rows across multiple runs).

10. End-to-end migration + rebuild + export test: **Not complete**
   - Remaining: add integration test that starts from legacy schema and verifies full lifecycle.

11. Consolidate ingest vs aggregate pipeline: **Not complete**
   - Remaining: architecture and implementation work to reduce dual-write model divergence.

12. Operator runbook docs: **Partially complete**
   - Added/updated planning docs for provenance + DB serialization.
   - Remaining: one concise production runbook with command recipes and failure handling.

## Detailed Next Steps

### Phase A: Safety + Migration Hardening
1. Add `src/podcast_atlas/policy.py` with canonical constants:
   - `DEFAULT_YEAR_MAX`, accepted place kinds, and review flags.
2. Refactor extraction and postprocess modules to import policy constants (remove duplicated literals).
3. Introduce migration registry:
   - `migrate_v1_to_v2`, etc., keyed by `PRAGMA user_version`.
4. Add migration smoke tests for each version jump.

### Phase B: Deterministic Rerun Correctness
1. Define rerun semantics per table:
   - what can be replaced,
   - what must be preserved,
   - how to keep FK integrity with nondet rows.
2. Implement episode-scoped deterministic prune utility:
   - only delete det rows linked to the episode/run being recomputed.
3. Add feed-scoped rerun mode in aggregate builder:
   - deterministic replacement for target feed episodes only.
4. Add tests for:
   - det rerun does not delete nondet/locked rows,
   - det rerun updates derived det rows for changed descriptions.

### Phase C: Export/Data Contract Consolidation
1. Decide canonical contract:
   - keep both raw + preferred arrays,
   - or shift UI/API to preferred-only by default.
2. Add schema docs for new payload keys:
   - `spans_preferred`, `places_preferred`, `entities_preferred`.
3. Add a strict schema test for payload shape to prevent regressions.

### Phase D: Pipeline Unification (Ingest vs Aggregate)
1. Architecture decision record:
   - select one canonical write path (`aggregate` or `ingest`) for all DB mutations.
2. Create adapter layer for legacy commands to canonical path.
3. Remove/retire duplicated extraction logic after parity verification.
4. Add cross-pipeline parity tests on fixtures before deletion of old path.

### Phase E: Operations + Tooling
1. Create `docs/runbooks/db-operations.md`:
   - migrate DB,
   - merge handcrafted metadata,
   - deterministic rebuild,
   - static export/build,
   - dsali sync/export/import commands.
2. Add CI job for targeted provenance tests + static export smoke build.
3. Add maintenance command:
   - `podcast-atlas db-health --db ...` reporting run counts, future-span violations, orphan FKs, and view consistency.

