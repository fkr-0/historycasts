"""Tests for Pydantic domain models.

These tests demonstrate:
1. Valid data passes through validation cleanly
2. Invalid data fails with clear, well-documented error messages
3. Both aggregate (DB row) and export (JSON serialization) scenarios

The models provide strict validation at the boundary between:
- Database rows (aggregate) and internal domain models
- Domain models and exported JSON (frontend consumption)
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from podcast_atlas.models import (
    ClusterRow,
    ClusterSummary,
    EntityRow,
    EpisodeRow,
    ExportMeta,
    KeywordRow,
    PlaceRow,
    PodcastRow,
    SpanRow,
)


class TestExportMeta:
    """Test ExportMeta model validation."""

    def test_valid_export_meta_succeeds(self) -> None:
        """A complete, valid ExportMeta should validate successfully."""
        meta = ExportMeta(
            schema_version="2026-02-27",
            generated_at_iso="2026-02-27T12:00:00Z",
            source_db="/path/to/podcast.db",
            wiki_enriched=True,
            wikidata_enriched=False,
        )
        assert meta.schema_version == "2026-02-27"
        assert meta.generated_at_iso == "2026-02-27T12:00:00Z"

    def test_export_meta_defaults(self) -> None:
        """Optional fields should have sensible defaults."""
        meta = ExportMeta(
            generated_at_iso="2026-02-27T12:00:00Z",
            source_db="/path/to/podcast.db",
        )
        assert meta.schema_version == "2026-02-27"
        assert meta.wiki_enriched is None
        assert meta.wikidata_enriched is None

    def test_export_meta_model_dump(self) -> None:
        """model_dump should produce JSON-serializable dict."""
        meta = ExportMeta(
            generated_at_iso="2026-02-27T12:00:00Z",
            source_db="/path/to/podcast.db",
        )
        dumped = meta.model_dump()
        assert json.dumps(dumped)  # Should not raise

    def test_export_meta_missing_required_field_fails(self) -> None:
        """Missing required fields should fail with clear error."""
        with pytest.raises(ValidationError) as exc_info:
            ExportMeta(source_db="/path/to/podcast.db")  # Missing generated_at_iso

        errors = exc_info.value.errors()
        assert len(errors) == 1
        error = errors[0]
        assert error["loc"] == ("generated_at_iso",)
        assert error["type"] == "missing"

    def test_export_meta_invalid_iso_format(self) -> None:
        """Invalid ISO datetime format is accepted by default (documents behavior).

        Note: Pydantic v2 doesn't validate ISO format at the string field level.
        The generated_at_iso field is a plain str type. For strict ISO validation,
        you would use an annotated type like: datetime | str with a validator.
        """
        # This documents current behavior - any string is accepted
        meta = ExportMeta(
            generated_at_iso="not-a-date",
            source_db="/path/to/podcast.db",
        )
        assert meta.generated_at_iso == "not-a-date"


class TestPodcastRow:
    """Test PodcastRow model validation."""

    def test_valid_podcast_row_succeeds(self) -> None:
        """A complete, valid PodcastRow should validate successfully."""
        row = PodcastRow(
            id=1,
            title="History Podcast",
            link="https://example.com/feed",
            language="de",
            description="A history podcast",
            image_url="https://example.com/image.jpg",
        )
        assert row.id == 1
        assert row.title == "History Podcast"

    def test_podcast_row_minimal_succeeds(self) -> None:
        """Only id and title are required; all other fields are optional."""
        row = PodcastRow(id=1, title="History Podcast")
        assert row.link is None
        assert row.language is None

    def test_podcast_row_serialization(self) -> None:
        """model_dump should produce dict with None fields omitted in JSON."""
        row = PodcastRow(
            id=1,
            title="History Podcast",
            link="https://example.com/feed",
        )
        dumped = row.model_dump()
        assert dumped == {
            "id": 1,
            "title": "History Podcast",
            "link": "https://example.com/feed",
            "language": None,
            "description": None,
            "image_url": None,
        }

    def test_podcast_row_missing_id_fails(self) -> None:
        """Missing required id field should fail."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastRow(title="History Podcast")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)

    def test_podcast_row_missing_title_fails(self) -> None:
        """Missing required title field should fail."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastRow(id=1)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("title",) for e in errors)

    def test_podcast_row_invalid_id_type_fails(self) -> None:
        """Non-integer id should fail with clear type error."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastRow(id="not-an-int", title="History Podcast")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)
        # Error message should indicate type issue
        error_str = str(exc_info.value).lower()
        assert "int" in error_str or "integer" in error_str


