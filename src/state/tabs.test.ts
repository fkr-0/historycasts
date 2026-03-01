import { describe, expect, test } from "vitest";
import type { Dataset } from "../types";
import {
  closeTab,
  ensureEpisodeTab,
  makeInitialTabs,
  nextActiveTabAfterClose,
} from "./tabs";

function makeDataset(): Dataset {
  return {
    meta: { schema_version: "x", generated_at_iso: new Date().toISOString() },
    podcasts: [],
    episodes: [{ id: 1, podcast_id: 1, title: "Ep1" }],
    spans: [],
    // @ts-expect-error minimal fixture
    episode_clusters: {},
  };
}

describe("tabs", () => {
  test("ensureEpisodeTab adds a new tab once", () => {
    const ds = makeDataset();
    const t0 = makeInitialTabs();
    const t1 = ensureEpisodeTab(ds, t0, 1);
    const t2 = ensureEpisodeTab(ds, t1, 1);
    expect(t1.length).toBe(2);
    expect(t2.length).toBe(2);
  });

  test("closeTab does not close explore", () => {
    const t0 = makeInitialTabs();
    expect(closeTab(t0, "explore")).toEqual(t0);
  });

  test("nextActiveTabAfterClose falls back to explore", () => {
    expect(nextActiveTabAfterClose("episode-1", "episode-1")).toBe("explore");
    expect(nextActiveTabAfterClose("episode-1", "episode-2")).toBe("episode-1");
  });
});
