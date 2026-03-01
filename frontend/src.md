Project Path: src

Source Tree:

```txt
src
├── App.integration.test.tsx
├── App.tsx
├── components
│   ├── ClusterPanel.tsx
│   ├── EpisodeDetail.tsx
│   ├── GraphIntervalSlider.tsx
│   ├── StackedBarTimeline.test.tsx
│   ├── StackedBarTimeline.tsx
│   └── Timeline.tsx
├── index.css
├── main.tsx
├── test
│   └── setup.ts
├── types.ts
├── urlState.ts
└── utils
    ├── timelineScales.test.ts
    ├── timelineScales.ts
    ├── timelineTransform.test.ts
    └── timelineTransform.ts

```

`App.integration.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App"
import type { Dataset } from "./types"

function createDataset(): Dataset {
  return {
    meta: {
      schema_version: "test",
      generated_at_iso: new Date().toISOString(),
      source_db: "test.db",
    },
    podcasts: [{ id: 1, title: "Test Podcast", link: "https://example.com", language: "en" }],
    episodes: [
      {
        id: 101,
        podcast_id: 1,
        title: "Episode Alpha",
        pub_date_iso: "2020-01-01T00:00:00Z",
        page_url: "https://example.com/alpha",
        audio_url: "https://example.com/alpha.mp3",
        kind: "regular",
        narrator: "Alice",
        description_pure: "Alpha description",
      },
      {
        id: 102,
        podcast_id: 1,
        title: "Episode Beta",
        pub_date_iso: "2021-01-01T00:00:00Z",
        page_url: "https://example.com/beta",
        audio_url: "https://example.com/beta.mp3",
        kind: "special",
        narrator: "Bob",
        description_pure: "Beta description",
      },
    ],
    spans: [
      {
        id: 1,
        episode_id: 101,
        start_iso: "1800-01-01T00:00:00Z",
        end_iso: "1802-01-01T00:00:00Z",
        precision: "year",
        qualifier: "exact",
        score: 0.9,
        source_section: "desc",
        source_text: "alpha span",
      },
      {
        id: 2,
        episode_id: 102,
        start_iso: "1850-01-01T00:00:00Z",
        end_iso: "1851-01-01T00:00:00Z",
        precision: "year",
        qualifier: "exact",
        score: 0.8,
        source_section: "desc",
        source_text: "beta span",
      },
    ],
    places: [],
    entities: [],
    episode_keywords: {},
    episode_clusters: {},
    clusters: [],
  }
}

describe("App integration", () => {
  beforeEach(() => {
    const dataset = createDataset()
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => dataset,
    } as Response)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("filters episodes and opens detail after timeline click", async () => {
    render(<App />)

    await screen.findByText("Matching episodes:")
    expect(screen.getByText("2")).toBeInTheDocument()

    const search = screen.getByLabelText("Search title")
    fireEvent.change(search, { target: { value: "Alpha" } })

    await waitFor(() => {
      expect(screen.getByText(/Matching episodes:/).textContent).toContain("1")
    })

    await waitFor(() => {
      const rects = document.querySelectorAll("rect.span-rect")
      expect(rects.length).toBeGreaterThan(0)
    })

    const firstRect = document.querySelector("rect.span-rect")
    expect(firstRect).toBeTruthy()
    if (firstRect) {
      fireEvent.click(firstRect)
    }

    await screen.findByText("Episode Alpha")
    expect(screen.getByText(/alpha span/i)).toBeInTheDocument()
  })
})

```

`App.tsx`:

```tsx
import { useEffect, useMemo, useState } from "react"
import { Group, Panel, Separator } from "react-resizable-panels"
import ClusterPanel from "./components/ClusterPanel"
import EpisodeDetail from "./components/EpisodeDetail"
import GraphIntervalSlider from "./components/GraphIntervalSlider"
import StackedBarTimeline from "./components/StackedBarTimeline"
import Timeline from "./components/Timeline"
import type { Dataset } from "./types"
import { type Filters, readFiltersFromUrl, writeFiltersToUrl } from "./urlState"

async function loadDataset(): Promise<Dataset> {
  const res = await fetch("/dataset.json", { cache: "no-store" })
  if (!res.ok) throw new Error(`Failed to load dataset.json: ${res.status}`)
  return (await res.json()) as Dataset
}

function hasSpanInYearRange(
  dataset: Dataset,
  episodeId: number,
  yearRange: [number, number]
): boolean {
  const [minYear, maxYear] = yearRange
  for (const s of dataset.spans) {
    if (s.episode_id !== episodeId) continue
    if (!s.start_iso || !s.end_iso) continue
    const a = new Date(s.start_iso).getUTCFullYear()
    const b = new Date(s.end_iso).getUTCFullYear()
    if (Number.isNaN(a) || Number.isNaN(b)) continue
    const lo = Math.min(a, b)
    const hi = Math.max(a, b)
    if (hi >= minYear && lo <= maxYear) return true
  }
  return false
}

function spanYearBounds(dataset: Dataset, episodeIds: Set<number>): [number, number] | null {
  let minYear = Number.POSITIVE_INFINITY
  let maxYear = Number.NEGATIVE_INFINITY

  for (const s of dataset.spans) {
    if (!episodeIds.has(s.episode_id)) continue
    if (!s.start_iso || !s.end_iso) continue
    const a = new Date(s.start_iso).getUTCFullYear()
    const b = new Date(s.end_iso).getUTCFullYear()
    if (Number.isNaN(a) || Number.isNaN(b)) continue
    minYear = Math.min(minYear, a, b)
    maxYear = Math.max(maxYear, a, b)
  }

  if (!Number.isFinite(minYear) || !Number.isFinite(maxYear)) return null
  return [Math.floor(minYear), Math.ceil(maxYear)]
}

export default function App() {
  const [dataset, setDataset] = useState<Dataset | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>(() => readFiltersFromUrl())
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<number | null>(null)
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [docModal, setDocModal] = useState<"readme" | "changelog" | null>(null)

  useEffect(() => {
    loadDataset()
      .then(setDataset)
      .catch(e => setErr(String(e)))
  }, [])

  useEffect(() => {
    writeFiltersToUrl(filters)
  }, [filters])

  const podcasts = dataset?.podcasts ?? []

  const episodesBeforeYearRange = useMemo(() => {
    if (!dataset) return []
    const q = filters.q.trim().toLowerCase()
    const narr = filters.narrator.trim().toLowerCase()
    const kind = filters.kind
    const clusterId = filters.clusterId

    return dataset.episodes.filter(e => {
      if (filters.podcastId !== "all" && e.podcast_id !== filters.podcastId) return false
      if (q && !e.title.toLowerCase().includes(q)) return false
      if (kind !== "all" && (e.kind ?? "") !== kind) return false
      if (narr && !(e.narrator ?? "").toLowerCase().includes(narr)) return false
      if (clusterId != null) {
        const cid = dataset.episode_clusters[String(e.id)]
        if (cid !== clusterId) return false
      }
      return true
    })
  }, [dataset, filters])

  const availableYearRange = useMemo<[number, number]>(() => {
    if (!dataset) return [-500, new Date().getUTCFullYear()]
    const ids = new Set(episodesBeforeYearRange.map(e => e.id))
    const bounds = spanYearBounds(dataset, ids)
    if (!bounds) return [-500, new Date().getUTCFullYear()]
    return bounds
  }, [dataset, episodesBeforeYearRange])

  const activeYearRange = useMemo<[number, number]>(() => {
    const [minY, maxY] = availableYearRange
    const rawMin = filters.yearMin ?? minY
    const rawMax = filters.yearMax ?? maxY
    const clampedMin = Math.max(minY, Math.min(rawMin, maxY - 1))
    const clampedMax = Math.min(maxY, Math.max(rawMax, clampedMin + 1))
    return [clampedMin, clampedMax]
  }, [availableYearRange, filters.yearMin, filters.yearMax])

  const filteredEpisodes = useMemo(() => {
    if (!dataset) return []
    return episodesBeforeYearRange.filter(e => hasSpanInYearRange(dataset, e.id, activeYearRange))
  }, [dataset, episodesBeforeYearRange, activeYearRange])

  const baseEpisodeIdSet = useMemo(
    () => new Set(episodesBeforeYearRange.map(e => e.id)),
    [episodesBeforeYearRange]
  )
  const sliderSpans = useMemo(
    () => (dataset?.spans ?? []).filter(s => baseEpisodeIdSet.has(s.episode_id)),
    [dataset, baseEpisodeIdSet]
  )

  if (err) return <div className="p-4">Error: {err}</div>
  if (!dataset) return <div className="p-4">Loading dataset…</div>

  return (
    <div className="h-screen">
      <Group direction="horizontal">
        <Panel
          defaultSize={22}
          minSize={15}
          maxSize={38}
          className="overflow-auto border-r border-[color:var(--border)] bg-[color:var(--surface)]/92 p-3"
          style={{ transition: "flex-grow 220ms ease, flex-basis 220ms ease" }}
        >
          {leftCollapsed ? (
            <button type="button" onClick={() => setLeftCollapsed(false)} className="text-xs">
              →
            </button>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <h2 className="m-0 text-xl font-semibold text-[color:var(--text)]">
                  Podcast Explorer
                </h2>
                <button type="button" onClick={() => setLeftCollapsed(true)} className="text-xs">
                  collapse
                </button>
              </div>
              <div className="mt-1 text-xs text-[color:var(--muted)]">
                schema {dataset.meta.schema_version} · generated{" "}
                {new Date(dataset.meta.generated_at_iso).toLocaleString()}
              </div>

              <div className="mt-4 grid gap-3">
                <label>
                  Podcast
                  <select
                    value={String(filters.podcastId)}
                    onChange={e =>
                      setFilters(f => ({
                        ...f,
                        podcastId: e.target.value === "all" ? "all" : Number(e.target.value),
                      }))
                    }
                    className="mt-1 w-full"
                  >
                    <option value="all">All</option>
                    {podcasts.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.title}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Search title
                  <input
                    value={filters.q}
                    onChange={e => setFilters(f => ({ ...f, q: e.target.value }))}
                    className="mt-1 w-full"
                  />
                </label>

                <label>
                  Kind
                  <select
                    value={filters.kind}
                    onChange={e => setFilters(f => ({ ...f, kind: e.target.value }))}
                    className="mt-1 w-full"
                  >
                    <option value="all">All</option>
                    <option value="regular">regular</option>
                    <option value="book">book</option>
                    <option value="meta">meta</option>
                    <option value="special">special</option>
                  </select>
                </label>

                <label>
                  Narrator contains
                  <input
                    value={filters.narrator}
                    onChange={e => setFilters(f => ({ ...f, narrator: e.target.value }))}
                    className="mt-1 w-full"
                  />
                </label>

                <label>
                  Timeline spans per episode (top-N)
                  <input
                    type="range"
                    min={1}
                    max={6}
                    value={filters.topN}
                    onChange={e => setFilters(f => ({ ...f, topN: Number(e.target.value) }))}
                    className="mt-1 w-full"
                  />
                  <div className="text-xs text-[color:var(--muted)]">{filters.topN}</div>
                </label>

                <label>
                  Axis density factor (k)
                  <input
                    type="range"
                    min={0.4}
                    max={2.5}
                    step={0.1}
                    value={filters.axisK}
                    onChange={e => setFilters(f => ({ ...f, axisK: Number(e.target.value) }))}
                    className="mt-1 w-full"
                  />
                  <div className="text-xs text-[color:var(--muted)]">
                    k = {filters.axisK.toFixed(1)}
                  </div>
                </label>

                <label>
                  Time scrubber year
                  <input
                    type="number"
                    value={filters.year ?? ""}
                    placeholder="e.g. 1776"
                    onChange={e =>
                      setFilters(f => ({
                        ...f,
                        year: e.target.value ? Number(e.target.value) : undefined,
                      }))
                    }
                    className="mt-1 w-full"
                  />
                </label>
              </div>

              <div className="mt-4">
                <ClusterPanel
                  dataset={dataset}
                  filters={filters}
                  onSelectCluster={cid => setFilters(f => ({ ...f, clusterId: cid }))}
                  onClearCluster={() => setFilters(f => ({ ...f, clusterId: undefined }))}
                />
              </div>

              <div className="mt-4 text-xs text-[color:var(--muted)]">
                Matching episodes: <b>{filteredEpisodes.length}</b>
              </div>
            </>
          )}
        </Panel>

        <Separator className="w-1 bg-[color:var(--border)] transition-colors hover:bg-[color:var(--accent)]" />

        <Panel defaultSize={53} minSize={34} className="relative overflow-hidden p-3 md:p-4">
          <div className="absolute right-3 top-3 z-20 flex items-center gap-2">
            <a
              href="https://github.com/example/historycasts"
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
            >
              GH
            </a>
            <a
              href="https://fkr.dev/"
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
            >
              FKR
            </a>
            <button
              type="button"
              onClick={() => setDocModal("readme")}
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
            >
              README
            </button>
            <button
              type="button"
              onClick={() => setDocModal("changelog")}
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
            >
              CHANGELOG
            </button>
            <button
              type="button"
              onClick={() => setLeftCollapsed(v => !v)}
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
            >
              {leftCollapsed ? "open filters" : "hide filters"}
            </button>
            <button
              type="button"
              onClick={() => setRightCollapsed(v => !v)}
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
            >
              {rightCollapsed ? "open details" : "hide details"}
            </button>
          </div>

          <div className="flex h-full flex-col gap-3 pt-10">
            <div className="min-h-[300px] flex-[0_0_56%] overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2">
              <StackedBarTimeline
                dataset={dataset}
                episodes={filteredEpisodes}
                selectedEpisodeId={selectedEpisodeId}
                onSelectEpisode={id => setSelectedEpisodeId(id)}
                scrubYear={filters.year}
                onScrubYear={y => setFilters(f => ({ ...f, year: y }))}
                visibleYearRange={activeYearRange}
                axisDensityK={filters.axisK}
              />
            </div>

            <GraphIntervalSlider
              spans={sliderSpans}
              minYear={availableYearRange[0]}
              maxYear={availableYearRange[1]}
              value={activeYearRange}
              onChange={next => setFilters(f => ({ ...f, yearMin: next[0], yearMax: next[1] }))}
            />

            <div className="min-h-[260px] flex-1 overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2">
              <Timeline
                dataset={dataset}
                episodes={filteredEpisodes}
                topN={filters.topN}
                selectedEpisodeId={selectedEpisodeId}
                onSelectEpisode={id => setSelectedEpisodeId(id)}
                scrubYear={filters.year}
                onScrubYear={y => setFilters(f => ({ ...f, year: y }))}
                visibleYearRange={activeYearRange}
              />
            </div>
          </div>
        </Panel>

        <Separator className="w-1 bg-[color:var(--border)] transition-colors hover:bg-[color:var(--accent)]" />

        <Panel
          defaultSize={25}
          minSize={16}
          maxSize={40}
          className="overflow-auto border-l border-[color:var(--border)] bg-[color:var(--surface)]/92 p-4"
          style={{ transition: "flex-grow 220ms ease, flex-basis 220ms ease" }}
        >
          {rightCollapsed ? (
            <button type="button" onClick={() => setRightCollapsed(false)} className="text-xs">
              ←
            </button>
          ) : (
            <EpisodeDetail dataset={dataset} episodeId={selectedEpisodeId} />
          )}
        </Panel>
      </Group>

      {docModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="relative h-[85vh] w-[min(1100px,96vw)] rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-2">
            <button
              type="button"
              onClick={() => setDocModal(null)}
              className="absolute right-3 top-3 z-10 rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
            >
              close
            </button>
            <iframe
              title={docModal}
              src={`/docs/${docModal}.html`}
              className="h-full w-full rounded-lg border border-[color:var(--border)] bg-white"
            />
          </div>
        </div>
      )}
    </div>
  )
}

```

