import type { Dataset } from "../../types"
import D3GazetteerMap from "../D3GazetteerMap"
import EpisodeRasterTimeline from "../EpisodeRasterTimeline"
import ExplorationOverview from "../explore/ExplorationOverview"
import GraphIntervalSlider from "../GraphIntervalSlider"

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

  onChangeActiveYearRange: (next: [number, number]) => void
}) {
  return (
    <div className="flex h-full min-h-[1600px] flex-col gap-3">
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

      <div className="min-h-[520px] flex-1 overflow-visible rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2 md:min-h-[640px] lg:min-h-[760px]">
        <D3GazetteerMap
          dataset={props.dataset}
          episodes={props.episodes}
          selectedEpisodeId={props.selectedEpisodeId}
          onSelectEpisode={props.onSelectEpisode}
          scrubYear={props.scrubYear}
        />
      </div>
    </div>
  )
}
