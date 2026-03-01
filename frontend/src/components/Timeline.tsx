import Plotly from "plotly.js-dist-min"
import { useEffect, useMemo, useRef, useState } from "react"
import type { Dataset } from "../types"

type Ep = Dataset["episodes"][number]
type TimelinePoint = {
  episodeId: number
  title: string
  pubDate: string
  rank: number
  midYear: number
  score: number
  snippet: string
  clusterId?: number
}
type PlotlyEventPoint = { customdata?: TimelinePoint }
type PlotlyHoverEvent = { points?: PlotlyEventPoint[]; event: { clientX: number; clientY: number } }
type PlotlyDiv = HTMLDivElement & {
  on: (event: string, handler: (ev: unknown) => void) => void
  removeAllListeners: (event: string) => void
}

function midYear(span: { start_iso?: string; end_iso?: string }): number | null {
  if (!span.start_iso || !span.end_iso) return null
  const s = new Date(span.start_iso)
  const e = new Date(span.end_iso)
  if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return null
  const mid = new Date((s.getTime() + e.getTime()) / 2)
  return mid.getUTCFullYear() + mid.getUTCMonth() / 12
}

function colorForCluster(clusterId: number): string {
  // deterministic HSL palette
  const h = (clusterId * 47) % 360
  return `hsl(${h},65%,45%)`
}

function opacityByYear(mid: number, scrubYear?: number): number {
  if (scrubYear == null || Number.isNaN(scrubYear)) return 0.85
  const d = Math.abs(mid - scrubYear)
  // gaussian-ish falloff, sigma ~ 40 years
  const sigma = 40
  const w = Math.exp(-(d * d) / (2 * sigma * sigma))
  return 0.15 + 0.85 * w
}