`components/ClusterPanel.tsx`:

```tsx
import { useMemo, useState } from "react"
import type { Dataset } from "../types"
import type { Filters } from "../urlState"

export default function ClusterPanel(props: {
  dataset: Dataset
  filters: Filters
  onSelectCluster: (clusterId: number) => void
  onClearCluster: () => void
}) {
  const [open, setOpen] = useState(true)
  const clusters = useMemo(() => {
    const pid = props.filters.podcastId
    return props.dataset.clusters
      .filter(c => (pid === "all" ? true : c.cluster.podcast_id === pid))
      .sort((a, b) => b.cluster.n_members - a.cluster.n_members)
  }, [props.dataset, props.filters.podcastId])

  return (
    <div>
      <div className="flex items-center justify-between">
        <h3 className="m-0 text-base font-semibold">Clusters</h3>
        <button type="button" onClick={() => setOpen(v => !v)} className="text-xs">
          {open ? "hide" : "show"}
        </button>
      </div>

      {props.filters.clusterId != null && (
        <div className="mt-2">
          <div className="text-xs text-[color:var(--muted)]">
            active cluster: {props.filters.clusterId}
          </div>
          <button type="button" onClick={props.onClearCluster} className="mt-1 text-xs">
            clear cluster filter
          </button>
        </div>
      )}

      {open && (
        <div className="mt-2 grid gap-2">
          {clusters.slice(0, 24).map(c => (
            <button
              type="button"
              key={c.cluster.id}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2 text-left"
              onClick={() => props.onSelectCluster(c.cluster.id)}
            >
              <div className="flex justify-between">
                <b>#{c.cluster.id}</b>
                <span className="text-xs text-[color:var(--muted)]">{c.cluster.n_members} eps</span>
              </div>
              <div className="text-xs text-[color:var(--muted)]">
                centroid: {c.cluster.centroid_mid_year.toFixed(0)} ·{" "}
                {c.cluster.centroid_lat.toFixed(1)}, {c.cluster.centroid_lon.toFixed(1)}
              </div>
              <div className="mt-1.5 text-xs">
                <div className="text-[color:var(--muted)]">top keywords</div>
                <div>
                  {c.top_keywords
                    .slice(0, 5)
                    .map(k => k.phrase)
                    .join(" · ")}
                </div>
              </div>
            </button>
          ))}
          {clusters.length > 24 && (
            <div className="text-xs text-[color:var(--muted)]">showing top 24 clusters</div>
          )}
        </div>
      )}
    </div>
  )
}

```

`components/EpisodeDetail.tsx`:

```tsx
import { useMemo } from "react"
import type { Dataset } from "../types"

export default function EpisodeDetail(props: { dataset: Dataset; episodeId: number | null }) {
  const ep = useMemo(() => {
    if (props.episodeId == null) return null
    return props.dataset.episodes.find(e => e.id === props.episodeId) ?? null
  }, [props.dataset.episodes, props.episodeId])

  const spans = useMemo(() => {
    if (!ep) return []
    return props.dataset.spans
      .filter(s => s.episode_id === ep.id)
      .slice()
      .sort((a, b) => b.score - a.score)
      .slice(0, 20)
  }, [props.dataset.spans, ep])

  const places = useMemo(() => {
    if (!ep) return []
    return props.dataset.places.filter(p => p.episode_id === ep.id)
  }, [props.dataset.places, ep])

  const entities = useMemo(() => {
    if (!ep) return []
    return props.dataset.entities
      .filter(en => en.episode_id === ep.id)
      .slice()
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 40)
  }, [props.dataset.entities, ep])

  const keywords = useMemo(() => {
    if (!ep) return []
    return (props.dataset.episode_keywords[String(ep.id)] ?? []).slice(0, 30)
  }, [props.dataset.episode_keywords, ep])

  if (!ep) {
    return (
      <div>
        <h2 className="mt-0">Episode</h2>
        <div className="text-[color:var(--muted)]">
          Click a bar in the timeline to open episode details.
        </div>
      </div>
    )
  }

  return (
    <div>
      <h2 className="mt-0 text-lg">{ep.title}</h2>
      <div className="text-xs text-[color:var(--muted)]">
        pub: {new Date(ep.pub_date_iso).toLocaleString()} · kind: {ep.kind ?? "?"} · narrator:{" "}
        {ep.narrator ?? "?"}
      </div>

      <div className="mt-2 flex flex-wrap gap-2">
        {ep.page_url && (
          <a
            href={ep.page_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
          >
            page
          </a>
        )}
        {ep.audio_url && (
          <a
            href={ep.audio_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
          >
            audio
          </a>
        )}
      </div>

      <div className="mt-3">
        <h3>Time spans</h3>
        <div className="grid gap-2">
          {spans.map((s, idx) => (
            <div
              key={s.id}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2"
            >
              <div className="flex justify-between">
                <b>#{idx + 1}</b>
                <span className="text-xs text-[color:var(--muted)]">
                  score {s.score.toFixed(2)}
                </span>
              </div>
              <div className="text-xs text-[color:var(--muted)]">
                {s.start_iso ?? "?"} → {s.end_iso ?? "?"} · {s.precision}/{s.qualifier} · section{" "}
                {s.source_section}
              </div>
              <div className="mt-1.5">{s.source_text}</div>
            </div>
          ))}
          {spans.length === 0 && (
            <div className="text-[color:var(--muted)]">No extracted spans.</div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <h3>Places</h3>
        <div className="grid gap-2">
          {places.map(p => (
            <div
              key={p.id}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2"
            >
              <b>{p.canonical_name}</b>{" "}
              <span className="text-xs text-[color:var(--muted)]">({p.place_kind})</span>
              <div className="text-xs text-[color:var(--muted)]">
                {p.lat != null && p.lon != null
                  ? `${p.lat.toFixed(3)}, ${p.lon.toFixed(3)} · r=${p.radius_km ?? "?"}km`
                  : "(no offline match)"}
              </div>
            </div>
          ))}
          {places.length === 0 && (
            <div className="text-[color:var(--muted)]">No extracted places.</div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <h3>Entities</h3>
        <div className="flex flex-wrap gap-1.5">
          {entities.map(e => (
            <span
              key={e.id}
              className="rounded-full border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
            >
              {e.name} <span className="text-[color:var(--muted)]">({e.kind})</span>
            </span>
          ))}
          {entities.length === 0 && (
            <div className="text-[color:var(--muted)]">No extracted entities.</div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <h3>Keywords</h3>
        <div className="flex flex-wrap gap-1.5">
          {keywords.map(k => (
            <span
              key={k.phrase}
              className="rounded-full border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
            >
              {k.phrase}
            </span>
          ))}
          {keywords.length === 0 && (
            <div className="text-[color:var(--muted)]">No extracted keywords.</div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <h3>Description</h3>
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-3 text-sm">
          {ep.description_pure ?? ""}
        </pre>
      </div>
    </div>
  )
}

```

