import { lazy, Suspense, useMemo, useState } from "react"
import { getExplorationIndex } from "../../state/explorationIndex"
import type { Dataset } from "../../types"
import type { Filters } from "../../urlState"
import EpisodeRasterTimeline from "../EpisodeRasterTimeline"
import ExplorationOverview from "../explore/ExplorationOverview"
import ExplorationScopeBar from "../explore/ExplorationScopeBar"
import GraphIntervalSlider from "../GraphIntervalSlider"

const GazetteerMap = lazy(() => import("../D3GazetteerMap"))

export default function ExploreTab(props: {
  dataset: Dataset
  episodes: Dataset["episodes"]
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void

  scrubYear?: number
  onScrubYear: (y?: number) => void

  availableYearRange: [number, number]
  activeYearRange: [number, number]
  sliderSpans: Dataset["spans"]

  axisDensityK: number
  topN: number
  filters: Filters
  onChangeFilters: (next: Filters | ((current: Filters) => Filters)) => void
  onResetScope: () => void

  onChangeActiveYearRange: (next: [number, number]) => void
}) {
  const [mapOpen, setMapOpen] = useState(false)
  const mappedCount = useMemo(() => {
    const mapped = getExplorationIndex(props.dataset).mappedEpisodeIds
    let count = 0
    for (const episode of props.episodes) if (mapped.has(episode.id)) count += 1
    return count
  }, [props.dataset, props.episodes])
  const unmappedCount = Math.max(0, props.episodes.length - mappedCount)

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <ExplorationScopeBar
        dataset={props.dataset}
        filters={props.filters}
        matchingCount={props.episodes.length}
        activeYearRange={props.activeYearRange}
        onChange={next => props.onChangeFilters(next)}
        onReset={props.onResetScope}
      />

      <ExplorationOverview
        dataset={props.dataset}
        episodes={props.episodes}
        activeYearRange={props.activeYearRange}
        onSelectYearRange={props.onChangeActiveYearRange}
      />

      <div className="min-h-[300px] flex-[0_0_34%] overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2 pr-4 md:min-h-[360px]">
        <EpisodeRasterTimeline
          dataset={props.dataset}
          episodes={props.episodes}
          selectedEpisodeId={props.selectedEpisodeId}
          onSelectEpisode={props.onSelectEpisode}
          visibleYearRange={props.activeYearRange}
          onSelectYearRange={props.onChangeActiveYearRange}
        />
      </div>

      <GraphIntervalSlider
        spans={props.sliderSpans}
        minYear={props.availableYearRange[0]}
        maxYear={props.availableYearRange[1]}
        value={props.activeYearRange}
        onChange={props.onChangeActiveYearRange}
      />

      <div className="flex-none overflow-visible rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">Historical geography</div>
            <div className="text-[11px] text-[color:var(--muted)]">
              {mappedCount} mapped in scope · {unmappedCount} unmapped. The interactive map is
              loaded only when opened.
            </div>
          </div>
          <button
            type="button"
            aria-controls="historical-geography-map"
            aria-expanded={mapOpen}
            onClick={() => setMapOpen(open => !open)}
            className="text-xs"
          >
            {mapOpen ? "Close interactive map" : "Open interactive map"}
          </button>
        </div>

        {mapOpen && (
          <div
            id="historical-geography-map"
            className="mt-3 min-h-[520px] md:min-h-[640px] lg:min-h-[760px]"
          >
            <Suspense
              fallback={
                <div className="grid min-h-72 place-items-center text-sm text-[color:var(--muted)]">
                  Loading interactive geography…
                </div>
              }
            >
              <GazetteerMap
                dataset={props.dataset}
                episodes={props.episodes}
                selectedEpisodeId={props.selectedEpisodeId}
                onSelectEpisode={props.onSelectEpisode}
                scrubYear={props.scrubYear}
              />
            </Suspense>
          </div>
        )}
      </div>
    </div>
  )
}
