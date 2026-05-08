import Plotly from "plotly.js-dist-min"
import { useEffect, useMemo, useRef } from "react"
import type { Dataset } from "../types"

// Simple “dots on a projected plane” map.
// No topojson world outline (keeps it small & static-host friendly).
// You can add borders later if you decide to ship world-atlas/topojson.

type Episode = Dataset["episodes"][number]
type MapPoint = {
  episodeId: number
  title: string
  lat: number
  lon: number
  place: string
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

function colorForCluster(clusterId: number): string {
  const h = (clusterId * 47) % 360
  return `hsl(${h},65%,45%)`
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
  const visibleEpisodeIdSet = new Set(visibleEpisodes.map(e => e.id))
  const points: MapPoint[] = []

  for (const ep of dataset.episodes) episodeById.set(ep.id, ep)

  for (const p of dataset.places) {
    if (p.lat == null || p.lon == null) continue
    const place = { episodeId: p.episode_id, name: p.canonical_name, lat: p.lat, lon: p.lon }
    geocodedByPlaceId.set(p.id, place)
    if (!firstGeocodedByEpisode.has(p.episode_id)) {
      firstGeocodedByEpisode.set(p.episode_id, { name: p.canonical_name, lat: p.lat, lon: p.lon })
    }
  }

  const chosenGeocodedByEpisode = new Map<number, { name: string; lat: number; lon: number }>()
  for (const ep of dataset.episodes) {
    const bestPlace = ep.best_place_id != null ? geocodedByPlaceId.get(ep.best_place_id) : undefined
    if (bestPlace) {
      chosenGeocodedByEpisode.set(ep.id, {
        name: bestPlace.name,
        lat: bestPlace.lat,
        lon: bestPlace.lon,
      })
      continue
    }
    const fallback = firstGeocodedByEpisode.get(ep.id)
    if (fallback) chosenGeocodedByEpisode.set(ep.id, fallback)
  }

  for (const [episodeId, place] of chosenGeocodedByEpisode) {
    if (!visibleEpisodeIdSet.has(episodeId)) continue
    const ep = episodeById.get(episodeId)
    if (!ep) continue
    points.push({
      episodeId,
      title: ep.title,
      lat: place.lat,
      lon: place.lon,
      place: place.name,
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

export default function D3GazetteerMap(props: {
  dataset: Dataset
  episodes: Episode[]
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
  scrubYear?: number
}) {
  const plotRef = useRef<HTMLDivElement>(null)

  const { points, stats } = useMemo(
    () => buildGazetteerMapData(props.dataset, props.episodes),
    [props.dataset, props.episodes]
  )

  useEffect(() => {
    if (!plotRef.current) return
    const el = plotRef.current

    Plotly.newPlot(
      el,
      [
        {
          type: "scattergeo",
          mode: "markers",
          lat: points.map(p => p.lat),
          lon: points.map(p => p.lon),
          text: points.map(p => `${p.title}<br>${p.place}`),
          customdata: points,
          hovertemplate: "%{text}<extra></extra>",
          marker: {
            size: points.map(p => (props.selectedEpisodeId === p.episodeId ? 10 : 7)),
            color: points.map(p => (p.clusterId ? colorForCluster(p.clusterId) : "#93a3b8")),
            opacity: 0.82,
            line: { width: 0.7, color: "rgba(255,255,255,0.35)" },
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

    const onClick = (ev: unknown) => {
      const click = ev as PlotlyClickEvent
      const point = click.points?.[0]?.customdata
      if (point?.episodeId != null) props.onSelectEpisode(point.episodeId)
    }

    const plotEl = el as PlotlyDiv
    plotEl.on("plotly_click", onClick)

    return () => {
      try {
        plotEl.removeAllListeners("plotly_click")
        Plotly.purge(el)
      } catch {
        // ignore
      }
    }
  }, [points, props.selectedEpisodeId, props.onSelectEpisode])

  return (
    <div className="flex h-full min-h-0 w-full flex-col overflow-visible rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2">
      <div className="mb-2 flex items-baseline justify-between">
        <div className="text-sm font-semibold">Gazetteer map</div>
        <div className="text-xs text-[color:var(--muted)]">
          {stats.visibleGeocodedEpisodes} shown / {stats.totalGeocodedEpisodes} geocoded (
          {stats.visibleEpisodes} filtered / {stats.totalEpisodes} total episodes)
        </div>
      </div>
      <div ref={plotRef} className="min-h-0 flex-1" />
    </div>
  )
}
