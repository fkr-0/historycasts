import { useCallback, useEffect, useMemo, useState } from "react"
import { useDataset } from "./app/useDataset"
import { useSearch } from "./app/useSearch"
import { useUrlFilters } from "./app/useUrlFilters"
import AppFrame from "./components/app/AppFrame"
import CenterTabs from "./components/app/CenterTabs"
import DocModal, { type DocModalKind } from "./components/app/DocModal"
import EpisodeTab from "./components/app/EpisodeTab"
import ExploreTab from "./components/app/ExploreTab"
import FiltersPanel from "./components/app/FiltersPanel"
import HeaderBar from "./components/app/HeaderBar"
import RightPanel from "./components/app/RightPanel"
import ClusterDetail from "./components/ClusterDetail"
import ClusterIndexView from "./components/clusters/ClusterIndexView"
import IntentQueueButton from "./components/intent/IntentQueueButton"
import IntentQueueModal from "./components/intent/IntentQueueModal"
import { useIntentQueue } from "./intent/useIntentQueue"
import {
  clampYearRange,
  filterEpisodesBase,
  filterEpisodesByYearRange,
  spanYearBounds,
} from "./state/episodeFiltering"
import {
  type CenterTab,
  closeTab,
  ensureClusterTab,
  ensureEpisodeTab,
  makeInitialTabs,
  nextActiveTabAfterClose,
} from "./state/tabs"
import { resetExplorationScope } from "./urlState"

