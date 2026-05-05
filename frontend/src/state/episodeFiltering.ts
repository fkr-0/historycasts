import type { Dataset } from "../types";
import type { Filters } from "../urlState";
import { parseIsoYear } from "../utils/historicalDate";

const MIN_REASONABLE_YEAR = -4000;
const MAX_REASONABLE_YEAR = new Date().getUTCFullYear() + 1;

function spanYears(span: { start_iso?: string; end_iso?: string }): [number, number] | null {
  if (!span.start_iso || !span.end_iso) return null;
  const a = parseIsoYear(span.start_iso);
  const b = parseIsoYear(span.end_iso);
  if (a == null || b == null) return null;

  const lo = Math.min(a, b);
  const hi = Math.max(a, b);
  if (lo < MIN_REASONABLE_YEAR || hi > MAX_REASONABLE_YEAR) return null;
  return [lo, hi];
}

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
    const years = spanYears(s);
    if (!years) continue;
    const [lo, hi] = years;
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
    const years = spanYears(s);
    if (!years) continue;
    const [a, b] = years;

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
