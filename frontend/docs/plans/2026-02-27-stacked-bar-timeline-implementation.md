# Stacked Bar Timeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the existing Plotly timeline scatter plot with a D3.js stacked bar chart visualization where podcasts group on Y-axis, historical time spans on X-axis, with flexible grouping architecture for future extensions.

**Architecture:** Create new `StackedBarTimeline.tsx` component using D3.js v7 for SVG rendering. Data flows from App → component → transform to D3 format → render with enter/update/exit pattern. Existing Timeline.tsx is preserved but commented out. Biome provides linting/formatting, Tailwind CSS enables progressive style migration.

**Tech Stack:** React 18, TypeScript 5, Vite 5, D3.js 7, Biome, Tailwind CSS 4, Vitest

---

## Task 1: Add Biome Dependency and Configuration

**Files:**
- Create: `biome.json`
- Modify: `package.json`
- Create: `.vscode/settings.json` (optional, for IDE integration)

**Step 1: Add Biome dependency**

Run: `pnpm add -D @biomejs/biome`

**Step 2: Create biome.json with recommended rules**

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.0/schema.json",
  "vcs": {
    "enabled": true,
    "clientKind": "git",
    "useIgnoreFile": true
  },
  "files": {
    "ignoreUnknown": false,
    "ignore": ["node_modules", "dist", "build"]
  },
  "formatter": {
    "enabled": true,
    "formatWithErrors": false,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineEnding": "lf",
    "lineWidth": 100
  },
  "organizeImports": {
    "enabled": true
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "correctness": {
        "noUnusedVariables": "error"
      },
      "style": {
        "noNonNullAssertion": "warn"
      },
      "suspicious": {
        "noExplicitAny": "warn"
      }
    }
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "double",
      "jsxQuoteStyle": "double",
      "trailingCommas": "es5",
      "semicolons": "always"
    }
  }
}
```

**Step 3: Add npm scripts to package.json**

Add to `"scripts"` section:
```json
"lint": "biome check .",
"lint:fix": "biome check --write .",
"format": "biome format --write .",
"check": "biome check --write ."
```

**Step 4: Run Biome to check current codebase**

Run: `pnpm lint`

Expected: Some linting errors reported (this is expected, we'll fix progressively)

**Step 5: Commit**

```bash
git add biome.json package.json pnpm-lock.yaml
git commit -m "feat: add Biome for linting and formatting

- Add @biomejs/biome dev dependency
- Configure with recommended rules
- Add lint, format, and check scripts"
```

---

## Task 2: Add Tailwind CSS and Configuration

**Files:**
- Create: `tailwind.config.js`
- Create: `postcss.config.js`
- Modify: `src/index.css`
- Modify: `src/main.tsx`
- Modify: `package.json`

**Step 1: Add Tailwind CSS dependencies**

Run: `pnpm add -D tailwindcss postcss autoprefixer`

**Step 2: Initialize Tailwind config**

Run: `pnpm exec tailwindcss init -p`

Expected: Creates `tailwind.config.js` and `postcss.config.js`

**Step 3: Configure tailwind.config.js**

Replace contents with:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**Step 4: Verify postcss.config.js exists**

Ensure it contains:
```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

**Step 5: Add Tailwind directives to index.css**

Create `src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 6: Import index.css in main.tsx**

After the existing imports, add:
```typescript
import "./index.css";
```

**Step 7: Update tsconfig.json for CSS imports**

Modify `tsconfig.json` to ensure CSS imports are allowed. Add to `compilerOptions` if not present:
```json
"allowImportingTsExtensions": false
```

**Step 8: Verify build works**

Run: `pnpm build`

Expected: Build succeeds without errors

**Step 9: Commit**

```bash
git add tailwind.config.js postcss.config.js src/index.css src/main.tsx package.json pnpm-lock.yaml
git commit -m "feat: add Tailwind CSS for styling

- Add tailwindcss, postcss, autoprefixer
- Configure content paths
- Add Tailwind directives to index.css
- Import in main.tsx"
```

---

## Task 3: Add D3.js Dependency

**Files:**
- Modify: `package.json`

**Step 1: Add D3.js dependency**

Run: `pnpm add d3@7`

Also add types:
Run: `pnpm add -D @types/d3@7`

**Step 2: Verify installation**

Run: `pnpm list d3 @types/d3`

Expected: Shows d3 and @types/d3 versions

**Step 3: Commit**

```bash
git add package.json pnpm-lock.yaml
git commit -m "feat: add D3.js v7 for data visualization

- Add d3 and @types/d3 dependencies
- Will be used for stacked bar timeline component"
```

---

## Task 4: Create Data Transformation Utilities

**Files:**
- Create: `src/utils/timelineTransform.ts`

**Step 1: Write the failing test**

Create `src/utils/timelineTransform.test.ts`:
```typescript
import { describe, it, expect } from "vitest";
import { transformToStackData, type D3StackData } from "./timelineTransform";
import type { Dataset } from "../types";

