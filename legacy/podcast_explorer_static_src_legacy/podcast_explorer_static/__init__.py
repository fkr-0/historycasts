"""Static-capable podcast explorer.

- Builds/upgrades a SQLite DB from one or more RSS feeds (local XML files).
- Extracts fuzzy historical time spans, places (offline gazetteer), entities, keywords.
- Computes 3D clusters (midYear, lat, lon) per podcast.
- Exports a single dataset.json that a static React app can load.
"""
