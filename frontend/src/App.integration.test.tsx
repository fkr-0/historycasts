import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App"
import type { Dataset } from "./types"

vi.mock("./components/Timeline", () => ({
  default: () => <div data-testid="timeline-mock" />,
}))

function createDataset(): Dataset {
  return {
    meta: {
      schema_version: "test",
      generated_at_iso: new Date().toISOString(),
      source_db: "test.db",
    },
    podcasts: [{ id: 1, title: "Test Podcast", link: "https://example.com", language: "en" }],
    episodes: [
      {
        id: 101,
        podcast_id: 1,
        title: "Episode Alpha",
        pub_date_iso: "2020-01-01T00:00:00Z",
        page_url: "https://example.com/alpha",
        audio_url: "https://example.com/alpha.mp3",
        kind: "regular",
        narrator: "Alice",
        description_pure: "Alpha description",
      },
      {
        id: 102,
        podcast_id: 1,
        title: "Episode Beta",
        pub_date_iso: "2021-01-01T00:00:00Z",
        page_url: "https://example.com/beta",
        audio_url: "https://example.com/beta.mp3",
        kind: "special",
        narrator: "Bob",
        description_pure: "Beta description",
      },
    ],
    spans: [
      {
        id: 1,
        episode_id: 101,
        start_iso: "1800-01-01T00:00:00Z",
        end_iso: "1802-01-01T00:00:00Z",
        precision: "year",
        qualifier: "exact",
        score: 0.9,
        source_section: "desc",
        source_text: "alpha span",
      },
      {
        id: 2,
        episode_id: 102,
        start_iso: "1850-01-01T00:00:00Z",
        end_iso: "1851-01-01T00:00:00Z",
        precision: "year",
        qualifier: "exact",
        score: 0.8,
        source_section: "desc",
        source_text: "beta span",
      },
    ],
    places: [],
    entities: [],
    episode_keywords: {
      "101": [{ phrase: "revolution", score: 0.8 }],
      "102": [{ phrase: "empire", score: 0.7 }],
    },
    episode_clusters: { "101": 1, "102": 1 },
    clusters: [
      {
        cluster: {
          id: 1,
          podcast_id: 1,
          k: 2,
          label: "Wars",
          centroid_mid_year: 1825,
          centroid_lat: 48,
          centroid_lon: 11,
          n_members: 2,
        },
        top_keywords: [
          { phrase: "revolution", score: 0.8 },
          { phrase: "empire", score: 0.6 },
        ],
        top_entities: [],
      },
    ],
    cluster_stats: [
      {
        cluster_id: 1,
        episode_count: 2,
        unique_podcast_count: 1,
        dominant_podcast_share: 1,
        temporal_span_years: 51,
        cohesion_proxy: 0.72,
      },
    ],
  }
}

describe("App integration", () => {
  beforeEach(() => {
    const dataset = createDataset()
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => dataset,
    } as Response)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("filters episodes and opens detail after timeline click", async () => {
    render(<App />)

    await screen.findByText("Matching episodes:")
    expect(screen.getByText("2")).toBeInTheDocument()

    const search = screen.getByLabelText(/Search title/i)
    fireEvent.change(search, { target: { value: "Alpha" } })

    await waitFor(() => {
      expect(screen.getByText(/Matching episodes:/).textContent).toContain("1")
    })

    await waitFor(() => {
      const rects = document.querySelectorAll("rect.span-rect")
      expect(rects.length).toBeGreaterThan(0)
    })

    const firstRect = document.querySelector("rect.span-rect")
    expect(firstRect).toBeTruthy()
    if (firstRect) {
      fireEvent.click(firstRect)
    }

    await screen.findByRole("button", { name: /^Episode Alpha$/i })
    expect(screen.getAllByText(/alpha span/i).length).toBeGreaterThan(0)
  })

  it("opens cluster detail tab from cluster panel", async () => {
    render(<App />)

    await screen.findByText("Matching episodes:")
    const clusterCard = screen.getByRole("button", { name: /#1/i })
    fireEvent.click(clusterCard)

    await screen.findByRole("button", { name: /^Wars$/i })
    await screen.findByText(/Cluster #1/i)
    expect(screen.getByText(/Cluster Episodes/i)).toBeInTheDocument()
  })
})