describe("transformToStackData", () => {
  it("groups episodes by podcast correctly", () => {
    const mockDataset: Dataset = {
      meta: { schema_version: "1.0", generated_at_iso: "2024-01-01", source_db: "test" },
      podcasts: [
        { id: 1, title: "Podcast A" },
        { id: 2, title: "Podcast B" },
      ],
      episodes: [
        { id: 1, podcast_id: 1, title: "Ep 1", pub_date_iso: "2024-01-01" },
        { id: 2, podcast_id: 1, title: "Ep 2", pub_date_iso: "2024-01-02" },
        { id: 3, podcast_id: 2, title: "Ep 3", pub_date_iso: "2024-01-03" },
      ],
      spans: [
        {
          id: 1,
          episode_id: 1,
          start_iso: "1700-01-01",
          end_iso: "1750-01-01",
          precision: "year",
          qualifier: "approx",
          score: 0.9,
          source_section: "intro",
          source_text: "In 1700...",
        },
        {
          id: 2,
          episode_id: 2,
          start_iso: "1800-01-01",
          end_iso: "1850-01-01",
          precision: "year",
          qualifier: "approx",
          score: 0.8,
          source_section: "chapter 1",
          source_text: "By 1800...",
        },
      ],
      places: [],
      entities: [],
      episode_keywords: {},
      episode_clusters: {},
      clusters: [],
    };

    const result = transformToStackData(mockDataset, [1, 2, 3]);

    expect(result).toHaveLength(2);
    expect(result[0].podcastId).toBe(1);
    expect(result[0].podcastTitle).toBe("Podcast A");
    expect(result[0].episodes).toHaveLength(2);
    expect(result[0].episodes[0].spans).toHaveLength(1);
    expect(result[0].episodes[0].spans[0].start).toEqual(new Date("1700-01-01"));
  });

  it("handles episodes with multiple spans", () => {
    const mockDataset: Dataset = {
      meta: { schema_version: "1.0", generated_at_iso: "2024-01-01", source_db: "test" },
      podcasts: [{ id: 1, title: "Podcast A" }],
      episodes: [{ id: 1, podcast_id: 1, title: "Ep 1", pub_date_iso: "2024-01-01" }],
      spans: [
        {
          id: 1,
          episode_id: 1,
          start_iso: "1700-01-01",
          end_iso: "1750-01-01",
          precision: "year",
          qualifier: "approx",
          score: 0.9,
          source_section: "intro",
          source_text: "In 1700...",
        },
        {
          id: 2,
          episode_id: 1,
          start_iso: "1800-01-01",
          end_iso: "1850-01-01",
          precision: "year",
          qualifier: "approx",
          score: 0.8,
          source_section: "chapter 1",
          source_text: "By 1800...",
        },
      ],
      places: [],
      entities: [],
      episode_keywords: {},
      episode_clusters: {},
      clusters: [],
    };

    const result = transformToStackData(mockDataset, [1]);

    expect(result[0].episodes[0].spans).toHaveLength(2);
  });

  it("handles empty episodes list", () => {
    const mockDataset: Dataset = {
      meta: { schema_version: "1.0", generated_at_iso: "2024-01-01", source_db: "test" },
      podcasts: [{ id: 1, title: "Podcast A" }],
      episodes: [],
      spans: [],
      places: [],
      entities: [],
      episode_keywords: {},
      episode_clusters: {},
      clusters: [],
    };

    const result = transformToStackData(mockDataset, []);

    expect(result).toEqual([]);
  });

  it("filters out invalid date ranges", () => {
    const mockDataset: Dataset = {
      meta: { schema_version: "1.0", generated_at_iso: "2024-01-01", source_db: "test" },
      podcasts: [{ id: 1, title: "Podcast A" }],
      episodes: [{ id: 1, podcast_id: 1, title: "Ep 1", pub_date_iso: "2024-01-01" }],
      spans: [
        {
          id: 1,
          episode_id: 1,
          start_iso: "invalid-date",
          end_iso: "1750-01-01",
          precision: "year",
          qualifier: "approx",
          score: 0.9,
          source_section: "intro",
          source_text: "In 1700...",
        },
        {
          id: 2,
          episode_id: 1,
          start_iso: "1800-01-01",
          end_iso: "1850-01-01",
          precision: "year",
          qualifier: "approx",
          score: 0.8,
          source_section: "chapter 1",
          source_text: "By 1800...",
        },
      ],
      places: [],
      entities: [],
      episode_keywords: {},
      episode_clusters: {},
      clusters: [],
    };

    const result = transformToStackData(mockDataset, [1]);

    // Only valid span should be included
    expect(result[0].episodes[0].spans).toHaveLength(1);
    expect(result[0].episodes[0].spans[0].start).toEqual(new Date("1800-01-01"));
  });
});
```

**Step 2: Run test to verify it fails**

Run: `pnpm test src/utils/timelineTransform.test.ts`

Expected: FAIL with "Cannot find module './timelineTransform'" or similar

**Step 3: Create the implementation**

Create `src/utils/timelineTransform.ts`:
```typescript
import type { Dataset } from "../types";

export interface D3StackData {
  podcastId: number;
  podcastTitle: string;
  episodes: Array<{
    episodeId: number;
    title: string;
    pubDate: string;
    spans: Array<{
      spanId: number;
      start: Date;
      end: Date;
      score: number;
      sourceText: string;
      clusterId?: number;
    }>;
  }>;
}

