export type PlaceKind = "city" | "region" | "country" | "unknown"
export type EntityKind = "person" | "org" | "event" | "place" | "unknown"

export interface Dataset {
  meta: {
    schema_version: string
    generated_at_iso: string
    source_db: string
    dataset_revision?: string
    wiki_enriched?: boolean
    wikidata_enriched?: boolean
  }
  podcasts: { id: number; title: string; link?: string; language?: string }[]
  episodes: {
    id: number
    podcast_id: number
    title: string
    pub_date_iso: string
    page_url?: string
    audio_url?: string
    kind?: string
    narrator?: string
    description_pure?: string
    best_span_id?: number
    best_place_id?: number
    row_fingerprint?: string
  }[]
  spans: {
    id: number
    episode_id: number
    start_iso?: string
    end_iso?: string
    precision: string
    qualifier: string
    score: number
    source_section: string
    source_text: string
    row_fingerprint?: string
  }[]
  places: {
    id: number
    episode_id: number
    canonical_name: string
    norm_key: string
    place_kind: PlaceKind
    lat?: number
    lon?: number
    radius_km?: number
    row_fingerprint?: string
  }[]
  entities: {
    id: number
    episode_id: number
    name: string
    kind: EntityKind
    confidence: number
    row_fingerprint?: string
  }[]
  episode_keywords: Record<string, { phrase: string; score: number }[]>
  episode_clusters: Record<string, number>
  clusters: {
    cluster: {
      id: number
      podcast_id: number
      k: number
      label: string
      centroid_mid_year: number
      centroid_lat: number
      centroid_lon: number
      n_members: number
      row_fingerprint?: string
    }
    top_keywords: { phrase: string; score: number }[]
    top_entities: { name: string; kind: EntityKind; count: number }[]
  }[]
  concepts?: {
    id: number
    name: string
    url?: string
    qid?: string
    kind?: string
  }[]
  episode_concepts?: Record<string, number[]>
  concept_claims?: {
    concept_id: number
    property: string
    value: string
  }[]
  cluster_stats?: {
    cluster_id: number
    episode_count: number
    unique_podcast_count: number
    dominant_podcast_share: number
    median_pub_year?: number
    temporal_span_years?: number
    mean_span_confidence?: number
    geo_dispersion?: number
    cohesion_proxy?: number
  }[]
  cluster_term_metrics?: {
    cluster_id: number
    term: string
    tfidf: number
    support: number
    global_support: number
    lift: number
    drop_impact: number
  }[]
  cluster_correlations?: {
    cluster_a: number
    cluster_b: number
    jaccard_episode_overlap: number
    cosine_term_similarity: number
    bridge_terms: string[]
  }[]
  cluster_entity_stats?: {
    cluster_id: number
    name: string
    kind: string
    count: number
    lift: number
  }[]
  cluster_place_stats?: {
    cluster_id: number
    canonical_name: string
    count: number
    lift: number
    lat?: number
    lon?: number
  }[]
  cluster_timeline_histogram?: {
    cluster_id: number
    start_year: number
    end_year: number
    count: number
  }[]
  cluster_next_steps?: {
    cluster_id: number
    title: string
    rationale: string
    action_type: string
    action_payload: Record<string, unknown>
  }[]
}