export default function App(): JSX.Element {
  const { dataset, err } = useDataset()
  const { filters, setFilters } = useUrlFilters()
  const search = useSearch(dataset, filters.q)

  const [selectedEpisodeId, setSelectedEpisodeId] = useState<number | null>(null)
  const [tabs, setTabs] = useState<CenterTab[]>(() => makeInitialTabs())
  const [activeTabId, setActiveTabId] = useState<CenterTab["id"]>("explore")

  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [docModal, setDocModal] = useState<DocModalKind | null>(null)

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return
    const mobile = window.matchMedia("(max-width: 767px)")
    const applyResponsiveShell = (matches: boolean) => {
      setLeftCollapsed(matches)
      setRightCollapsed(matches)
    }
    applyResponsiveShell(mobile.matches)
    const onChange = (event: MediaQueryListEvent) => applyResponsiveShell(event.matches)
    mobile.addEventListener("change", onChange)
    return () => mobile.removeEventListener("change", onChange)
  }, [])
  const [intentModalOpen, setIntentModalOpen] = useState(false)
  const intentQueue = useIntentQueue(dataset)

  const episodesBase = useMemo(() => {
    if (!dataset) return []
    return filterEpisodesBase(dataset, filters)
  }, [dataset, filters])

  const availableYearRange = useMemo<[number, number]>(() => {
    if (!dataset) return [-500, new Date().getUTCFullYear()]
    const ids = new Set(episodesBase.map(e => e.id))
    const bounds = spanYearBounds(dataset, ids)
    return bounds ?? [-500, new Date().getUTCFullYear()]
  }, [dataset, episodesBase])

  const activeYearRange = useMemo<[number, number]>(() => {
    return clampYearRange(availableYearRange, filters.yearMin, filters.yearMax)
  }, [availableYearRange, filters.yearMin, filters.yearMax])

  const filteredEpisodes = useMemo(() => {
    if (!dataset) return []
    return filterEpisodesByYearRange(dataset, episodesBase, activeYearRange)
  }, [dataset, episodesBase, activeYearRange])

  const scopedSearchHits = useMemo(() => {
    if (!dataset || search.hits.length === 0) return []

    const visibleEpisodeIds = new Set(filteredEpisodes.map(episode => episode.id))
    const visibleClusterIds = new Set<number>()
    for (const episodeId of visibleEpisodeIds) {
      const clusterId = dataset.episode_clusters[String(episodeId)]
      if (clusterId != null) visibleClusterIds.add(clusterId)
    }

    return search.hits.filter(hit => {
      if (hit.doc.episodeId != null) return visibleEpisodeIds.has(hit.doc.episodeId)
      if (hit.doc.clusterId != null) return visibleClusterIds.has(hit.doc.clusterId)
      return false
    })
  }, [dataset, filteredEpisodes, search.hits])

  const baseEpisodeIdSet = useMemo(() => new Set(episodesBase.map(e => e.id)), [episodesBase])

  const sliderSpans = useMemo(() => {
    if (!dataset) return []
    return dataset.spans.filter(s => baseEpisodeIdSet.has(s.episode_id))
  }, [dataset, baseEpisodeIdSet])

  function openEpisodeTab(episodeId: number) {
    if (!dataset) return
    setSelectedEpisodeId(episodeId)
    setTabs(prev => ensureEpisodeTab(dataset, prev, episodeId))
    setActiveTabId(`episode-${episodeId}`)
  }

  function openClusterTab(clusterId: number) {
    if (!dataset) return
    setFilters(f => ({ ...f, clusterId }))
    setTabs(prev => ensureClusterTab(dataset, prev, clusterId))
    setActiveTabId(`cluster-${clusterId}`)
  }

  function handleCloseTab(tabId: CenterTab["id"]) {
    setTabs(prev => closeTab(prev, tabId))
    setActiveTabId(active => nextActiveTabAfterClose(active, tabId))
  }

  const handleClusterScopeChange = useCallback(
    (scope: { term: string; yearRange: [number, number] }) => {
      setFilters(current => {
        const nextTerm = scope.term
        const nextMin = scope.yearRange[0]
        const nextMax = scope.yearRange[1]
        if (
          current.clusterTerm === nextTerm &&
          current.clusterYearMin === nextMin &&
          current.clusterYearMax === nextMax
        ) {
          return current
        }
        return {
          ...current,
          clusterTerm: nextTerm,
          clusterYearMin: nextMin,
          clusterYearMax: nextMax,
        }
      })
    },
    [setFilters]
  )

  const activeTab = tabs.find(t => t.id === activeTabId) ?? tabs[0]

  if (err) return <div className="p-4">Error: {err}</div>
  if (!dataset) return <div className="p-4">Loading dataset…</div>

  return (
    <>
      <AppFrame
        leftCollapsed={leftCollapsed}
        rightCollapsed={rightCollapsed}
        left={
          <FiltersPanel
            dataset={dataset}
            filters={filters}
            onChange={setFilters}
            onSelectCluster={openClusterTab}
            collapsed={leftCollapsed}
            onUncollapse={() => setLeftCollapsed(false)}
            matchingCount={filteredEpisodes.length}
            onResetScope={() => setFilters(current => resetExplorationScope(current))}
            onQueueOperation={intentQueue.addOperation}
          />
        }
        center={
          <div className="flex h-full flex-col gap-3">
            <HeaderBar
              searchValue={filters.q}
              onSearchChange={q => setFilters(current => ({ ...current, q }))}
              onSearchEnter={search.pin}
              onSearchClear={() => {
                setFilters(current => ({ ...current, q: "" }))
                search.clear()
              }}
              leftCollapsed={leftCollapsed}
              rightCollapsed={rightCollapsed}
              onToggleLeft={() => setLeftCollapsed(v => !v)}
              onToggleRight={() => setRightCollapsed(v => !v)}
              onOpenReadme={() => setDocModal("readme")}
              onOpenChangelog={() => setDocModal("changelog")}
              intentControls={
                <IntentQueueButton
                  queued={intentQueue.queueCounts.queued}
                  applied={intentQueue.queueCounts.applied}
                  invalid={intentQueue.queueCounts.invalid}
                  onClick={() => setIntentModalOpen(true)}
                />
              }
            />

            <CenterTabs
              tabs={tabs}
              activeTabId={activeTabId}
              onActivate={id => {
                setActiveTabId(id)
                if (id.startsWith("episode-")) {
                  const epId = Number(id.slice("episode-".length))
                  if (Number.isFinite(epId)) setSelectedEpisodeId(epId)
                }
              }}
              onClose={handleCloseTab}
            />

            <div className="min-h-0 flex-1 overflow-auto">
              {activeTab.id === "explore" ? (
                <ExploreTab
                  dataset={dataset}
                  episodes={filteredEpisodes}
                  selectedEpisodeId={selectedEpisodeId}
                  onSelectEpisode={openEpisodeTab}
                  scrubYear={filters.year}
                  onScrubYear={y => setFilters(f => ({ ...f, year: y }))}
                  availableYearRange={availableYearRange}
                  activeYearRange={activeYearRange}
                  sliderSpans={sliderSpans}
                  axisDensityK={filters.axisK}
                  topN={filters.topN}
                  filters={filters}
                  onChangeFilters={setFilters}
                  onResetScope={() => setFilters(current => resetExplorationScope(current))}
                  onChangeActiveYearRange={next =>
                    setFilters(f => ({ ...f, yearMin: next[0], yearMax: next[1] }))
                  }
                />
              ) : activeTab.id === "clusters" ? (
                <ClusterIndexView
                  dataset={dataset}
                  sortBy={filters.clusterSort ?? "size"}
                  onSortChange={sort => setFilters(f => ({ ...f, clusterSort: sort }))}
                  onSelectCluster={openClusterTab}
                />
              ) : (
                <>
                  {"episodeId" in activeTab ? (
                    <EpisodeTab
                      dataset={dataset}
                      episodeId={activeTab.episodeId}
                      onQueueOperation={intentQueue.addOperation}
                    />
                  ) : null}
                  {"clusterId" in activeTab ? (
                    <ClusterDetail
                      dataset={dataset}
                      clusterId={activeTab.clusterId}
                      selectedEpisodeId={selectedEpisodeId}
                      onSelectEpisode={openEpisodeTab}
                      onSelectCluster={openClusterTab}
                      initialTerm={filters.clusterTerm}
                      initialYearRange={
                        filters.clusterYearMin != null && filters.clusterYearMax != null
                          ? [filters.clusterYearMin, filters.clusterYearMax]
                          : undefined
                      }
                      onScopeChange={handleClusterScopeChange}
                    />
                  ) : null}
                </>
              )}
            </div>
          </div>
        }
        right={
          <RightPanel
            dataset={dataset}
            collapsed={rightCollapsed}
            onUncollapse={() => setRightCollapsed(false)}
            searchQuery={filters.q}
            searchHits={scopedSearchHits}
            searchMode={search.mode}
            onSelectEpisode={openEpisodeTab}
            onSelectCluster={openClusterTab}
            episodes={filteredEpisodes}
            selectedEpisodeId={selectedEpisodeId}
            rightPanelRef={search.rightPanelRef}
            tableSort={filters.tableSort}
            tableDir={filters.tableDir}
            onTableSortChange={(tableSort, tableDir) =>
              setFilters(current => ({ ...current, tableSort, tableDir }))
            }
            onQueueOperation={intentQueue.addOperation}
          />
        }
      />

      {docModal && <DocModal kind={docModal} onClose={() => setDocModal(null)} />}
      {intentModalOpen && (
        <IntentQueueModal
          operations={intentQueue.operations}
          queued={intentQueue.queueCounts.queued}
          applied={intentQueue.queueCounts.applied}
          invalid={intentQueue.queueCounts.invalid}
          cancelled={intentQueue.queueCounts.cancelled}
          onClose={() => setIntentModalOpen(false)}
          onReconcile={intentQueue.reconcile}
          onCleanup={intentQueue.cleanup}
          onCancel={intentQueue.cancel}
          onRemove={intentQueue.remove}
          onExportJson={intentQueue.exportJson}
          onExportSql={intentQueue.exportSql}
        />
      )}
    </>
  )
}
