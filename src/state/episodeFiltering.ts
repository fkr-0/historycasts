import type { Dataset } from "../types";
import type { Filters } from "../urlState";

/**
 * True iff episode has at least one span overlapping [minYear, maxYear].
 * This is used for the interval slider filtering.
 */
export function hasSpanInYearRange(
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

/**
 * Compute year bounds from spans for the given episode id set.
 * Returns null if there are no usable spans.
 */
export function spanYearBounds(
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

/**
 * Base filtering (podcast/title/kind/narrator/cluster) BEFORE year-range filtering.
 * This matches the intent of both original App variants.
 */
export function filterEpisodesBase(dataset: Dataset, filters: Filters) {
  const q = filters.q.trim().toLowerCase();
  const narr = filters.narrator.trim().toLowerCase();
  const kind = filters.kind;
  const clusterId = filters.clusterId;

  return dataset.episodes.filter((e) => {
    if (filters.podcastId !== "all" && e.podcast_id !== filters.podcastId)
      return false;

    if (q && !e.title.toLowerCase().includes(q)) return false;

    if (kind !== "all" && (e.kind ?? "") !== kind) return false;

    if (narr && !(e.narrator ?? "").toLowerCase().includes(narr))
      return false;

    if (clusterId != null) {
      const cid = dataset.episode_clusters[String(e.id)];
      if (cid !== clusterId) return false;
    }

    return true;
  });
}

/**
 * Clamp a user-selected year range to available bounds (and enforce min < max).
 */
export function clampYearRange(
  available: [number, number],
  requestedMin?: number,
  requestedMax?: number,
): [number, number] {
  const [minY, maxY] = available;

  const rawMin = requestedMin ?? minY;
  const rawMax = requestedMax ?? maxY;

  const clampedMin = Math.max(minY, Math.min(rawMin, maxY - 1));
  const clampedMax = Math.min(maxY, Math.max(rawMax, clampedMin + 1));

  return [clampedMin, clampedMax];
}

/**
 * Apply year-range filtering to already-base-filtered episodes.
 */
export function filterEpisodesByYearRange(
  dataset: Dataset,
  episodes: Array<{ id: number }>,
  yearRange: [number, number],
) {
  return episodes.filter((e) => hasSpanInYearRange(dataset, e.id, yearRange));
}