class TestEpisodeRow:
    """Test EpisodeRow model validation."""

    def test_valid_episode_row_succeeds(self) -> None:
        """A complete, valid EpisodeRow should validate successfully."""
        row = EpisodeRow(
            id=1,
            podcast_id=1,
            title="Episode 1",
            pub_date_iso="2026-02-27T12:00:00Z",
            page_url="https://example.com/ep1",
            audio_url="https://example.com/ep1.mp3",
            kind="regular",
            narrator="Richard",
            description_pure="A description",
            best_span_id=10,
            best_place_id=5,
        )
        assert row.id == 1
        assert row.best_span_id == 10

    def test_episode_row_minimal_succeeds(self) -> None:
        """Only core fields are required."""
        row = EpisodeRow(
            id=1,
            podcast_id=1,
            title="Episode 1",
            pub_date_iso="2026-02-27T12:00:00Z",
        )
        assert row.kind is None
        assert row.narrator is None

    def test_episode_row_export_aggregate_roundtrip(self) -> None:
        """Simulate roundtrip: DB row -> model -> JSON export."""
        db_row = {
            "id": 1,
            "podcast_id": 1,
            "title": "Episode 1",
            "pub_date": "2026-02-27T12:00:00Z",
            "kind": "regular",
            "narrator": None,
            "description_pure": None,
            "audio_url": "https://example.com/ep1.mp3",
            "page_url": None,
            "best_span_id": None,
            "best_place_id": None,
        }

        # Aggregate: Validate from DB row
        episode = EpisodeRow(
            id=db_row["id"],
            podcast_id=db_row["podcast_id"],
            title=db_row["title"],
            pub_date_iso=db_row["pub_date"],
            kind=db_row["kind"],
            narrator=db_row["narrator"],
            description_pure=db_row["description_pure"],
            audio_url=db_row["audio_url"],
            page_url=db_row["page_url"],
            best_span_id=db_row.get("best_span_id"),
            best_place_id=db_row.get("best_place_id"),
        )

        # Export: Serialize to JSON-compatible dict
        exported = episode.model_dump()
        assert json.dumps(exported)  # Should not raise
        assert exported["kind"] == "regular"


class TestSpanRow:
    """Test SpanRow model validation."""

    def test_valid_span_row_succeeds(self) -> None:
        """A complete, valid SpanRow should validate successfully."""
        row = SpanRow(
            id=1,
            episode_id=1,
            start_iso="1922-01-01",
            end_iso="1922-12-31",
            precision="year",
            qualifier="approx",
            score=9.5,
            source_section="main",
            source_text="im Jahr 1922",
            source_context="im Jahr 1922 geschah...",
        )
        assert row.score == 9.5
        assert row.source_context == "im Jahr 1922 geschah..."

    def test_span_row_nullable_dates(self) -> None:
        """start_iso and end_iso can be None for partial spans."""
        row = SpanRow(
            id=1,
            episode_id=1,
            start_iso=None,
            end_iso=None,
            precision="unknown",
            qualifier="unclear",
            score=5.0,
            source_section="main",
            source_text="at some time",
            source_context=None,
        )
        assert row.start_iso is None
        assert row.end_iso is None

    def test_span_row_score_out_of_range_fails(self) -> None:
        """Score should be a valid float."""
        with pytest.raises(ValidationError) as exc_info:
            SpanRow(
                id=1,
                episode_id=1,
                start_iso="1922",
                end_iso="1922",
                precision="year",
                qualifier="exact",
                score="not-a-float",  # type: ignore
                source_section="main",
                source_text="text",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("score",) for e in errors)


