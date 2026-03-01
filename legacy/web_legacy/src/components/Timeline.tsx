import React, { useMemo } from 'react'
import { CartesianGrid, Legend, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import type { Episode } from '../types'

const PALETTE = [
  '#1f77b4',
  '#ff7f0e',
  '#2ca02c',
  '#d62728',
  '#9467bd',
  '#8c564b',
  '#e377c2',
  '#7f7f7f',
]

function toMs(iso: string): number {
  return new Date(iso).getTime()
}

function fmtDate(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10)
}

export default function Timeline(props: { episodes: Episode[] }) {
  const podcasts = useMemo(() => {
    const ids = Array.from(new Set(props.episodes.map((e) => e.podcast_id)))
    ids.sort()
    return ids
  }, [props.episodes])

  const podIndex = useMemo(() => {
    const m = new Map<string, number>()
    podcasts.forEach((id, i) => m.set(id, i))
    return m
  }, [podcasts])

  const byIncident = useMemo(() => {
    const m = new Map<string, { x: number; y: number; e: Episode }[]>()
    for (const e of props.episodes) {
      const inc = e.incident_type || 'other'
      const arr = m.get(inc) ?? []
      arr.push({ x: toMs(e.published_at), y: podIndex.get(e.podcast_id) ?? 0, e })
      m.set(inc, arr)
    }
    return Array.from(m.entries()).sort((a, b) => a[0].localeCompare(b[0]))
  }, [props.episodes, podIndex])

  return (
    <div style={{ height: 340, border: '1px solid #ddd', borderRadius: 8 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
          <CartesianGrid />
          <XAxis
            dataKey="x"
            type="number"
            domain={['auto', 'auto']}
            tickFormatter={(v) => fmtDate(v as number)}
            name="date"
          />
          <YAxis
            dataKey="y"
            type="number"
            domain={[0, Math.max(0, podcasts.length - 1)]}
            tickFormatter={(v) => podcasts[Math.round(v as number)] ?? ''}
            name="podcast"
          />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            formatter={(_, __, p) => {
              const e = (p.payload as any).e as Episode
              return [e.title, `${e.podcast_id} • ${fmtDate(toMs(e.published_at))}`]
            }}
          />
          <Legend />
          {byIncident.map(([inc, pts], i) => (
            <Scatter key={inc} name={inc} data={pts} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
