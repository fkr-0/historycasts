# Podcast Explorer Frontend

React + TypeScript frontend for exploring history podcast episodes with a D3 stacked-bar timeline.

## Stack

- React 18 + TypeScript
- Vite 5
- D3.js 7
- Tailwind CSS 4
- Biome (lint/format)
- Vitest + Testing Library

## Development

```bash
pnpm install
pnpm dev
```

## Quality Checks

```bash
pnpm lint
pnpm lint:fix
pnpm test
pnpm build
```

## Key Components

- `src/components/StackedBarTimeline.tsx`: D3 stacked timeline grouped by podcast.
- `src/components/ClusterPanel.tsx`: cluster filtering controls.
- `src/components/EpisodeDetail.tsx`: selected episode details.
- `src/App.integration.test.tsx`: integration coverage for filtering + timeline click selection.