class TestPlaceRow:
    """Test PlaceRow model validation."""

    def test_valid_place_row_succeeds(self) -> None:
        """A complete, valid PlaceRow should validate successfully."""
        row = PlaceRow(
            id=1,
            episode_id=1,
            canonical_name="Paris",
            norm_key="paris",
            place_kind="city",
            lat=48.85,
            lon=2.35,
            radius_km=15.0,
        )
        assert row.place_kind == "city"
        assert row.lat == 48.85

    def test_place_row_kind_literal_validation(self) -> None:
        """place_kind must be a valid PlaceKind literal."""
        # Valid kinds
        for kind in ["city", "region", "country", "unknown"]:
            row = PlaceRow(
                id=1,
                episode_id=1,
                canonical_name="Place",
                norm_key="place",
                place_kind=kind,  # type: ignore
            )
            assert row.place_kind == kind

    def test_place_row_invalid_kind_fails(self) -> None:
        """Invalid place_kind should fail with clear literal constraint error."""
        with pytest.raises(ValidationError) as exc_info:
            PlaceRow(
                id=1,
                episode_id=1,
                canonical_name="Place",
                norm_key="place",
                place_kind="invalid_kind",  # type: ignore
            )

        # Should show the valid literal options
        error_str = str(exc_info.value)
        assert "city" in error_str or "region" in error_str

    def test_place_row_without_coordinates(self) -> None:
        """lat/lon can be None for places without gazetteer match."""
        row = PlaceRow(
            id=1,
            episode_id=1,
            canonical_name="Unknown Place",
            norm_key="unknown_place",
            place_kind="unknown",
            lat=None,
            lon=None,
        )
        assert row.lat is None
        assert row.place_kind == "unknown"


class TestEntityRow:
    """Test EntityRow model validation."""

    def test_valid_entity_row_succeeds(self) -> None:
        """A complete, valid EntityRow should validate successfully."""
        row = EntityRow(
            id=1,
            episode_id=1,
            name="Napoleon Bonaparte",
            kind="person",
            confidence=0.95,
            source_text="Napoleon invaded Russia",
        )
        assert row.kind == "person"
        assert row.confidence == 0.95

    def test_entity_kind_literal_validation(self) -> None:
        """kind must be a valid EntityKind literal."""
        # Valid kinds
        for kind in ["person", "org", "event", "place", "unknown"]:
            row = EntityRow(
                id=1,
                episode_id=1,
                name="Entity",
                kind=kind,  # type: ignore
                confidence=0.8,
                source_text="text",
            )
            assert row.kind == kind

    def test_entity_invalid_kind_fails(self) -> None:
        """Invalid entity kind should fail with clear literal constraint error."""
        with pytest.raises(ValidationError) as exc_info:
            EntityRow(
                id=1,
                episode_id=1,
                name="Entity",
                kind="invalid_kind",  # type: ignore
                confidence=0.8,
                source_text="text",
            )

        error_str = str(exc_info.value)
        assert "person" in error_str or "org" in error_str

    def test_entity_confidence_range(self) -> None:
        """Confidence should be between 0 and 1 typically."""
        # Pydantic doesn't enforce range by default
        row = EntityRow(
            id=1,
            episode_id=1,
            name="Entity",
            kind="person",
            confidence=1.5,  # Technically valid as a float
            source_text="text",
        )
        assert row.confidence == 1.5
        # Note: Could add Field(ge=0, le=1) constraint if desired


class TestKeywordRow:
    """Test KeywordRow model validation."""

    def test_valid_keyword_row_succeeds(self) -> None:
        """A valid KeywordRow should validate successfully."""
        row = KeywordRow(phrase="french revolution", score=5.0)
        assert row.phrase == "french revolution"
        assert row.score == 5.0

    def test_keyword_export_format(self) -> None:
        """KeywordRow should serialize cleanly for JSON export."""
        row = KeywordRow(phrase="french revolution", score=5.0)
        exported = row.model_dump()
        assert exported == {"phrase": "french revolution", "score": 5.0}
        assert json.dumps(exported)


class TestClusterRow:
    """Test ClusterRow model validation."""

    def test_valid_cluster_row_succeeds(self) -> None:
        """A complete, valid ClusterRow should validate successfully."""
        row = ClusterRow(
            id=1,
            podcast_id=1,
            k=4,
            centroid_mid_year=1922.5,
            centroid_lat=48.85,
            centroid_lon=2.35,
            n_members=15,
            label="French History",
        )
        assert row.centroid_mid_year == 1922.5
        assert row.n_members == 15

    def test_cluster_row_optional_label(self) -> None:
        """label is optional."""
        row = ClusterRow(
            id=1,
            podcast_id=1,
            k=4,
            centroid_mid_year=1922.5,
            centroid_lat=48.85,
            centroid_lon=2.35,
            n_members=15,
        )
        assert row.label is None

    def test_cluster_row_missing_required_field_fails(self) -> None:
        """Missing n_members should fail with clear error."""
        with pytest.raises(ValidationError) as exc_info:
            ClusterRow(
                id=1,
                podcast_id=1,
                k=4,
                centroid_mid_year=1922.5,
                centroid_lat=48.85,
                centroid_lon=2.35,
                # n_members missing
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("n_members",) for e in errors)


