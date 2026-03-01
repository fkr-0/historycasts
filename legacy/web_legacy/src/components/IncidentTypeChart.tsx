import React, { useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Episode } from '../types'

export default function IncidentTypeChart(props: { episodes: Episode[] }) {
  const data = useMemo(() => {
    const m = new Map<string, number>()
    for (const e of props.episodes) {
      const k = e.incident_type || 'other'
      m.set(k, (m.get(k) ?? 0) + 1)
    }
    return Array.from(m.entries())
      .map(([k, v]) => ({ incident_type: k, count: v }))
      .sort((a, b) => b.count - a.count)
  }, [props.episodes])

  return (
    <div style={{ height: 220, border: '1px solid #ddd', borderRadius: 8, marginTop: 12 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
          <CartesianGrid />
          <XAxis dataKey="incident_type" interval={0} angle={-20} textAnchor="end" height={60} />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
