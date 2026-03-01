# Archive Audit (2026-02-27)

This file records `.tgz` bundles found at project root, analyzed for overlap, and moved to `legacy/archives/`.

## Decision rule
- Keep active source of truth in `src/`, `scripts/`, `tests/`, `schemas/`, `data/`, and `dbs/`.
- Treat tarballs as historical snapshots unless they contain uniquely needed code not present in active tree.
- Defer webapp harmonization (`web/` and `podcast_explorer_static/frontend/`) for a separate pass.

## Archive inventory

| file | sha256 | classification | disposition |
|---|---|---|---|
| `podcast-atlas(1).tgz` | `52c55aea658962e26c1579a5f917ec28a3a14d4b9afefc6f179e630b85af75a3` | Python package snapshot (`src/podcast_atlas`, tests) | moved to legacy |
| `podcast-atlas-combined(1).tgz` | `a50667fdabf00e1be856fb7581e106fbd012407cfed7d3baec1b1242d86b0ddf` | Python snapshot with `__pycache__` | moved to legacy |
| `podcast-atlas-combined.tgz` | `a50667fdabf00e1be856fb7581e106fbd012407cfed7d3baec1b1242d86b0ddf` | exact duplicate of `podcast-atlas-combined(1).tgz` | moved to legacy |
| `podcast-atlas.tgz` | `61a6bfde747eb514740a58d320c9b4ada887a717e4d6892cfab9608c4a214601` | earlier Python snapshot with `__pycache__` | moved to legacy |
| `podcast_explorer_gazetteer_ui.tgz` | `290fcadf709862fcb0015b39031e74192429432925e06fe23a3752be8c250ecb` | full repo snapshot incl. `.git` | moved to legacy |
| `podcast_explorer_latest.tgz` | `89dc1eab0ef4c29ebc837dbef5552f2cf70ddabc59a71f192cfa8bd9d0986b87` | full project snapshot incl. `.git` | moved to legacy |
| `podcast_explorer_static_4feeds.tgz` | `701cdfe313a3ac221e9f461940cefc81e259b44b3abecd19902f93f6b2109bc4` | static explorer package snapshot | moved to legacy |
| `podcast_fuzzy_viz_refined.tgz` | `365f1d03dc19ac97f552489397fae8d0f28d3795209ea4510a946e56d1f4a227` | fuzzy-viz branch snapshot | moved to legacy |
| `podcast_fuzzy_viz_semantic.tgz` | `35fc3fbf899c928941563ac050ff407de347b2a2758916193af54ed6d794da06` | fuzzy-viz semantic snapshot | moved to legacy |
| `podcast_static_explorer_0.8.0.tgz` | `c4889ecde9940578599b8791b97b4247168e7ac1b2d0e26324c05b1fccc6155a` | old static export artifact | moved to legacy |
| `podcast_static_explorer_0.8.3.tgz` | `32e8a49634d82571995129f9d442570cf42e730d932c8b1b5ea855aefccfba26` | newer static export artifact | moved to legacy |

## Notes
- Harmonization target is now the unpacked active tree, not tarball snapshots.
- If needed, inspect archives via `tar -tzf legacy/archives/<name>.tgz`.
