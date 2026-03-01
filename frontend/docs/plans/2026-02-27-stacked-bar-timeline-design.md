# Stacked Bar Timeline Design

**Date:** 2026-02-27
**Status:** Approved

## Overview

Replace the current timeline scatter plot with a stacked bar chart visualization where:
- **Y-axis:** Podcasts (architected for flexible grouping later: speaker, gender, cluster)
- **X-axis:** Historical time (span dates)
- **Stacks:** Episodes within each podcast, shown as time segments with gaps between them
- **Visuals:** Color-coded by cluster, with hover interactions

**Technology:** D3.js (chosen over Plotly.js for custom visualization flexibility and better interactivity)

## Architecture

### New Component Structure
```
src/components/
├── Timeline.tsx           # Keep existing (hidden/unused, not deleted)
├── StackedBarTimeline.tsx # New D3.js component
└── TimelineView.tsx       # Future container for view switching
```

### Extensibility for Grouping
```typescript
type GroupBy = "podcast" | "speaker" | "gender" | "cluster";

interface StackConfig {
  groupBy: GroupBy;
  // Future options...
}
```

### Data Flow
1. `App.tsx` → passes episodes, spans, dataset to `StackedBarTimeline`
2. `StackedBarTimeline` → transforms data into D3-friendly format
3. D3 renders SVG with:
   - Y-axis: Podcast names (one row per podcast)
   - X-axis: Time scale (historical years)
   - Rects: Episode spans (colored by cluster)

## Component Design

### StackedBarTimeline Props
```typescript
interface StackedBarTimelineProps {
  dataset: Dataset;
  episodes: Episode[];  // filtered episodes
  selectedEpisodeId: number | null;
  onSelectEpisode: (id: number) => void;
  scrubYear?: number;
  onScrubYear: (y?: number) => void;
  // Future: groupBy?: GroupBy;
}
```

### Handling Multiple Spans Per Episode
- Same episode with multiple time periods → multiple separate rects in the chart
- All rects for the same episode share the same visual treatment
- Click on any rect → selects that episode
- Future: tooltip or sidebar actions for span-specific details

### Color Coding
- Cluster-based coloring (consistent with existing visualization)
- Ad-hoc fallback for episodes without clusters

### D3 Chart Structure
- SVG container with responsive sizing
- Time scale (x): Linear scale from min span start to max span end
- Group scale (y): Band scale for podcasts
- Per-podcast group: `<g>` containing episode rects
- Episode rects: Positioned by time, colored by cluster, opacity by scrubYear

### Interactions
- **Hover:** Show episode details tooltip (reuse existing hover card)
- **Click:** Select episode
- **Scrub year slider:** Fade non-matching spans
- **Play/pause:** Animate through years

## Tooling Setup

### Biome (linting + formatting)
```bash
pnpm add -D @biomejs/biome
```
- `biome.json`: Recommended rules
- Scripts: `lint`, `format`, `check`
- VSCode extension for IDE integration

### Tailwind CSS
```bash
pnpm add -D tailwindcss postcss autoprefixer
```
- `tailwind.config.js`: Config with content paths
- `postcss.config.js`: Required for Vite
- `src/index.css`: Import Tailwind directives
- Progressive migration: New components use Tailwind, old inline styles stay

## Data Transformation

### Transforming Dataset → D3 Format
```typescript
interface D3StackData {
  podcastId: number;
  podcastTitle: string;
  episodes: Array<{
    episodeId: number;
    title: string;
    spans: Array<{
      start: Date;
      end: Date;
      score: number;
      clusterId?: number;
    }>;
  }>;
}
```

### Y-axis Ordering
Podcasts sorted by title (configurable later for other grouping options)

### X-axis Bounds
Min/max of all span dates across visible episodes

### Episode Rect Positioning
- x: `timeScale(span.start)`
- width: `timeScale(span.end) - timeScale(span.start)`
- y: `podcastScale(podcastTitle)`
- height: `podcastScale.bandwidth()`

## D3 Rendering Implementation

### SVG Structure
```html
<svg>
  <g class="x-axis"></g>
  <g class="y-axis"></g>
  <g class="grid-lines"></g>
  <g class="stacks">
    <g class="podcast-1">
      <rect class="episode-1-span-1" />
      <rect class="episode-1-span-2" />
    </g>
  </g>
</svg>
```

### Key D3 Patterns
- `d3.scaleTime()` for x-axis (historical dates)
- `d3.scaleBand()` for y-axis (podcasts)
- `d3.axisBottom()` / `d3.axisLeft()` for axes
- Enter/update/exit pattern for reactive updates

### Responsive Sizing
- Use `ResizeObserver` on container
- Update scales and re-render on resize

### Animation
- Scrub year: Transition opacity using `d3.transition()`
- Initial render: Fade-in animation

## Timeline Integration

### In App.tsx
```tsx
// Hide existing Timeline, keep source
{/*
<Timeline ... />
*/}

// New component
<StackedBarTimeline
  dataset={dataset}
  episodes={filteredEpisodes}
  selectedEpisodeId={selectedEpisodeId}
  onSelectEpisode={(id) => setSelectedEpisodeId(id)}
  scrubYear={filters.year}
  onScrubYear={(y) => setFilters((f) => ({ ...f, year: y }))}
/>
```

### Shared Controls
- Play/pause button (works with D3 opacity transitions)
- Scrub year slider (already exists)
- Year input (already exists)

### Preserve Existing Components
- Keep Timeline.tsx source (commented out)
- Reuse hover card component for D3 interactions

## Testing Strategy

### Unit Tests (Vitest)
- Data transformations: grouping, filtering, edge cases
- Scale creation: time scale, band scale
- Component rendering: correct counts, interactions

### Integration Tests
- Test with real dataset fixture
- Verify hover card positioning
- Verify play/pause animation

### Visual Regression
- Consider snapshot tests for SVG output (optional)

## Migration Plan

### Phase 1 - Tooling Setup
1. Add Biome and Tailwind dependencies
2. Configure `biome.json` and `tailwind.config.js`
3. Set up PostCSS config
4. Add Tailwind directives to `index.css`
5. Add npm scripts for lint/format

### Phase 2 - New Component
1. Create `StackedBarTimeline.tsx` with D3.js
2. Add data transformation utilities
3. Implement D3 rendering with hover/click
4. Write tests for new component

### Phase 3 - Integration
1. Hide existing Timeline (comment out, not delete)
2. Wire up StackedBarTimeline in App.tsx
3. Verify shared controls work
4. Test with real data

### Phase 4 - Progressive Styling
1. Migrate App.tsx inline styles to Tailwind
2. Migrate other components gradually
3. Run Biome linter and fix issues
