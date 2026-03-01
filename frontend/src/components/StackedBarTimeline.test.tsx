import { render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { Dataset } from "../types"
import StackedBarTimeline from "./StackedBarTimeline"

// Create minimal mock dataset for testing
function createMockDataset(): Dataset {
  return {
    meta: {
      schema_version: "1.0",
      generated_at_iso: new Date().toISOString(),
      source_db: "test",
    },
    podcasts: [
      { id: 1, title: "Test Podcast 1", link: "https://example.com", language: "en" },
      { id: 2, title: "Test Podcast 2", link: "https://example.com", language: "en" },
    ],
    episodes: [
      {
        id: 1,
        podcast_id: 1,
        title: "Episode 1",
        pub_date_iso: "2024-01-01T00:00:00Z",
        page_url: "https://example.com/ep1",
        audio_url: "https://example.com/ep1.mp3",
        kind: "interview",
        narrator: "John Doe",
        description_pure: "Test episode",
        best_span_id: 1,
        best_place_id: 1,
      },
      {
        id: 2,
        podcast_id: 2,
        title: "Episode 2",
        pub_date_iso: "2024-02-01T00:00:00Z",
        page_url: "https://example.com/ep2",
        audio_url: "https://example.com/ep2.mp3",
        kind: "interview",
        narrator: "Jane Doe",
        description_pure: "Test episode 2",
        best_span_id: 2,
        best_place_id: 2,
      },
    ],
    spans: [
      {
        id: 1,
        episode_id: 1,
        start_iso: "2024-01-01T00:00:00Z",
        end_iso: "2024-01-02T00:00:00Z",
        precision: "day",
        qualifier: "approximate",
        score: 0.9,
        source_section: "intro",
        source_text: "Test span 1",
      },
      {
        id: 2,
        episode_id: 2,
        start_iso: "2024-02-01T00:00:00Z",
        end_iso: "2024-02-02T00:00:00Z",
        precision: "day",
        qualifier: "approximate",
        score: 0.8,
        source_section: "intro",
        source_text: "Test span 2",
      },
    ],
    places: [
      {
        id: 1,
        episode_id: 1,
        canonical_name: "New York",
        norm_key: "new_york",
        place_kind: "city",
        lat: 40.7128,
        lon: -74.006,
        radius_km: 10,
      },
      {
        id: 2,
        episode_id: 2,
        canonical_name: "London",
        norm_key: "london",
        place_kind: "city",
        lat: 51.5074,
        lon: -0.1278,
        radius_km: 10,
      },
    ],
    entities: [],
    episode_keywords: {},
    episode_clusters: {},
    clusters: [],
  }
}

describe("StackedBarTimeline", () => {
  it("should render an SVG element", () => {
    const mockDataset = createMockDataset()
    const mockEpisodes = mockDataset.episodes

    render(
      <StackedBarTimeline
        dataset={mockDataset}
        episodes={mockEpisodes}
        selectedEpisodeId={null}
        onSelectEpisode={() => {}}
        onScrubYear={() => {}}
      />
    )

    // Check that an SVG element is rendered
    const svg = document.querySelector("svg")
    expect(svg).toBeTruthy()
  })
})
