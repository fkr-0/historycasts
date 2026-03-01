# Podcast Explorer (static pages)

This repo builds a single SQLite database from multiple RSS XML feeds, extracts historical time spans, places (offline gazetteer), entities, keywords, computes time-place clusters, and exports **one** `dataset.json` for a fully static React app.

## What you get

- `podcast_latest_4feeds.db` – SQLite DB containing **4 podcasts**.
- `frontend/public/dataset.json` – pre-exported dataset for the static app.
- `frontend/` – Vite + React + Plotly explorer (no backend needed).

## Build / update DB

```bash
python -m pip install -e '.[dev]'
pytest

podcast-db \
  --db podcast_latest_4feeds.db \
  --gazetteer gazetteer_curated.csv \
  --rss /path/to/mp3.rss \
  --rss /path/to/feed \
  --rss /path/to/esh.xml \
  --rss /path/to/rest-gesch.xml \
  --limit 0
```

## Export JSON for static pages

```bash
podcast-export --db podcast_latest_4feeds.db --out frontend/public/dataset.json
```

## Run UI

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

### Features

- **Time scrubber** (year slider) + **play/pause** animation.
- **Cluster coloring** on both timeline and map.
- Tooltip cards on hover, click to open episode detail.
- URL query parameters persist filters for shareable links.

## Extend the gazetteer

`gazetteer_curated.csv` columns:

- `name, kind, lat, lon, radius_km, aliases`
- aliases separated by `|`

Add more places to increase geocoding + clustering coverage.