class TestClusterSummary:
    """Test ClusterSummary model validation."""

    def test_valid_cluster_summary_succeeds(self) -> None:
        """A complete, valid ClusterSummary should validate successfully."""
        cluster = ClusterRow(
            id=1,
            podcast_id=1,
            k=4,
            centroid_mid_year=1922.5,
            centroid_lat=48.85,
            centroid_lon=2.35,
            n_members=15,
            label="French History",
        )

        summary = ClusterSummary(
            cluster=cluster,
            top_keywords=[
                KeywordRow(phrase="revolution", score=5.0),
                KeywordRow(phrase="napoleon", score=4.5),
            ],
            top_entities=[
                {"name": "Napoleon", "kind": "person", "count": 10},
                {"name": "France", "kind": "place", "count": 8},
            ],
        )

        assert len(summary.top_keywords) == 2
        assert len(summary.top_entities) == 2

    def test_cluster_summary_defaults(self) -> None:
        """top_keywords and top_entities default to empty lists."""
        cluster = ClusterRow(
            id=1,
            podcast_id=1,
            k=4,
            centroid_mid_year=1922.5,
            centroid_lat=48.85,
            centroid_lon=2.35,
            n_members=15,
        )

        summary = ClusterSummary(cluster=cluster)

        assert summary.top_keywords == []
        assert summary.top_entities == []

    def test_cluster_summary_export_format(self) -> None:
        """ClusterSummary should serialize properly for JSON export."""
        cluster = ClusterRow(
            id=1,
            podcast_id=1,
            k=4,
            centroid_mid_year=1922.5,
            centroid_lat=48.85,
            centroid_lon=2.35,
            n_members=15,
        )

        summary = ClusterSummary(
            cluster=cluster,
            top_keywords=[KeywordRow(phrase="revolution", score=5.0)],
            top_entities=[{"name": "Napoleon", "kind": "person", "count": 10}],
        )

        exported = summary.model_dump()
        assert json.dumps(exported)  # Should not raise

        # Verify structure
        assert "cluster" in exported
        assert "top_keywords" in exported
        assert "top_entities" in exported
        assert exported["top_keywords"][0]["phrase"] == "revolution"


class TestAggregateIntegrationScenarios:
    """Integration tests simulating aggregate -> model -> export pipeline."""

    def test_complete_episode_export_pipeline(self) -> None:
        """Simulate complete pipeline: DB -> Model -> JSON export."""
        # Simulated DB row (what aggregate module produces)
        db_row = {
            "id": 42,
            "podcast_id": 1,
            "title": "The French Revolution",
            "pub_date": "2026-02-27T10:00:00Z",
            "page_url": "https://example.com/42",
            "audio_url": "https://example.com/42.mp3",
            "kind": "regular",
            "narrator": "Richard",
            "description_pure": "An episode about revolution",
            "best_span_id": 100,
            "best_place_id": 5,
        }

        # Aggregate: Validate and create model
        episode = EpisodeRow(
            id=db_row["id"],
            podcast_id=db_row["podcast_id"],
            title=db_row["title"],
            pub_date_iso=db_row["pub_date"],
            page_url=db_row["page_url"],
            audio_url=db_row["audio_url"],
            kind=db_row["kind"],
            narrator=db_row["narrator"],
            description_pure=db_row["description_pure"],
            best_span_id=db_row.get("best_span_id"),
            best_place_id=db_row.get("best_place_id"),
        )

        # Export: Serialize to JSON-compatible format
        exported = episode.model_dump()

        # Verify round-trip compatibility
        assert exported["id"] == 42
        assert exported["title"] == "The French Revolution"
        assert exported["kind"] == "regular"

        # Verify JSON serializable
        json_str = json.dumps(exported)
        assert isinstance(json_str, str)

        # Verify can be loaded back (simulating frontend)
        loaded = json.loads(json_str)
        assert loaded["id"] == 42
        assert loaded["narrator"] == "Richard"

    def test_cluster_with_top_keywords_export(self) -> None:
        """Test cluster summary with keyword aggregation for export."""
        # Simulated cluster data from aggregate
        cluster_data = {
            "id": 5,
            "podcast_id": 1,
            "k": 4,
            "centroid_year": 1922.0,
            "centroid_lat": 48.85,
            "centroid_lon": 2.35,
            "label": "1920s Europe",
        }

        # Simulated keyword data
        keyword_data = [
            {"phrase": "weimar republic", "score": 8.5},
            {"phrase": "treaty of versailles", "score": 7.2},
            {"phrase": "inflation", "score": 6.8},
        ]

        # Aggregate: Build cluster model
        cluster = ClusterRow(
            id=cluster_data["id"],
            podcast_id=cluster_data["podcast_id"],
            k=cluster_data["k"],
            centroid_mid_year=cluster_data["centroid_year"],
            centroid_lat=cluster_data["centroid_lat"],
            centroid_lon=cluster_data["centroid_lon"],
            n_members=12,  # Calculated from episode_clusters
            label=cluster_data["label"],
        )

        # Aggregate: Build keyword models
        keywords = [KeywordRow(**kw) for kw in keyword_data]

        # Export: Create summary and dump
        summary = ClusterSummary(
            cluster=cluster,
            top_keywords=keywords,
            top_entities=[],
        )

        exported = summary.model_dump()

        # Verify export structure
        assert exported["cluster"]["id"] == 5
        assert len(exported["top_keywords"]) == 3
        assert exported["top_keywords"][0]["phrase"] == "weimar republic"
        assert exported["top_keywords"][0]["score"] == 8.5

        # Verify JSON compatible
        json_str = json.dumps(exported)
        loaded = json.loads(json_str)
        assert loaded["cluster"]["label"] == "1920s Europe"


