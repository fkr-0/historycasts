import { useEffect, useMemo, useRef, useState } from "react"
import { getExplorationIndex } from "../state/explorationIndex"
import type { Dataset } from "../types"
import { colorForCluster } from "../visual/clusterVisuals"
import ClusterLegend from "./ClusterLegend"

type Episode = Dataset["episodes"][number]
export type MapPoint = {
  episodeId: number
  episodeIds: number[]
  title: string
  lat: number
  lon: number
  place: string
  count: number
  clusterId?: number
}

type MapStats = {
  totalEpisodes: number
  visibleEpisodes: number
  totalGeocodedEpisodes: number
  visibleGeocodedEpisodes: number
}

type PlotlyEventPoint = { customdata?: MapPoint }
type PlotlyClickEvent = { points?: PlotlyEventPoint[] }
type PlotlyDiv = HTMLDivElement & {
  on: (event: string, handler: (ev: unknown) => void) => void
  removeAllListeners: (event: string) => void
}

export function buildGazetteerMapData(
  dataset: Dataset,
  visibleEpisodes: Episode[]
): { points: MapPoint[]; stats: MapStats } {
  const geocodedByPlaceId = new Map<
    number,
    { episodeId: number; name: string; lat: number; lon: number }
  >()
  const firstGeocodedByEpisode = new Map<number, { name: string; lat: number; lon: number }>()
  const episodeById = new Map<number, Episode>()
  const visibleEpisodeIdSet = new Set(visibleEpisodes.map(episode => episode.id))
  const points: MapPoint[] = []

  for (const episode of dataset.episodes) episodeById.set(episode.id, episode)

  for (const placeRow of dataset.places) {
    if (placeRow.lat == null || placeRow.lon == null) continue
    const place = {
      episodeId: placeRow.episode_id,
      name: placeRow.canonical_name,
      lat: placeRow.lat,
      lon: placeRow.lon,
    }
    geocodedByPlaceId.set(placeRow.id, place)
    if (!firstGeocodedByEpisode.has(placeRow.episode_id)) {
      firstGeocodedByEpisode.set(placeRow.episode_id, {
        name: placeRow.canonical_name,
        lat: placeRow.lat,
        lon: placeRow.lon,
      })
    }
  }

  const chosenGeocodedByEpisode = new Map<number, { name: string; lat: number; lon: number }>()
  for (const episode of dataset.episodes) {
    const bestPlace =
      episode.best_place_id != null ? geocodedByPlaceId.get(episode.best_place_id) : undefined
    if (bestPlace) {
      chosenGeocodedByEpisode.set(episode.id, {
        name: bestPlace.name,
        lat: bestPlace.lat,
        lon: bestPlace.lon,
      })
      continue
    }
    const fallback = firstGeocodedByEpisode.get(episode.id)
    if (fallback) chosenGeocodedByEpisode.set(episode.id, fallback)
  }

  for (const [episodeId, place] of chosenGeocodedByEpisode) {
    if (!visibleEpisodeIdSet.has(episodeId)) continue
    const episode = episodeById.get(episodeId)
    if (!episode) continue
    points.push({
      episodeId,
      episodeIds: [episodeId],
      title: episode.title,
      lat: place.lat,
      lon: place.lon,
      place: place.name,
      count: 1,
      clusterId: dataset.episode_clusters[String(episodeId)],
    })
  }

  return {
    points,
    stats: {
      totalEpisodes: dataset.episodes.length,
      visibleEpisodes: visibleEpisodes.length,
      totalGeocodedEpisodes: chosenGeocodedByEpisode.size,
      visibleGeocodedEpisodes: points.length,
    },
  }
}

export function aggregateGazetteerMapPoints(points: MapPoint[]): MapPoint[] {
  const grouped = new Map<string, MapPoint>()

  for (const point of points) {
    const key = `${point.place.toLocaleLowerCase()}|${point.lat.toFixed(4)}|${point.lon.toFixed(4)}`
    const current = grouped.get(key)
    if (!current) {
      grouped.set(key, { ...point, episodeIds: [...point.episodeIds] })
      continue
    }
    current.episodeIds.push(...point.episodeIds)
    current.count += point.count
    current.title = `${current.count} episodes at ${current.place}`
    if (current.clusterId !== point.clusterId) current.clusterId = undefined
  }

  return [...grouped.values()].sort(
    (left, right) => right.count - left.count || left.place.localeCompare(right.place)
  )
}

function opacityAtYear(point: MapPoint, years: Map<number, number>, scrubYear?: number): number {
  if (scrubYear == null || Number.isNaN(scrubYear)) return 0.84
  const distances = point.episodeIds
    .map(episodeId => years.get(episodeId))
    .filter((year): year is number => year != null)
    .map(year => Math.abs(year - scrubYear))
  if (distances.length === 0) return 0.35
  const distance = Math.min(...distances)
  const weight = Math.exp(-(distance * distance) / (2 * 55 * 55))
  return 0.2 + weight * 0.8
}

