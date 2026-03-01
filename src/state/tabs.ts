import type { Dataset } from "../types";

export type CenterTab =
  | { id: "explore"; title: "Explore" }
  | { id: `episode-${number}`; title: string; episodeId: number };

export function makeInitialTabs(): CenterTab[] {
  return [{ id: "explore", title: "Explore" }];
}

export function tabIdForEpisode(episodeId: number): `episode-${number}` {
  return `episode-${episodeId}`;
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

export function closeTab(
  tabs: CenterTab[],
  tabId: CenterTab["id"],
): CenterTab[] {
  if (tabId === "explore") return tabs;
  return tabs.filter((t) => t.id !== tabId);
}

export function nextActiveTabAfterClose(
  activeId: CenterTab["id"],
  closingId: CenterTab["id"],
): CenterTab["id"] {
  if (activeId !== closingId) return activeId;
  return "explore";
}
