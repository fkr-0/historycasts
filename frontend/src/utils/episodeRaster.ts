import type { Dataset } from "../types"
import { parseIsoYear } from "./historicalDate"

const MIN_REASONABLE_YEAR = -4000
const MAX_REASONABLE_YEAR = new Date().getUTCFullYear() + 1

export interface EpisodeInterval {
  id: number
  startYear: number
  endYear: number
  score: number
  sourceText: string
}

export interface EpisodeRasterRow {
  episodeId: number
  title: string
  podcastId: number
  firstYear: number
  intervals: EpisodeInterval[]
}

export interface DensityPoint {
  year: number
  count: number
}

export interface DensityBin {
  startYear: number
  endYear: number
  count: number
}

function parseIntervalYears(startIso?: string, endIso?: string): [number, number] | null {
  const a = parseIsoYear(startIso)
  const b = parseIsoYear(endIso)
  if (a == null || b == null) return null
  const lo = Math.min(a, b)
  const hi = Math.max(a, b)
  if (lo < MIN_REASONABLE_YEAR || hi > MAX_REASONABLE_YEAR) return null
  return [lo, hi]
}

export function buildEpisodeRasterRows(
  dataset: Dataset,
  episodes: Dataset["episodes"]
): EpisodeRasterRow[] {
  const byEpisode = new Map<number, EpisodeInterval[]>()

  for (const sp of dataset.spans) {
    const years = parseIntervalYears(sp.start_iso, sp.end_iso)
    if (!years) continue
    const [startYear, endYear] = years
    const arr = byEpisode.get(sp.episode_id) ?? []
    arr.push({
      id: sp.id,
      startYear,
      endYear,
      score: sp.score ?? 0,
      sourceText: sp.source_text ?? "",
    })
    byEpisode.set(sp.episode_id, arr)
  }

  const rows: EpisodeRasterRow[] = []
  for (const ep of episodes) {
    const intervals = byEpisode.get(ep.id) ?? []
    if (intervals.length === 0) continue
    intervals.sort(
      (a, b) => a.startYear - b.startYear || a.endYear - b.endYear || b.score - a.score
    )
    rows.push({
      episodeId: ep.id,
      title: ep.title,
      podcastId: ep.podcast_id,
      firstYear: intervals[0].startYear,
      intervals,
    })
  }

  rows.sort((a, b) => a.firstYear - b.firstYear || a.episodeId - b.episodeId)
  return rows
}

export function buildDensitySeries(
  rows: EpisodeRasterRow[],
  minYear: number,
  maxYear: number
): DensityPoint[] {
  const points: DensityPoint[] = []
  for (let year = minYear; year <= maxYear; year += 1) {
    let count = 0
    for (const row of rows) {
      if (row.intervals.some(it => it.startYear <= year && it.endYear >= year)) {
        count += 1
      }
    }
    points.push({ year, count })
  }
  return points
}

function niceStep(rawStep: number): number {
  if (!Number.isFinite(rawStep) || rawStep <= 1) return 1
  const base = 10 ** Math.floor(Math.log10(rawStep))
  return (
    [1, 2, 5, 10].map(multiplier => multiplier * base).find(step => step >= rawStep) ?? 10 * base
  )
}

export function buildBinnedDensitySeries(
  rows: EpisodeRasterRow[],
  minYear: number,
  maxYear: number,
  maxBins = 180
): DensityBin[] {
  if (rows.length === 0 || maxYear < minYear) return []
  const step = niceStep((maxYear - minYear + 1) / Math.max(1, maxBins))
  const first = Math.floor(minYear / step) * step
  const last = Math.ceil((maxYear + 1) / step) * step
  const bins: DensityBin[] = []

  for (let startYear = first; startYear < last; startYear += step) {
    const endYear = startYear + step - 1
    let count = 0
    for (const row of rows) {
      if (
        row.intervals.some(
          interval => interval.endYear >= startYear && interval.startYear <= endYear
        )
      ) {
        count += 1
      }
    }
    bins.push({ startYear, endYear, count })
  }

  return bins
}