export default function D3GazetteerMap(props: {
  dataset: Dataset
  episodes: Episode[]
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
  scrubYear?: number
}) {
  const plotRef = useRef<HTMLDivElement>(null)
  const [mode, setMode] = useState<"places" | "episodes">("places")

  const { points, stats } = useMemo(
    () => buildGazetteerMapData(props.dataset, props.episodes),
    [props.dataset, props.episodes]
  )
  const placePoints = useMemo(() => aggregateGazetteerMapPoints(points), [points])
  const displayPoints = mode === "places" ? placePoints : points
  const historicalYears = useMemo(
    () => getExplorationIndex(props.dataset).bestHistoricalYearByEpisode,
    [props.dataset]
  )

  useEffect(() => {
    const element = plotRef.current
    if (!element || displayPoints.length === 0) return

    let cancelled = false
    let plotly: typeof import("plotly.js-dist-min").default | null = null
    let plotElement: PlotlyDiv | null = null

    async function renderPlot() {
      const module = await import("plotly.js-dist-min")
      if (cancelled) return
      plotly = module.default

      await plotly.newPlot(
        element,
        [
          {
            type: "scattergeo",
            mode: "markers",
            lat: displayPoints.map(point => point.lat),
            lon: displayPoints.map(point => point.lon),
            text: displayPoints.map(point =>
              point.count > 1
                ? `${point.place}<br>${point.count} episodes`
                : `${point.title}<br>${point.place}`
            ),
            customdata: displayPoints,
            hovertemplate: "%{text}<extra></extra>",
            marker: {
              size: displayPoints.map(point =>
                mode === "places"
                  ? Math.min(28, 7 + Math.sqrt(point.count) * 3.6)
                  : props.selectedEpisodeId === point.episodeId
                    ? 12
                    : 7
              ),
              color: displayPoints.map(point =>
                point.clusterId ? colorForCluster(point.clusterId) : "#93a3b8"
              ),
              opacity: displayPoints.map(point =>
                opacityAtYear(point, historicalYears, props.scrubYear)
              ),
              line: { width: 0.8, color: "rgba(255,255,255,0.45)" },
            },
          },
        ] as unknown as object[],
        {
          margin: { l: 0, r: 0, t: 0, b: 0 },
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          geo: {
            scope: "world",
            projection: { type: "natural earth" },
            showframe: false,
            showcoastlines: true,
            coastlinecolor: "rgba(255,255,255,0.25)",
            showcountries: true,
            countrycolor: "rgba(255,255,255,0.20)",
            showland: true,
            landcolor: "rgba(120,145,172,0.24)",
            showocean: true,
            oceancolor: "rgba(53,79,105,0.22)",
            bgcolor: "rgba(0,0,0,0)",
          },
        },
        { displayModeBar: false, responsive: true }
      )
      if (cancelled) {
        plotly.purge(element)
        return
      }

      const onClick = (event: unknown) => {
        const click = event as PlotlyClickEvent
        const point = click.points?.[0]?.customdata
        if (point?.episodeId != null) props.onSelectEpisode(point.episodeId)
      }

      plotElement = element as PlotlyDiv
      plotElement.on("plotly_click", onClick)
    }

    void renderPlot()

    return () => {
      cancelled = true
      try {
        plotElement?.removeAllListeners("plotly_click")
        plotly?.purge(element)
      } catch {
        // Plotly may already have removed the graph during an async rerender.
      }
    }
  }, [
    displayPoints,
    historicalYears,
    mode,
    props.onSelectEpisode,
    props.scrubYear,
    props.selectedEpisodeId,
  ])

  const visibleClusterIds = [
    ...new Set(points.map(point => point.clusterId).filter((id): id is number => id != null)),
  ]
  const coveragePercent =
    stats.visibleEpisodes === 0
      ? 0
      : Math.round((stats.visibleGeocodedEpisodes / stats.visibleEpisodes) * 100)
  const unmappedCount = Math.max(0, stats.visibleEpisodes - stats.visibleGeocodedEpisodes)
  const topPlaces = placePoints.slice(0, 6)

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-visible rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2">
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold">Historical geography</div>
          <div className="text-[11px] text-[color:var(--muted)]">
            Offline gazetteer matches; marker opacity follows the scrub year.
          </div>
        </div>
        <label className="text-xs text-[color:var(--muted)]">
          Map view
          <select
            aria-label="Map display mode"
            className="ml-2 py-1 text-xs"
            value={mode}
            onChange={event => setMode(event.target.value as typeof mode)}
          >
            <option value="places">place density</option>
            <option value="episodes">episode points</option>
          </select>
        </label>
      </div>

      <div className="mb-2 flex flex-wrap gap-2 text-[11px]">
        <span className="rounded-full border border-[color:var(--border)] px-2 py-1">
          {stats.visibleGeocodedEpisodes} mapped · {coveragePercent}% coverage
        </span>
        <span className="rounded-full border border-[color:var(--border)] px-2 py-1 text-[color:var(--muted)]">
          {unmappedCount} without coordinates
        </span>
        <span className="rounded-full border border-[color:var(--border)] px-2 py-1 text-[color:var(--muted)]">
          {displayPoints.length} visible markers
        </span>
      </div>

      {visibleClusterIds.length > 0 && (
        <div className="mb-2">
          <ClusterLegend dataset={props.dataset} clusterIds={visibleClusterIds} />
        </div>
      )}

      {mode === "places" && topPlaces.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1 text-[10px] text-[color:var(--muted)]">
          <span className="py-1">Top places:</span>
          {topPlaces.map(point => (
            <button
              key={`${point.place}-${point.lat}-${point.lon}`}
              type="button"
              className="px-2 py-1 text-[10px]"
              onClick={() => props.onSelectEpisode(point.episodeId)}
              title={`Open a representative episode for ${point.place}`}
            >
              {point.place} · {point.count}
            </button>
          ))}
        </div>
      )}

      {displayPoints.length === 0 ? (
        <div className="grid min-h-72 flex-1 place-items-center rounded-lg border border-dashed border-[color:var(--border)] px-6 text-center text-sm text-[color:var(--muted)]">
          No mapped episodes are available for the current filters. Broaden the year or source
          filters, or inspect the unmapped count above.
        </div>
      ) : (
        <div
          ref={plotRef}
          aria-label={`${mode === "places" ? "Aggregated place" : "Episode"} map with ${displayPoints.length} markers`}
          className="min-h-0 flex-1"
          role="img"
        />
      )}
    </div>
  )
}
