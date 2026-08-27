import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { Dataset } from "../../types"
import type { Filters } from "../../urlState"
import ExplorationScopeBar from "./ExplorationScopeBar"

const dataset: Dataset = {
  meta: {
    schema_version: "test",
    generated_at_iso: "2026-08-27T18:00:00Z",
    source_db: "active.db",
    source_db_sha256: "261310d853c7471883f9810808985a6b4c7000d7d612df3545dec41f182f924d",
    dataset_revision: "test-revision",
    coverage: {
      episodes_total: 1406,
      episodes_dated: 1406,
      episodes_mapped: 93,
      episodes_unmapped: 1313,
      episodes_clustered: 76,
    },
  },
  podcasts: [],
  episodes: [],
  spans: [],
  places: [],
  entities: [],
  episode_keywords: {},
  episode_clusters: {},
  clusters: [],
}

const filters: Filters = {
  podcastId: "all",
  q: "empire",
  kind: "all",
  narrator: "",
  geo: "all",
  topN: 1,
  axisK: 1,
}

describe("ExplorationScopeBar", () => {
  it("states corpus coverage truthfully and exposes one reset action", () => {
    const onReset = vi.fn()
    render(
      <ExplorationScopeBar
        dataset={dataset}
        filters={filters}
        matchingCount={12}
        activeYearRange={[1800, 1900]}
        onChange={vi.fn()}
        onReset={onReset}
      />
    )

    expect(screen.getByText(/12 of 1406 episodes remain/i)).toBeInTheDocument()
    expect(screen.getByText(/93\/1406 mapped/i)).toBeInTheDocument()
    expect(screen.getByText(/1313 unmapped/i)).toBeInTheDocument()
    expect(
      screen.getByText(/Unmapped episodes remain in search, timeline, and table/i)
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /clear scope/i }))
    expect(onReset).toHaveBeenCalledTimes(1)
  })
})
