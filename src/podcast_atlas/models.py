"""Pydantic domain models for podcast dataset validation and serialization.

These models provide strict type validation for the dataset export,
ensuring data integrity when serializing to JSON for the static frontend.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# Type aliases for literal values
PlaceKind = Literal["city", "region", "country", "unknown"]
EntityKind = Literal["person", "org", "event", "place", "unknown"]


class ExportMeta(BaseModel):
    """Metadata about the exported dataset."""

    schema_version: str = "2026-02-27"
    generated_at_iso: str
    source_db: str
    dataset_revision: str | None = None
    wiki_enriched: bool | None = None
    wikidata_enriched: bool | None = None


class PodcastRow(BaseModel):
    """A podcast feed/channel."""

    id: int
    title: str
    link: str | None = None
    language: str | None = None
    description: str | None = None
    image_url: str | None = None


class EpisodeRow(BaseModel):
    """A single podcast episode."""

    id: int
    podcast_id: int
    title: str
    pub_date_iso: str
    page_url: str | None = None
    audio_url: str | None = None
    kind: str | None = None
    narrator: str | None = None
    description_pure: str | None = None
    best_span_id: int | None = None
    best_place_id: int | None = None
    row_fingerprint: str | None = None


class SpanRow(BaseModel):
    """A time span extracted from episode text."""

    id: int
    episode_id: int
    start_iso: str | None = None
    end_iso: str | None = None
    precision: str
    qualifier: str
    score: float
    source_section: str
    source_text: str
    source_context: str | None = None
    row_fingerprint: str | None = None


class PlaceRow(BaseModel):
    """A geographic place mentioned in an episode."""

    id: int
    episode_id: int
    canonical_name: str
    norm_key: str
    place_kind: PlaceKind
    lat: float | None = None
    lon: float | None = None
    radius_km: float | None = None
    row_fingerprint: str | None = None


class EntityRow(BaseModel):
    """A named entity extracted from episode text."""

    id: int
    episode_id: int
    name: str
    kind: EntityKind
    confidence: float
    source_text: str
    row_fingerprint: str | None = None


class KeywordRow(BaseModel):
    """A keyword/phrase associated with content."""

    phrase: str
    score: float


class ClusterRow(BaseModel):
    """A cluster of related episodes."""

    id: int
    podcast_id: int
    k: int
    centroid_mid_year: float
    centroid_lat: float
    centroid_lon: float
    n_members: int
    label: str | None = None
    row_fingerprint: str | None = None


class ClusterSummary(BaseModel):
    """A cluster with its top keywords and entities."""

    cluster: ClusterRow
    top_keywords: list[KeywordRow] = Field(default_factory=list)
    top_entities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of {name, kind, count} dicts",
    )


class ClusterStatsRow(BaseModel):
    cluster_id: int
    episode_count: int
    unique_podcast_count: int
    dominant_podcast_share: float
    median_pub_year: int | None = None
    temporal_span_years: int | None = None
    mean_span_confidence: float | None = None
    geo_dispersion: float | None = None
    cohesion_proxy: float | None = None


class ClusterTermMetricRow(BaseModel):
    cluster_id: int
    term: str
    tfidf: float
    support: int
    global_support: int
    lift: float
    drop_impact: float


class ClusterCorrelationRow(BaseModel):
    cluster_a: int
    cluster_b: int
    jaccard_episode_overlap: float
    cosine_term_similarity: float
    bridge_terms: list[str] = Field(default_factory=list)


class ClusterTimelineBinRow(BaseModel):
    cluster_id: int
    start_year: int
    end_year: int
    count: int


class ClusterEntityStatRow(BaseModel):
    cluster_id: int
    name: str
    kind: str
    count: int
    lift: float


class ClusterPlaceStatRow(BaseModel):
    cluster_id: int
    canonical_name: str
    count: int
    lift: float
    lat: float | None = None
    lon: float | None = None


class ClusterNextStepRow(BaseModel):
    cluster_id: int
    title: str
    rationale: str
    action_type: str
    action_payload: dict[str, Any] = Field(default_factory=dict)
