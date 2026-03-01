import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import ClusterDetail from "./ClusterDetail"
import type { Dataset } from "../types"

function makeDataset(): Dataset {
  return {
    meta: {
      schema_version: "test",
      generated_at_iso: new Date().toISOString(),
      source_db: "test.db",
    },
    podcasts: [{ id: 1, title: "History Pod" }],
    episodes: [
      {
        id: 101,
        podcast_id: 1,
        title: "Napoleonic Front",
        pub_date_iso: "2020-01-01T00:00:00Z",
        description_pure: "Campaigns and empires",
      },
      {
        id: 102,
        podcast_id: 1,
        title: "Constitutional Turns",
        pub_date_iso: "2021-01-01T00:00:00Z",
        description_pure: "Reform and parliament",
      },
    ],
    spans: [
      {
        id: 1,
        episode_id: 101,
        start_iso: "1800-01-01T00:00:00Z",
        end_iso: "1805-01-01T00:00:00Z",
        precision: "year",
        qualifier: "exact",
        score: 0.91,
        source_section: "desc",
        source_text: "early 1800s",
      },
      {
        id: 2,
        episode_id: 102,
        start_iso: "1810-01-01T00:00:00Z",
        end_iso: "1813-01-01T00:00:00Z",
        precision: "year",
        qualifier: "exact",
        score: 0.84,
        source_section: "desc",
        source_text: "1810s",
      },
    ],
    places: [],
    entities: [
      { id: 1, episode_id: 101, name: "Napoleon", kind: "person", confidence: 0.9 },
      { id: 2, episode_id: 102, name: "Parliament", kind: "org", confidence: 0.8 },
    ],
    episode_keywords: {
      "101": [
        { phrase: "empire", score: 0.9 },
        { phrase: "campaign", score: 0.7 },
      ],
      "102": [
        { phrase: "constitution", score: 0.88 },
        { phrase: "parliament", score: 0.65 },
      ],
    },
    episode_clusters: { "101": 7, "102": 7 },
    clusters: [
      {
        cluster: {
          id: 7,
          podcast_id: 1,
          k: 2,
          label: "Power structures",
          centroid_mid_year: 1809,
          centroid_lat: 48,
          centroid_lon: 12,
          n_members: 2,
        },
        top_keywords: [
          { phrase: "empire", score: 0.9 },
          { phrase: "constitution", score: 0.88 },
        ],
        top_entities: [],
      },
    ],
    cluster_stats: [
      {
        cluster_id: 7,
        episode_count: 2,
        unique_podcast_count: 1,
        dominant_podcast_share: 1,
        temporal_span_years: 13,
        cohesion_proxy: 0.65,
        geo_dispersion: 1.2,
      },
    ],
    cluster_term_metrics: [
      { cluster_id: 7, term: "empire", tfidf: 1.2, support: 1, global_support: 2, lift: 1.1, drop_impact: 0.2 },
      {
        cluster_id: 7,
        term: "constitution",
        tfidf: 1.1,
        support: 1,
        global_support: 3,
        lift: 1.05,
        drop_impact: 0.18,
      },
    ],
    cluster_entity_stats: [
      { cluster_id: 7, name: "Napoleon", kind: "person", count: 4, lift: 2.4 },
      { cluster_id: 7, name: "Parliament", kind: "org", count: 3, lift: 1.7 },
    ],
    cluster_place_stats: [
      { cluster_id: 7, canonical_name: "Paris", count: 4, lift: 2.1, lat: 48.85, lon: 2.35 },
      { cluster_id: 7, canonical_name: "London", count: 2, lift: 1.4, lat: 51.5, lon: -0.12 },
    ],
    cluster_timeline_histogram: [
      { cluster_id: 7, start_year: 1800, end_year: 1806, count: 3 },
      { cluster_id: 7, start_year: 1807, end_year: 1813, count: 5 },
    ],
  }
}

describe("ClusterDetail", () => {
  it("renders entity and place lift sections", () => {
    render(
      <ClusterDetail
        dataset={makeDataset()}
        clusterId={7}
        selectedEpisodeId={null}
        onSelectEpisode={vi.fn()}
        onSelectCluster={vi.fn()}
      />,
    )

    expect(screen.getByRole("heading", { name: /entity lift/i })).toBeInTheDocument()
    expect(screen.getByText(/^Napoleon$/)).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /place lift/i })).toBeInTheDocument()
    expect(screen.getByText(/^Paris$/)).toBeInTheDocument()
  })

  it("filters episode table when clicking a graph term node", () => {
    render(
      <ClusterDetail
        dataset={makeDataset()}
        clusterId={7}
        selectedEpisodeId={null}
        onSelectEpisode={vi.fn()}
        onSelectCluster={vi.fn()}
      />,
    )

    const termNode = screen.getByRole("button", { name: /term node empire/i })
    fireEvent.click(termNode)

    expect(screen.getByText(/1 \/ 2 in view/i)).toBeInTheDocument()
    expect(screen.getByText(/Napoleonic Front/i)).toBeInTheDocument()
    const scopeValue = (screen.getByLabelText(/cluster scope query/i) as HTMLInputElement).value
    expect(scopeValue).toContain("clusterTerm=empire")
  })
})