`components/GraphIntervalSlider.tsx`:

```tsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react"

interface SpanLite {
  start_iso?: string
  end_iso?: string
}

export default function GraphIntervalSlider(props: {
  spans: SpanLite[]
  minYear: number
  maxYear: number
  value: [number, number]
  onChange: (next: [number, number]) => void
}) {
  const { spans, minYear, maxYear, value, onChange } = props
  const rootRef = useRef<HTMLDivElement | null>(null)
  const [width, setWidth] = useState(900)
  const [dragging, setDragging] = useState<"min" | "max" | null>(null)

  useEffect(() => {
    const el = rootRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      const w = entries[0]?.contentRect.width ?? 900
      setWidth(Math.max(320, Math.floor(w)))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const years = useMemo(() => {
    const out: number[] = []
    for (let y = minYear; y <= maxYear; y += 1) out.push(y)
    return out
  }, [minYear, maxYear])

  const series = useMemo(() => {
    const res = years.map(y => ({ year: y, count: 0, avgDur: 0 }))
    const totalDur = new Array(res.length).fill(0)

    for (const sp of spans) {
      if (!sp.start_iso || !sp.end_iso) continue
      const s = new Date(sp.start_iso)
      const e = new Date(sp.end_iso)
      if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) continue

      const a = Math.min(s.getUTCFullYear(), e.getUTCFullYear())
      const b = Math.max(s.getUTCFullYear(), e.getUTCFullYear())
      const dur = Math.max(1, b - a + 1)

      const lo = Math.max(a, minYear)
      const hi = Math.min(b, maxYear)
      for (let y = lo; y <= hi; y += 1) {
        const i = y - minYear
        res[i].count += 1
        totalDur[i] += dur
      }
    }

    for (let i = 0; i < res.length; i += 1) {
      res[i].avgDur = res[i].count > 0 ? totalDur[i] / res[i].count : 0
    }

    return res
  }, [spans, years, minYear, maxYear])

  const maxCount = useMemo(() => Math.max(1, ...series.map(s => s.count)), [series])

  const overallAvg = useMemo(() => {
    let sum = 0
    let n = 0
    for (const p of series) {
      if (p.year < value[0] || p.year > value[1]) continue
      if (p.count <= 0) continue
      sum += p.avgDur
      n += 1
    }
    return n > 0 ? sum / n : 0
  }, [series, value])

  const margin = { top: 12, right: 10, bottom: 18, left: 10 }
  const innerW = Math.max(50, width - margin.left - margin.right)
  const h = 128
  const innerH = h - margin.top - margin.bottom

  const x = (year: number) =>
    margin.left + ((year - minYear) / Math.max(1, maxYear - minYear)) * innerW
  const y = (count: number) => margin.top + (1 - count / maxCount) * innerH

  const points = series.map(p => `${x(p.year)},${y(p.count)}`).join(" ")

  const hotColor = [255, 140, 95]
  const coldColor = [96, 154, 255]

  const colorForYear = (p: (typeof series)[number]) => {
    if (p.count <= 0 || overallAvg <= 0) return "rgba(120,130,160,0.2)"
    const tRaw = Math.max(-1, Math.min(1, (p.avgDur - overallAvg) / overallAvg))
    const t = Math.abs(tRaw)
    const base = tRaw <= 0 ? hotColor : coldColor
    const alpha = 0.2 + 0.55 * t
    return `rgba(${base[0]},${base[1]},${base[2]},${alpha})`
  }

  const toYear = useCallback(
    (clientX: number) => {
      const rect = rootRef.current?.getBoundingClientRect()
      if (!rect) return value[0]
      const clamped = Math.max(
        margin.left,
        Math.min(rect.width - margin.right, clientX - rect.left)
      )
      const f = (clamped - margin.left) / Math.max(1, innerW)
      return Math.round(minYear + f * (maxYear - minYear))
    },
    [innerW, margin.left, margin.right, maxYear, minYear, value]
  )

  useEffect(() => {
    const onMove = (ev: MouseEvent) => {
      if (!dragging) return
      const yv = toYear(ev.clientX)
      if (dragging === "min") {
        onChange([Math.min(yv, value[1] - 1), value[1]])
      } else {
        onChange([value[0], Math.max(yv, value[0] + 1)])
      }
    }
    const onUp = () => setDragging(null)
    window.addEventListener("mousemove", onMove)
    window.addEventListener("mouseup", onUp)
    return () => {
      window.removeEventListener("mousemove", onMove)
      window.removeEventListener("mouseup", onUp)
    }
  }, [dragging, onChange, toYear, value])

  return (
    <div
      ref={rootRef}
      className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/75 p-2"
    >
      <div className="mb-1 flex items-center justify-between text-xs text-[color:var(--muted)]">
        <span>Graph interval slider (coverage + heat)</span>
        <span>
          {value[0]} - {value[1]}
        </span>
      </div>
      <svg width={width} height={h} role="img" aria-label="graph interval slider">
        <rect x={0} y={0} width={width} height={h} fill="transparent" />

        <polyline points={points} fill="none" stroke="rgba(230,230,250,0.92)" strokeWidth={1.5} />

        {series.map(p => {
          const xx = x(p.year)
          const yy = y(p.count)
          return (
            <line
              key={p.year}
              x1={xx}
              y1={h - margin.bottom}
              x2={xx}
              y2={yy}
              stroke={colorForYear(p)}
              strokeWidth={1.6}
            />
          )
        })}

        <rect
          x={margin.left}
          y={margin.top}
          width={Math.max(0, x(value[0]) - margin.left)}
          height={innerH}
          fill="rgba(8,8,16,0.45)"
        />
        <rect
          x={x(value[1])}
          y={margin.top}
          width={Math.max(0, margin.left + innerW - x(value[1]))}
          height={innerH}
          fill="rgba(8,8,16,0.45)"
        />

        <line
          x1={x(value[0])}
          x2={x(value[0])}
          y1={margin.top}
          y2={h - margin.bottom}
          stroke="#e6e6fa"
          strokeWidth={2.5}
        />
        <line
          x1={x(value[1])}
          x2={x(value[1])}
          y1={margin.top}
          y2={h - margin.bottom}
          stroke="#e6e6fa"
          strokeWidth={2.5}
        />

        <circle
          cx={x(value[0])}
          cy={h - margin.bottom}
          r={7}
          fill="#a490c2"
          onMouseDown={() => setDragging("min")}
          onKeyDown={ev => {
            if (ev.key === "ArrowLeft") onChange([Math.max(minYear, value[0] - 1), value[1]])
            if (ev.key === "ArrowRight") onChange([Math.min(value[1] - 1, value[0] + 1), value[1]])
          }}
          role="slider"
          aria-label="Minimum year handle"
          aria-valuemin={minYear}
          aria-valuemax={value[1] - 1}
          aria-valuenow={value[0]}
          tabIndex={0}
          style={{ cursor: "ew-resize" }}
        />
        <circle
          cx={x(value[1])}
          cy={h - margin.bottom}
          r={7}
          fill="#a490c2"
          onMouseDown={() => setDragging("max")}
          onKeyDown={ev => {
            if (ev.key === "ArrowLeft") onChange([value[0], Math.max(value[0] + 1, value[1] - 1)])
            if (ev.key === "ArrowRight") onChange([value[0], Math.min(maxYear, value[1] + 1)])
          }}
          role="slider"
          aria-label="Maximum year handle"
          aria-valuemin={value[0] + 1}
          aria-valuemax={maxYear}
          aria-valuenow={value[1]}
          tabIndex={0}
          style={{ cursor: "ew-resize" }}
        />
      </svg>
    </div>
  )
}

```

`components/StackedBarTimeline.test.tsx`:

```tsx
import { render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { Dataset } from "../types"
import StackedBarTimeline from "./StackedBarTimeline"

// Create minimal mock dataset for testing
function createMockDataset(): Dataset {
  return {
    meta: {
      schema_version: "1.0",
      generated_at_iso: new Date().toISOString(),
      source_db: "test",
    },
    podcasts: [
      { id: 1, title: "Test Podcast 1", link: "https://example.com", language: "en" },
      { id: 2, title: "Test Podcast 2", link: "https://example.com", language: "en" },
    ],
    episodes: [
      {
        id: 1,
        podcast_id: 1,
        title: "Episode 1",
        pub_date_iso: "2024-01-01T00:00:00Z",
        page_url: "https://example.com/ep1",
        audio_url: "https://example.com/ep1.mp3",
        kind: "interview",
        narrator: "John Doe",
        description_pure: "Test episode",
        best_span_id: 1,
        best_place_id: 1,
      },
      {
        id: 2,
        podcast_id: 2,
        title: "Episode 2",
        pub_date_iso: "2024-02-01T00:00:00Z",
        page_url: "https://example.com/ep2",
        audio_url: "https://example.com/ep2.mp3",
        kind: "interview",
        narrator: "Jane Doe",
        description_pure: "Test episode 2",
        best_span_id: 2,
        best_place_id: 2,
      },
    ],
    spans: [
      {
        id: 1,
        episode_id: 1,
        start_iso: "2024-01-01T00:00:00Z",
        end_iso: "2024-01-02T00:00:00Z",
        precision: "day",
        qualifier: "approximate",
        score: 0.9,
        source_section: "intro",
        source_text: "Test span 1",
      },
      {
        id: 2,
        episode_id: 2,
        start_iso: "2024-02-01T00:00:00Z",
        end_iso: "2024-02-02T00:00:00Z",
        precision: "day",
        qualifier: "approximate",
        score: 0.8,
        source_section: "intro",
        source_text: "Test span 2",
      },
    ],
    places: [
      {
        id: 1,
        episode_id: 1,
        canonical_name: "New York",
        norm_key: "new_york",
        place_kind: "city",
        lat: 40.7128,
        lon: -74.006,
        radius_km: 10,
      },
      {
        id: 2,
        episode_id: 2,
        canonical_name: "London",
        norm_key: "london",
        place_kind: "city",
        lat: 51.5074,
        lon: -0.1278,
        radius_km: 10,
      },
    ],
    entities: [],
    episode_keywords: {},
    episode_clusters: {},
    clusters: [],
  }
}

describe("StackedBarTimeline", () => {
  it("should render an SVG element", () => {
    const mockDataset = createMockDataset()
    const mockEpisodes = mockDataset.episodes

    render(
      <StackedBarTimeline
        dataset={mockDataset}
        episodes={mockEpisodes}
        selectedEpisodeId={null}
        onSelectEpisode={() => {}}
        onScrubYear={() => {}}
      />
    )

    // Check that an SVG element is rendered
    const svg = document.querySelector("svg")
    expect(svg).toBeTruthy()
  })
})

```