export function transformToStackData(
  dataset: Dataset,
  episodeIds: number[]
): D3StackData[] {
  // Build a map of episode_id -> spans
  const spansByEpisode = new Map<number, Dataset["spans"]>();
  for (const span of dataset.spans) {
    const arr = spansByEpisode.get(span.episode_id) ?? [];
    arr.push(span);
    spansByEpisode.set(span.episode_id, arr);
  }

  // Build a map of podcast_id -> episodes
  const episodesByPodcast = new Map<number, Dataset["episodes"]>();
  for (const ep of dataset.episodes) {
    if (!episodeIds.includes(ep.id)) continue;
    const arr = episodesByPodcast.get(ep.podcast_id) ?? [];
    arr.push(ep);
    episodesByPodcast.set(ep.podcast_id, arr);
  }

  // Transform to D3 format
  const result: D3StackData[] = [];

  for (const [podcastId, episodes] of episodesByPodcast) {
    const podcast = dataset.podcasts.find((p) => p.id === podcastId);
    if (!podcast) continue;

    const transformedEpisodes = episodes.map((ep) => {
      const spans = (spansByEpisode.get(ep.id) ?? [])
        .map((sp) => {
          const start = sp.start_iso ? new Date(sp.start_iso) : null;
          const end = sp.end_iso ? new Date(sp.end_iso) : null;

          // Filter out invalid dates
          if (!start || !end || Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
            return null;
          }

          return {
            spanId: sp.id,
            start,
            end,
            score: sp.score,
            sourceText: sp.source_text,
            clusterId: dataset.episode_clusters[String(ep.id)],
          };
        })
        .filter((s): s is NonNullable<typeof s> => s !== null);

      return {
        episodeId: ep.id,
        title: ep.title,
        pubDate: ep.pub_date_iso,
        spans,
      };
    });

    // Sort episodes by publication date
    transformedEpisodes.sort((a, b) => new Date(a.pubDate).getTime() - new Date(b.pubDate).getTime());

    result.push({
      podcastId,
      podcastTitle: podcast.title,
      episodes: transformedEpisodes,
    });
  }

  // Sort podcasts by title
  result.sort((a, b) => a.podcastTitle.localeCompare(b.podcastTitle));

  return result;
}
```

**Step 4: Run tests to verify they pass**

Run: `pnpm test src/utils/timelineTransform.test.ts`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/utils/timelineTransform.ts src/utils/timelineTransform.test.ts
git commit -m "feat: add data transformation utilities for stacked timeline

- Add transformToStackData function
- Groups episodes by podcast with their spans
- Handles multiple spans per episode
- Filters invalid date ranges
- Add comprehensive unit tests"
```

---

## Task 5: Create D3 Scale Utilities

**Files:**
- Create: `src/utils/timelineScales.ts`

**Step 1: Write the failing test**

Create `src/utils/timelineScales.test.ts`:
```typescript
import { describe, it, expect } from "vitest";
import { createTimeScale, createPodcastScale, type D3StackData } from "./timelineScales";
import { scaleTime, scaleBand } from "d3";

describe("createTimeScale", () => {
  it("creates time scale with correct domain", () => {
    const mockData: D3StackData[] = [
      {
        podcastId: 1,
        podcastTitle: "Podcast A",
        episodes: [
          {
            episodeId: 1,
            title: "Ep 1",
            pubDate: "2024-01-01",
            spans: [
              { spanId: 1, start: new Date("1700-01-01"), end: new Date("1750-01-01"), score: 0.9, sourceText: "test" },
              { spanId: 2, start: new Date("1800-01-01"), end: new Date("1850-01-01"), score: 0.8, sourceText: "test" },
            ],
          },
        ],
      },
    ];

    const scale = createTimeScale(mockData, 500, 50);

    expect(scale(new Date("1700-01-01"))).toBeGreaterThanOrEqual(50);
    expect(scale(new Date("1850-01-01"))).toBeLessThanOrEqual(500);
  });

  it("handles empty data", () => {
    const scale = createTimeScale([], 500, 50);
    // Should return a valid scale even with empty data
    expect(scale).toBeDefined();
  });
});

describe("createPodcastScale", () => {
  it("creates band scale for podcasts", () => {
    const mockData: D3StackData[] = [
      { podcastId: 1, podcastTitle: "Podcast A", episodes: [] },
      { podcastId: 2, podcastTitle: "Podcast B", episodes: [] },
    ];

    const scale = createPodcastScale(mockData, 400, 40);

    expect(scale.domain()).toEqual(["Podcast A", "Podcast B"]);
    expect(scale.bandwidth()).toBeGreaterThan(0);
  });

  it("handles single podcast", () => {
    const mockData: D3StackData[] = [
      { podcastId: 1, podcastTitle: "Podcast A", episodes: [] },
    ];

    const scale = createPodcastScale(mockData, 400, 40);

    expect(scale.domain()).toEqual(["Podcast A"]);
    expect(scale.bandwidth()).toBeGreaterThan(0);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `pnpm test src/utils/timelineScales.test.ts`

Expected: FAIL with "Cannot find module './timelineScales'" or similar

**Step 3: Create the implementation**

Create `src/utils/timelineScales.ts`:
```typescript
import { scaleTime, scaleBand, type ScaleTime, type ScaleBand } from "d3";
import type { D3StackData } from "./timelineTransform";

export interface Scales {
  xScale: ScaleTime<number, number>;
  yScale: ScaleBand<string>;
}

export function createTimeScale(data: D3StackData[], width: number, margin: { left: number; right: number }): ScaleTime<number, number> {
  // Find min/max dates across all spans
  let minDate: Date | null = null;
  let maxDate: Date | null = null;

  for (const podcast of data) {
    for (const episode of podcast.episodes) {
      for (const span of episode.spans) {
        if (!minDate || span.start < minDate) minDate = span.start;
        if (!maxDate || span.end > maxDate) maxDate = span.end;
      }
    }
  }

  // Default range if no data
  if (!minDate || !maxDate) {
    const now = new Date();
    minDate = new Date(now.getFullYear() - 100, 0, 1);
    maxDate = now;
  }

  // Add padding to the range
  const yearPadding = (maxDate.getTime() - minDate.getTime()) * 0.05;

  return scaleTime()
    .domain([new Date(minDate.getTime() - yearPadding), new Date(maxDate.getTime() + yearPadding)])
    .range([margin.left, width - margin.right]);
}

export function createPodcastScale(data: D3StackData[], height: number, margin: { top: number; bottom: number }): ScaleBand<string> {
  const podcastNames = data.map((d) => d.podcastTitle);

  return scaleBand()
    .domain(podcastNames)
    .range([margin.top, height - margin.bottom])
    .padding(0.2);
}

