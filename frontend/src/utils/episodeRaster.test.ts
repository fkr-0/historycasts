import { describe, expect, it } from "vitest"
import type { Dataset } from "../types"
import { buildDensitySeries, buildEpisodeRasterRows } from "./episodeRaster"

function makeDataset(): Dataset {
  return {
    meta: { schema_version: "test", generated_at_iso: new Date().toISOString() },
    podcasts: [{ id: 1, title: "P1" }, { id: 2, title: "P2" }],
    episodes: [
      { id: 10, podcast_id: 1, title: "A", pub_date_iso: "2020-01-01T00:00:00Z" },
      { id: 11, podcast_id: 1, title: "B", pub_date_iso: "2020-01-02T00:00:00Z" },
      { id: 12, podcast_id: 2, title: "C", pub_date_iso: "2020-01-03T00:00:00Z" },
    ],
    spans: [
      { id: 1, episode_id: 10, start_iso: "1800-01-01", end_iso: "1810-12-31", score: 1, source_text: "a" },
      { id: 2, episode_id: 11, start_iso: "-0401-01-01", end_iso: "-0390-12-31", score: 1, source_text: "b" },
      { id: 3, episode_id: 12, start_iso: "1805-01-01", end_iso: "1815-12-31", score: 1, source_text: "c" },
    ],
    places: [],
    entities: [],
    episode_keywords: {},
    episode_clusters: {},
    clusters: [],
  }
}

describe("episodeRaster", () => {
  it("sorts rows by first-mentioned year ascending", () => {
    const ds = makeDataset()
    const rows = buildEpisodeRasterRows(ds, ds.episodes)
    expect(rows.map((r) => r.episodeId)).toEqual([11, 10, 12])
  })

  it("computes episode-overlap density by year", () => {
    const ds = makeDataset()
    const rows = buildEpisodeRasterRows(ds, ds.episodes)
    const series = buildDensitySeries(rows, 1800, 1815)
    const y1804 = series.find((p) => p.year === 1804)
    const y1805 = series.find((p) => p.year === 1805)
    const y1812 = series.find((p) => p.year === 1812)
    expect(y1804?.count).toBe(1)
    expect(y1805?.count).toBe(2)
    expect(y1812?.count).toBe(1)
  })
})