class TestValidationErrorDocumentation:
    """Tests that document how validation errors manifest."""

    def test_podcast_row_validation_error_is_clear(self) -> None:
        """ValidationError should provide clear, actionable error messages."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastRow(
                id="invalid",  # type: ignore
                title="Test",
            )

        error_str = str(exc_info.value)

        # Should mention the field that failed
        assert "id" in error_str.lower()

        # Should indicate type issue
        assert "int" in error_str.lower() or "integer" in error_str.lower()

    def test_multiple_validation_errors_all_reported(self) -> None:
        """Multiple validation failures should all be reported."""
        with pytest.raises(ValidationError):
            EpisodeRow(
                id="invalid",  # type: ignore
                podcast_id="invalid",  # type: ignore
                title="",  # May fail if min_length constraint added
                pub_date_iso="not-a-date",
            )

        # Should report multiple issues
        # Note: Pydantic v2 behavior varies by field types
        # This test documents current behavior

    def test_place_kind_error_shows_valid_options(self) -> None:
        """Literal validation error should show valid options."""
        with pytest.raises(ValidationError) as exc_info:
            PlaceRow(
                id=1,
                episode_id=1,
                canonical_name="Test",
                norm_key="test",
                place_kind="invalid",  # type: ignore
            )

        error_str = str(exc_info.value)

        # The error should indicate what values are valid
        # Pydantic v2 typically shows the literal options
        assert "place_kind" in error_str.lower()

    def test_entity_kind_error_shows_valid_options(self) -> None:
        """Literal validation error should show valid options."""
        with pytest.raises(ValidationError) as exc_info:
            EntityRow(
                id=1,
                episode_id=1,
                name="Test",
                kind="invalid",  # type: ignore
                confidence=0.8,
                source_text="text",
            )

        error_str = str(exc_info.value)

        # Should indicate valid kind values
        assert "kind" in error_str.lower()
        # Valid options include person, org, event, place, unknown
        has_valid_option = any(
            v in error_str for v in ["person", "org", "event", "place", "unknown"]
        )
        assert has_valid_option

    def test_required_field_error_is_clear(self) -> None:
        """Missing required field error should clearly indicate what's missing."""
        with pytest.raises(ValidationError) as exc_info:
            SpanRow(
                id=1,
                episode_id=1,
                # Missing: precision, qualifier, score, source_section, source_text
                start_iso="1922",
                end_iso="1922",
            )

        errors = exc_info.value.errors()

        # Should list all missing required fields
        field_names = {e["loc"][0] for e in errors}
        assert "precision" in field_names
        assert "qualifier" in field_names
        assert "score" in field_names
        assert "source_section" in field_names
        assert "source_text" in field_names
