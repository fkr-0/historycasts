import React, { useState } from 'react'
import type { Episode } from '../types'

export default function EpisodeTable(props: { episodes: Episode[] }) {
  const [open, setOpen] = useState<string | null>(null)

  return (
    <div style={{ border: '1px solid #ddd', borderRadius: 8, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#f6f6f6' }}>
            <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #ddd' }}>Date</th>
            <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #ddd' }}>Podcast</th>
            <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #ddd' }}>Title</th>
            <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #ddd' }}>Type</th>
            <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #ddd' }}>Location</th>
          </tr>
        </thead>
        <tbody>
          {props.episodes.map((e) => (
            <React.Fragment key={e.guid}>
              <tr
                onClick={() => setOpen(open === e.guid ? null : e.guid)}
                style={{ cursor: 'pointer' }}
              >
                <td style={{ padding: 8, borderBottom: '1px solid #eee', whiteSpace: 'nowrap' }}>{
                  e.published_at.slice(0, 10)
                }</td>
                <td style={{ padding: 8, borderBottom: '1px solid #eee', whiteSpace: 'nowrap' }}>{e.podcast_id}</td>
                <td style={{ padding: 8, borderBottom: '1px solid #eee' }}>{e.title}</td>
                <td style={{ padding: 8, borderBottom: '1px solid #eee', whiteSpace: 'nowrap' }}>{e.incident_type}</td>
                <td style={{ padding: 8, borderBottom: '1px solid #eee', whiteSpace: 'nowrap' }}>{e.primary_location?.name ?? '—'}</td>
              </tr>
              {open === e.guid ? (
                <tr>
                  <td colSpan={5} style={{ padding: 10, background: '#fafafa', borderBottom: '1px solid #eee' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div>
                        <div style={{ fontWeight: 600, marginBottom: 6 }}>Extracted context</div>
                        <div style={{ fontSize: 13 }}>
                          <div><b>Time:</b> {e.primary_time.kind === 'point' ? e.primary_time.year : e.primary_time.kind}</div>
                          <div><b>Persons:</b> {e.persons.length ? e.persons.join(', ') : '—'}</div>
                          <div><b>Links:</b> {e.links.length ? e.links.join(' • ') : '—'}</div>
                        </div>
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, marginBottom: 6 }}>Description</div>
                        <div style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>{e.description.trim()}</div>
                      </div>
                    </div>
                  </td>
                </tr>
              ) : null}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  )
}
