import { select, geoMercator, geoPath } from "d3"
import { useEffect, useMemo, useRef } from "react"
import type { Dataset } from "../types"

// Simple “dots on a projected plane” map.
// No topojson world outline (keeps it small & static-host friendly).
// You can add borders later if you decide to ship world-atlas/topojson.

type Episode = Dataset["episodes"][number]

function colorForCluster(clusterId: number): string {
  const h = (clusterId * 47) % 360
  return `hsl(${h},65%,45%)`
}

export default function D3GazetteerMap(props: {
  dataset: Dataset
  episodes: Episode[]
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
  scrubYear?: number
}) {
  const svgRef = useRef<SVGSVGElement>(null)

  const points = useMemo(() => {
    const episodeIdSet = new Set(props.episodes.map(e => e.id))
    const episodeMap = new Map<number, Episode>()
    for (const e of props.episodes) episodeMap.set(e.id, e)

    // pick first place per episode (already deduped in exporter typically)
    const placeByEpisode = new Map<number, { lat: number; lon: number; name: string }>()
    for (const p of props.dataset.places) {
      if (!episodeIdSet.has(p.episode_id)) continue
      if (p.lat == null || p.lon == null) continue
      if (!placeByEpisode.has(p.episode_id)) placeByEpisode.set(p.episode_id, { lat: p.lat, lon: p.lon, name: p.canonical_name })
    }

    const out: Array<{
      episodeId: number
      title: string
      lat: number
      lon: number
      place: string
      clusterId?: number
    }> = []

    for (const [episodeId, pl] of placeByEpisode) {
      const ep = episodeMap.get(episodeId)
      if (!ep) continue
      out.push({
        episodeId,
        title: ep.title,
        lat: pl.lat,
        lon: pl.lon,
        place: pl.name,
        clusterId: props.dataset.episode_clusters[String(episodeId)]
      })
    }

    return out
  }, [props.dataset, props.episodes])

  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return

    const width = svg.clientWidth || 800
    const height = svg.clientHeight || 420

    const root = select(svg)
    root.selectAll("*").remove()

    const proj = geoMercator().translate([width / 2, height / 1.7]).scale(Math.min(width, height) * 0.16)
    const path = geoPath(proj)

    // Background sphere
    root
      .append("path")
      .attr("d", path({ type: "Sphere" } as any)!)
      .attr("fill", "rgba(255,255,255,0.03)")
      .attr("stroke", "rgba(255,255,255,0.10)")

    // Dots
    const g = root.append("g")

    g.selectAll("circle")
      .data(points)
      .enter()
      .append("circle")
      .attr("cx", d => proj([d.lon, d.lat])?.[0] ?? -999)
      .attr("cy", d => proj([d.lon, d.lat])?.[1] ?? -999)
      .attr("r", d => (props.selectedEpisodeId === d.episodeId ? 5.5 : 3.2))
      .attr("fill", d => (d.clusterId ? colorForCluster(d.clusterId) : "rgba(200,200,200,0.7)"))
      .attr("fill-opacity", d => (props.selectedEpisodeId === d.episodeId ? 1 : 0.75))
      .attr("stroke", "rgba(255,255,255,0.25)")
      .attr("stroke-width", 0.6)
      .style("cursor", "pointer")
      .on("click", (_, d) => props.onSelectEpisode(d.episodeId))
      .append("title")
      .text(d => `${d.title}\n${d.place}`)

  }, [points, props.selectedEpisodeId])

  return (
    <div className="h-full w-full overflow-hidden rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2">
      <div className="mb-2 flex items-baseline justify-between">
        <div className="text-sm font-semibold">Gazetteer map</div>
        <div className="text-xs text-[color:var(--muted)]">{points.length} episodes with geocoded places</div>
      </div>
      <svg ref={svgRef} className="h-[380px] w-full" />
    </div>
  )
}
