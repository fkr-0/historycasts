import { describe, expect, test } from "vitest";
import type { Dataset } from "../types";
import {
  clampYearRange,
  filterEpisodesBase,
  filterEpisodesByYearRange,
  hasSpanInYearRange,
  spanYearBounds,
} from "./episodeFiltering";

function makeDataset(): Dataset {
  return {
    meta: { schema_version: "x", generated_at_iso: new Date().toISOString() },
    podcasts: [{ id: 1, title: "P1" }],
    episodes: [
      { id: 10, podcast_id: 1, title: "Hello Rome", kind: "regular", narrator: "A" },
      { id: 11, podcast_id: 1, title: "Bye Paris", kind: "book", narrator: "B" },
    ],
    spans: [
      { episode_id: 10, start_iso: "0100-01-01T00:00:00Z", end_iso: "0200-01-01T00:00:00Z" },
      { episode_id: 11, start_iso: "1500-01-01T00:00:00Z", end_iso: "1600-01-01T00:00:00Z" },
    ],
    // @ts-expect-error: minimal fixture shape; real app has full mapping
    episode_clusters: { "10": 1, "11": 2 },
  };
}

describe("episodeFiltering", () => {
  test("hasSpanInYearRange detects overlap", () => {
    const ds = makeDataset();
    expect(hasSpanInYearRange(ds, 10, [50, 150])).toBe(true);
    expect(hasSpanInYearRange(ds, 10, [201, 300])).toBe(false);
  });

  test("spanYearBounds returns min/max across selected episodes", () => {
    const ds = makeDataset();
    const bounds = spanYearBounds(ds, new Set([10, 11]));
    expect(bounds).toEqual([100, 1600]);
  });

  test("clampYearRange enforces bounds and min<max", () => {
    expect(clampYearRange([0, 10], -5, 99)).toEqual([0, 10]);
    expect(clampYearRange([0, 10], 9, 9)).toEqual([9, 10]);
  });

  test("filterEpisodesBase applies title/kind/narrator/podcast filters", () => {
    const ds = makeDataset();

    const filters = {
      podcastId: "all" as const,
      q: "rome",
      kind: "all" as const,
      narrator: "",
      topN: 3,
      axisK: 1.0,
      year: undefined as number | undefined,
      yearMin: undefined as number | undefined,
      yearMax: undefined as number | undefined,
      clusterId: undefined as number | undefined,
    };

    const res = filterEpisodesBase(ds, filters);
    expect(res.map((e) => e.id)).toEqual([10]);
  });

  test("filterEpisodesByYearRange keeps only episodes overlapping active range", () => {
    const ds = makeDataset();
    const base = ds.episodes;
    const res = filterEpisodesByYearRange(ds, base, [1400, 1700]);
    expect(res.map((e) => e.id)).toEqual([11]);
  });
});
