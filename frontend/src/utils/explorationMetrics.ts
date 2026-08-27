import { getExplorationIndex } from "../state/explorationIndex"
import type { Dataset } from "../types"

export interface CoverageSummary {
  visibleEpisodes: number
  datedEpisodes: number
  mappedEpisodes: number
  clusteredEpisodes: number
}

export interface PodcastCoverageRow {
  podcastId: number
  title: string
  episodes: number
  dated: number
  mapped: number
  clustered: number
}

export interface HistoricalBin {
  startYear: number
  endYear: number
  count: number
}

export interface ExplorationMetrics {
  coverage: CoverageSummary
  podcastCoverage: PodcastCoverageRow[]
  historicalBins: HistoricalBin[]
  historicalYearCount: number
}

function niceStep(rawStep: number): number {
  if (!Number.isFinite(rawStep) || rawStep <= 1) return 1
  const base = 10 ** Math.floor(Math.log10(rawStep))
  return (
    [1, 2, 5, 10].map(multiplier => multiplier * base).find(step => step >= rawStep) ?? 10 * base
  )
}

function buildHistoricalBins(years: number[], maxBins: number): HistoricalBin[] {
  if (years.length === 0) return []
  const minYear = Math.floor(Math.min(...years))
  const maxYear = Math.ceil(Math.max(...years))
  const step = niceStep((maxYear - minYear + 1) / Math.max(1, maxBins))
  const first = Math.floor(minYear / step) * step
  const last = Math.ceil((maxYear + 1) / step) * step
  const bins: HistoricalBin[] = []

  for (let startYear = first; startYear < last; startYear += step) {
    bins.push({ startYear, endYear: startYear + step - 1, count: 0 })
  }

  for (const year of years) {
    const index = Math.min(bins.length - 1, Math.max(0, Math.floor((year - first) / step)))
    bins[index].count += 1
  }

  return bins
}

export function buildExplorationMetrics(
  dataset: Dataset,
  visibleEpisodes: Dataset["episodes"],
  maxHistoricalBins = 24
): ExplorationMetrics {
  const index = getExplorationIndex(dataset)

  const podcastRows = new Map<number, PodcastCoverageRow>()
  const podcastTitles = new Map(dataset.podcasts.map(podcast => [podcast.id, podcast.title]))
  const historicalYears: number[] = []
  let clusteredEpisodes = 0

  for (const episode of visibleEpisodes) {
    const row = podcastRows.get(episode.podcast_id) ?? {
      podcastId: episode.podcast_id,
      title: podcastTitles.get(episode.podcast_id) ?? `Podcast ${episode.podcast_id}`,
      episodes: 0,
      dated: 0,
      mapped: 0,
      clustered: 0,
    }
    row.episodes += 1

    const midYear = index.bestHistoricalYearByEpisode.get(episode.id)
    if (midYear != null) {
      row.dated += 1
      historicalYears.push(midYear)
    }
    if (index.mappedEpisodeIds.has(episode.id)) row.mapped += 1
    if (index.clusteredEpisodeIds.has(episode.id)) {
      row.clustered += 1
      clusteredEpisodes += 1
    }
    podcastRows.set(episode.podcast_id, row)
  }

  return {
    coverage: {
      visibleEpisodes: visibleEpisodes.length,
      datedEpisodes: historicalYears.length,
      mappedEpisodes: visibleEpisodes.filter(episode => index.mappedEpisodeIds.has(episode.id))
        .length,
      clusteredEpisodes,
    },
    podcastCoverage: [...podcastRows.values()].sort(
      (left, right) => right.episodes - left.episodes || left.title.localeCompare(right.title)
    ),
    historicalBins: buildHistoricalBins(historicalYears, maxHistoricalBins),
    historicalYearCount: historicalYears.length,
  }
}
