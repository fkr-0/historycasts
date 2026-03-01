import type { Dataset } from "../types";

export type CenterTab =
  | { id: "explore"; title: "Explore" }
  | { id: "clusters"; title: "Clusters" }
  | { id: `episode-${number}`; title: string; episodeId: number }
  | { id: `cluster-${number}`; title: string; clusterId: number };

export function makeInitialTabs(): CenterTab[] {
  return [
    { id: "explore", title: "Explore" },
    { id: "clusters", title: "Clusters" },
  ];
}

export function tabIdForEpisode(episodeId: number): `episode-${number}` {
  return `episode-${episodeId}`;
}

export function tabIdForCluster(clusterId: number): `cluster-${number}` {
  return `cluster-${clusterId}`;
}

export function ensureEpisodeTab(
  dataset: Dataset,
  tabs: CenterTab[],
  episodeId: number,
): CenterTab[] {
  const ep = dataset.episodes.find((e) => e.id === episodeId);
  if (!ep) return tabs;

  const id = tabIdForEpisode(episodeId);
  if (tabs.some((t) => t.id === id)) return tabs;

  return [...tabs, { id, title: ep.title, episodeId }];
}

export function ensureClusterTab(
  dataset: Dataset,
  tabs: CenterTab[],
  clusterId: number,
): CenterTab[] {
  const cluster = dataset.clusters.find((c) => c.cluster.id === clusterId)?.cluster;
  if (!cluster) return tabs;

  const id = tabIdForCluster(clusterId);
  if (tabs.some((t) => t.id === id)) return tabs;

  const title = cluster.label?.trim() ? cluster.label : `Cluster ${clusterId}`;
  return [...tabs, { id, title, clusterId }];
}

export function closeTab(
  tabs: CenterTab[],
  tabId: CenterTab["id"],
): CenterTab[] {
  if (tabId === "explore" || tabId === "clusters") return tabs;
  return tabs.filter((t) => t.id !== tabId);
}

export function nextActiveTabAfterClose(
  activeId: CenterTab["id"],
  closingId: CenterTab["id"],
): CenterTab["id"] {
  if (activeId !== closingId) return activeId;
  return "explore";
}
