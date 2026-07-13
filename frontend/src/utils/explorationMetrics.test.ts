import { describe, expect, it } from "vitest"
import type { Dataset } from "../types"
import { buildExplorationMetrics } from "./explorationMetrics"

function datasetFixture(): Dataset {
  return {
    meta: { schema_version: "test", generated_at_iso: "2026-01-01", source_db: "test.db" },
    podcasts: [
      { id: 1, title: "Alpha" },
      { id: 2, title: "Beta" },
    ],
    episodes: [
      { id: 1, podcast_id: 1, title: "One", pub_date_iso: "2020-01-01", best_span_id: 10 },
      { id: 2, podcast_id: 1, title: "Two", pub_date_iso: "2020-01-02" },
      { id: 3, podcast_id: 2, title: "Three", pub_date_iso: "2020-01-03" },
    ],
    spans: [
      {
        id: 10,
        episode_id: 1,
        start_iso: "1800-01-01",
        end_iso: "1810-12-31",
        precision: "year",
        qualifier: "",
        score: 0.9,
        source_section: "main",
        source_text: "1800",
      },
      {
        id: 11,
        episode_id: 2,
        start_iso: "1900-01-01",
        end_iso: "1900-12-31",
        precision: "year",
        qualifier: "",
        score: 0.7,
        source_section: "main",
        source_text: "1900",
      },
    ],
    places: [
      {
        id: 20,
        episode_id: 1,
        canonical_name: "Berlin",
        norm_key: "berlin",
        place_kind: "city",
        lat: 52.5,
        lon: 13.4,
      },
    ],
    entities: [],
    episode_keywords: {},
    episode_clusters: { "1": 100 },
    clusters: [],
  }
}

describe("buildExplorationMetrics", () => {
  it("summarizes visible coverage and builds historical bins", () => {
    const dataset = datasetFixture()
    const metrics = buildExplorationMetrics(dataset, dataset.episodes)

    expect(metrics.coverage).toEqual({
      visibleEpisodes: 3,
      datedEpisodes: 2,
      mappedEpisodes: 1,
      clusteredEpisodes: 1,
    })
    expect(metrics.podcastCoverage[0]).toMatchObject({
      title: "Alpha",
      episodes: 2,
      dated: 2,
      mapped: 1,
      clustered: 1,
    })
    expect(metrics.historicalBins.reduce((sum, bin) => sum + bin.count, 0)).toBe(2)
  })
})
