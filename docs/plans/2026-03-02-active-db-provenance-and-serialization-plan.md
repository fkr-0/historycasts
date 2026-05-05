# Active DB Provenance + Serialization Plan

## Goal
Track `historycasts/active.db` as a Git-friendly filesystem mirror in a dedicated remote repository, while protecting handcrafted metadata from deterministic rebuilds and merging existing handcrafted metadata from `res/res.json`.

## 6feeds Patch Review -> Transfer Decisions

1. Provenance columns on derived tables (`run_id`, `origin`, `locked`): **Transfer**
   - Reason: preserves nondeterministic/manual records across rebuilds.
2. `runs` table for run-level provenance: **Transfer**
   - Reason: supports replay/audit and deterministic vs handcrafted lineage.
3. Preference views (`v_best_time_span`, `v_best_place`, entity/keyword/cluster preference): **Transfer**
   - Reason: stable read path preferring locked+nondet rows over det rows.
4. Immutable `episodes_raw` split: **Defer**
   - Reason: larger migration surface; not required to safely merge/retain handcrafted metadata now.
5. Deterministic cleanup guards (future-year span cleanup): **Defer**
   - Reason: orthogonal to current merge/protection objective.
6. Heuristic review run insertion: **Defer**
   - Reason: useful extension, but needs product-level acceptance criteria before enabling by default.

## Implemented in Mainline

1. Added provenance migration utility (`src/podcast_atlas/provenance.py`) to:
   - create `runs`,
   - add provenance columns to existing DBs in-place,
   - bootstrap legacy rows to deterministic run ids,
   - create preference/UI views.
2. Updated aggregate schema bootstrap to include provenance and run migration by default.
3. Updated aggregate deterministic builder to create a deterministic run and write derived rows with provenance.
4. Updated dataset export to use UI/preference views when present.
5. Added handcrafted metadata importer (`src/podcast_atlas/metadata_merge.py`) and CLI command:
   - `podcast-atlas merge-handcrafted --db active.db --res-json res/res.json`
   - writes imported records as `origin='nondet'`, `locked=1`.
6. Added script wrapper `scripts/merge_res_metadata.py`.
7. Added tests for provenance migration/preference and handcrafted metadata merge.

## db_seri_al_ize Integration Plan (Remote FS Repo)

### Architecture
1. Keep `historycasts` as source app repo.
2. Create separate repo (example: `historycasts-dbfs.git`) that stores only the serialized DB filesystem.
3. Use `db_seri_al_ize` as canonical bridge:
   - app DB (`active.db`) <-> FS tree (`historycasts-dbfs`).

### One-Time Setup
1. Create working dir for DB FS repo:
   - `mkdir -p ../historycasts-dbfs && cd ../historycasts-dbfs && git init`
2. Initialize DSALI repo from current DB:
   - `dsali init --fs . --db ../historycasts/active.db`
3. Add remote and push:
   - `git remote add origin <remote-url>`
   - `git push -u origin HEAD`

### Daily Write Workflow (authoritative DB in `historycasts/active.db`)
1. Apply deterministic/manual updates in app repo DB.
2. Export DB -> FS repo:
   - `db-seri-al-ize export --db ../historycasts/active.db --out ../historycasts-dbfs --conf ../historycasts-dbfs/sericonf.yml`
3. Validate and commit FS repo:
   - `dsali validate --fs ../historycasts-dbfs --conf ../historycasts-dbfs/sericonf.yml`
   - `cd ../historycasts-dbfs && git add -A && git commit -m "db snapshot: <summary>" && git push`

### Daily Read/Sync Workflow (restore DB from FS repo)
1. Pull FS repo:
   - `cd ../historycasts-dbfs && git pull --ff-only`
2. Import FS -> app DB:
   - `db-seri-al-ize import --fs ../historycasts-dbfs --out ../historycasts/active.db --conf ../historycasts-dbfs/sericonf.yml`
3. Verify app export path:
   - `cd ../historycasts && uv run podcast-atlas export-static --db active.db --out static_site/dataset.json`

### Safety Rules
1. Treat FS repo as immutable history of DB commits.
2. Keep handcrafted imports as `origin='nondet', locked=1`; deterministic rebuilds must only target `origin='det'` rows.
3. Run `dsali validate` before every DBFS commit.