`components/StackedBarTimeline.tsx`:

```tsx
import { axisBottom, axisLeft, select } from "d3"
import { useEffect, useMemo, useRef, useState } from "react"
import type { Dataset } from "../types"
import { createScales, type Scales } from "../utils/timelineScales"
import type { D3StackData } from "../utils/timelineTransform"
import { transformToStackData } from "../utils/timelineTransform"

type Episode = Dataset["episodes"][number]

export interface StackedBarTimelineProps {
  dataset: Dataset
  episodes: Episode[]
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
  scrubYear?: number
  onScrubYear: (y?: number) => void
  visibleYearRange?: [number, number]
  axisDensityK?: number
}

const MARGIN = { top: 20, right: 20, bottom: 40, left: 60 }

export default function StackedBarTimeline(props: StackedBarTimelineProps): JSX.Element {
  const {
    dataset,
    episodes,
    selectedEpisodeId,
    onSelectEpisode,
    scrubYear,
    visibleYearRange,
    axisDensityK = 1,
  } = props

  const svgRef = useRef<SVGSVGElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 })

  // Hover state for episode detail card
  const [hoverData, setHoverData] = useState<{
    x: number
    y: number
    episodeId: number
    episodeTitle: string
    spanStart: Date
    spanEnd: Date
    score: number
    sourceText: string
    clusterId?: number
  } | null>(null)

  // Transform data to D3 stack format
  const stackData: D3StackData[] = useMemo(() => {
    const episodeIds = episodes.map(ep => ep.id)
    return transformToStackData(dataset, episodeIds)
  }, [dataset, episodes])

  // Create a lookup map for episode titles
  const episodeTitleMap = useMemo(() => {
    const map = new Map<number, string>()
    for (const podcast of stackData) {
      for (const episode of podcast.episodes) {
        map.set(episode.episodeId, episode.title)
      }
    }
    return map
  }, [stackData])

  // Create scales
  const scales: Scales = useMemo(() => {
    return createScales(stackData, dimensions.width, dimensions.height, MARGIN, visibleYearRange)
  }, [stackData, dimensions, visibleYearRange])

  // Handle resize with ResizeObserver
  useEffect(() => {
    const svgElement = svgRef.current
    if (!svgElement) return

    const resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        setDimensions({ width, height })
      }
    })

    resizeObserver.observe(svgElement)

    return () => {
      resizeObserver.disconnect()
    }
  }, [])

  // D3 rendering
  useEffect(() => {
    const svgElement = svgRef.current
    if (!svgElement) return

    // Handle empty data
    if (stackData.length === 0) {
      select(svgElement).selectAll("*").remove()
      return
    }

    const { xScale, yScale } = scales
    const minBarWidth = 1

    // Helper function to calculate opacity based on scrub year
    function opacityByYear(spanStart: Date, spanEnd: Date, scrubYear?: number): number {
      if (scrubYear == null || Number.isNaN(scrubYear)) return 0.85
      const mid = spanStart.getTime() + (spanEnd.getTime() - spanStart.getTime()) / 2
      const midYear = new Date(mid).getUTCFullYear()
      const d = Math.abs(midYear - scrubYear)
      const sigma = 40
      const w = Math.exp(-(d * d) / (2 * sigma * sigma))
      return 0.15 + 0.85 * w
    }

    function spanRectX(start: Date, end: Date): number {
      const a = xScale(start)
      const b = xScale(end)
      return Math.min(a, b)
    }

    function spanRectWidth(start: Date, end: Date): number {
      const a = xScale(start)
      const b = xScale(end)
      const w = Math.abs(b - a)
      if (!Number.isFinite(w)) return minBarWidth
      return Math.max(minBarWidth, w)
    }

    const contentWidth = Math.max(120, dimensions.width - MARGIN.left - MARGIN.right)
    const domainMinYear = visibleYearRange?.[0] ?? xScale.domain()[0].getUTCFullYear()
    const domainMaxYear = visibleYearRange?.[1] ?? xScale.domain()[1].getUTCFullYear()
    const yearsSpan = Math.max(1, domainMaxYear - domainMinYear)
    const targetTicks = Math.max(2, Math.floor(contentWidth / Math.max(45, 80 * axisDensityK)))
    const rawStep = yearsSpan / targetTicks
    const base = 10 ** Math.floor(Math.log10(Math.max(rawStep, 1)))
    const candidates = [1, 2, 5].map(v => v * base)
    const step = candidates.find(c => c >= rawStep) ?? 10 * base

    const axisYears: number[] = []
    const first = Math.ceil(domainMinYear / step) * step
    for (let y = first; y <= domainMaxYear; y += step) axisYears.push(y)
    if (!axisYears.includes(domainMinYear)) axisYears.unshift(domainMinYear)
    if (!axisYears.includes(domainMaxYear)) axisYears.push(domainMaxYear)

    const axisTickDates = axisYears.map(y => new Date(Date.UTC(y, 0, 1)))

    // Clear previous content
    select(svgElement).selectAll("*").remove()

    // Create main SVG with proper dimensions
    const svg = select(svgElement).attr("width", dimensions.width).attr("height", dimensions.height)

    // Create main group with margin transform
    const mainGroup = svg.append("g").attr("transform", `translate(${MARGIN.left}, ${MARGIN.top})`)

    // Create podcast groups using D3 data binding
    const podcastGroups = mainGroup
      .selectAll<SVGGElement, D3StackData>(".podcast-group")
      .data(stackData)
      .join("g")
      .attr("class", "podcast-group")
      .attr("transform", d => `translate(0, ${yScale(d.podcastTitle) ?? 0})`)

    // For each podcast group, render span rects
    podcastGroups.each(function (podcastData) {
      const podcastGroup = select(this)

      // Collect all spans from all episodes
      const allSpans: Array<{
        span: D3StackData["episodes"][number]["spans"][number]
        episodeId: number
      }> = []

      for (const episode of podcastData.episodes) {
        for (const span of episode.spans) {
          allSpans.push({ span, episodeId: episode.episodeId })
        }
      }

      // Sort spans by start time
      allSpans.sort((a, b) => a.span.start.getTime() - b.span.start.getTime())

      // Create unique colors per episode using HSL
      const episodeColors = new Map<number, string>()
      for (const episode of podcastData.episodes) {
        const hue = (episode.episodeId * 47) % 360
        episodeColors.set(episode.episodeId, `hsl(${hue}, 70%, 55%)`)
      }

      // Render span rects using D3 data binding with enter/update/exit pattern
      podcastGroup
        .selectAll<SVGRectElement, (typeof allSpans)[number]>("rect.span-rect")
        .data(allSpans)
        .join(
          enter =>
            enter
              .append("rect")
              .attr("class", "span-rect")
              .attr("x", d => spanRectX(d.span.start, d.span.end))
              .attr("width", d => spanRectWidth(d.span.start, d.span.end))
              .attr("y", 0)
              .attr("height", yScale.bandwidth())
              .attr("fill", d => episodeColors.get(d.episodeId) ?? "#ccc")
              .attr("stroke", "white")
              .attr("stroke-width", d => (d.episodeId === selectedEpisodeId ? 3 : 1))
              .attr("rx", 2)
              .attr("cursor", "pointer")
              .attr("opacity", d => opacityByYear(d.span.start, d.span.end, scrubYear))
              .on("click", (_event, d) => onSelectEpisode(d.episodeId))
              .on("mouseover", (event, d) => {
                const episodeTitle = episodeTitleMap.get(d.episodeId) ?? `Episode ${d.episodeId}`
                setHoverData({
                  x: event.clientX,
                  y: event.clientY,
                  episodeId: d.episodeId,
                  episodeTitle,
                  spanStart: d.span.start,
                  spanEnd: d.span.end,
                  score: d.span.score,
                  sourceText: d.span.sourceText,
                  clusterId: d.span.clusterId,
                })
              })
              .on("mouseout", () => {
                setHoverData(null)
              }),
          update =>
            update
              .attr("x", d => spanRectX(d.span.start, d.span.end))
              .attr("width", d => spanRectWidth(d.span.start, d.span.end))
              .attr("y", 0)
              .attr("height", yScale.bandwidth())
              .attr("stroke-width", d => (d.episodeId === selectedEpisodeId ? 3 : 1))
              .transition()
              .duration(150)
              .attr("opacity", d => opacityByYear(d.span.start, d.span.end, scrubYear)),
          exit => exit.transition().duration(150).attr("opacity", 0).remove()
        )
    })

    // Add x-axis
    const xAxisGroup = mainGroup
      .append("g")
      .attr("class", "x-axis")
      .attr("transform", `translate(0, ${dimensions.height - MARGIN.top - MARGIN.bottom})`)

    const xAxis = axisBottom(xScale)
      .tickValues(axisTickDates)
      .tickFormat(d => {
        const date = d as Date
        const y = date.getUTCFullYear()
        return y < 0 ? `${Math.abs(y)} BCE` : `${y}`
      })

    xAxisGroup.call(xAxis)

    // Style x-axis
    xAxisGroup.selectAll(".domain, .tick line").attr("stroke", "rgba(230, 230, 250, 0.35)")
    xAxisGroup
      .selectAll(".tick text")
      .attr("fill", "rgba(230, 230, 250, 0.9)")
      .attr("font-size", "12px")

    // Add y-axis
    const yAxisGroup = mainGroup.append("g").attr("class", "y-axis")

    const yAxis = axisLeft(yScale)

    yAxisGroup.call(yAxis)

    // Style y-axis
    yAxisGroup.selectAll(".domain, .tick line").attr("stroke", "rgba(230, 230, 250, 0.35)")
    yAxisGroup
      .selectAll(".tick text")
      .attr("fill", "rgba(230, 230, 250, 0.9)")
      .attr("font-size", "12px")
  }, [
    stackData,
    scales,
    dimensions,
    onSelectEpisode,
    episodeTitleMap,
    scrubYear,
    selectedEpisodeId,
    visibleYearRange,
    axisDensityK,
  ])

  return (
    <>
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        style={{ display: "block", overflow: "visible", background: "transparent" }}
        data-testid="stacked-bar-timeline"
      />
      {hoverData && (
        <div
          style={{
            position: "fixed",
            left: hoverData.x + 14,
            top: hoverData.y + 14,
            maxWidth: 380,
            background: "rgba(25, 20, 44, 0.96)",
            border: "1px solid rgba(164, 144, 194, 0.35)",
            borderRadius: 10,
            padding: 10,
            boxShadow: "0 14px 36px rgba(0,0,0,0.45)",
            zIndex: 9999,
            pointerEvents: "none",
            color: "#e6e6fa",
          }}
        >
          <div style={{ fontWeight: 700 }}>{hoverData.episodeTitle}</div>
          <div style={{ fontSize: 12, color: "#c8bbdc", marginTop: 4 }}>
            span: {hoverData.spanStart.getFullYear()}–{hoverData.spanEnd.getFullYear()}
          </div>
          {hoverData.clusterId != null && (
            <div style={{ fontSize: 12, color: "#c8bbdc", marginTop: 4 }}>
              cluster: <b>#{hoverData.clusterId}</b>
            </div>
          )}
          <div style={{ fontSize: 12, marginTop: 8, color: "#c8bbdc" }}>
            score: {hoverData.score.toFixed(2)}
          </div>
          <div style={{ fontSize: 12, marginTop: 4 }}>{hoverData.sourceText}</div>
          <div style={{ fontSize: 11, marginTop: 8, color: "#a490c2" }}>
            click to open details →
          </div>
        </div>
      )}
    </>
  )
}

```