export default function Timeline(props: {
  dataset: Dataset
  episodes: Ep[]
  topN: number
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
  scrubYear?: number
  onScrubYear: (y?: number) => void
  visibleYearRange?: [number, number]
}) {
  const plotRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<HTMLDivElement | null>(null)

  const [playing, setPlaying] = useState(false)

  const [hoverCard, setHoverCard] = useState<{
    x: number
    y: number
    episodeId: number
    spanRank: number
    score: number
    snippet: string
    clusterId?: number
  } | null>(null)

  const spansByEpisode = useMemo(() => {
    const m = new Map<number, Dataset["spans"]>()
    for (const sp of props.dataset.spans) {
      const arr = m.get(sp.episode_id) ?? []
      arr.push(sp)
      m.set(sp.episode_id, arr)
    }
    for (const [k, arr] of m) {
      arr.sort((a, b) => b.score - a.score)
      m.set(k, arr)
    }
    return m
  }, [props.dataset.spans])

  const placeByEpisode = useMemo(() => {
    const m = new Map<number, { lat: number; lon: number; name: string; kind: string }>()
    for (const p of props.dataset.places) {
      if (p.lat == null || p.lon == null) continue
      if (!m.has(p.episode_id))
        m.set(p.episode_id, { lat: p.lat, lon: p.lon, name: p.canonical_name, kind: p.place_kind })
    }
    return m
  }, [props.dataset.places])

  const episodeCluster = props.dataset.episode_clusters

  const timelinePoints = useMemo(() => {
    const pts: TimelinePoint[] = []

    for (const e of props.episodes) {
      const spans = spansByEpisode.get(e.id) ?? []
      const cid = episodeCluster[String(e.id)]
      for (let i = 0; i < Math.min(props.topN, spans.length); i++) {
        const sp = spans[i]
        const my = midYear(sp)
        if (my == null) continue
        if (
          props.visibleYearRange &&
          (my < props.visibleYearRange[0] || my > props.visibleYearRange[1])
        ) {
          continue
        }
        pts.push({
          episodeId: e.id,
          title: e.title,
          pubDate: e.pub_date_iso,
          rank: i + 1,
          midYear: my,
          score: sp.score,
          snippet: sp.source_text,
          clusterId: cid,
        })
      }
    }
    return pts
  }, [props.episodes, spansByEpisode, props.topN, episodeCluster, props.visibleYearRange])

  // drive animation
  useEffect(() => {
    if (!playing) return

    const points = timelinePoints.map(p => p.midYear)
    if (points.length === 0) return

    const minY = Math.floor(Math.min(...points))
    const maxY = Math.ceil(Math.max(...points))

    let y = props.scrubYear ?? minY
    const id = window.setInterval(() => {
      y += 1
      if (y > maxY) y = minY
      props.onScrubYear(y)
    }, 120)

    return () => window.clearInterval(id)
  }, [playing, timelinePoints, props.scrubYear, props.onScrubYear])

  // timeline plot
  useEffect(() => {
    if (!plotRef.current) return
    const el = plotRef.current

    const ranks = [...new Set(timelinePoints.map(p => p.rank))].sort((a, b) => a - b)
    const traces = ranks.map(r => {
      const pts = timelinePoints.filter(p => p.rank === r)
      const opacityBase = r === 1 ? 1.0 : Math.max(0.15, 1 - (r - 1) * 0.18)

      const colors = pts.map(p => (p.clusterId ? colorForCluster(p.clusterId) : "#888"))
      const opacities = pts.map(p => opacityByYear(p.midYear, props.scrubYear) * opacityBase)

      return {
        type: "scatter" as const,
        mode: "markers" as const,
        name: `rank ${r}`,
        x: pts.map(p => p.midYear),
        y: pts.map(() => r),
        text: pts.map(p => p.title),
        customdata: pts,
        marker: {
          size: r === 1 ? 9 : 7,
          color: colors,
          opacity: opacities,
          line: { width: 0 },
        },
        hoverinfo: "none" as const,
      }
    })

    Plotly.newPlot(
      el,
      traces as unknown as object[],
      {
        title: "Historical time mentions (top-N per episode) — colored by cluster",
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#e6e6fa" },
        xaxis: { title: "mid-year" },
        yaxis: { title: "rank", tickmode: "array", tickvals: ranks },
        margin: { l: 50, r: 10, t: 40, b: 40 },
        showlegend: true,
      },
      { displayModeBar: true, responsive: true }
    )

    const onHover = (ev: unknown) => {
      const hover = ev as PlotlyHoverEvent
      const cd = hover.points?.[0]?.customdata
      if (!cd) return
      setHoverCard({
        x: hover.event.clientX,
        y: hover.event.clientY,
        episodeId: cd.episodeId,
        spanRank: cd.rank,
        score: cd.score,
        snippet: cd.snippet,
        clusterId: cd.clusterId,
      })
    }
    const onUnhover = () => setHoverCard(null)
    const onClick = (ev: unknown) => {
      const click = ev as PlotlyHoverEvent
      const cd = click.points?.[0]?.customdata
      if (cd?.episodeId) props.onSelectEpisode(cd.episodeId)
    }

    const plotEl = el as PlotlyDiv
    plotEl.on("plotly_hover", onHover)
    plotEl.on("plotly_unhover", onUnhover)
    plotEl.on("plotly_click", onClick)

    return () => {
      try {
        plotEl.removeAllListeners("plotly_hover")
        plotEl.removeAllListeners("plotly_unhover")
        plotEl.removeAllListeners("plotly_click")
      } catch {
        // ignore
      }
    }
  }, [timelinePoints, props.scrubYear, props.onSelectEpisode])

  // map plot (colored by cluster)
  useEffect(() => {
    if (!mapRef.current) return
    const el = mapRef.current

    const pts = props.episodes
      .map(e => {
        const p = placeByEpisode.get(e.id)
        if (!p) return null
        const cid = episodeCluster[String(e.id)]
        return {
          episodeId: e.id,
          title: e.title,
          lat: p.lat,
          lon: p.lon,
          place: p.name,
          clusterId: cid,
        }
      })
      .filter(Boolean) as {
      episodeId: number
      title: string
      lat: number
      lon: number
      place: string
      clusterId?: number
    }[]

    const colors = pts.map(p => (p.clusterId ? colorForCluster(p.clusterId) : "#888"))
    const opacities = pts.map(p => {
      // approximate mid-year using best span if available
      const spans = spansByEpisode.get(p.episodeId) ?? []
      const my = spans.length ? midYear(spans[0]) : null
      return my == null ? 0.65 : opacityByYear(my, props.scrubYear)
    })

    Plotly.newPlot(
      el,
      [
        {
          type: "scattergeo",
          mode: "markers",
          lat: pts.map(p => p.lat),
          lon: pts.map(p => p.lon),
          text: pts.map(p => p.title),
          customdata: pts,
          marker: { size: 7, color: colors, opacity: opacities },
          hoverinfo: "none",
        },
      ] as unknown as object[],
      {
        title: "Places (offline gazetteer matches) — colored by cluster",
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: "#e6e6fa" },
        geo: { scope: "world" },
        margin: { l: 10, r: 10, t: 40, b: 10 },
      },
      { displayModeBar: true, responsive: true }
    )

    const onHover = (ev: unknown) => {
      const hover = ev as PlotlyHoverEvent
      const cd = hover.points?.[0]?.customdata
      if (!cd) return
      setHoverCard({
        x: hover.event.clientX,
        y: hover.event.clientY,
        episodeId: cd.episodeId,
        spanRank: 0,
        score: 0,
        snippet: `place: ${cd.place}`,
        clusterId: cd.clusterId,
      })
    }
    const onUnhover = () => setHoverCard(null)
    const onClick = (ev: unknown) => {
      const click = ev as PlotlyHoverEvent
      const cd = click.points?.[0]?.customdata
      if (cd?.episodeId) props.onSelectEpisode(cd.episodeId)
    }

    const plotEl = el as PlotlyDiv
    plotEl.on("plotly_hover", onHover)
    plotEl.on("plotly_unhover", onUnhover)
    plotEl.on("plotly_click", onClick)

    return () => {
      try {
        plotEl.removeAllListeners("plotly_hover")
        plotEl.removeAllListeners("plotly_unhover")
        plotEl.removeAllListeners("plotly_click")
      } catch {
        // ignore
      }
    }
  }, [
    props.episodes,
    placeByEpisode,
    props.scrubYear,
    episodeCluster,
    spansByEpisode,
    props.onSelectEpisode,
  ])

  const episodeById = useMemo(() => {
    const m = new Map<number, Ep>()
    for (const e of props.dataset.episodes) m.set(e.id, e)
    return m
  }, [props.dataset.episodes])

  const hoverEpisode = hoverCard ? episodeById.get(hoverCard.episodeId) : null

  return (
    <div
      style={{
        height: "100%",
        display: "grid",
        gridTemplateRows: "auto 1fr 1fr",
        gap: 10,
        position: "relative",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button type="button" onClick={() => setPlaying(p => !p)}>
          {playing ? "pause" : "play"}
        </button>
        <div style={{ fontSize: 12, color: "#555" }}>
          time animation: {props.scrubYear ?? "(disabled)"}
        </div>
        <input
          type="range"
          min={-500}
          max={2026}
          value={props.scrubYear ?? 0}
          onChange={e => props.onScrubYear(Number(e.target.value))}
          style={{ width: 260 }}
        />
        <button type="button" onClick={() => props.onScrubYear(undefined)}>
          clear
        </button>
        <div style={{ marginLeft: "auto", fontSize: 12, color: "#555" }}>
          hover fades by year; clusters color points
        </div>
      </div>

      <div ref={plotRef} style={{ width: "100%", height: "100%" }} />
      <div ref={mapRef} style={{ width: "100%", height: "100%" }} />

      {hoverCard && hoverEpisode && (
        <div
          style={{
            position: "fixed",
            left: hoverCard.x + 14,
            top: hoverCard.y + 14,
            maxWidth: 380,
            background: "white",
            border: "1px solid #ccc",
            borderRadius: 10,
            padding: 10,
            boxShadow: "0 10px 30px rgba(0,0,0,0.15)",
            zIndex: 9999,
            pointerEvents: "none",
          }}
        >
          <div style={{ fontWeight: 700 }}>{hoverEpisode.title}</div>
          <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>
            pub: {new Date(hoverEpisode.pub_date_iso).toLocaleDateString()} · kind:{" "}
            {hoverEpisode.kind ?? "?"} · narrator: {hoverEpisode.narrator ?? "?"}
          </div>
          {hoverCard.clusterId != null && (
            <div style={{ fontSize: 12, color: "#555", marginTop: 4 }}>
              cluster: <b>#{hoverCard.clusterId}</b>
            </div>
          )}
          <div style={{ fontSize: 12, marginTop: 8 }}>
            {hoverCard.spanRank > 0 ? (
              <>
                <div style={{ color: "#555" }}>
                  span rank {hoverCard.spanRank} · score {hoverCard.score.toFixed(2)}
                </div>
                <div>{hoverCard.snippet}</div>
              </>
            ) : (
              <div>{hoverCard.snippet}</div>
            )}
          </div>
          <div style={{ fontSize: 12, color: "#555", marginTop: 8 }}>click to open details →</div>
        </div>
      )}
    </div>
  )
}
