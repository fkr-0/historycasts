import type { Dataset } from "../../types";
import D3GazetteerMap from "../D3GazetteerMap";
import EpisodeRasterTimeline from "../EpisodeRasterTimeline";
import GraphIntervalSlider from "../GraphIntervalSlider";

export default function ExploreTab(props: {
  dataset: Dataset;
  episodes: Dataset["episodes"];
  selectedEpisodeId: number | null;
  onSelectEpisode: (id: number) => void;

  scrubYear?: number;
  onScrubYear: (y?: number) => void;

  availableYearRange: [number, number];
  activeYearRange: [number, number];
  sliderSpans: Dataset["spans"];

  axisDensityK: number;
  topN: number;

  onChangeActiveYearRange: (next: [number, number]) => void;
}) {
  return (
    <div className="flex h-full flex-col gap-3">
      <div className="min-h-[300px] flex-[0_0_56%] overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2 pr-4">
        <EpisodeRasterTimeline
          dataset={props.dataset}
          episodes={props.episodes}
          selectedEpisodeId={props.selectedEpisodeId}
          onSelectEpisode={props.onSelectEpisode}
          visibleYearRange={props.activeYearRange}
        />
      </div>

      <GraphIntervalSlider
        spans={props.sliderSpans}
        minYear={props.availableYearRange[0]}
        maxYear={props.availableYearRange[1]}
        value={props.activeYearRange}
        onChange={props.onChangeActiveYearRange}
      />

      <div className="min-h-[320px] flex-1 overflow-visible rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2">
        <D3GazetteerMap
          dataset={props.dataset}
          episodes={props.episodes}
          selectedEpisodeId={props.selectedEpisodeId}
          onSelectEpisode={props.onSelectEpisode}
          scrubYear={props.scrubYear}
        />
      </div>
    </div>
  );
}
