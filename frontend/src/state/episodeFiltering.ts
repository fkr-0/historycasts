import type { Dataset } from "../types"
import type { Filters } from "../urlState"
import { getExplorationIndex } from "./explorationIndex"

/**
 * True iff episode has at least one span overlapping [minYear, maxYear].
 * This is used for the interval slider filtering.
 */
export function hasSpanInYearRange(
  dataset: Dataset,
  episodeId: number,
  yearRange: [number, number]
): boolean {
  const [minYear, maxYear] = yearRange
  const intervals = getExplorationIndex(dataset).intervalsByEpisode.get(episodeId) ?? []
  return intervals.some(interval => interval.endYear >= minYear && interval.startYear <= maxYear)
}

/**
 * Compute year bounds from spans for the given episode id set.
 * Returns null if there are no usable spans.
 */
export function spanYearBounds(dataset: Dataset, episodeIds: Set<number>): [number, number] | null {
  let minYear = Number.POSITIVE_INFINITY
  let maxYear = Number.NEGATIVE_INFINITY

  const { intervalsByEpisode } = getExplorationIndex(dataset)
  for (const episodeId of episodeIds) {
    for (const interval of intervalsByEpisode.get(episodeId) ?? []) {
      minYear = Math.min(minYear, interval.startYear)
      maxYear = Math.max(maxYear, interval.endYear)
    }
  }

  if (!Number.isFinite(minYear) || !Number.isFinite(maxYear)) return null
  return [Math.floor(minYear), Math.ceil(maxYear)]
}

/**
 * Base filtering BEFORE year-range filtering. The expensive corpus-derived values
 * are built once per immutable dataset object and reused across interactions.
 */
export function filterEpisodesBase(dataset: Dataset, filters: Filters) {
  const q = filters.q.trim().toLowerCase()
  const narr = filters.narrator.trim().toLowerCase()
  const kind = filters.kind
  const clusterId = filters.clusterId
  const index = getExplorationIndex(dataset)

  return dataset.episodes.filter(e => {
    if (filters.podcastId !== "all" && e.podcast_id !== filters.podcastId) return false

    if (q && !(index.searchTextByEpisode.get(e.id) ?? e.title.toLowerCase()).includes(q))
      return false

    if (kind !== "all" && (e.kind ?? "") !== kind) return false

    if (narr && !(e.narrator ?? "").toLowerCase().includes(narr)) return false

    if (clusterId != null) {
      const cid = dataset.episode_clusters[String(e.id)]
      if (cid !== clusterId) return false
    }

    if (filters.geo === "mapped" && !index.mappedEpisodeIds.has(e.id)) return false
    if (filters.geo === "unmapped" && index.mappedEpisodeIds.has(e.id)) return false

    return true
  })
}

/**
 * Clamp a user-selected year range to available bounds (and enforce min < max).
 */
export function clampYearRange(
  available: [number, number],
  requestedMin?: number,
  requestedMax?: number
): [number, number] {
  const [minY, maxY] = available

  const rawMin = requestedMin ?? minY
  const rawMax = requestedMax ?? maxY

  const clampedMin = Math.max(minY, Math.min(rawMin, maxY - 1))
  const clampedMax = Math.min(maxY, Math.max(rawMax, clampedMin + 1))

  return [clampedMin, clampedMax]
}

/**
 * Apply year-range filtering to already-base-filtered episodes.
 */
export function filterEpisodesByYearRange(
  dataset: Dataset,
  episodes: Array<{ id: number }>,
  yearRange: [number, number]
) {
  const [minYear, maxYear] = yearRange
  const intervalsByEpisode = getExplorationIndex(dataset).intervalsByEpisode
  return episodes.filter(episode =>
    (intervalsByEpisode.get(episode.id) ?? []).some(
      interval => interval.endYear >= minYear && interval.startYear <= maxYear
    )
  )
}
