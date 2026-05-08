import { describe, expect, it, vi } from "vitest"
import type { Dataset } from "../types"

vi.mock("plotly.js-dist-min", () => ({
  default: {
    newPlot: vi.fn(),
    purge: vi.fn(),
  },
}))

import { buildGazetteerMapData } from "./D3GazetteerMap"

function makeDataset(): Dataset {
  return {
    meta: {
      schema_version: "test",
      generated_at_iso: new Date().toISOString(),
      source_db: "test.db",
    },
    podcasts: [{ id: 1, title: "Testcast" }],
    episodes: [
      {
        id: 1,
        podcast_id: 1,
        title: "One",
        pub_date_iso: "2020-01-01T00:00:00Z",
        best_place_id: 101,
      },
      { id: 2, podcast_id: 1, title: "Two", pub_date_iso: "2020-01-02T00:00:00Z" },
      { id: 3, podcast_id: 1, title: "Three", pub_date_iso: "2020-01-03T00:00:00Z" },
    ],
    spans: [],
    places: [
      {
        id: 100,
        episode_id: 1,
        canonical_name: "NoGeo",
        norm_key: "nogeo",
        place_kind: "city",
      },
      {
        id: 101,
        episode_id: 1,
        canonical_name: "Berlin",
        norm_key: "berlin",
        place_kind: "city",
        lat: 52.52,
        lon: 13.4,
      },
      {
        id: 102,
        episode_id: 2,
        canonical_name: "Paris",
        norm_key: "paris",
        place_kind: "city",
        lat: 48.85,
        lon: 2.35,
      },
      {
        id: 103,
        episode_id: 3,
        canonical_name: "Missing",
        norm_key: "missing",
        place_kind: "city",
      },
    ],
    entities: [],
    episode_keywords: {},
    episode_clusters: { "1": 11, "2": 12 },
    clusters: [],
  }
}

describe("buildGazetteerMapData", () => {
  it("returns visible and total geocoded episode stats and honors best_place_id", () => {
    const dataset = makeDataset()
    const visibleEpisodes = dataset.episodes.filter(e => e.id !== 2)

    const result = buildGazetteerMapData(dataset, visibleEpisodes)

    expect(result.stats.totalGeocodedEpisodes).toBe(2)
    expect(result.stats.visibleGeocodedEpisodes).toBe(1)
    expect(result.points).toHaveLength(1)
    expect(result.points[0]?.place).toBe("Berlin")
    expect(result.points[0]?.episodeId).toBe(1)
  })
})
