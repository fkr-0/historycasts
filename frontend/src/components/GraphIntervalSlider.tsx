import { useCallback, useEffect, useMemo, useRef, useState } from "react"

interface SpanLite {
  start_iso?: string
  end_iso?: string
}

export default function GraphIntervalSlider(props: {
  spans: SpanLite[]
  minYear: number
  maxYear: number
  value: [number, number]
  onChange: (next: [number, number]) => void
}) {
  const { spans, minYear, maxYear, value, onChange } = props
  const rootRef = useRef<HTMLDivElement | null>(null)
  const [width, setWidth] = useState(900)
  const [dragging, setDragging] = useState<"min" | "max" | null>(null)

  useEffect(() => {
    const el = rootRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      const w = entries[0]?.contentRect.width ?? 900
      setWidth(Math.max(320, Math.floor(w)))
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const years = useMemo(() => {
    const out: number[] = []
    for (let y = minYear; y <= maxYear; y += 1) out.push(y)
    return out
  }, [minYear, maxYear])

  const series = useMemo(() => {
    const res = years.map(y => ({ year: y, count: 0, avgDur: 0 }))
    const totalDur = new Array(res.length).fill(0)

    for (const sp of spans) {
      if (!sp.start_iso || !sp.end_iso) continue
      const s = new Date(sp.start_iso)
      const e = new Date(sp.end_iso)
      if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) continue

      const a = Math.min(s.getUTCFullYear(), e.getUTCFullYear())
      const b = Math.max(s.getUTCFullYear(), e.getUTCFullYear())
      const dur = Math.max(1, b - a + 1)

      const lo = Math.max(a, minYear)
      const hi = Math.min(b, maxYear)
      for (let y = lo; y <= hi; y += 1) {
        const i = y - minYear
        res[i].count += 1
        totalDur[i] += dur
      }
    }

    for (let i = 0; i < res.length; i += 1) {
      res[i].avgDur = res[i].count > 0 ? totalDur[i] / res[i].count : 0
    }

    return res
  }, [spans, years, minYear, maxYear])

  const maxCount = useMemo(() => Math.max(1, ...series.map(s => s.count)), [series])

  const overallAvg = useMemo(() => {
    let sum = 0
    let n = 0
    for (const p of series) {
      if (p.year < value[0] || p.year > value[1]) continue
      if (p.count <= 0) continue
      sum += p.avgDur
      n += 1
    }
    return n > 0 ? sum / n : 0
  }, [series, value])

  const margin = { top: 12, right: 10, bottom: 18, left: 10 }
  const innerW = Math.max(50, width - margin.left - margin.right)
  const h = 128
  const innerH = h - margin.top - margin.bottom

  const x = (year: number) =>
    margin.left + ((year - minYear) / Math.max(1, maxYear - minYear)) * innerW
  const y = (count: number) => margin.top + (1 - count / maxCount) * innerH

  const points = series.map(p => `${x(p.year)},${y(p.count)}`).join(" ")

  const hotColor = [255, 140, 95]
  const coldColor = [96, 154, 255]

  const colorForYear = (p: (typeof series)[number]) => {
    if (p.count <= 0 || overallAvg <= 0) return "rgba(120,130,160,0.2)"
    const tRaw = Math.max(-1, Math.min(1, (p.avgDur - overallAvg) / overallAvg))
    const t = Math.abs(tRaw)
    const base = tRaw <= 0 ? hotColor : coldColor
    const alpha = 0.2 + 0.55 * t
    return `rgba(${base[0]},${base[1]},${base[2]},${alpha})`
  }

  const toYear = useCallback(
    (clientX: number) => {
      const rect = rootRef.current?.getBoundingClientRect()
      if (!rect) return value[0]
      const clamped = Math.max(
        margin.left,
        Math.min(rect.width - margin.right, clientX - rect.left)
      )
      const f = (clamped - margin.left) / Math.max(1, innerW)
      return Math.round(minYear + f * (maxYear - minYear))
    },
    [innerW, margin.left, margin.right, maxYear, minYear, value]
  )

  useEffect(() => {
    const onMove = (ev: MouseEvent) => {
      if (!dragging) return
      const yv = toYear(ev.clientX)
      if (dragging === "min") {
        onChange([Math.min(yv, value[1] - 1), value[1]])
      } else {
        onChange([value[0], Math.max(yv, value[0] + 1)])
      }
    }
    const onUp = () => setDragging(null)
    window.addEventListener("mousemove", onMove)
    window.addEventListener("mouseup", onUp)
    return () => {
      window.removeEventListener("mousemove", onMove)
      window.removeEventListener("mouseup", onUp)
    }
  }, [dragging, onChange, toYear, value])

  return (
    <div
      ref={rootRef}
      className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/75 p-2"
    >
      <div className="mb-1 flex items-center justify-between text-xs text-[color:var(--muted)]">
        <span>Graph interval slider (coverage + heat)</span>
        <span>
          {value[0]} - {value[1]}
        </span>
      </div>
      <svg width={width} height={h} role="img" aria-label="graph interval slider">
        <rect x={0} y={0} width={width} height={h} fill="transparent" />

        <polyline points={points} fill="none" stroke="rgba(230,230,250,0.92)" strokeWidth={1.5} />

        {series.map(p => {
          const xx = x(p.year)
          const yy = y(p.count)
          return (
            <line
              key={p.year}
              x1={xx}
              y1={h - margin.bottom}
              x2={xx}
              y2={yy}
              stroke={colorForYear(p)}
              strokeWidth={1.6}
            />
          )
        })}

        <rect
          x={margin.left}
          y={margin.top}
          width={Math.max(0, x(value[0]) - margin.left)}
          height={innerH}
          fill="rgba(8,8,16,0.45)"
        />
        <rect
          x={x(value[1])}
          y={margin.top}
          width={Math.max(0, margin.left + innerW - x(value[1]))}
          height={innerH}
          fill="rgba(8,8,16,0.45)"
        />

        <line
          x1={x(value[0])}
          x2={x(value[0])}
          y1={margin.top}
          y2={h - margin.bottom}
          stroke="#e6e6fa"
          strokeWidth={2.5}
        />
        <line
          x1={x(value[1])}
          x2={x(value[1])}
          y1={margin.top}
          y2={h - margin.bottom}
          stroke="#e6e6fa"
          strokeWidth={2.5}
        />

        <circle
          cx={x(value[0])}
          cy={h - margin.bottom}
          r={7}
          fill="#a490c2"
          onMouseDown={() => setDragging("min")}
          onKeyDown={ev => {
            if (ev.key === "ArrowLeft") onChange([Math.max(minYear, value[0] - 1), value[1]])
            if (ev.key === "ArrowRight") onChange([Math.min(value[1] - 1, value[0] + 1), value[1]])
          }}
          role="slider"
          aria-label="Minimum year handle"
          aria-valuemin={minYear}
          aria-valuemax={value[1] - 1}
          aria-valuenow={value[0]}
          tabIndex={0}
          style={{ cursor: "ew-resize" }}
        />
        <circle
          cx={x(value[1])}
          cy={h - margin.bottom}
          r={7}
          fill="#a490c2"
          onMouseDown={() => setDragging("max")}
          onKeyDown={ev => {
            if (ev.key === "ArrowLeft") onChange([value[0], Math.max(value[0] + 1, value[1] - 1)])
            if (ev.key === "ArrowRight") onChange([value[0], Math.min(maxYear, value[1] + 1)])
          }}
          role="slider"
          aria-label="Maximum year handle"
          aria-valuemin={value[0] + 1}
          aria-valuemax={maxYear}
          aria-valuenow={value[1]}
          tabIndex={0}
          style={{ cursor: "ew-resize" }}
        />
      </svg>
    </div>
  )
}
