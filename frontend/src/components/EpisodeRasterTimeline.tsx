import { useEffect, useMemo, useRef, useState } from "react"
import type { Dataset } from "../types"
import { buildDensitySeries, buildEpisodeRasterRows } from "../utils/episodeRaster"
import TimelineBarBlock from "./timeline/TimelineBarBlock"

type Episode = Dataset["episodes"][number]

export interface EpisodeRasterTimelineProps {
  dataset: Dataset
  episodes: Episode[]
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
  visibleYearRange?: [number, number]
}

const MARGIN = { top: 16, right: 20, bottom: 30, left: 66 }

function colorForPodcast(podcastId: number): string {
  const hue = (podcastId * 67) % 360
  return `hsl(${hue}, 68%, 56%)`
}

export default function EpisodeRasterTimeline(props: EpisodeRasterTimelineProps): JSX.Element {
  const rootRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 900, height: 420 })

  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const ro = new ResizeObserver(entries => {
      const r = entries[0]?.contentRect
      if (!r) return
      setDimensions({
        width: Math.max(420, Math.floor(r.width)),
        height: Math.max(260, Math.floor(r.height)),
      })
    })
    ro.observe(root)
    return () => ro.disconnect()
  }, [])

  const rows = useMemo(
    () => buildEpisodeRasterRows(props.dataset, props.episodes),
    [props.dataset, props.episodes]
  )

  const [minYear, maxYear] = useMemo<[number, number]>(() => {
    if (props.visibleYearRange) return props.visibleYearRange
    if (rows.length === 0) return [0, new Date().getUTCFullYear()]
    let lo = Number.POSITIVE_INFINITY
    let hi = Number.NEGATIVE_INFINITY
    for (const row of rows) {
      for (const it of row.intervals) {
        lo = Math.min(lo, it.startYear)
        hi = Math.max(hi, it.endYear)
      }
    }
    if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [0, new Date().getUTCFullYear()]
    return [Math.floor(lo), Math.ceil(hi)]
  }, [props.visibleYearRange, rows])

  const clippedRows = useMemo(() => {
    return rows
      .map(row => ({
        ...row,
        intervals: row.intervals.filter(it => it.endYear >= minYear && it.startYear <= maxYear),
      }))
      .filter(row => row.intervals.length > 0)
  }, [rows, minYear, maxYear])

  const density = useMemo(
    () => buildDensitySeries(clippedRows, minYear, maxYear),
    [clippedRows, minYear, maxYear]
  )

  const densityMax = useMemo(() => Math.max(1, ...density.map(d => d.count)), [density])

  const innerWidth = Math.max(100, dimensions.width - MARGIN.left - MARGIN.right)
  const innerHeight = Math.max(100, dimensions.height - MARGIN.top - MARGIN.bottom)
  const densityHeight = Math.min(110, Math.max(70, Math.floor(innerHeight * 0.24)))
  const rasterTop = MARGIN.top + densityHeight + 12
  const rasterHeight = Math.max(40, dimensions.height - rasterTop - MARGIN.bottom)
  const rowGap = 1
  const rowHeight = Math.max(
    3,
    Math.floor(
      (rasterHeight - rowGap * Math.max(0, clippedRows.length - 1)) /
        Math.max(1, clippedRows.length)
    )
  )

  const x = (year: number) => {
    const f = (year - minYear) / Math.max(1, maxYear - minYear)
    return MARGIN.left + Math.max(0, Math.min(1, f)) * innerWidth
  }
  const yDensity = (count: number) => {
    const f = count / Math.max(1, densityMax)
    return MARGIN.top + densityHeight - f * densityHeight
  }

  const xTicks = useMemo(() => {
    const span = Math.max(1, maxYear - minYear)
    const approx = Math.max(3, Math.floor(innerWidth / 90))
    const rawStep = Math.max(1, span / approx)
    const base = 10 ** Math.floor(Math.log10(rawStep))
    const step = [1, 2, 5, 10].map(v => v * base).find(v => v >= rawStep) ?? base * 10
    const out: number[] = []
    const first = Math.ceil(minYear / step) * step
    for (let y = first; y <= maxYear; y += step) out.push(y)
    if (!out.includes(minYear)) out.unshift(minYear)
    if (!out.includes(maxYear)) out.push(maxYear)
    return out
  }, [minYear, maxYear, innerWidth])

  return (
    <div
      ref={rootRef}
      className="h-full w-full rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2"
      data-testid="episode-raster-timeline"
    >
      <div className="mb-1 flex items-baseline justify-between text-xs text-[color:var(--muted)]">
        <span>Episode overlap timeline (density + interval raster)</span>
        <span>{clippedRows.length} episodes</span>
      </div>

      <svg
        width={dimensions.width}
        height={dimensions.height - 28}
        style={{ display: "block", width: "100%", height: "calc(100% - 24px)" }}
      >
        <line
          x1={MARGIN.left}
          x2={MARGIN.left}
          y1={MARGIN.top}
          y2={MARGIN.top + densityHeight}
          stroke="rgba(230,230,250,0.35)"
          strokeWidth={1}
        />
        <line
          x1={MARGIN.left}
          x2={MARGIN.left + innerWidth}
          y1={MARGIN.top + densityHeight}
          y2={MARGIN.top + densityHeight}
          stroke="rgba(230,230,250,0.35)"
          strokeWidth={1}
        />
        <text x={8} y={MARGIN.top + 12} fill="rgba(230,230,250,0.9)" fontSize={11}>
          episodes
        </text>

        {density.map(d => {
          const x0 = x(d.year)
          const x1 = x(d.year + 1)
          return (
            <TimelineBarBlock
              key={`density-${d.year}`}
              x={x0}
              y={yDensity(d.count)}
              width={Math.max(1, x1 - x0)}
              height={MARGIN.top + densityHeight - yDensity(d.count)}
              fill="rgba(164,144,194,0.42)"
              stroke="rgba(255,255,255,0.12)"
              strokeWidth={0.3}
              rx={0.2}
              title={`${d.year}: ${d.count} episodes`}
            />
          )
        })}

        <line
          x1={MARGIN.left}
          x2={MARGIN.left}
          y1={rasterTop}
          y2={rasterTop + rasterHeight}
          stroke="rgba(230,230,250,0.35)"
          strokeWidth={1}
        />

        {clippedRows.map((row, idx) => {
          const y = rasterTop + idx * (rowHeight + rowGap)
          return (
            <g key={`row-${row.episodeId}`}>
              {row.intervals.map(it => {
                const x0 = x(it.startYear)
                const x1 = x(it.endYear + 1)
                const active = props.selectedEpisodeId === row.episodeId
                return (
                  <g
                    key={it.id}
                    onClick={() => props.onSelectEpisode(row.episodeId)}
                    style={{ cursor: "pointer" }}
                  >
                    <TimelineBarBlock
                      x={x0}
                      y={y}
                      width={Math.max(1.5, x1 - x0)}
                      height={rowHeight}
                      fill={colorForPodcast(row.podcastId)}
                      stroke={active ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.16)"}
                      strokeWidth={active ? 1.2 : 0.45}
                      rx={1.2}
                      opacity={active ? 0.98 : 0.82}
                      title={`${row.title}: ${it.startYear}–${it.endYear}`}
                    />
                  </g>
                )
              })}
            </g>
          )
        })}

        {xTicks.map(year => {
          const xx = x(year)
          return (
            <g key={`tick-${year}`}>
              <line
                x1={xx}
                x2={xx}
                y1={rasterTop + rasterHeight}
                y2={rasterTop + rasterHeight + 5}
                stroke="rgba(230,230,250,0.42)"
                strokeWidth={1}
              />
              <text
                x={xx}
                y={rasterTop + rasterHeight + 18}
                textAnchor="middle"
                fill="rgba(230,230,250,0.9)"
                fontSize={11}
              >
                {year < 0 ? `${Math.abs(year)} BCE` : year}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
