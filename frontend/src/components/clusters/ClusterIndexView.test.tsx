import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import ClusterIndexView from "./ClusterIndexView"
import type { Dataset } from "../../types"

function ds(): Dataset {
  return {
    meta: {
      schema_version: "x",
      generated_at_iso: new Date().toISOString(),
      source_db: "x.db",
    },
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
          id: 1,
          podcast_id: 1,
          k: 3,
          label: "A",
          centroid_mid_year: 1800,
          centroid_lat: 0,
          centroid_lon: 0,
          n_members: 30,
        },
        top_keywords: [{ phrase: "empire", score: 0.7 }],
        top_entities: [],
      },
      {
        cluster: {
          id: 2,
          podcast_id: 1,
          k: 3,
          label: "B",
          centroid_mid_year: 1700,
          centroid_lat: 0,
          centroid_lon: 0,
          n_members: 10,
        },
        top_keywords: [{ phrase: "constitution", score: 0.8 }],
        top_entities: [],
      },
    ],
    cluster_stats: [
      {
        cluster_id: 1,
        episode_count: 30,
        unique_podcast_count: 1,
        dominant_podcast_share: 0.95,
        temporal_span_years: 22,
        cohesion_proxy: 0.2,
      },
      {
        cluster_id: 2,
        episode_count: 10,
        unique_podcast_count: 3,
        dominant_podcast_share: 0.4,
        temporal_span_years: 280,
        cohesion_proxy: 0.8,
      },
    ],
  }
}

describe("ClusterIndexView", () => {
  it("sorts by selected metric and opens selected cluster", () => {
    const onSelect = vi.fn()
    const onSort = vi.fn()
    render(
      <ClusterIndexView
        dataset={ds()}
        sortBy="size"
        onSortChange={onSort}
        onSelectCluster={onSelect}
      />,
    )

    fireEvent.change(screen.getByLabelText(/sort clusters/i), { target: { value: "cohesion" } })
    expect(onSort).toHaveBeenCalledWith("cohesion")

    fireEvent.click(screen.getByRole("button", { name: /open cluster #2/i }))
    expect(onSelect).toHaveBeenCalledWith(2)
  })
})
