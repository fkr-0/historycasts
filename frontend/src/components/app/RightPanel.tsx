import { useCallback } from "react";
import type { Dataset } from "../../types";
import type { IntentOperation } from "../../intent/types";
import EpisodesTable from "../EpisodesTable";
import SearchResultsPanel from "../SearchResultsPanel";
import { default as EpisodeDetail } from "../EpisodeDetail";
import type { SearchHit } from "../../search/searchIndex";
import type { SearchMode } from "../../app/useSearch";

export default function RightPanel(props: {
  dataset: Dataset;

  collapsed: boolean;
  onUncollapse: () => void;

  searchQuery: string;
  searchHits: SearchHit[];
  searchMode: SearchMode;

  onSelectEpisode: (episodeId: number) => void;
  onSelectCluster: (clusterId: number) => void;
  onQueueOperation?: (op: IntentOperation) => void;

  episodes: Dataset["episodes"];
  selectedEpisodeId: number | null;

  rightPanelRef: React.RefObject<HTMLDivElement>;
}) {
  const selectEpisodeFromSearch = useCallback(
    (episodeId: number) => {
      props.onSelectEpisode(episodeId);
      // push details into view (scroll results out)
      props.rightPanelRef.current?.scrollTo({ top: 500, behavior: "smooth" });
    },
    [props],
  );

  const selectClusterFromSearch = useCallback(
    (clusterId: number) => {
      props.onSelectCluster(clusterId);
      props.rightPanelRef.current?.scrollTo({ top: 0, behavior: "smooth" });
    },
    [props],
  );

  if (props.collapsed) {
    return (
      <button type="button" onClick={props.onUncollapse} className="text-xs">
        ←
      </button>
    );
  }

  return (
    <div ref={props.rightPanelRef} className="h-full overflow-auto">
      <SearchResultsPanel
        dataset={props.dataset}
        query={props.searchQuery}
        hits={props.searchHits}
        mode={props.searchMode}
        onSelectEpisode={selectEpisodeFromSearch}
        onSelectCluster={selectClusterFromSearch}
      />

      <div className="mt-3">
        <EpisodesTable
          dataset={props.dataset}
          episodes={props.episodes}
          selectedEpisodeId={props.selectedEpisodeId}
          onSelectEpisode={props.onSelectEpisode}
        />
      </div>

      <div className="mt-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <EpisodeDetail
          dataset={props.dataset}
          episodeId={props.selectedEpisodeId}
          onQueueOperation={props.onQueueOperation}
        />
      </div>
    </div>
  );
}
