import { describe, expect, it } from "vitest"
import type { Dataset } from "./types"
import { clusterLabel, clusterLegendRows, colorForCluster } from "./visual/clusterVisuals"

function dataset(): Dataset {
  return {
    meta: { schema_version: "x", generated_at_iso: new Date().toISOString(), source_db: "x.db" },
    podcasts: [],
    episodes: [],
    spans: [],
    places: [],
    entities: [],
    episode_keywords: {},
    episode_clusters: {},
    clusters: [
      {
        cluster: {
          id: 2,
          podcast_id: 1,
          k: 3,
          label: "Power structures",
          centroid_mid_year: 1800,
          centroid_lat: 0,
          centroid_lon: 0,
          n_members: 10,
        },
        top_keywords: [],
        top_entities: [],
      },
      {
        cluster: {
          id: 1,
          podcast_id: 1,
          k: 3,
          label: "",
          centroid_mid_year: 1700,
          centroid_lat: 0,
          centroid_lon: 0,
          n_members: 5,
        },
        top_keywords: [],
        top_entities: [],
      },
    ],
  }
}

describe("clusterVisuals", () => {
  it("builds stable colors and fallback labels", () => {
    expect(colorForCluster(7)).toBe(colorForCluster(7))
    expect(clusterLabel(dataset(), 2)).toBe("Power structures")
    expect(clusterLabel(dataset(), 1)).toBe("Cluster #1")
    expect(clusterLabel(dataset(), 99)).toBe("Cluster #99")
  })

  it("builds sorted legend rows with optional filtering", () => {
    expect(clusterLegendRows(dataset()).map(row => row.id)).toEqual([1, 2])
    expect(clusterLegendRows(dataset(), [2])).toEqual([
      {
        id: 2,
        label: "Power structures",
        memberCount: 10,
        color: colorForCluster(2),
      },
    ])
  })
})