export function createScales(
  data: D3StackData[],
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number }
): Scales {
  return {
    xScale: createTimeScale(data, width, { left: margin.left, right: margin.right }),
    yScale: createPodcastScale(data, height, { top: margin.top, bottom: margin.bottom }),
  };
}
```

**Step 4: Run tests to verify they pass**

Run: `pnpm test src/utils/timelineScales.test.ts`

Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/utils/timelineScales.ts src/utils/timelineScales.test.ts
git commit -m "feat: add D3 scale utilities for timeline

- Add createTimeScale for x-axis (historical time)
- Add createPodcastScale for y-axis (podcasts)
- Handle edge cases: empty data, single podcast
- Add comprehensive unit tests"
```

---

## Task 6: Create Base StackedBarTimeline Component

**Files:**
- Create: `src/components/StackedBarTimeline.tsx`

**Step 1: Create basic component structure**

Create `src/components/StackedBarTimeline.tsx`:
```typescript
import React, { useRef, useEffect, useMemo, useState } from "react";
import { select, selectAll, type Selection } from "d3";
import type { Dataset } from "../types";
import { transformToStackData, type D3StackData } from "../utils/timelineTransform";
import { createScales, type Scales } from "../utils/timelineScales";

type Ep = Dataset["episodes"][number];

interface StackedBarTimelineProps {
  dataset: Dataset;
  episodes: Ep[];
  selectedEpisodeId: number | null;
  onSelectEpisode: (id: number) => void;
  scrubYear?: number;
  onScrubYear: (y?: number) => void;
}

export default function StackedBarTimeline(props: StackedBarTimelineProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  const [dimensions, setDimensions] = useState({ width: 800, height: 400 });

  // Transform data
  const stackData = useMemo(() => {
    const episodeIds = props.episodes.map((e) => e.id);
    return transformToStackData(props.dataset, episodeIds);
  }, [props.dataset, props.episodes]);

  // Create scales
  const scales = useMemo(() => {
    const margin = { top: 20, right: 30, bottom: 40, left: 120 };
    return createScales(stackData, dimensions.width, dimensions.height, margin);
  }, [stackData, dimensions]);

  // Responsive sizing
  useEffect(() => {
    const container = svgRef.current?.parentElement;
    if (!container) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });

    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
  }, []);

  // Render D3 chart
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = select(svgRef.current);
    const margin = { top: 20, right: 30, bottom: 40, left: 120 };
    const innerWidth = dimensions.width - margin.left - margin.right;
    const innerHeight = dimensions.height - margin.top - margin.bottom;

    // Clear previous content
    svg.selectAll("*").remove();

    // Create main group
    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Add x-axis
    const xAxis = g.append("g")
      .attr("class", "x-axis")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(scales.xScale.axis ? scales.xScale.axis() : ((g: any) => g));

    // Add y-axis
    const yAxis = g.append("g")
      .attr("class", "y-axis")
      .call(scales.yScale.axis ? scales.yScale.axis() : ((g: any) => g));

  }, [scales, dimensions]);

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        style={{ display: "block" }}
      />
    </div>
  );
}
```

**Step 2: Create test file**

Create `src/components/StackedBarTimeline.test.tsx`:
```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import StackedBarTimeline from "./StackedBarTimeline";
import type { Dataset } from "../types";

describe("StackedBarTimeline", () => {
  it("renders svg element", () => {
    const mockDataset: Dataset = {
      meta: { schema_version: "1.0", generated_at_iso: "2024-01-01", source_db: "test" },
      podcasts: [{ id: 1, title: "Test Podcast" }],
      episodes: [{ id: 1, podcast_id: 1, title: "Ep 1", pub_date_iso: "2024-01-01" }],
      spans: [],
      places: [],
      entities: [],
      episode_keywords: {},
      episode_clusters: {},
      clusters: [],
    };

    render(
      <StackedBarTimeline
        dataset={mockDataset}
        episodes={[]}
        selectedEpisodeId={null}
        onSelectEpisode={vi.fn()}
        onScrubYear={vi.fn()}
      />
    );

    const svg = document.querySelector("svg");
    expect(svg).toBeTruthy();
  });
});
```

**Step 3: Install testing library dependencies**

Run: `pnpm add -D @testing-library/react @testing-library/jest-dom jsdom`

**Step 4: Configure Vitest for React testing**

Modify `vite.config.ts`:
```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
```

**Step 5: Create test setup file**

Create `src/test/setup.ts`:
```typescript
import "@testing-library/jest-dom";
```

**Step 6: Run test to verify it passes**

Run: `pnpm test src/components/StackedBarTimeline.test.tsx`

Expected: PASS

**Step 7: Commit**

```bash
git add src/components/StackedBarTimeline.tsx src/components/StackedBarTimeline.test.tsx vite.config.ts src/test/setup.ts package.json pnpm-lock.yaml
git commit -m "feat: create base StackedBarTimeline component

- Add SVG container with D3.js integration
- Add responsive sizing with ResizeObserver
- Add axes rendering
- Set up test infrastructure with Vitest + Testing Library
- Add basic rendering test"
```

---

## Task 7: Implement Episode Rects Rendering

**Files:**
- Modify: `src/components/StackedBarTimeline.tsx`

**Step 1: Update component to render episode spans**

