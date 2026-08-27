import { useCallback } from "react"
import type { SearchMode } from "../../app/useSearch"
import type { IntentOperation } from "../../intent/types"
import type { SearchHit } from "../../search/searchIndex"
import type { Dataset } from "../../types"
import { default as EpisodeDetail } from "../EpisodeDetail"
import EpisodesTable from "../EpisodesTable"
import SearchResultsPanel from "../SearchResultsPanel"

export default function RightPanel(props: {
  dataset: Dataset

  collapsed: boolean

  searchQuery: string
  searchHits: SearchHit[]
  searchMode: SearchMode

  onSelectEpisode: (episodeId: number) => void
  onSelectCluster: (clusterId: number) => void
  onQueueOperation?: (op: IntentOperation) => void

  episodes: Dataset["episodes"]
  selectedEpisodeId: number | null

  tableSort?: "title" | "pub_date_iso"
  tableDir?: "asc" | "desc"
  onTableSortChange: (sortBy?: "title" | "pub_date_iso", direction?: "asc" | "desc") => void

  rightPanelRef: React.RefObject<HTMLDivElement>
}) {
  const selectEpisodeFromSearch = useCallback(
    (episodeId: number) => {
      props.onSelectEpisode(episodeId)
      // push details into view (scroll results out)
      props.rightPanelRef.current?.scrollTo({ top: 500, behavior: "smooth" })
    },
    [props]
  )

  const selectClusterFromSearch = useCallback(
    (clusterId: number) => {
      props.onSelectCluster(clusterId)
      props.rightPanelRef.current?.scrollTo({ top: 0, behavior: "smooth" })
    },
    [props]
  )

  if (props.collapsed) {
    return <aside id="details-panel" aria-label="Details panel" aria-hidden="true" />
  }

  return (
    <aside
      id="details-panel"
      ref={props.rightPanelRef}
      aria-label="Episode search and details"
      className="h-full overflow-auto"
    >
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
          sortBy={props.tableSort}
          sortDirection={props.tableDir}
          onSortChange={props.onTableSortChange}
        />
      </div>

      <div className="mt-3 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <EpisodeDetail
          dataset={props.dataset}
          episodeId={props.selectedEpisodeId}
          onQueueOperation={props.onQueueOperation}
        />
      </div>
    </aside>
  )
}