`components/Timeline.tsx`:

```tsx
import Plotly from "plotly.js-dist-min"
import { useEffect, useMemo, useRef, useState } from "react"
import type { Dataset } from "../types"

type Ep = Dataset["episodes"][number]
type TimelinePoint = {
  episodeId: number
  title: string
  pubDate: string
  rank: number
  midYear: number
  score: number
  snippet: string
  clusterId?: number
}
type PlotlyEventPoint = { customdata?: TimelinePoint }
type PlotlyHoverEvent = { points?: PlotlyEventPoint[]; event: { clientX: number; clientY: number } }
type PlotlyDiv = HTMLDivElement & {
  on: (event: string, handler: (ev: unknown) => void) => void
  removeAllListeners: (event: string) => void
}

function midYear(span: { start_iso?: string; end_iso?: string }): number | null {
  if (!span.start_iso || !span.end_iso) return null
  const s = new Date(span.start_iso)
  const e = new Date(span.end_iso)
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return null
  const mid = new Date((s.getTime() + e.getTime()) / 2)
  return mid.getUTCFullYear() + mid.getUTCMonth() / 12
}

function colorForCluster(clusterId: number): string {
  // deterministic HSL palette
  const h = (clusterId * 47) % 360
  return `hsl(${h},65%,45%)`
}

function opacityByYear(mid: number, scrubYear?: number): number {
  if (scrubYear == null || Number.isNaN(scrubYear)) return 0.85
  const d = Math.abs(mid - scrubYear)
  // gaussian-ish falloff, sigma ~ 40 years
  const sigma = 40
  const w = Math.exp(-(d * d) / (2 * sigma * sigma))
  return 0.15 + 0.85 * w
}

export default function Timeline(props: {
  dataset: Dataset
  episodes: Ep[]
  topN: number
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
  scrubYear?: number
  onScrubYear: (y?: number) => void
  visibleYearRange?: [number, number]
}) {
  const plotRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<HTMLDivElement | null>(null)

  const [playing, setPlaying] = useState(false)

  const [hoverCard, setHoverCard] = useState<{
    x: number
    y: number
    episodeId: number
    spanRank: number
    score: number
    snippet: string
    clusterId?: number
  } | null>(null)

  const spansByEpisode = useMemo(() => {
    const m = new Map<number, Dataset["spans"]>()
    for (const sp of props.dataset.spans) {
      const arr = m.get(sp.episode_id) ?? []
      arr.push(sp)
      m.set(sp.episode_id, arr)
    }
    for (const [k, arr] of m) {
      arr.sort((a, b) => b.score - a.score)
      m.set(k, arr)
    }
    return m
  }, [props.dataset.spans])

  const placeByEpisode = useMemo(() => {
    const m = new Map<number, { lat: number; lon: number; name: string; kind: string }>()
    for (const p of props.dataset.places) {
      if (p.lat == null || p.lon == null) continue
      if (!m.has(p.episode_id))
        m.set(p.episode_id, { lat: p.lat, lon: p.lon, name: p.canonical_name, kind: p.place_kind })
    }
    return m
  }, [props.dataset.places])

  const episodeCluster = props.dataset.episode_clusters

  const timelinePoints = useMemo(() => {
    const pts: TimelinePoint[] = []

    for (const e of props.episodes) {
      const spans = spansByEpisode.get(e.id) ?? []
      const cid = episodeCluster[String(e.id)]
      for (let i = 0; i < Math.min(props.topN, spans.length); i++) {
        const sp = spans[i]
        const my = midYear(sp)
        if (my == null) continue
        if (
          props.visibleYearRange &&
          (my < props.visibleYearRange[0] || my > props.visibleYearRange[1])
        ) {
          continue
        }
        pts.push({
          episodeId: e.id,
          title: e.title,
          pubDate: e.pub_date_iso,
          rank: i + 1,
          midYear: my,
          score: sp.score,
          snippet: sp.source_text,
          clusterId: cid,
        })
      }
    }
    return pts
  }, [props.episodes, spansByEpisode, props.topN, episodeCluster, props.visibleYearRange])

  // drive animation
  useEffect(() => {
    if (!playing) return

    const points = timelinePoints.map(p => p.midYear)
    if (points.length === 0) return

    const minY = Math.floor(Math.min(...points))
    const maxY = Math.ceil(Math.max(...points))

    let y = props.scrubYear ?? minY
    const id = window.setInterval(() => {
      y += 1
      if (y > maxY) y = minY
      props.onScrubYear(y)
    }, 120)

    return () => window.clearInterval(id)
  }, [playing, timelinePoints, props.scrubYear, props.onScrubYear])

  // timeline plot
  useEffect(() => {
    if (!plotRef.current) return
    const el = plotRef.current

    const ranks = [...new Set(timelinePoints.map(p => p.rank))].sort((a, b) => a - b)
    const traces = ranks.map(r => {
      const pts = timelinePoints.filter(p => p.rank === r)
      const opacityBase = r === 1 ? 1.0 : Math.max(0.15, 1 - (r - 1) * 0.18)

      const colors = pts.map(p => (p.clusterId ? colorForCluster(p.clusterId) : "#888"))
      const opacities = pts.map(p => opacityByYear(p.midYear, props.scrubYear) * opacityBase)

      return {
        type: "scatter" as const,
        mode: "markers" as const,
        name: `rank ${r}`,
        x: pts.map(p => p.midYear),
        y: pts.map(() => r),
        text: pts.map(p => p.title),
        customdata: pts,
        marker: {
          size: r === 1 ? 9 : 7,
          color: colors,
          opacity: opacities,
          line: { width: 0 },
        },
        hoverinfo: "none" as const,
      }
    })

    Plotly.newPlot(
      el,
      traces as unknown as object[],
      {
        title: "Historical time mentions (top-N per episode) — colored by cluster",
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#e6e6fa" },
        xaxis: { title: "mid-year" },
        yaxis: { title: "rank", tickmode: "array", tickvals: ranks },
        margin: { l: 50, r: 10, t: 40, b: 40 },
        showlegend: true,
      },
      { displayModeBar: true, responsive: true }
    )

    const onHover = (ev: unknown) => {
      const hover = ev as PlotlyHoverEvent
      const cd = hover.points?.[0]?.customdata
      if (!cd) return
      setHoverCard({
        x: hover.event.clientX,
        y: hover.event.clientY,
        episodeId: cd.episodeId,
        spanRank: cd.rank,
        score: cd.score,
        snippet: cd.snippet,
        clusterId: cd.clusterId,
      })
    }
    const onUnhover = () => setHoverCard(null)
    const onClick = (ev: unknown) => {
      const click = ev as PlotlyHoverEvent
      const cd = click.points?.[0]?.customdata
      if (cd?.episodeId) props.onSelectEpisode(cd.episodeId)
    }

    const plotEl = el as PlotlyDiv
    plotEl.on("plotly_hover", onHover)
    plotEl.on("plotly_unhover", onUnhover)
    plotEl.on("plotly_click", onClick)

    return () => {
      try {
        plotEl.removeAllListeners("plotly_hover")
        plotEl.removeAllListeners("plotly_unhover")
        plotEl.removeAllListeners("plotly_click")
      } catch {
        // ignore
      }
    }
  }, [timelinePoints, props.scrubYear, props.onSelectEpisode])

  // map plot (colored by cluster)
  useEffect(() => {
    if (!mapRef.current) return
    const el = mapRef.current

    const pts = props.episodes
      .map(e => {
        const p = placeByEpisode.get(e.id)
        if (!p) return null
        const cid = episodeCluster[String(e.id)]
        return {
          episodeId: e.id,
          title: e.title,
          lat: p.lat,
          lon: p.lon,
          place: p.name,
          clusterId: cid,
        }
      })
      .filter(Boolean) as {
      episodeId: number
      title: string
      lat: number
      lon: number
      place: string
      clusterId?: number
    }[]

    const colors = pts.map(p => (p.clusterId ? colorForCluster(p.clusterId) : "#888"))
    const opacities = pts.map(p => {
      // approximate mid-year using best span if available
      const spans = spansByEpisode.get(p.episodeId) ?? []
      const my = spans.length ? midYear(spans[0]) : null
      return my == null ? 0.65 : opacityByYear(my, props.scrubYear)
    })

    Plotly.newPlot(
      el,
      [
        {
          type: "scattergeo",
          mode: "markers",
          lat: pts.map(p => p.lat),
          lon: pts.map(p => p.lon),
          text: pts.map(p => p.title),
          customdata: pts,
          marker: { size: 7, color: colors, opacity: opacities },
          hoverinfo: "none",
        },
      ] as unknown as object[],
      {
        title: "Places (offline gazetteer matches) — colored by cluster",
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#e6e6fa" },
        geo: { scope: "world" },
        margin: { l: 10, r: 10, t: 40, b: 10 },
      },
      { displayModeBar: true, responsive: true }
    )

    const onHover = (ev: unknown) => {
      const hover = ev as PlotlyHoverEvent
      const cd = hover.points?.[0]?.customdata
      if (!cd) return
      setHoverCard({
        x: hover.event.clientX,
        y: hover.event.clientY,
        episodeId: cd.episodeId,
        spanRank: 0,
        score: 0,
        snippet: `place: ${cd.place}`,
        clusterId: cd.clusterId,
      })
    }
    const onUnhover = () => setHoverCard(null)
    const onClick = (ev: unknown) => {
      const click = ev as PlotlyHoverEvent
      const cd = click.points?.[0]?.customdata
      if (cd?.episodeId) props.onSelectEpisode(cd.episodeId)
    }

    const plotEl = el as PlotlyDiv
    plotEl.on("plotly_hover", onHover)
    plotEl.on("plotly_unhover", onUnhover)
    plotEl.on("plotly_click", onClick)

    return () => {
      try {
        plotEl.removeAllListeners("plotly_hover")
        plotEl.removeAllListeners("plotly_unhover")
        plotEl.removeAllListeners("plotly_click")
      } catch {
        // ignore
      }
    }
  }, [
    props.episodes,
    placeByEpisode,
    props.scrubYear,
    episodeCluster,
    spansByEpisode,
    props.onSelectEpisode,
  ])

  const episodeById = useMemo(() => {
    const m = new Map<number, Ep>()
    for (const e of props.dataset.episodes) m.set(e.id, e)
    return m
  }, [props.dataset.episodes])

  const hoverEpisode = hoverCard ? episodeById.get(hoverCard.episodeId) : null

  return (
    <div
      style={{
        height: "100%",
        display: "grid",
        gridTemplateRows: "auto 1fr 1fr",
        gap: 10,
        position: "relative",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button type="button" onClick={() => setPlaying(p => !p)}>
          {playing ? "pause" : "play"}
        </button>
        <div style={{ fontSize: 12, color: "#555" }}>
          time animation: {props.scrubYear ?? "(disabled)"}
        </div>
        <input
          type="range"
          min={-500}
          max={2026}
          value={props.scrubYear ?? 0}
          onChange={e => props.onScrubYear(Number(e.target.value))}
          style={{ width: 260 }}
        />
        <button type="button" onClick={() => props.onScrubYear(undefined)}>
          clear
        </button>
        <div style={{ marginLeft: "auto", fontSize: 12, color: "#555" }}>
          hover fades by year; clusters color points
        </div>
      </div>

      <div ref={plotRef} style={{ width: "100%", height: "100%" }} />
      <div ref={mapRef} style={{ width: "100%", height: "100%" }} />

      {hoverCard && hoverEpisode && (
        <div
          style={{
            position: "fixed",
            left: hoverCard.x + 14,
            top: hoverCard.y + 14,
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
          <div style={{ fontWeight: 700 }}>{hoverEpisode.title}</div>
          <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>
            pub: {new Date(hoverEpisode.pub_date_iso).toLocaleDateString()} · kind:{" "}
            {hoverEpisode.kind ?? "?"} · narrator: {hoverEpisode.narrator ?? "?"}
          </div>
          {hoverCard.clusterId != null && (
            <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>
              cluster: <b>#{hoverCard.clusterId}</b>
            </div>
          )}
          <div style={{ fontSize: 12, marginTop: 8 }}>
            {hoverCard.spanRank > 0 ? (
              <>
                <div style={{ color: "#555" }}>
                  span rank {hoverCard.spanRank} · score {hoverCard.score.toFixed(2)}
                </div>
                <div>{hoverCard.snippet}</div>
              </>
            ) : (
              <div>{hoverCard.snippet}</div>
            )}
          </div>
          <div style={{ fontSize: 12, color: "#555", marginTop: 8 }}>click to open details →</div>
        </div>
      )}
    </div>
  )
}

```