Replace the rendering useEffect in `StackedBarTimeline.tsx` with:
```typescript
  // Render D3 chart
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = select(svgRef.current);
    const margin = { top: 20, right: 30, bottom: 40, left: 120 };
    const innerWidth = dimensions.width - margin.left - margin.right;
    const innerHeight = dimensions.height - margin.top - margin.bottom;

    // Clear previous content
    svg.selectAll("*").remove();

    // Create main group
    const g = svg
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Add x-axis
    const xAxis = g.append("g")
      .attr("class", "x-axis")
      .attr("transform", `translate(0,${innerHeight})`);

    xAxis.call((g: any) => {
      const axis = select(g);
      axis.call(select(window as any).scaleAxis?.bottom ?? ((s: any) => s));
    });

    // Add y-axis
    const yAxis = g.append("g")
      .attr("class", "y-axis");

    // Create podcast groups
    const podcastGroups = g.selectAll(".podcast-group")
      .data(stackData)
      .enter()
      .append("g")
      .attr("class", "podcast-group")
      .attr("transform", (d) => `translate(0,${scales.yScale(d.podcastTitle) ?? 0})`);

    // Add episode rects within each podcast group
    podcastGroups.each(function(podcastData) {
      const group = select(this);

      // Collect all spans from all episodes in this podcast
      const allSpans: Array<{
        episodeId: number;
        episodeTitle: string;
        span: D3StackData["episodes"][number]["spans"][number];
      }> = [];

      for (const episode of podcastData.episodes) {
        for (const span of episode.spans) {
          allSpans.push({ episodeId: episode.episodeId, episodeTitle: episode.title, span });
        }
      }

      // Sort spans by start time
      allSpans.sort((a, b) => a.span.start.getTime() - b.span.start.getTime());

      // Create unique color per episode
      const episodeColors = new Map<number, string>();
      let hue = 0;
      for (const episode of podcastData.episodes) {
        episodeColors.set(episode.episodeId, `hsl(${hue}, 65%, 45%)`);
        hue = (hue + 47) % 360;
      }

      // Render span rects
      group.selectAll(".span-rect")
        .data(allSpans)
        .enter()
        .append("rect")
        .attr("class", "span-rect")
        .attr("x", (d) => scales.xScale(d.span.start))
        .attr("width", (d) => scales.xScale(d.span.end) - scales.xScale(d.span.start))
        .attr("y", 0)
        .attr("height", scales.yScale.bandwidth())
        .attr("fill", (d) => episodeColors.get(d.episodeId) ?? "#888")
        .attr("stroke", "white")
        .attr("stroke-width", 1)
        .attr("rx", 2)
        .style("cursor", "pointer")
        .on("click", (event, d) => {
          props.onSelectEpisode(d.episodeId);
        });
    });

  }, [scales, dimensions, stackData, props]);
```

**Step 2: Run tests**

Run: `pnpm test`

Expected: All existing tests still pass

**Step 3: Commit**

```bash
git add src/components/StackedBarTimeline.tsx
git commit -m "feat: render episode span rects in timeline

- Add podcast groups
- Render spans as colored rects
- Add unique colors per episode
- Add click handlers for episode selection
- Spans sorted by start time"
```

---

## Task 8: Add Hover Card Interaction

**Files:**
- Modify: `src/components/StackedBarTimeline.tsx`

**Step 1: Add hover state and card rendering**

Add state and hover card to `StackedBarTimeline.tsx`:
```typescript
  const [hoverData, setHoverData] = useState<{
    x: number;
    y: number;
    episodeId: number;
    episodeTitle: string;
    spanStart: Date;
    spanEnd: Date;
    score: number;
    sourceText: string;
    clusterId?: number;
  } | null>(null);
```

Add hover card JSX before the closing div:
```typescript
  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <svg
        ref={svgRef}
        width={dimensions.width}
        height={dimensions.height}
        style={{ display: "block" }}
      />
      {hoverData && (
        <div
          style={{
            position: "fixed",
            left: hoverData.x + 14,
            top: hoverData.y + 14,
            maxWidth: 380,
            background: "white",
            border: "1px solid #ccc",
            borderRadius: 10,
            padding: 10,
            boxShadow: "0 10px 30px rgba(0,0,0,0.15)",
            zIndex: 9999,
            pointerEvents: "none",
          }}
        >
          <div style={{ fontWeight: 700 }}>{hoverData.episodeTitle}</div>
          <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>
            {hoverData.spanStart.getFullYear()} - {hoverData.spanEnd.getFullYear()}
          </div>
          {hoverData.clusterId != null && (
            <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>
              cluster: <b>#{hoverData.clusterId}</b>
            </div>
          )}
          <div style={{ fontSize: 12, marginTop: 8 }}>
            <div style={{ color: "#555" }}>score {hoverData.score.toFixed(2)}</div>
            <div style={{ fontStyle: "italic" }}>{hoverData.sourceText}</div>
          </div>
          <div style={{ fontSize: 12, color: "#555", marginTop: 8 }}>click to open details →</div>
        </div>
      )}
    </div>
  );
```

**Step 2: Add hover event handlers to rects**

Update the rect rendering code to add hover handlers:
```typescript
      // Render span rects
      group.selectAll(".span-rect")
        .data(allSpans)
        .enter()
        .append("rect")
        .attr("class", "span-rect")
        .attr("x", (d) => scales.xScale(d.span.start))
        .attr("width", (d) => scales.xScale(d.span.end) - scales.xScale(d.span.start))
        .attr("y", 0)
        .attr("height", scales.yScale.bandwidth())
        .attr("fill", (d) => episodeColors.get(d.episodeId) ?? "#888")
        .attr("stroke", "white")
        .attr("stroke-width", 1)
        .attr("rx", 2)
        .style("cursor", "pointer")
        .on("click", (event, d) => {
          props.onSelectEpisode(d.episodeId);
        })
        .on("mouseover", (event, d) => {
          setHoverData({
            x: event.clientX,
            y: event.clientY,
            episodeId: d.episodeId,
            episodeTitle: d.episodeTitle,
            spanStart: d.span.start,
            spanEnd: d.span.end,
            score: d.span.score,
            sourceText: d.span.sourceText,
            clusterId: d.span.clusterId,
          });
        })
        .on("mouseout", () => {
          setHoverData(null);
        });
```

