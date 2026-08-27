import { useEffect, useMemo, useRef, useState } from "react"
import type { Dataset } from "../types"
import { buildBinnedDensitySeries, buildEpisodeRasterRows } from "../utils/episodeRaster"
import { colorForCluster } from "../visual/clusterVisuals"
import TimelineBarBlock from "./timeline/TimelineBarBlock"

type Episode = Dataset["episodes"][number]

export interface EpisodeRasterTimelineProps {
  dataset: Dataset
  episodes: Episode[]
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
  visibleYearRange?: [number, number]
  onSelectYearRange?: (range: [number, number]) => void
}

const MARGIN = { top: 16, right: 20, bottom: 30, left: 66 }
const AUTO_ROW_LIMIT = 80
const MAX_RASTER_ROWS = 120

export default function EpisodeRasterTimeline(props: EpisodeRasterTimelineProps): JSX.Element {
  const rootRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 900, height: 420 })
  const [displayMode, setDisplayMode] = useState<"auto" | "density" | "rows">("auto")

  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const ro = new ResizeObserver(entries => {
      const r = entries[0]?.contentRect
      if (!r) return
      setDimensions({
        width: Math.max(220, Math.floor(r.width)),
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

  const innerWidth = Math.max(100, dimensions.width - MARGIN.left - MARGIN.right)
  const innerHeight = Math.max(100, dimensions.height - MARGIN.top - MARGIN.bottom)
  const densityOnly =
    displayMode === "density" || (displayMode === "auto" && clippedRows.length > AUTO_ROW_LIMIT)
  const rasterRows = densityOnly ? [] : clippedRows.slice(0, MAX_RASTER_ROWS)
  const hiddenRowCount = Math.max(0, clippedRows.length - rasterRows.length)

  const density = useMemo(
    () =>
      buildBinnedDensitySeries(
        clippedRows,
        minYear,
        maxYear,
        Math.max(30, Math.floor(innerWidth / 5))
      ),
    [clippedRows, minYear, maxYear, innerWidth]
  )

  const densityMax = useMemo(() => Math.max(1, ...density.map(d => d.count)), [density])

  const densityHeight = densityOnly
    ? Math.max(100, innerHeight - 24)
    : Math.min(110, Math.max(70, Math.floor(innerHeight * 0.24)))
  const rasterTop = MARGIN.top + densityHeight + 12
  const rasterHeight = Math.max(40, dimensions.height - rasterTop - MARGIN.bottom)
  const rowGap = 1
  const rowHeight = Math.max(
    3,
    Math.floor(
      (rasterHeight - rowGap * Math.max(0, rasterRows.length - 1)) / Math.max(1, rasterRows.length)
    )
  )
  const axisY = densityOnly ? MARGIN.top + densityHeight : rasterTop + rasterHeight

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
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-xs text-[color:var(--muted)]">
        <div>
          <span className="font-medium text-[color:var(--text)]">Historical coverage timeline</span>
          <span className="ml-2">density plus episode intervals</span>
        </div>
        <div className="flex items-center gap-2">
          <span>{clippedRows.length} dated episodes</span>
          <label>
            View
            <select
              aria-label="Timeline display mode"
              className="ml-1 py-1 text-xs"
              value={displayMode}
              onChange={event => setDisplayMode(event.target.value as typeof displayMode)}
            >
              <option value="auto">adaptive</option>
              <option value="density">density</option>
              <option value="rows">episode rows</option>
            </select>
          </label>
        </div>
      </div>

      <fieldset
        aria-label="Historical episode density and interval timeline"
        className="m-0 min-w-0 border-0 p-0"
      >
        <svg
          width={dimensions.width}
          height={dimensions.height - 28}
          style={{ display: "block", width: "100%", height: "calc(100% - 24px)" }}
        >
          <title>
            Historical episode density. Select a density bar to zoom; episode intervals open their
            episode.
          </title>
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
            const x0 = x(d.startYear)
            const x1 = x(d.endYear + 1)
            return (
              // biome-ignore lint/a11y/useSemanticElements: SVG has no native button element; keyboard activation and naming are provided.
              <g
                key={`density-${d.startYear}`}
                aria-label={`${d.startYear} to ${d.endYear}: ${d.count} episodes; zoom to range`}
                onClick={() => props.onSelectYearRange?.([d.startYear, d.endYear])}
                onKeyDown={event => {
                  if ((event.key === "Enter" || event.key === " ") && props.onSelectYearRange) {
                    event.preventDefault()
                    props.onSelectYearRange([d.startYear, d.endYear])
                  }
                }}
                role="button"
                tabIndex={0}
              >
                <TimelineBarBlock
                  x={x0}
                  y={yDensity(d.count)}
                  width={Math.max(1, x1 - x0)}
                  height={MARGIN.top + densityHeight - yDensity(d.count)}
                  fill="rgba(164,144,194,0.55)"
                  stroke="rgba(255,255,255,0.16)"
                  strokeWidth={0.4}
                  rx={0.8}
                  title={`${d.startYear}–${d.endYear}: ${d.count} episodes`}
                />
              </g>
            )
          })}

          {!densityOnly && (
            <line
              x1={MARGIN.left}
              x2={MARGIN.left}
              y1={rasterTop}
              y2={rasterTop + rasterHeight}
              stroke="rgba(230,230,250,0.35)"
              strokeWidth={1}
            />
          )}

          {rasterRows.map((row, idx) => {
            const y = rasterTop + idx * (rowHeight + rowGap)
            return (
              <g key={`row-${row.episodeId}`}>
                {row.intervals.map(it => {
                  const x0 = x(it.startYear)
                  const x1 = x(it.endYear + 1)
                  const active = props.selectedEpisodeId === row.episodeId
                  return (
                    // biome-ignore lint/a11y/useSemanticElements: SVG has no native button element; keyboard activation and naming are provided.
                    <g
                      key={it.id}
                      aria-label={`${row.title}: ${it.startYear} to ${it.endYear}; open episode`}
                      onClick={() => props.onSelectEpisode(row.episodeId)}
                      onKeyDown={event => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault()
                          props.onSelectEpisode(row.episodeId)
                        }
                      }}
                      role="button"
                      style={{ cursor: "pointer" }}
                      tabIndex={0}
                    >
                      <TimelineBarBlock
                        x={x0}
                        y={y}
                        width={Math.max(1.5, x1 - x0)}
                        height={rowHeight}
                        fill={row.clusterId ? colorForCluster(row.clusterId) : "#93a3b8"}
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
                  y1={axisY}
                  y2={axisY + 5}
                  stroke="rgba(230,230,250,0.42)"
                  strokeWidth={1}
                />
                <text
                  x={xx}
                  y={axisY + 18}
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
      </fieldset>

      {densityOnly && clippedRows.length > AUTO_ROW_LIMIT && (
        <div className="mt-1 text-[11px] text-[color:var(--muted)]">
          Adaptive mode is showing density because {clippedRows.length} rows would be unreadable.
          Narrow the filters or choose “episode rows” for detail.
        </div>
      )}
      {hiddenRowCount > 0 && !densityOnly && (
        <div className="mt-1 text-[11px] text-[color:var(--muted)]">
          Showing the first {rasterRows.length} chronological rows; {hiddenRowCount} additional rows
          are summarized by the density chart.
        </div>
      )}
    </div>
  )
}
