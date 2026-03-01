# GitHub Pages Publish And Git Reset Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish Historycasts to GitHub Pages using CI-built artifacts (dataset extracted from committed `active.db`) and reinitialize git with a safe ignore policy.

**Architecture:** Keep `active.db` as the source artifact in the repository for the first release phase. In CI, run `podcast-atlas build-static` to derive `static_site/dataset.json` and frontend assets, then package/deploy via the existing Pages artifact flow. Keep branch protections simple at first: one workflow for quality + build + deploy, optional tag release bundle.

**Tech Stack:** GitHub Actions, GitHub Pages, Python (`uv`), Node (`pnpm`), Vite, SQLite, `podcast-atlas` CLI.

### Task 1: Reinitialize Git Safely

**Files:**
- Modify: `.gitignore`
- Create (manual command output): new `.git/` directory
- Reference backup location: `../historycasts.git-backup-<timestamp>`

**Step 1: Verify old repo backup exists**

Run: `ls -ld ../historycasts.git-backup-*`
Expected: at least one backup directory exists with full `.git` contents.

**Step 2: Initialize fresh git repo**

Run: `git init -b main`
Expected: new `.git` directory and `main` branch.

**Step 3: Apply sane ignore policy**

Ensure `.gitignore` ignores transient DB files (`*.db-wal`, `*.db-shm`, `*.db-journal`) but keeps `active.db` tracked.

**Step 4: Validate tracked file set before first commit**

Run:
- `git add -A`
- `git status --short`
Expected: no `node_modules/`, no `frontend/dist/`, no transient sqlite files.

**Step 5: Commit baseline**

Run:
- `git commit -m "chore: reinitialize repository with sane gitignore"`

### Task 2: Align GitHub Pages Workflow (Reference: niebelungen deploy style)

**Files:**
- Modify: `.github/workflows/ci-pages.yml`

**Step 1: Keep trigger/concurrency/deploy split simple**

Target:
- `on.push.branches: [main]`
- keep `workflow_dispatch`
- keep `concurrency` for pages deployment (single in-flight deployment).

**Step 2: Keep quality gate before deployment**

Retain `quality` job and make `build-pages` depend on it (`needs: quality`).

**Step 3: Build from committed DB instead of sample DB**

Change build step from:
- `uv run podcast-atlas build-sample --db active.db`
to:
- fail-fast check: `test -f active.db`
- build using committed DB:
  - `uv run podcast-atlas build-static --db active.db --dataset-out static_site/dataset.json --web-dir frontend`

**Step 4: Keep base-path compatibility for Pages**

If frontend uses root-relative fetches, pass base path env during build (pattern from niebelungen):
- `VITE_BASE_PATH=/${{ github.event.repository.name }}/`

Only add this if app routing/assets need a non-root base.

**Step 5: Keep artifact upload + deploy-pages**

Retain:
- `actions/upload-pages-artifact@v3`
- `actions/deploy-pages@v4`

### Task 3: Document First-Phase Publishing Model

**Files:**
- Modify: `README.md`
- Modify: `DATASETS.md` (if present)

**Step 1: Add explicit model statement**

Document:
- `active.db` is committed for now.
- CI derives `static_site/dataset.json` and pages bundle from that DB.

**Step 2: Add release growth path**

Document future migration:
- move DB out of repo if size/velocity grows,
- publish DB via release asset or object storage,
- keep CI extraction source configurable.

### Task 4: Validate Pages Build Locally

**Files:**
- No new files required

**Step 1: Rebuild static bundle locally**

Run:
- `uv sync --group dev`
- `pnpm --dir frontend install --no-frozen-lockfile`
- `uv run podcast-atlas build-static --db active.db --dataset-out static_site/dataset.json --web-dir frontend`

Expected: `frontend/dist` and `static_site/dataset.json` generated.

**Step 2: Build pages bundle**

Run:
- `uv run python scripts/build_pages_bundle.py --db active.db --dataset static_site/dataset.json --web-dist frontend/dist --static-site static_site --out pages --repo local/historycasts --sha local`

Expected: `pages/app`, `pages/data/dataset.json`, `pages/reports/build-report.html`.

### Task 5: CI Verification and Cutover

**Files:**
- Modify: `.github/workflows/ci-pages.yml` (final tweaks only)

**Step 1: Push to test branch and run workflow**

Expected:
- quality job passes,
- build-pages job deploys artifact successfully.

**Step 2: Verify deployed endpoints**

Check:
- `/app/`
- `/data/dataset.json`
- `/reports/build-report.html`

**Step 3: Optional tag release**

Push `v*` tag and verify release artifact generation if keeping `create-release` job.