**Step 3: Run tests**

Run: `pnpm test`

Expected: All tests pass

**Step 4: Commit**

```bash
git add src/components/StackedBarTimeline.tsx
git commit -m "feat: add hover card interaction to timeline

- Show episode details on hover
- Display span dates, score, and snippet
- Include cluster ID if available
- Position card near cursor
- Clear hover state on mouseout"
```

---

## Task 9: Add Scrub Year Opacity Transitions

**Files:**
- Modify: `src/components/StackedBarTimeline.tsx`

**Step 1: Add opacity calculation helper**

Add helper function in component (before return):
```typescript
  function opacityByYear(spanStart: Date, spanEnd: Date, scrubYear?: number): number {
    if (scrubYear == null || Number.isNaN(scrubYear)) return 0.85;
    const mid = spanStart.getTime() + (spanEnd.getTime() - spanStart.getTime()) / 2;
    const midYear = new Date(mid).getUTCFullYear();
    const d = Math.abs(midYear - scrubYear);
    // gaussian-ish falloff, sigma ~ 40 years
    const sigma = 40;
    const w = Math.exp(-(d * d) / (2 * sigma * sigma));
    return 0.15 + 0.85 * w;
  }
```

**Step 2: Update rect rendering to use opacity**

Update the rect rendering to apply opacity:
```typescript
      // Render span rects
      group.selectAll(".span-rect")
        .data(allSpans)
        .enter()
        .append("rect")
        .attr("class", "span-rect")
        .attr("x", (d) => scales.xScale(d.span.start))
        .attr("width", (d) => scales.xScale(d.span.end) - scales.xScale(d.span.start))
        .attr("y", 0)
        .attr("height", scales.yScale.bandwidth())
        .attr("fill", (d) => episodeColors.get(d.episodeId) ?? "#888")
        .attr("stroke", "white")
        .attr("stroke-width", 1)
        .attr("rx", 2)
        .attr("opacity", (d) => opacityByYear(d.span.start, d.span.end, props.scrubYear))
        .style("cursor", "pointer")
        .on("click", (event, d) => {
          props.onSelectEpisode(d.episodeId);
        })
        .on("mouseover", (event, d) => {
          setHoverData({
            x: event.clientX,
            y: event.clientY,
            episodeId: d.episodeId,
            episodeTitle: d.episodeTitle,
            spanStart: d.span.start,
            spanEnd: d.span.end,
            score: d.span.score,
            sourceText: d.span.sourceText,
            clusterId: d.span.clusterId,
          });
        })
        .on("mouseout", () => {
          setHoverData(null);
        });
```

**Step 3: Add transition for scrub year changes**

Add a transition when scrubYear changes by wrapping the opacity update in a transition. Replace the rect rendering with:
```typescript
      // Render span rects
      const rects = group.selectAll(".span-rect")
        .data(allSpans);

      rects.enter()
        .append("rect")
        .attr("class", "span-rect")
        .attr("x", (d) => scales.xScale(d.span.start))
        .attr("width", (d) => scales.xScale(d.span.end) - scales.xScale(d.span.start))
        .attr("y", 0)
        .attr("height", scales.yScale.bandwidth())
        .attr("fill", (d) => episodeColors.get(d.episodeId) ?? "#888")
        .attr("stroke", "white")
        .attr("stroke-width", 1)
        .attr("rx", 2)
        .attr("opacity", (d) => opacityByYear(d.span.start, d.span.end, props.scrubYear))
        .style("cursor", "pointer")
        .on("click", (event, d) => {
          props.onSelectEpisode(d.episodeId);
        })
        .on("mouseover", (event, d) => {
          setHoverData({
            x: event.clientX,
            y: event.clientY,
            episodeId: d.episodeId,
            episodeTitle: d.episodeTitle,
            spanStart: d.span.start,
            spanEnd: d.span.end,
            score: d.span.score,
            sourceText: d.span.sourceText,
            clusterId: d.span.clusterId,
          });
        })
        .on("mouseout", () => {
          setHoverData(null);
        })
        .merge(rects)
        .transition()
        .duration(150)
        .attr("opacity", (d) => opacityByYear(d.span.start, d.span.end, props.scrubYear));

      rects.exit().remove();
```

**Step 4: Run tests**

Run: `pnpm test`

Expected: All tests pass

**Step 5: Commit**

```bash
git add src/components/StackedBarTimeline.tsx
git commit -m "feat: add scrub year opacity transitions

- Calculate opacity based on distance from scrub year
- Gaussian falloff with sigma ~40 years
- Smooth transitions when scrub year changes
- Maintain minimum opacity for visibility"
```

---

## Task 10: Add Proper D3 Axes

**Files:**
- Modify: `src/components/StackedBarTimeline.tsx`

**Step 1: Import D3 axis modules**

Update imports to include axis functions:
```typescript
import { select, selectAll, scaleAxisBottom, scaleAxisLeft } from "d3";
```

Actually, the correct imports are:
```typescript
import { select, selectAll, axisBottom, axisLeft } from "d3";
```

**Step 2: Update axes rendering**

Replace the axes rendering code with:
```typescript
    // Add x-axis
    const xAxis = g.append("g")
      .attr("class", "x-axis")
      .attr("transform", `translate(0,${innerHeight})`)
      .call(axisBottom(scales.xScale).ticks(10));

    // Add y-axis with podcast labels
    const yAxis = g.append("g")
      .attr("class", "y-axis")
      .call(axisLeft(scales.yScale));
```

**Step 3: Style axes**

