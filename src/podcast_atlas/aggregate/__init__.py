"""Aggregation subsystem.

This package contains extraction and DB-build primitives used by the
high-level podcast_atlas orchestration layer.
"""

from .cluster import Point, k_for_n, kmeans
from .db_build import build_db
from .extract import (
    Span,
    best_span,
    clean_description,
    extract_entities,
    extract_places,
    extract_spans,
    guess_place_candidates,
    rake_phrases,
    segment_text,
)
from .gazetteer import Gazetteer, GazetteerEntry, load_gazetteer_csv, norm_key
from .rss_parse import EpisodeItem, PodcastInfo, html_to_text, parse_rss
from .schema import ensure_schema

__all__ = [
    "Point",
    "k_for_n",
    "kmeans",
    "build_db",
    "Span",
    "best_span",
    "clean_description",
    "extract_entities",
    "extract_places",
    "extract_spans",
    "guess_place_candidates",
    "rake_phrases",
    "segment_text",
    "Gazetteer",
    "GazetteerEntry",
    "load_gazetteer_csv",
    "norm_key",
    "EpisodeItem",
    "PodcastInfo",
    "html_to_text",
    "parse_rss",
    "ensure_schema",
]
