import type { Dataset } from "../types"
import { parseIsoYear } from "../utils/historicalDate"

const MIN_REASONABLE_YEAR = -4000
const MAX_REASONABLE_YEAR = new Date().getUTCFullYear() + 1

export interface IndexedEpisodeInterval {
  id: number
  startYear: number
  endYear: number
  score: number
  sourceText: string
}

export interface ExplorationIndex {
  intervalsByEpisode: Map<number, IndexedEpisodeInterval[]>
  mappedEpisodeIds: Set<number>
  clusteredEpisodeIds: Set<number>
  bestHistoricalYearByEpisode: Map<number, number>
  searchTextByEpisode: Map<number, string>
}

const indexCache = new WeakMap<Dataset, ExplorationIndex>()

function parseIntervalYears(startIso?: string, endIso?: string): [number, number] | null {
  const a = parseIsoYear(startIso)
  const b = parseIsoYear(endIso)
  if (a == null || b == null) return null
  const lo = Math.min(a, b)
  const hi = Math.max(a, b)
  if (lo < MIN_REASONABLE_YEAR || hi > MAX_REASONABLE_YEAR) return null
  return [lo, hi]
}

function pushSearch(parts: Map<number, string[]>, episodeId: number, value: unknown) {
  if (typeof value !== "string" || !value.trim()) return
  const current = parts.get(episodeId)
  if (current) current.push(value)
  else parts.set(episodeId, [value])
}

export function buildExplorationIndex(dataset: Dataset): ExplorationIndex {
  const intervalsByEpisode = new Map<number, IndexedEpisodeInterval[]>()
  const mappedEpisodeIds = new Set<number>()
  const clusteredEpisodeIds = new Set<number>()
  const bestHistoricalYearByEpisode = new Map<number, number>()
  const searchParts = new Map<number, string[]>()
  const spanById = new Map<number, Dataset["spans"][number]>()
  const bestSpanByEpisode = new Map<number, Dataset["spans"][number]>()

  for (const episode of dataset.episodes) {
    searchParts.set(
      episode.id,
      [episode.title, episode.description_pure, episode.narrator, episode.kind].filter(
        (value): value is string => typeof value === "string" && value.length > 0
      )
    )
  }

  for (const span of dataset.spans ?? []) {
    spanById.set(span.id, span)
    const years = parseIntervalYears(span.start_iso, span.end_iso)
    if (years) {
      const [startYear, endYear] = years
      const intervals = intervalsByEpisode.get(span.episode_id) ?? []
      intervals.push({
        id: span.id,
        startYear,
        endYear,
        score: span.score ?? 0,
        sourceText: span.source_text ?? "",
      })
      intervalsByEpisode.set(span.episode_id, intervals)

      const current = bestSpanByEpisode.get(span.episode_id)
      if (!current || (span.score ?? 0) > (current.score ?? 0)) {
        bestSpanByEpisode.set(span.episode_id, span)
      }
    }
    pushSearch(searchParts, span.episode_id, span.source_text)
  }

  for (const episode of dataset.episodes) {
    const explicit = episode.best_span_id == null ? undefined : spanById.get(episode.best_span_id)
    if (explicit && parseIntervalYears(explicit.start_iso, explicit.end_iso)) {
      bestSpanByEpisode.set(episode.id, explicit)
    }
  }

  for (const [episodeId, span] of bestSpanByEpisode) {
    const years = parseIntervalYears(span.start_iso, span.end_iso)
    if (years) bestHistoricalYearByEpisode.set(episodeId, (years[0] + years[1]) / 2)
  }

  for (const place of dataset.places ?? []) {
    pushSearch(searchParts, place.episode_id, place.canonical_name)
    pushSearch(searchParts, place.episode_id, place.place_kind)
    if (place.lat != null && place.lon != null) mappedEpisodeIds.add(place.episode_id)
  }

  for (const entity of dataset.entities ?? []) {
    pushSearch(searchParts, entity.episode_id, entity.name)
    pushSearch(searchParts, entity.episode_id, entity.kind)
  }

  for (const [episodeIdRaw, keywords] of Object.entries(dataset.episode_keywords ?? {})) {
    const episodeId = Number(episodeIdRaw)
    for (const keyword of keywords) pushSearch(searchParts, episodeId, keyword.phrase)
  }

  const clusterById = new Map((dataset.clusters ?? []).map(row => [row.cluster.id, row]))
  for (const [episodeIdRaw, clusterId] of Object.entries(dataset.episode_clusters ?? {})) {
    const episodeId = Number(episodeIdRaw)
    clusteredEpisodeIds.add(episodeId)
    const cluster = clusterById.get(clusterId)
    if (!cluster) continue
    pushSearch(searchParts, episodeId, cluster.cluster.label)
    for (const keyword of cluster.top_keywords) pushSearch(searchParts, episodeId, keyword.phrase)
    for (const entity of cluster.top_entities) pushSearch(searchParts, episodeId, entity.name)
  }

  for (const intervals of intervalsByEpisode.values()) {
    intervals.sort(
      (left, right) =>
        left.startYear - right.startYear || left.endYear - right.endYear || right.score - left.score
    )
  }

  const searchTextByEpisode = new Map<number, string>()
  for (const [episodeId, parts] of searchParts) {
    searchTextByEpisode.set(episodeId, parts.join("\n").toLocaleLowerCase())
  }

  return {
    intervalsByEpisode,
    mappedEpisodeIds,
    clusteredEpisodeIds,
    bestHistoricalYearByEpisode,
    searchTextByEpisode,
  }
}

export function getExplorationIndex(dataset: Dataset): ExplorationIndex {
  const cached = indexCache.get(dataset)
  if (cached) return cached
  const index = buildExplorationIndex(dataset)
  indexCache.set(dataset, index)
  return index
}