Add axis styling after the axes creation:
```typescript
    // Style x-axis
    xAxis.selectAll("line")
      .style("stroke", "#ccc");
    xAxis.selectAll("text")
      .style("font-size", "12px")
      .style("fill", "#555");

    // Style y-axis
    yAxis.selectAll("line")
      .style("stroke", "#ccc");
    yAxis.selectAll("text")
      .style("font-size", "12px")
      .style("fill", "#555");
```

**Step 4: Run tests**

Run: `pnpm test`

Expected: All tests pass

**Step 5: Commit**

```bash
git add src/components/StackedBarTimeline.tsx
git commit -m "feat: add proper D3 axes to timeline

- Implement x-axis with year ticks
- Implement y-axis with podcast labels
- Add axis styling
- Use D3 axisBottom and axisLeft functions"
```

---

## Task 11: Integrate StackedBarTimeline into App

**Files:**
- Modify: `src/App.tsx`

**Step 1: Import StackedBarTimeline**

Add import at top with other component imports:
```typescript
import Timeline from "./components/Timeline";
import StackedBarTimeline from "./components/StackedBarTimeline";
```

**Step 2: Comment out existing Timeline**

Comment out the existing Timeline component (around line 144-153):
```tsx
      <div style={{ padding: 12, overflow: "hidden" }}>
        {/* <Timeline
          dataset={dataset}
          episodes={filteredEpisodes}
          topN={filters.topN}
          selectedEpisodeId={selectedEpisodeId}
          onSelectEpisode={(id) => setSelectedEpisodeId(id)}
          scrubYear={filters.year}
          onScrubYear={(y) => setFilters((f) => ({ ...f, year: y }))}
        /> */}
        <StackedBarTimeline
          dataset={dataset}
          episodes={filteredEpisodes}
          selectedEpisodeId={selectedEpisodeId}
          onSelectEpisode={(id) => setSelectedEpisodeId(id)}
          scrubYear={filters.year}
          onScrubYear={(y) => setFilters((f) => ({ ...f, year: y }))}
        />
      </div>
```

**Step 3: Remove unused topN prop**

The `topN` filter is no longer used by StackedBarTimeline (we show all spans). You can keep the UI control for now or remove it later.

**Step 4: Run dev server to test**

Run: `pnpm dev`

Expected: App loads, stacked bar timeline displays

**Step 5: Test interactions**

- Verify hover cards appear
- Verify clicking selects episode
- Verify scrub year slider updates opacity

**Step 6: Run tests**

Run: `pnpm test`

Expected: All tests pass

**Step 7: Commit**

```bash
git add src/App.tsx
git commit -m "feat: integrate StackedBarTimeline into app

- Replace Timeline with StackedBarTimeline
- Keep existing Timeline source (commented out)
- Wire up shared props for episode selection and scrub year
- Remove dependency on topN filter (show all spans)"
```

---

## Task 12: Progressive Tailwind Migration - App.tsx

**Files:**
- Modify: `src/App.tsx`

**Step 1: Migrate main container to Tailwind**

Replace the inline styled div with Tailwind classes (around line 53):
```tsx
  return (
    <div className="grid grid-cols-[360px_1fr_420px] h-screen">
```

**Step 2: Migrate sidebar styling**

Update sidebar div (around line 55):
```tsx
      <div className="border-r border-gray-300 p-3 overflow-auto">
```

**Step 3: Migrate headings**

Update headings and labels:
```tsx
        <h2 className="m-2 text-lg font-semibold">Podcast Explorer</h2>
        <div className="text-xs text-gray-600">
          schema {dataset.meta.schema_version} · generated {new Date(dataset.meta.generated_at_iso).toLocaleString()}
        </div>

        <div className="mt-3 grid gap-2.5">
```

**Step 4: Migrate form elements**

Update labels and inputs:
```tsx
          <label>
            <span className="block text-sm font-medium">Podcast</span>
            <select
              value={String(filters.podcastId)}
              onChange={(e) =>
                setFilters((f) => ({
                  ...f,
                  podcastId: e.target.value === "all" ? "all" : Number(e.target.value),
                }))
              }
              className="w-full mt-1"
            >
```

**Step 5: Migrate timeline controls area**

Update timeline controls div:
```tsx
        <div className="mt-3">
          <ClusterPanel
```

**Step 6: Migrate main content area**

Update main content div:
```tsx
      <div className="p-3 overflow-hidden">
```

**Step 7: Migrate detail panel**

Update detail panel div:
```tsx
      <div className="border-l border-gray-300 p-3 overflow-auto">
```

**Step 8: Run tests**

Run: `pnpm test`

Expected: All tests pass

**Step 9: Run dev server to verify**

Run: `pnpm dev`

Expected: Visual appearance unchanged

**Step 10: Run Biome to format**

Run: `pnpm format`

Expected: Auto-formats code

**Step 11: Commit**

```bash
git add src/App.tsx
git commit -m "refactor: migrate App.tsx to Tailwind CSS

- Replace inline styles with Tailwind classes
- Use grid-cols-[...] for custom grid layout
- Maintain identical visual appearance
- Apply Biome formatting"
```

---

## Task 13: Run Biome Linter and Fix Issues

**Files:**
- Multiple

**Step 1: Run Biome check**

Run: `pnpm lint`

Expected: Shows various linting issues

**Step 2: Auto-fix what can be fixed**

Run: `pnpm lint:fix`

Expected: Fixes auto-fixable issues

**Step 3: Manually fix remaining issues**

Address each remaining linting issue:
- Unused imports
- Unused variables
- Code style issues

**Step 4: Re-run linter**

Run: `pnpm lint`

Expected: All issues resolved (or only warnings)

**Step 5: Run tests**

Run: `pnpm test`

Expected: All tests pass

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: fix Biome linting issues