`index.css`:

```css
@import "tailwindcss";

@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap");

:root {
  --bg-0: #120f1d;
  --bg-1: #1c1830;
  --bg-2: #2b1e3e;
  --surface: #241c38;
  --surface-2: #302548;
  --text: #e6e6fa;
  --muted: #c8bbdc;
  --accent: #a490c2;
  --accent-2: #4a4e8f;
  --border: rgba(164, 144, 194, 0.28);
}

html,
body,
#root {
  height: 100%;
}

body {
  margin: 0;
  color: var(--text);
  font-family: "IBM Plex Sans", "Space Grotesk", "Segoe UI", sans-serif;
  background:
    radial-gradient(1200px 700px at 8% -10%, rgba(74, 78, 143, 0.35), transparent 48%),
    radial-gradient(1000px 700px at 100% 0%, rgba(164, 144, 194, 0.25), transparent 45%),
    linear-gradient(160deg, var(--bg-0), var(--bg-1) 52%, var(--bg-2));
}

h1,
h2,
h3,
h4 {
  font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
  letter-spacing: 0.01em;
}

input,
select,
button,
textarea {
  color: var(--text);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.45rem 0.6rem;
}

button:hover {
  border-color: rgba(164, 144, 194, 0.65);
  background: #3a2e56;
}

input:focus,
select:focus,
button:focus,
textarea:focus {
  outline: 2px solid rgba(164, 144, 194, 0.55);
  outline-offset: 1px;
}

```

`main.tsx`:

```tsx
import React from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import "./index.css"

const root = document.getElementById("root")
if (!root) {
  throw new Error("Missing root element")
}

createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

```

`test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest"

if (!("ResizeObserver" in globalThis)) {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // @ts-expect-error test-only shim
  globalThis.ResizeObserver = ResizeObserverMock
}

```

`types.ts`:

```ts
export type PlaceKind = "city" | "region" | "country" | "unknown"
export type EntityKind = "person" | "org" | "event" | "place" | "unknown"

export interface Dataset {
  meta: { schema_version: string; generated_at_iso: string; source_db: string }
  podcasts: { id: number; title: string; link?: string; language?: string }[]
  episodes: {
    id: number
    podcast_id: number
    title: string
    pub_date_iso: string
    page_url?: string
    audio_url?: string
    kind?: string
    narrator?: string
    description_pure?: string
    best_span_id?: number
    best_place_id?: number
  }[]
  spans: {
    id: number
    episode_id: number
    start_iso?: string
    end_iso?: string
    precision: string
    qualifier: string
    score: number
    source_section: string
    source_text: string
  }[]
  places: {
    id: number
    episode_id: number
    canonical_name: string
    norm_key: string
    place_kind: PlaceKind
    lat?: number
    lon?: number
    radius_km?: number
  }[]
  entities: {
    id: number
    episode_id: number
    name: string
    kind: EntityKind
    confidence: number
  }[]
  episode_keywords: Record<string, { phrase: string; score: number }[]>
  episode_clusters: Record<string, number>
  clusters: {
    cluster: {
      id: number
      podcast_id: number
      k: number
      label: string
      centroid_mid_year: number
      centroid_lat: number
      centroid_lon: number
      n_members: number
    }
    top_keywords: { phrase: string; score: number }[]
    top_entities: { name: string; kind: EntityKind; count: number }[]
  }[]
}

```

`urlState.ts`:

```ts
export type Filters = {
  podcastId: number | "all"
  q: string
  kind: string | "all"
  narrator: string
  clusterId?: number
  topN: number
  year?: number
  yearMin?: number
  yearMax?: number
  axisK: number
}

const num = (v: string | null) => (v == null || v.trim() === "" ? undefined : Number(v))
const parseKind = (value: string | null): Filters["kind"] => {
  if (
    value === "all" ||
    value === "regular" ||
    value === "book" ||
    value === "meta" ||
    value === "special"
  ) {
    return value
  }
  return "all"
}

export function readFiltersFromUrl(): Filters {
  const u = new URL(window.location.href)
  const p = u.searchParams
  const podcastRaw = p.get("podcast") ?? "all"
  const podcastId = podcastRaw === "all" ? "all" : Number(podcastRaw)

  return {
    podcastId,
    q: p.get("q") ?? "",
    kind: parseKind(p.get("kind")),
    narrator: p.get("narrator") ?? "",
    clusterId: num(p.get("cluster")),
    topN: Math.max(1, Math.min(6, Number(p.get("topN") ?? "1"))),
    year: num(p.get("year")),
    yearMin: num(p.get("yearMin")),
    yearMax: num(p.get("yearMax")),
    axisK: Math.max(0.3, Math.min(3, Number(p.get("axisK") ?? "1"))),
  }
}

export function writeFiltersToUrl(f: Filters) {
  const u = new URL(window.location.href)
  const p = u.searchParams

  p.set("podcast", String(f.podcastId))

  if (f.q) p.set("q", f.q)
  else p.delete("q")

  if (f.kind !== "all") p.set("kind", f.kind)
  else p.delete("kind")

  if (f.narrator) p.set("narrator", f.narrator)
  else p.delete("narrator")

  if (f.clusterId != null && !Number.isNaN(f.clusterId)) p.set("cluster", String(f.clusterId))
  else p.delete("cluster")

  p.set("topN", String(f.topN))

  if (f.year != null && !Number.isNaN(f.year)) p.set("year", String(f.year))
  else p.delete("year")

  if (f.yearMin != null && !Number.isNaN(f.yearMin)) p.set("yearMin", String(f.yearMin))
  else p.delete("yearMin")

  if (f.yearMax != null && !Number.isNaN(f.yearMax)) p.set("yearMax", String(f.yearMax))
  else p.delete("yearMax")

  p.set("axisK", String(f.axisK))

  window.history.replaceState({}, "", u.toString())
}

```

`utils/timelineScales.test.ts`:

```ts
import { describe, expect, it } from "vitest"
import { createPodcastScale, createScales, createTimeScale } from "./timelineScales"
import type { D3StackData } from "./timelineTransform"

describe("timelineScales", () => {
  const createMockData = (): D3StackData[] => [
    {
      podcastId: 1,
      podcastTitle: "History Podcast",
      episodes: [
        {
          episodeId: 1,
          title: "Episode 1",
          pubDate: "2020-01-15T00:00:00Z",
          spans: [
            {
              spanId: 1,
              start: new Date("1800-01-01T00:00:00Z"),
              end: new Date("1850-12-31T00:00:00Z"),
              score: 0.9,
              sourceText: "In the early 19th century...",
            },
            {
              spanId: 2,
              start: new Date("1900-01-01T00:00:00Z"),
              end: new Date("1950-12-31T00:00:00Z"),
              score: 0.8,
              sourceText: "During the 20th century...",
            },
          ],
        },
      ],
    },
    {
      podcastId: 2,
      podcastTitle: "Another Podcast",
      episodes: [
        {
          episodeId: 2,
          title: "Episode 2",
          pubDate: "2020-02-20T00:00:00Z",
          spans: [
            {
              spanId: 3,
              start: new Date("1750-01-01T00:00:00Z"),
              end: new Date("1800-12-31T00:00:00Z"),
              score: 0.95,
              sourceText: "The mid-18th century...",
            },
          ],
        },
      ],
    },
  ]

  describe("createTimeScale", () => {
    it("should create time scale with correct domain from span dates", () => {
      const data = createMockData()
      const width = 800
      const margin = { left: 50, right: 50 }

      const scale = createTimeScale(data, width, margin)

      // Check that the domain covers the earliest start and latest end
      const [minDate, maxDate] = scale.domain()
      expect(minDate.getTime()).toBeLessThanOrEqual(new Date("1750-01-01T00:00:00Z").getTime())
      expect(maxDate.getTime()).toBeGreaterThanOrEqual(new Date("1950-12-31T00:00:00Z").getTime())
    })

    it("should create time scale with correct range accounting for margins", () => {
      const data = createMockData()
      const width = 800
      const margin = { left: 50, right: 50 }

      const scale = createTimeScale(data, width, margin)

      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.left)
      expect(maxRange).toBe(width - margin.right)
    })

    it("should handle empty data by returning default scale", () => {
      const data: D3StackData[] = []
      const width = 800
      const margin = { left: 50, right: 50 }

      const scale = createTimeScale(data, width, margin)

      // Should return a valid scale even with empty data
      expect(scale).toBeDefined()
      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.left)
      expect(maxRange).toBe(width - margin.right)
    })

    it("should handle data with no spans", () => {
      const data: D3StackData[] = [
        {
          podcastId: 1,
          podcastTitle: "Empty Podcast",
          episodes: [
            {
              episodeId: 1,
              title: "Empty Episode",
              pubDate: "2020-01-15T00:00:00Z",
              spans: [],
            },
          ],
        },
      ]
      const width = 800
      const margin = { left: 50, right: 50 }

      const scale = createTimeScale(data, width, margin)

      // Should return a valid scale even with no spans
      expect(scale).toBeDefined()
      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.left)
      expect(maxRange).toBe(width - margin.right)
    })
  })

  describe("createPodcastScale", () => {
    it("should create band scale for podcasts using their titles", () => {
      const data = createMockData()
      const height = 600
      const margin = { top: 50, bottom: 50 }

      const scale = createPodcastScale(data, height, margin)

      // Domain should contain podcast titles
      const domain = scale.domain()
      expect(domain).toContain("History Podcast")
      expect(domain).toContain("Another Podcast")
    })

    it("should create band scale with correct range accounting for margins", () => {
      const data = createMockData()
      const height = 600
      const margin = { top: 50, bottom: 50 }

      const scale = createPodcastScale(data, height, margin)

      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.top)
      expect(maxRange).toBe(height - margin.bottom)
    })

    it("should handle single podcast", () => {
      const data: D3StackData[] = [
        {
          podcastId: 1,
          podcastTitle: "Solo Podcast",
          episodes: [
            {
              episodeId: 1,
              title: "Episode 1",
              pubDate: "2020-01-15T00:00:00Z",
              spans: [
                {
                  spanId: 1,
                  start: new Date("1800-01-01T00:00:00Z"),
                  end: new Date("1850-12-31T00:00:00Z"),
                  score: 0.9,
                  sourceText: "Test",
                },
              ],
            },
          ],
        },
      ]
      const height = 600
      const margin = { top: 50, bottom: 50 }

      const scale = createPodcastScale(data, height, margin)

      expect(scale.domain()).toEqual(["Solo Podcast"])
      // Bandwidth should be positive and reasonable
      expect(scale.bandwidth()).toBeGreaterThan(0)
    })

    it("should handle empty data by returning empty domain scale", () => {
      const data: D3StackData[] = []
      const height = 600
      const margin = { top: 50, bottom: 50 }

      const scale = createPodcastScale(data, height, margin)

      expect(scale.domain()).toEqual([])
      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.top)
      expect(maxRange).toBe(height - margin.bottom)
    })
  })

  describe("createScales", () => {
    it("should create both x and y scales with correct configuration", () => {
      const data = createMockData()
      const width = 800
      const height = 600
      const margin = { top: 50, right: 50, bottom: 50, left: 50 }

      const scales = createScales(data, width, height, margin)

      expect(scales.xScale).toBeDefined()
      expect(scales.yScale).toBeDefined()

      // Check xScale range
      const [xMin, xMax] = scales.xScale.range()
      expect(xMin).toBe(margin.left)
      expect(xMax).toBe(width - margin.right)

      // Check yScale range
      const [yMin, yMax] = scales.yScale.range()
      expect(yMin).toBe(margin.top)
      expect(yMax).toBe(height - margin.bottom)
    })

    it("should have xScale domain that covers all span dates", () => {
      const data = createMockData()
      const width = 800
      const height = 600
      const margin = { top: 50, right: 50, bottom: 50, left: 50 }

      const scales = createScales(data, width, height, margin)

      const [minDate, maxDate] = scales.xScale.domain()
      expect(minDate.getTime()).toBeLessThanOrEqual(new Date("1750-01-01T00:00:00Z").getTime())
      expect(maxDate.getTime()).toBeGreaterThanOrEqual(new Date("1950-12-31T00:00:00Z").getTime())
    })

    it("should have yScale domain with all podcast titles", () => {
      const data = createMockData()
      const width = 800
      const height = 600
      const margin = { top: 50, right: 50, bottom: 50, left: 50 }

      const scales = createScales(data, width, height, margin)

      expect(scales.yScale.domain()).toContain("History Podcast")
      expect(scales.yScale.domain()).toContain("Another Podcast")
    })

    it("should handle empty data gracefully", () => {
      const data: D3StackData[] = []
      const width = 800
      const height = 600
      const margin = { top: 50, right: 50, bottom: 50, left: 50 }

      const scales = createScales(data, width, height, margin)

      expect(scales.xScale).toBeDefined()
      expect(scales.yScale).toBeDefined()
      expect(scales.yScale.domain()).toEqual([])
    })
  })
})

```

`utils/timelineScales.ts`:

```ts
import { type ScaleBand, type ScaleTime, scaleBand, scaleTime } from "d3"
import type { D3StackData } from "./timelineTransform"

export interface Scales {
  xScale: ScaleTime<number, number>
  yScale: ScaleBand<string>
}

interface Margin {
  top: number
  right: number
  bottom: number
  left: number
}

interface HorizontalMargin {
  left: number
  right: number
}

interface VerticalMargin {
  top: number
  bottom: number
}

/**
 * Extracts the minimum and maximum dates from all spans in the dataset.
 * Returns undefined if no spans are found.
 */
function extractDateRange(data: D3StackData[]): [Date, Date] | undefined {
  if (data.length === 0) {
    return undefined
  }

  const allDates: Date[] = []

  for (const podcast of data) {
    for (const episode of podcast.episodes) {
      for (const span of episode.spans) {
        allDates.push(span.start, span.end)
      }
    }
  }

  if (allDates.length === 0) {
    return undefined
  }

  const minDate = new Date(Math.min(...allDates.map(d => d.getTime())))
  const maxDate = new Date(Math.max(...allDates.map(d => d.getTime())))

  return [minDate, maxDate]
}

/**
 * Creates a D3 time scale for the x-axis.
 * The scale domain is determined by the earliest start and latest end dates across all spans.
 *
 * @param data - The transformed stack data
 * @param width - The total width of the chart
 * @param margin - The horizontal margins (left and right)
 * @returns A D3 scaleTime with appropriate domain and range
 */
export function createTimeScale(
  data: D3StackData[],
  width: number,
  margin: HorizontalMargin,
  explicitYearRange?: [number, number]
): ScaleTime<number, number> {
  const safeWidth = Math.max(width, margin.left + margin.right + 20)
  const range: [number, number] = [margin.left, safeWidth - margin.right]

  const dateRange = extractDateRange(data)
  if (explicitYearRange) {
    const [startYear, endYear] = explicitYearRange
    return scaleTime()
      .range(range)
      .domain([new Date(Date.UTC(startYear, 0, 1)), new Date(Date.UTC(endYear, 11, 31))])
  }

  if (dateRange === undefined) {
    // Return a scale with a default domain when no data is available
    return scaleTime()
      .range(range)
      .domain([new Date(0), new Date(1)])
  }

  return scaleTime().range(range).domain(dateRange)
}

/**
 * Creates a D3 band scale for the y-axis using podcast titles.
 *
 * @param data - The transformed stack data
 * @param height - The total height of the chart
 * @param margin - The vertical margins (top and bottom)
 * @returns A D3 scaleBand with podcast titles as domain
 */
export function createPodcastScale(
  data: D3StackData[],
  height: number,
  margin: VerticalMargin
): ScaleBand<string> {
  const safeHeight = Math.max(height, margin.top + margin.bottom + 20)
  const range: [number, number] = [margin.top, safeHeight - margin.bottom]

  // Extract podcast titles from data
  const domain = data.map(d => d.podcastTitle)

  return scaleBand().range(range).domain(domain).padding(0.1)
}

/**
 * Creates both x (time) and y (band) scales for the timeline visualization.
 *
 * @param data - The transformed stack data
 * @param width - The total width of the chart
 * @param height - The total height of the chart
 * @param margin - The margin object with all sides
 * @returns An object containing both xScale and yScale
 */
export function createScales(
  data: D3StackData[],
  width: number,
  height: number,
  margin: Margin,
  explicitYearRange?: [number, number]
): Scales {
  const xScale = createTimeScale(
    data,
    width,
    { left: margin.left, right: margin.right },
    explicitYearRange
  )
  const yScale = createPodcastScale(data, height, { top: margin.top, bottom: margin.bottom })

  return { xScale, yScale }
}

```

`utils/timelineTransform.test.ts`:

```ts
import { describe, expect, it } from "vitest"
import type { Dataset } from "../types"
import { transformToStackData } from "./timelineTransform"

describe("transformToStackData", () => {
  const createMockDataset = (): Dataset => ({
    meta: {
      schema_version: "1.0",
      generated_at_iso: "2024-01-01T00:00:00Z",
      source_db: "test",
    },
    podcasts: [
      { id: 1, title: "History Podcast", link: "https://example.com" },
      { id: 2, title: "Another Podcast", link: "https://example.com" },
    ],
    episodes: [
      {
        id: 1,
        podcast_id: 1,
        title: "Episode 1",
        pub_date_iso: "2020-01-15T00:00:00Z",
        page_url: "https://example.com/ep1",
      },
      {
        id: 2,
        podcast_id: 1,
        title: "Episode 2",
        pub_date_iso: "2020-02-20T00:00:00Z",
        page_url: "https://example.com/ep2",
      },
      {
        id: 3,
        podcast_id: 2,
        title: "Episode 3",
        pub_date_iso: "2020-03-10T00:00:00Z",
        page_url: "https://example.com/ep3",
      },
    ],
    spans: [
      {
        id: 1,
        episode_id: 1,
        start_iso: "1800-01-01T00:00:00Z",
        end_iso: "1850-12-31T00:00:00Z",
        precision: "year",
        qualifier: "approx",
        score: 0.9,
        source_section: "intro",
        source_text: "In the early 19th century...",
      },
      {
        id: 2,
        episode_id: 1,
        start_iso: "1900-01-01T00:00:00Z",
        end_iso: "1950-12-31T00:00:00Z",
        precision: "year",
        qualifier: "approx",
        score: 0.8,
        source_section: "body",
        source_text: "During the 20th century...",
      },
      {
        id: 3,
        episode_id: 2,
        start_iso: "1750-01-01T00:00:00Z",
        end_iso: "1800-12-31T00:00:00Z",
        precision: "year",
        qualifier: "exact",
        score: 0.95,
        source_section: "intro",
        source_text: "The mid-18th century...",
      },
      {
        id: 4,
        episode_id: 3,
        start_iso: "2000-01-01T00:00:00Z",
        end_iso: "2010-12-31T00:00:00Z",
        precision: "year",
        qualifier: "approx",
        score: 0.7,
        source_section: "body",
        source_text: "In the 2000s...",
      },
    ],
    places: [],
    entities: [],
    episode_keywords: {},
    episode_clusters: {},
    clusters: [],
  })

  it("should groups episodes by podcast correctly", () => {
    const dataset = createMockDataset()
    const episodeIds = [1, 2, 3]

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(2)
    expect(result[0].podcastId).toBe(2)
    expect(result[0].podcastTitle).toBe("Another Podcast")
    expect(result[0].episodes).toHaveLength(1)
    expect(result[0].episodes[0].episodeId).toBe(3)

    expect(result[1].podcastId).toBe(1)
    expect(result[1].podcastTitle).toBe("History Podcast")
    expect(result[1].episodes).toHaveLength(2)
  })

  it("should handle episodes with multiple spans", () => {
    const dataset = createMockDataset()
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(1)
    expect(result[0].episodes).toHaveLength(1)
    expect(result[0].episodes[0].spans).toHaveLength(2)
    expect(result[0].episodes[0].spans[0].spanId).toBe(1)
    expect(result[0].episodes[0].spans[1].spanId).toBe(2)
  })

  it("should handle empty episodes list", () => {
    const dataset = createMockDataset()
    const episodeIds: number[] = []

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(0)
  })

  it("should filter out spans with invalid date ranges", () => {
    const dataset: Dataset = {
      ...createMockDataset(),
      spans: [
        ...createMockDataset().spans,
        {
          id: 99,
          episode_id: 1,
          start_iso: undefined,
          end_iso: undefined,
          precision: "unknown",
          qualifier: "unknown",
          score: 0.5,
          source_section: "unknown",
          source_text: "Invalid span",
        },
        {
          id: 100,
          episode_id: 1,
          start_iso: "invalid-date",
          end_iso: "also-invalid",
          precision: "unknown",
          qualifier: "unknown",
          score: 0.5,
          source_section: "unknown",
          source_text: "Another invalid span",
        },
      ],
    }
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(1)
    expect(result[0].episodes[0].spans).toHaveLength(2)
    expect(result[0].episodes[0].spans.every(span => span.spanId !== 99)).toBe(true)
    expect(result[0].episodes[0].spans.every(span => span.spanId !== 100)).toBe(true)
  })

  it("should sort podcasts by title alphabetically", () => {
    const dataset: Dataset = {
      ...createMockDataset(),
      podcasts: [
        { id: 3, title: "Zebra Podcast" },
        { id: 1, title: "Apple Podcast" },
        { id: 2, title: "Middle Podcast" },
      ],
      episodes: [
        {
          id: 1,
          podcast_id: 3,
          title: "Episode 1",
          pub_date_iso: "2020-01-15T00:00:00Z",
        },
        {
          id: 2,
          podcast_id: 1,
          title: "Episode 2",
          pub_date_iso: "2020-02-20T00:00:00Z",
        },
        {
          id: 3,
          podcast_id: 2,
          title: "Episode 3",
          pub_date_iso: "2020-03-10T00:00:00Z",
        },
      ],
      spans: [],
      places: [],
      entities: [],
      episode_keywords: {},
      episode_clusters: {},
      clusters: [],
      meta: createMockDataset().meta,
    }
    const episodeIds = [1, 2, 3]

    const result = transformToStackData(dataset, episodeIds)

    expect(result[0].podcastTitle).toBe("Apple Podcast")
    expect(result[1].podcastTitle).toBe("Middle Podcast")
    expect(result[2].podcastTitle).toBe("Zebra Podcast")
  })

  it("should sort episodes by publication date (ascending)", () => {
    const dataset = createMockDataset()
    const episodeIds = [1, 2, 3]

    const result = transformToStackData(dataset, episodeIds)

    const historyPodcast = result.find(p => p.podcastId === 1)
    expect(historyPodcast?.episodes[0].episodeId).toBe(1)
    expect(historyPodcast?.episodes[1].episodeId).toBe(2)
  })

  it("should include cluster IDs when available in episode_clusters", () => {
    const dataset: Dataset = {
      ...createMockDataset(),
      episode_clusters: {
        "1": 42,
      },
    }
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    expect(result[0].episodes[0].spans).toHaveLength(2)
    expect(result[0].episodes[0].spans[0].clusterId).toBe(42)
    expect(result[0].episodes[0].spans[1].clusterId).toBe(42)
  })

  it("should handle missing cluster IDs gracefully", () => {
    const dataset = createMockDataset()
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    expect(result[0].episodes[0].spans).toHaveLength(2)
    expect(result[0].episodes[0].spans[0].clusterId).toBeUndefined()
  })

  it("should convert date strings to Date objects", () => {
    const dataset = createMockDataset()
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    const span = result[0].episodes[0].spans[0]
    expect(span.start).toBeInstanceOf(Date)
    expect(span.end).toBeInstanceOf(Date)
    expect(span.start.getTime()).toBe(new Date("1800-01-01T00:00:00Z").getTime())
    expect(span.end.getTime()).toBe(new Date("1850-12-31T00:00:00Z").getTime())
  })

  it("should handle unknown podcast IDs gracefully", () => {
    const dataset = createMockDataset()
    const episodeIds = [999]

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(0)
  })

  it("should handle episodes without spans", () => {
    const dataset = createMockDataset()
    const episodeIds = [1, 2, 3]
    // Remove spans for episode 3
    dataset.spans = dataset.spans.filter(s => s.episode_id !== 3)

    const result = transformToStackData(dataset, episodeIds)

    const anotherPodcast = result.find(p => p.podcastId === 2)
    expect(anotherPodcast?.episodes).toHaveLength(1)
    expect(anotherPodcast?.episodes[0].spans).toHaveLength(0)
  })

  it("should preserve all required span properties", () => {
    const dataset = createMockDataset()
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    const span = result[0].episodes[0].spans[0]
    expect(span.spanId).toBe(1)
    expect(span.score).toBe(0.9)
    expect(span.sourceText).toBe("In the early 19th century...")
  })
})

```

`utils/timelineTransform.ts`:

```ts
import type { Dataset } from "../types"

export interface D3StackData {
  podcastId: number
  podcastTitle: string
  episodes: Array<{
    episodeId: number
    title: string
    pubDate: string
    spans: Array<{
      spanId: number
      start: Date
      end: Date
      score: number
      sourceText: string
      clusterId?: number
    }>
  }>
}

function isValidDate(dateString: string | undefined): dateString is string {
  if (!dateString) return false
  const date = new Date(dateString)
  return date instanceof Date && !Number.isNaN(date.getTime())
}

export function transformToStackData(dataset: Dataset, episodeIds: number[]): D3StackData[] {
  if (episodeIds.length === 0) {
    return []
  }

  // Create a map of episodes by ID
  const episodesMap = new Map(
    dataset.episodes.filter(ep => episodeIds.includes(ep.id)).map(ep => [ep.id, ep])
  )

  // Create a map of podcasts by ID
  const podcastsMap = new Map(dataset.podcasts.map(p => [p.id, p]))

  // Group episodes by podcast
  const podcastEpisodesMap = new Map<number, Set<number>>()

  for (const episodeId of episodeIds) {
    const episode = episodesMap.get(episodeId)
    if (episode) {
      const podcastId = episode.podcast_id
      if (!podcastEpisodesMap.has(podcastId)) {
        podcastEpisodesMap.set(podcastId, new Set())
      }
      podcastEpisodesMap.get(podcastId)?.add(episodeId)
    }
  }

  // Create the result array
  const result: D3StackData[] = []

  for (const [podcastId, episodeIdSet] of podcastEpisodesMap.entries()) {
    const podcast = podcastsMap.get(podcastId)
    if (!podcast) continue

    // Get episodes for this podcast and sort by pub date
    const episodes: D3StackData["episodes"] = []
    const episodeIdsForPodcast = Array.from(episodeIdSet)

    for (const episodeId of episodeIdsForPodcast) {
      const episode = episodesMap.get(episodeId)
      if (!episode) continue

      // Get spans for this episode (only those with valid dates)
      const validSpans = dataset.spans.filter(
        span =>
          span.episode_id === episodeId && isValidDate(span.start_iso) && isValidDate(span.end_iso)
      )

      const spans = validSpans.map(span => {
        const a = new Date(span.start_iso)
        const b = new Date(span.end_iso)
        const start = a.getTime() <= b.getTime() ? a : b
        const end = a.getTime() <= b.getTime() ? b : a
        return {
          spanId: span.id,
          start,
          end,
          score: span.score,
          sourceText: span.source_text,
          clusterId: dataset.episode_clusters[String(episodeId)],
        }
      })

      episodes.push({
        episodeId: episode.id,
        title: episode.title,
        pubDate: episode.pub_date_iso,
        spans,
      })
    }

    // Sort episodes by publication date
    episodes.sort((a, b) => {
      const dateA = new Date(a.pubDate).getTime()
      const dateB = new Date(b.pubDate).getTime()
      return dateA - dateB
    })

    result.push({
      podcastId,
      podcastTitle: podcast.title,
      episodes,
    })
  }

  // Sort podcasts by title
  result.sort((a, b) => a.podcastTitle.localeCompare(b.podcastTitle))

  return result
}

```