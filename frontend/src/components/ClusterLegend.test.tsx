import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import type { Dataset } from "../types"
import ClusterLegend from "./ClusterLegend"

const dataset: Dataset = {
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
        id: 3,
        podcast_id: 1,
        k: 3,
        label: "Revolutions",
        centroid_mid_year: 1800,
        centroid_lat: 0,
        centroid_lon: 0,
        n_members: 12,
      },
      top_keywords: [],
      top_entities: [],
    },
  ],
}

describe("ClusterLegend", () => {
  it("renders cluster swatches with labels and counts", () => {
    render(<ClusterLegend dataset={dataset} clusterIds={[3]} />)

    expect(screen.getByText("Cluster legend")).toBeInTheDocument()
    expect(screen.getByText("#3")).toBeInTheDocument()
    expect(screen.getByText("Revolutions")).toBeInTheDocument()
    expect(screen.getByText("12 eps")).toBeInTheDocument()
  })
})
