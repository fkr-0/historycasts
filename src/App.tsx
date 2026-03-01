import { useMemo, useState } from "react";
import type { Dataset } from "./types";

import AppFrame from "./components/app/AppFrame";
import HeaderBar from "./components/app/HeaderBar";
import DocModal, { type DocModalKind } from "./components/app/DocModal";
import FiltersPanel from "./components/app/FiltersPanel";
import CenterTabs from "./components/app/CenterTabs";
import ExploreTab from "./components/app/ExploreTab";
import EpisodeTab from "./components/app/EpisodeTab";
import RightPanel from "./components/app/RightPanel";

import { useDataset } from "./app/useDataset";
import { useUrlFilters } from "./app/useUrlFilters";
import { useSearch } from "./app/useSearch";

import {
  clampYearRange,
  filterEpisodesBase,
  filterEpisodesByYearRange,
  spanYearBounds,
} from "./state/episodeFiltering";

import {
  closeTab,
  ensureEpisodeTab,
  makeInitialTabs,
  nextActiveTabAfterClose,
  type CenterTab,
} from "./state/tabs";

export default function App(): JSX.Element {
  const { dataset, err } = useDataset();
  const { filters, setFilters } = useUrlFilters();
  const search = useSearch(dataset);

  const [selectedEpisodeId, setSelectedEpisodeId] = useState<number | null>(null);
  const [tabs, setTabs] = useState<CenterTab[]>(() => makeInitialTabs());
  const [activeTabId, setActiveTabId] = useState<CenterTab["id"]>("explore");

  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [docModal, setDocModal] = useState<DocModalKind | null>(null);

  if (err) return <div className="p-4">Error: {err}</div>;
  if (!dataset) return <div className="p-4">Loading dataset…</div>;

  const episodesBase = useMemo(() => filterEpisodesBase(dataset, filters), [dataset, filters]);

  const availableYearRange = useMemo<[number, number]>(() => {
    const ids = new Set(episodesBase.map((e) => e.id));
    const bounds = spanYearBounds(dataset, ids);
    return bounds ?? [-500, new Date().getUTCFullYear()];
  }, [dataset, episodesBase]);

  const activeYearRange = useMemo<[number, number]>(() => {
    return clampYearRange(availableYearRange, filters.yearMin, filters.yearMax);
  }, [availableYearRange, filters.yearMin, filters.yearMax]);

  const filteredEpisodes = useMemo(() => {
    return filterEpisodesByYearRange(dataset, episodesBase, activeYearRange);
  }, [dataset, episodesBase, activeYearRange]);

  const baseEpisodeIdSet = useMemo(() => new Set(episodesBase.map((e) => e.id)), [episodesBase]);

  const sliderSpans = useMemo(() => {
    return dataset.spans.filter((s) => baseEpisodeIdSet.has(s.episode_id));
  }, [dataset, baseEpisodeIdSet]);

  function openEpisodeTab(episodeId: number) {
    setSelectedEpisodeId(episodeId);
    setTabs((prev) => ensureEpisodeTab(dataset, prev, episodeId));
    setActiveTabId(`episode-${episodeId}`);
  }

  function handleCloseTab(tabId: CenterTab["id"]) {
    setTabs((prev) => closeTab(prev, tabId));
    setActiveTabId((active) => nextActiveTabAfterClose(active, tabId));
  }

  const activeTab = tabs.find((t) => t.id === activeTabId) ?? tabs[0];

  return (
    <>
      <AppFrame
        left={
          <FiltersPanel
            dataset={dataset}
            filters={filters}
            onChange={setFilters}
            collapsed={leftCollapsed}
            onUncollapse={() => setLeftCollapsed(false)}
            matchingCount={filteredEpisodes.length}
          />
        }
        center={
          <div className="flex h-full flex-col gap-3">
            <HeaderBar
              searchValue={search.query}
              onSearchChange={search.setQuery}
              onSearchEnter={search.pin}
              onSearchClear={search.clear}
              leftCollapsed={leftCollapsed}
              rightCollapsed={rightCollapsed}
              onToggleLeft={() => setLeftCollapsed((v) => !v)}
              onToggleRight={() => setRightCollapsed((v) => !v)}
              onOpenReadme={() => setDocModal("readme")}
              onOpenChangelog={() => setDocModal("changelog")}
            />

            <CenterTabs
              tabs={tabs}
              activeTabId={activeTabId}
              onActivate={(id) => {
                setActiveTabId(id);
                if (id.startsWith("episode-")) {
                  const epId = Number(id.slice("episode-".length));
                  if (Number.isFinite(epId)) setSelectedEpisodeId(epId);
                }
              }}
              onClose={handleCloseTab}
            />

            <div className="min-h-0 flex-1">
              {activeTab.id === "explore" ? (
                <ExploreTab
                  dataset={dataset}
                  episodes={filteredEpisodes}
                  selectedEpisodeId={selectedEpisodeId}
                  onSelectEpisode={openEpisodeTab}
                  scrubYear={filters.year}
                  onScrubYear={(y) => setFilters((f) => ({ ...f, year: y }))}
                  availableYearRange={availableYearRange}
                  activeYearRange={activeYearRange}
                  sliderSpans={sliderSpans}
                  axisDensityK={filters.axisK}
                  topN={filters.topN}
                  onChangeActiveYearRange={(next) =>
                    setFilters((f) => ({ ...f, yearMin: next[0], yearMax: next[1] }))
                  }
                />
              ) : (
                <>
                  {"episodeId" in activeTab ? (
                    <EpisodeTab dataset={dataset} episodeId={activeTab.episodeId} />
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
            searchQuery={search.query}
            searchHits={search.hits}
            searchMode={search.mode}
            onSelectEpisode={openEpisodeTab}
            onSelectCluster={(clusterId) => setFilters((f) => ({ ...f, clusterId }))}
            episodes={filteredEpisodes}
            selectedEpisodeId={selectedEpisodeId}
            rightPanelRef={search.rightPanelRef}
          />
        }
      />

      {docModal && <DocModal kind={docModal} onClose={() => setDocModal(null)} />}
    </>
  );
}
