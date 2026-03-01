// utils/filterUtils.ts
import type { Dataset } from "../types";
import type { Filters } from "../urlState";

export function filterEpisodes(dataset: Dataset | null, filters: Filters) {
  if (!dataset) return [];
  const q = filters.q.trim().toLowerCase();
  const narr = filters.narrator.trim().toLowerCase();
  const kind = filters.kind;
  const clusterId = filters.clusterId;

  return dataset.episodes.filter((e) => {
    if (filters.podcastId !== "all" && e.podcast_id !== filters.podcastId)
      return false;
    if (q && !e.title.toLowerCase().includes(q)) return false;
    if (kind !== "all" && (e.kind ?? "") !== kind) return false;
    if (narr && !(e.narrator ?? "").toLowerCase().includes(narr)) return false;
    if (clusterId != null) {
      const cid = dataset.episode_clusters[String(e.id)];
      if (cid !== clusterId) return false;
    }
    return true;
  });
}

function hasSpanInYearRange(
  dataset: Dataset,
  episodeId: number,
  yearRange: [number, number],
): boolean {
  const [minYear, maxYear] = yearRange;
  for (const s of dataset.spans) {
    if (s.episode_id !== episodeId) continue;
    if (!s.start_iso || !s.end_iso) continue;
    const a = new Date(s.start_iso).getUTCFullYear();
    const b = new Date(s.end_iso).getUTCFullYear();
    if (Number.isNaN(a) || Number.isNaN(b)) continue;
    const lo = Math.min(a, b);
    const hi = Math.max(a, b);
    if (hi >= minYear && lo <= maxYear) return true;
  }
  return false;
}

function spanYearBounds(
  dataset: Dataset,
  episodeIds: Set<number>,
): [number, number] | null {
  let minYear = Number.POSITIVE_INFINITY;
  let maxYear = Number.NEGATIVE_INFINITY;
  for (const s of dataset.spans) {
    if (!episodeIds.has(s.episode_id)) continue;
    if (!s.start_iso || !s.end_iso) continue;
    const a = new Date(s.start_iso).getUTCFullYear();
    const b = new Date(s.end_iso).getUTCFullYear();
    if (Number.isNaN(a) || Number.isNaN(b)) continue;
    minYear = Math.min(minYear, a, b);
    maxYear = Math.max(maxYear, a, b);
  }
  if (!Number.isFinite(minYear) || !Number.isFinite(maxYear)) return null;
  return [Math.floor(minYear), Math.ceil(maxYear)];
}
