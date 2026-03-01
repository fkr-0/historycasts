import React, { useEffect, useMemo, useState } from 'react'
import { MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import type { BBox, Episode } from '../types'
import L from 'leaflet'

// Fix default marker icons in Vite/React
import iconUrl from 'leaflet/dist/images/marker-icon.png'
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png'
import shadowUrl from 'leaflet/dist/images/marker-shadow.png'

L.Icon.Default.mergeOptions({
  iconRetinaUrl,
  iconUrl,
  shadowUrl,
})

function FitBounds(props: { bbox: BBox | null }) {
  const map = useMap()
  useEffect(() => {
    if (!props.bbox) return
    const b = props.bbox
    const bounds = L.latLngBounds(
      L.latLng(b.minLat, b.minLon),
      L.latLng(b.maxLat, b.maxLon),
    )
    map.fitBounds(bounds, { animate: false })
  }, [props.bbox])
  return null
}

function BoundsReporter(props: { onChange: (b: BBox) => void }) {
  useMapEvents({
    moveend(e) {
      const b = e.target.getBounds()
      props.onChange({
        minLon: b.getWest(),
        minLat: b.getSouth(),
        maxLon: b.getEast(),
        maxLat: b.getNorth(),
      })
    },
    zoomend(e) {
      const b = e.target.getBounds()
      props.onChange({
        minLon: b.getWest(),
        minLat: b.getSouth(),
        maxLon: b.getEast(),
        maxLat: b.getNorth(),
      })
    },
  })
  return null
}

export default function MapView(props: {
  episodes: Episode[]
  onBboxChange: (b: BBox | null) => void
  bbox?: BBox | null
}) {
  const points = useMemo(() => props.episodes.filter((e) => e.primary_location), [props.episodes])

  // Default center roughly Europe.
  const [center] = useState<[number, number]>([51.0, 10.0])

  // On first render, clear bbox until map reports it.
  useEffect(() => {
    props.onBboxChange(null)
  }, [])

  return (
    <div style={{ height: 340, border: '1px solid #ddd', borderRadius: 8, overflow: 'hidden' }}>
      <MapContainer center={center} zoom={4} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        />
        <BoundsReporter onChange={(b) => props.onBboxChange(b)} />
        <FitBounds bbox={props.bbox ?? null} />
        {points.map((e) => (
          <Marker
            key={e.guid}
            position={[e.primary_location!.lat, e.primary_location!.lon]}
            title={e.title}
          >
            <Popup>
              <div style={{ maxWidth: 260 }}>
                <div style={{ fontWeight: 600 }}>{e.title}</div>
                <div style={{ fontSize: 12, color: '#444' }}>
                  {e.podcast_id} • {e.published_at.slice(0, 10)}
                </div>
                <div style={{ fontSize: 12, marginTop: 6 }}>
                  {e.primary_location?.name} ({e.incident_type})
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
