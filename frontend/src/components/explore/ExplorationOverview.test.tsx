import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { Dataset } from "../../types"
import ExplorationOverview from "./ExplorationOverview"

function fixture(): Dataset {
  return {
    meta: { schema_version: "test", generated_at_iso: "2026-01-01", source_db: "test.db" },
    podcasts: [{ id: 1, title: "History source" }],
    episodes: [
      { id: 1, podcast_id: 1, title: "One", pub_date_iso: "2020-01-01", best_span_id: 10 },
    ],
    spans: [
      {
        id: 10,
        episode_id: 1,
        start_iso: "1800-01-01",
        end_iso: "1800-12-31",
        precision: "year",
        qualifier: "",
        score: 1,
        source_section: "main",
        source_text: "1800",
      },
    ],
    places: [],
    entities: [],
    episode_keywords: {},
    episode_clusters: {},
    clusters: [],
  }
}

describe("ExplorationOverview", () => {
  it("shows coverage and lets users zoom from the historical chart", () => {
    const onSelectYearRange = vi.fn()
    const dataset = fixture()
    render(
      <ExplorationOverview
        dataset={dataset}
        episodes={dataset.episodes}
        activeYearRange={[1700, 1900]}
        onSelectYearRange={onSelectYearRange}
      />
    )

    expect(screen.getByText("Historically dated")).toBeTruthy()
    const bar = screen.getByRole("button", { name: /1800.*1 episodes.*zoom/i })
    fireEvent.click(bar)
    expect(onSelectYearRange).toHaveBeenCalledWith([1800, 1800])
  })
})
