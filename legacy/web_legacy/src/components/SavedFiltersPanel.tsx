import React, { useEffect, useMemo, useState } from 'react'
import type { EpisodeFilter, SavedFilter, SavedFiltersExport } from '../types'

const STORAGE_KEY = 'podcast-atlas.savedFilters.v1'

function nowIso() {
  return new Date().toISOString()
}

function randomId() {
  return Math.random().toString(16).slice(2) + '-' + Date.now().toString(16)
}

function safeParseJson(text: string): any {
  try {
    return { ok: true as const, value: JSON.parse(text) }
  } catch (e: any) {
    return { ok: false as const, error: String(e?.message ?? e) }
  }
}

function loadSaved(): SavedFilter[] {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return []
  const p = safeParseJson(raw)
  if (!p.ok) return []
  const v = p.value
  if (!Array.isArray(v)) return []
  // soft-validate shape
  return v.filter((x) => x && typeof x.id === 'string' && typeof x.name === 'string' && x.filter)
}

function storeSaved(items: SavedFilter[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

function normalizeFilter(f: EpisodeFilter): EpisodeFilter {
  return {
    podcast_id: f.podcast_id ?? '',
    incident_type: f.incident_type ?? '',
    q: f.q ?? '',
    date_start: f.date_start ?? null,
    date_end: f.date_end ?? null,
    bbox: f.bbox ?? null,
  }
}

export default function SavedFiltersPanel(props: { current: EpisodeFilter; onApply: (f: EpisodeFilter) => void }) {
  const [saved, setSaved] = useState<SavedFilter[]>(() => loadSaved())
  const [name, setName] = useState<string>('')
  const [exportOpen, setExportOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [importText, setImportText] = useState('')
  const [error, setError] = useState<string>('')

  useEffect(() => {
    storeSaved(saved)
  }, [saved])

  const exportPayload: SavedFiltersExport = useMemo(
    () => ({ version: 1, exported_at: nowIso(), saved }),
    [saved],
  )

  function saveCurrent() {
    const nm = name.trim() || `Saved ${new Date().toLocaleString()}`
    const item: SavedFilter = {
      id: randomId(),
      name: nm,
      created_at: nowIso(),
      filter: normalizeFilter(props.current),
    }
    setSaved([item, ...saved])
    setName('')
  }

  function remove(id: string) {
    setSaved(saved.filter((s) => s.id !== id))
  }

  function doImport() {
    setError('')
    const parsed = safeParseJson(importText)
    if (!parsed.ok) {
      setError(`Invalid JSON: ${parsed.error}`)
      return
    }

    const v = parsed.value
    if (!v || v.version !== 1 || !Array.isArray(v.saved)) {
      setError('JSON does not look like a v1 saved-filters export')
      return
    }

    const imported: SavedFilter[] = v.saved
      .filter((x: any) => x && typeof x.id === 'string' && typeof x.name === 'string' && x.filter)
      .map((x: any) => ({
        id: x.id,
        name: x.name,
        created_at: typeof x.created_at === 'string' ? x.created_at : nowIso(),
        filter: normalizeFilter(x.filter),
      }))

    // merge by id (import wins)
    const byId = new Map<string, SavedFilter>()
    for (const s of saved) byId.set(s.id, s)
    for (const s of imported) byId.set(s.id, s)

    setSaved(Array.from(byId.values()).sort((a, b) => b.created_at.localeCompare(a.created_at)))
    setImportText('')
    setImportOpen(false)
  }

  async function copyExport() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(exportPayload, null, 2))
    } catch {
      // ignore
    }
  }

  return (
    <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ fontWeight: 700 }}>Saved filters</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setExportOpen(!exportOpen)} type="button">
            Export
          </button>
          <button onClick={() => setImportOpen(!importOpen)} type="button">
            Import
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'end', flexWrap: 'wrap', marginTop: 8 }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 240, flex: 1 }}>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Berlin + 1980s" />
        </label>
        <button onClick={saveCurrent} type="button">
          Save current filter
        </button>
      </div>

      {exportOpen ? (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: '#444' }}>Export payload (versioned)</div>
          <textarea
            readOnly
            style={{ width: '100%', height: 140, fontFamily: 'monospace', fontSize: 12 }}
            value={JSON.stringify(exportPayload, null, 2)}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={copyExport} type="button">
              Copy
            </button>
          </div>
        </div>
      ) : null}

      {importOpen ? (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: '#444' }}>Paste an export JSON here</div>
          <textarea
            style={{ width: '100%', height: 140, fontFamily: 'monospace', fontSize: 12 }}
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            placeholder='{"version":1, "exported_at":"…", "saved":[…]}'
          />
          {error ? <div style={{ color: 'crimson', fontSize: 12 }}>{error}</div> : null}
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={doImport} type="button">
              Import now
            </button>
          </div>
        </div>
      ) : null}

      <div style={{ marginTop: 10 }}>
        {saved.length === 0 ? (
          <div style={{ fontSize: 12, color: '#444' }}>No saved filters yet.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {saved.map((s) => (
              <div
                key={s.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 10,
                  padding: '6px 8px',
                  background: '#fafafa',
                  borderRadius: 6,
                  border: '1px solid #eee',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{s.name}</div>
                  <div style={{ fontSize: 12, color: '#555' }}>
                    {s.filter.podcast_id ? `podcast:${s.filter.podcast_id} ` : ''}
                    {s.filter.incident_type ? `type:${s.filter.incident_type} ` : ''}
                    {s.filter.q ? `q:"${s.filter.q}" ` : ''}
                    {s.filter.date_start && s.filter.date_end ? `${s.filter.date_start}..${s.filter.date_end}` : ''}
                    {s.filter.bbox ? ' (bbox)' : ''}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <button onClick={() => props.onApply(s.filter)} type="button">
                    Apply
                  </button>
                  <button onClick={() => remove(s.id)} type="button">
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
