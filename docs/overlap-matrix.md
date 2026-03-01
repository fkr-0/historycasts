# Module Overlap Matrix

Comparison target: `src/podcast_explorer_static/*` vs canonical implementations under `src/podcast_atlas/*`.

| Legacy file | Overlap in `podcast_atlas` before refactor | Canonical target now |
|---|---|---|
| `__init__.py` | Package description only | compatibility package kept |
| `cli.py` | Partial (`podcast_atlas.cli` has broader CLI, not same command shape) | `podcast_atlas.aggregate.cli` (compat shim forwards) |
| `cluster.py` | Missing equivalent | `podcast_atlas.aggregate.cluster` |
| `db_build.py` | Partial (`podcast_atlas.ingest` covers ingest but schema/data model differ) | `podcast_atlas.aggregate.db_build` |
| `export_static.py` | Strong overlap (`podcast_atlas.static_export`) | `podcast_atlas.export.dataset` |
| `extract.py` | Partial overlap (`podcast_atlas.extract` provides different extraction model) | `podcast_atlas.aggregate.extract` |
| `gazetteer.py` | Partial overlap (`podcast_atlas.gazetteer` has different model fields/CSV format) | `podcast_atlas.aggregate.gazetteer` |
| `rss_parse.py` | Partial overlap (`podcast_atlas.rss` parses RSS differently) | `podcast_atlas.aggregate.rss_parse` |
| `schema.py` | Partial overlap (`podcast_atlas.db` has different schema) | `podcast_atlas.aggregate.schema` |

## Conclusion

The two module trees were **not strictly function-identical**. Some features overlapped, but data model/schema and extraction behavior diverged.

This refactor sets one canonical direction:

- `podcast_atlas.aggregate` and `podcast_atlas.export` are authoritative.
- Legacy `podcast_explorer_static` modules have been removed after importer migration.
