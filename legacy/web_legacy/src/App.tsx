import React, { useEffect, useMemo, useState } from 'react'
import type { BBox, Episode, EpisodeFilter, Podcast } from './types'
import { PRESETS } from './presets'
import TimeRangeSlider from './components/TimeRangeSlider'
import Timeline from './components/Timeline'
import IncidentTypeChart from './components/IncidentTypeChart'
import MapView from './components/MapView'
import EpisodeTable from './components/EpisodeTable'
import SavedFiltersPanel from './components/SavedFiltersPanel'

const API_BASE = (import.meta as any).env?.VITE_API_BASE ?? 'http://127.0.0.1:8000'

type Meta = {
  min_date: string | null
  max_date: string | null
  incident_types: string[]
  podcasts: Podcast[]
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null)
  const [episodes, setEpisodes] = useState<Episode[]>([])

  const [podcastId, setPodcastId] = useState<string>('')
  const [incidentType, setIncidentType] = useState<string>('')
  const [q, setQ] = useState<string>('')
  const [presetId, setPresetId] = useState<string>('all')

  const [epochMinMax, setEpochMinMax] = useState<[number, number] | null>(null)
  const [epochRange, setEpochRange] = useState<[number, number] | null>(null)

  const [bbox, setBbox] = useState<BBox | null>(null)

  const currentFilter: EpisodeFilter = useMemo(() => {
    const ds = epochRange ? isoDate(new Date(epochRange[0])) : null
    const de = epochRange ? isoDate(new Date(epochRange[1])) : null
    return {
      podcast_id: podcastId,
      incident_type: effectiveIncident,
      q: effectiveQ,
      date_start: ds,
      date_end: de,
      bbox,
    }
  }, [podcastId, effectiveIncident, effectiveQ, epochRange, bbox])

  function applyFilter(f: EpisodeFilter) {
    // Apply explicit values; presets can change and should not be required for reproducibility.
    setPresetId('all')
    setPodcastId(f.podcast_id || '')
    setIncidentType(f.incident_type || '')
    setQ(f.q || '')

    if (f.date_start && f.date_end) {
      const s = new Date(f.date_start + 'T00:00:00Z').getTime()
      const e = new Date(f.date_end + 'T00:00:00Z').getTime()
      setEpochRange([s, e])
    }

    setBbox(f.bbox)
  }

  useEffect(() => {
    fetch(`${API_BASE}/api/meta`)
      .then((r) => r.json())
      .then((m: Meta) => {
        setMeta(m)
        if (m.min_date && m.max_date) {
          const min = new Date(m.min_date + 'T00:00:00Z').getTime()
          const max = new Date(m.max_date + 'T00:00:00Z').getTime()
          setEpochMinMax([min, max])
          setEpochRange([min, max])
        }
      })
  }, [])

  const effectivePreset = useMemo(() => PRESETS.find((p) => p.id === presetId) ?? PRESETS[0], [presetId])

  const effectiveIncident = incidentType || effectivePreset.filter.incident_type || ''
  const effectiveQ = q || effectivePreset.filter.q || ''

  useEffect(() => {
    const params = new URLSearchParams()
    if (podcastId) params.set('podcast_id', podcastId)
    if (effectiveIncident) params.set('incident_type', effectiveIncident)
    if (effectiveQ) params.set('q', effectiveQ)

    if (epochRange) {
      params.set('date_start', isoDate(new Date(epochRange[0])))
      params.set('date_end', isoDate(new Date(epochRange[1])))
    }

    if (bbox) {
      params.set('bbox', `${bbox.minLon},${bbox.minLat},${bbox.maxLon},${bbox.maxLat}`)
    }

    fetch(`${API_BASE}/api/episodes?` + params.toString())
      .then((r) => r.json())
      .then((j) => setEpisodes(j.episodes ?? []))
  }, [podcastId, effectiveIncident, effectiveQ, epochRange, bbox])

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ margin: 0 }}>Podcast Atlas</h1>
      <p style={{ marginTop: 4, color: '#444' }}>
        Timeline + map exploration of RSS podcasts with extracted context (time, place, persons, incident type).
      </p>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end', marginTop: 12 }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          Preset
          <select value={presetId} onChange={(e) => setPresetId(e.target.value)}>
            {PRESETS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          Podcast
          <select value={podcastId} onChange={(e) => setPodcastId(e.target.value)}>
            <option value="">All</option>
            {(meta?.podcasts ?? []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.id} — {p.title}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          Incident type
          <select value={incidentType} onChange={(e) => setIncidentType(e.target.value)}>
            <option value="">(preset / any)</option>
            {(meta?.incident_types ?? []).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 260 }}>
          Text query
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title/description" />
        </label>
      </div>

      <div style={{ marginTop: 12 }}>
        <SavedFiltersPanel current={currentFilter} onApply={applyFilter} />
      </div>

      <div style={{ marginTop: 18 }}>
        <h2 style={{ margin: '8px 0' }}>Time span</h2>
        {epochMinMax && epochRange ? (
          <TimeRangeSlider
            min={epochMinMax[0]}
            max={epochMinMax[1]}
            value={epochRange}
            onChange={setEpochRange}
          />
        ) : (
          <div>Loading…</div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 18 }}>
        <div>
          <h2 style={{ margin: '8px 0' }}>Timeline</h2>
          <Timeline episodes={episodes} />
          <IncidentTypeChart episodes={episodes} />
        </div>
        <div>
          <h2 style={{ margin: '8px 0' }}>Map filter</h2>
          <MapView episodes={episodes} onBboxChange={setBbox} bbox={bbox} />
          <div style={{ fontSize: 12, color: '#444', marginTop: 6 }}>
            Tip: pan/zoom the map. Episodes are filtered to the current view bounds.
          </div>
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <h2 style={{ margin: '8px 0' }}>Episodes ({episodes.length})</h2>
        <EpisodeTable episodes={episodes} />
      </div>
    </div>
  )
}
