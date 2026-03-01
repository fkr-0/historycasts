export type Podcast = {
  id: string
  title: string
  feed_url: string
  link: string
}

export type Episode = {
  podcast_id: string
  guid: string
  title: string
  published_at: string
  audio_url?: string | null
  duration_seconds?: number | null
  incident_type: string
  primary_time: {
    kind: string
    year?: number | null
    start_year?: number | null
    end_year?: number | null
  }
  primary_location?: {
    name: string
    country?: string | null
    lat: number
    lon: number
  } | null
  persons: string[]
  links: string[]
  description: string
}

export type BBox = { minLon: number; minLat: number; maxLon: number; maxLat: number }

export type EpisodeFilter = {
  podcast_id: string
  incident_type: string
  q: string
  date_start: string | null
  date_end: string | null
  bbox: BBox | null
}

export type SavedFilter = {
  id: string
  name: string
  created_at: string
  filter: EpisodeFilter
}

export type SavedFiltersExport = {
  version: 1
  exported_at: string
  saved: SavedFilter[]
}
