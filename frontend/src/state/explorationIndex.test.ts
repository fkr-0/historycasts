import { describe, expect, it } from "vitest"
import type { Dataset } from "../types"
import type { Filters } from "../urlState"
import { filterEpisodesBase, filterEpisodesByYearRange } from "./episodeFiltering"
import { getExplorationIndex } from "./explorationIndex"

function fixture(): Dataset {
  return {
    meta: { schema_version: "test", generated_at_iso: "2026-01-01", source_db: "active.db" },
    podcasts: [{ id: 1, title: "History" }],
    episodes: [
      { id: 1, podcast_id: 1, title: "Roman roads", pub_date_iso: "2020-01-01" },
      { id: 2, podcast_id: 1, title: "Industrial cities", pub_date_iso: "2020-01-02" },
      { id: 3, podcast_id: 1, title: "Unknown coast", pub_date_iso: "2020-01-03" },
    ],
    spans: [
      {
        id: 10,
        episode_id: 1,
        start_iso: "0100-01-01",
        end_iso: "0200-01-01",
        precision: "year",
        qualifier: "",
        score: 0.8,
        source_section: "main",
        source_text: "imperial frontier",
      },
      {
        id: 11,
        episode_id: 2,
        start_iso: "1800-01-01",
        end_iso: "1850-01-01",
        precision: "year",
        qualifier: "",
        score: 0.9,
        source_section: "main",
        source_text: "factories",
      },
    ],
    places: [
      {
        id: 20,
        episode_id: 1,
        canonical_name: "Rome",
        norm_key: "rome",
        place_kind: "city",
        lat: 41.9,
        lon: 12.5,
      },
    ],
    entities: [{ id: 30, episode_id: 2, name: "Manchester", kind: "place", confidence: 1 }],
    episode_keywords: { "3": [{ phrase: "navigation", score: 0.8 }] },
    episode_clusters: { "1": 7 },
    clusters: [
      {
        cluster: {
          id: 7,
          podcast_id: 1,
          k: 1,
          label: "Roman world",
          centroid_mid_year: 150,
          centroid_lat: 41.9,
          centroid_lon: 12.5,
          n_members: 1,
        },
        top_keywords: [{ phrase: "legion", score: 1 }],
        top_entities: [],
      },
    ],
  }
}

const filters: Filters = {
  podcastId: "all",
  q: "",
  kind: "all",
  narrator: "",
  geo: "all",
  topN: 1,
  axisK: 1,
}

describe("exploration index", () => {
  it("caches immutable corpus derivations and indexes non-title evidence", () => {
    const dataset = fixture()
    const first = getExplorationIndex(dataset)
    const second = getExplorationIndex(dataset)

    expect(second).toBe(first)
    expect(first.mappedEpisodeIds).toEqual(new Set([1]))
    expect(first.searchTextByEpisode.get(2)).toContain("manchester")
    expect(first.searchTextByEpisode.get(3)).toContain("navigation")
  })

  it("composes corpus search, geography and time without dropping unmapped episodes by default", () => {
    const dataset = fixture()

    expect(filterEpisodesBase(dataset, filters).map(episode => episode.id)).toEqual([1, 2, 3])
    expect(
      filterEpisodesBase(dataset, { ...filters, q: "manchester", geo: "unmapped" }).map(
        episode => episode.id
      )
    ).toEqual([2])

    const mapped = filterEpisodesBase(dataset, { ...filters, geo: "mapped" })
    expect(
      filterEpisodesByYearRange(dataset, mapped, [90, 220]).map(episode => episode.id)
    ).toEqual([1])
  })
})