- Run biome lint:fix on all files
- Manually fix remaining issues
- Ensure code meets recommended linting standards"
```

---

## Task 14: Add Integration Tests

**Files:**
- Create: `src/integration/stackedBarTimeline.integration.test.tsx`

**Step 1: Create integration test**

Create `src/integration/stackedBarTimeline.integration.test.tsx`:
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import StackedBarTimeline from "../components/StackedBarTimeline";
import type { Dataset } from "../types";

describe("StackedBarTimeline Integration", () => {
  let mockDataset: Dataset;

  beforeEach(() => {
    mockDataset = {
      meta: { schema_version: "1.0", generated_at_iso: "2024-01-01", source_db: "test" },
      podcasts: [
        { id: 1, title: "History Podcast" },
        { id: 2, title: "Story Podcast" },
      ],
      episodes: [
        { id: 1, podcast_id: 1, title: "Episode 1", pub_date_iso: "2024-01-01" },
        { id: 2, podcast_id: 1, title: "Episode 2", pub_date_iso: "2024-01-02" },
        { id: 3, podcast_id: 2, title: "Episode 3", pub_date_iso: "2024-01-03" },
      ],
      spans: [
        {
          id: 1,
          episode_id: 1,
          start_iso: "1700-01-01",
          end_iso: "1750-01-01",
          precision: "year",
          qualifier: "approx",
          score: 0.9,
          source_section: "intro",
          source_text: "In the year 1700, something happened",
        },
        {
          id: 2,
          episode_id: 1,
          start_iso: "1800-01-01",
          end_iso: "1850-01-01",
          precision: "year",
          qualifier: "approx",
          score: 0.8,
          source_section: "chapter 1",
          source_text: "By 1800, the world had changed",
        },
        {
          id: 3,
          episode_id: 2,
          start_iso: "1750-01-01",
          end_iso: "1800-01-01",
          precision: "year",
          qualifier: "approx",
          score: 0.7,
          source_section: "intro",
          source_text: "Between 1750 and 1800",
        },
      ],
      places: [],
      entities: [],
      episode_keywords: {},
      episode_clusters: { "1": 1, "2": 1 },
      clusters: [],
    };
  });

  it("renders all podcasts with their episodes", () => {
    const onSelectEpisode = vi.fn();
    const { container } = render(
      <StackedBarTimeline
        dataset={mockDataset}
        episodes={mockDataset.episodes}
        selectedEpisodeId={null}
        onSelectEpisode={onSelectEpisode}
        onScrubYear={vi.fn()}
      />
    );

    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("calls onSelectEpisode when a span rect is clicked", async () => {
    const onSelectEpisode = vi.fn();
    const { container } = render(
      <StackedBarTimeline
        dataset={mockDataset}
        episodes={mockDataset.episodes}
        selectedEpisodeId={null}
        onSelectEpisode={onSelectEpisode}
        onScrubYear={vi.fn()}
      />
    );

    // Wait for D3 to render
    await waitFor(() => {
      const rects = container.querySelectorAll(".span-rect");
      expect(rects.length).toBeGreaterThan(0);
    });

    const rects = container.querySelectorAll(".span-rect");
    if (rects[0]) {
      fireEvent.click(rects[0]);
      expect(onSelectEpisode).toHaveBeenCalled();
    }
  });
});
```

**Step 2: Run integration tests**

Run: `pnpm test src/integration/stackedBarTimeline.integration.test.tsx`

Expected: Tests pass

**Step 3: Commit**

```bash
git add src/integration/stackedBarTimeline.integration.test.tsx
git commit -m "test: add integration tests for StackedBarTimeline

- Test rendering with real dataset
- Test click interactions on span rects
- Verify episode selection callback"
```

---

## Task 15: Final Verification and Documentation

**Files:**
- Create: `README.md` (if not exists) or update

**Step 1: Create/update README**

Create `README.md` with project info:
```markdown
# Podcast Explorer Frontend

A React-based podcast timeline explorer with historical time span visualization.

## Tech Stack

- React 18 with TypeScript
- Vite 5 for build tooling
- D3.js 7 for data visualization
- Tailwind CSS for styling
- Biome for linting and formatting
- Vitest for testing

## Development

```bash
# Install dependencies
pnpm install

# Start dev server
pnpm dev

# Run tests
pnpm test

# Lint and format
pnpm lint
pnpm format

# Build
pnpm build
```

## Components

- **StackedBarTimeline**: D3.js-powered stacked bar chart showing historical time spans grouped by podcast
- **Timeline**: Original Plotly-based scatter plot (hidden, preserved for reference)
- **ClusterPanel**: Episode cluster filtering
- **EpisodeDetail**: Episode details panel
```

**Step 2: Run full test suite**

Run: `pnpm test`

Expected: All tests pass

**Step 3: Run linter**

Run: `pnpm lint`

Expected: No errors (warnings acceptable)

**Step 4: Build production version**

Run: `pnpm build`

Expected: Build succeeds

**Step 5: Verify build output**

Run: `pnpm preview`

Expected: Preview works correctly

**Step 6: Final commit**

```bash
git add README.md
git commit -m "docs: add README with project documentation

- Document tech stack
- Add development commands
- Describe key components"
```

---

## Completion Checklist

- [x] Biome installed and configured
- [x] Tailwind CSS installed and configured
- [x] D3.js dependency added
- [x] Data transformation utilities created and tested
- [x] D3 scale utilities created and tested
- [x] StackedBarTimeline component created
- [x] Episode rects render correctly
- [x] Hover interactions work
- [x] Scrub year opacity transitions work
- [x] Proper axes rendered
- [x] Component integrated into App (Timeline preserved)
- [x] App.tsx migrated to Tailwind
- [x] Linting issues resolved
- [x] Integration tests passing
- [x] README documentation added
- [x] All tests passing
- [x] Production build successful
