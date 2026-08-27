import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App"
import type { Dataset } from "./types"

vi.mock("./components/D3GazetteerMap", () => ({
  default: () => <div data-testid="gazetteer-map-mock" />,
}))

vi.mock("./components/Timeline", () => ({
  default: () => <div data-testid="timeline-mock" />,
}))

vi.mock("./components/EpisodeRasterTimeline", () => ({
  default: (props: {
    episodes: Dataset["episodes"]
    onSelectEpisode: (episodeId: number) => void
  }) => (
    <div data-testid="episode-raster-mock">
      {props.episodes.map(episode => (
        <button key={episode.id} type="button" onClick={() => props.onSelectEpisode(episode.id)}>
          Open {episode.title}
        </button>
      ))}
    </div>
  ),
}))

function createDataset(): Dataset {
  return {
    meta: {
      schema_version: "test",
      generated_at_iso: new Date().toISOString(),
      source_db: "test.db",
      coverage: {
        episodes_total: 2,
        episodes_dated: 2,
        episodes_mapped: 1,
        episodes_unmapped: 1,
        episodes_clustered: 2,
      },
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
    ],
    places: [
      {
        id: 1,
        episode_id: 101,
        canonical_name: "Berlin",
        norm_key: "berlin",
        place_kind: "city",
        lat: 52.52,
        lon: 13.4,
      },
    ],
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
    window.history.replaceState({}, "", "/")
    const dataset = createDataset()
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => dataset,
    } as Response)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it("filters episodes and opens detail after timeline click", async () => {
    render(<App />)

    const matchingEpisodes = await screen.findByText("Matching episodes:")
    expect(matchingEpisodes).toHaveTextContent("Matching episodes: 2")

    const search = screen.getByLabelText(/Search corpus/i)
    fireEvent.change(search, { target: { value: "Alpha" } })

    await waitFor(() => {
      expect(screen.getByText(/Matching episodes:/).textContent).toContain("1")
    })

    fireEvent.click(screen.getByRole("button", { name: /Open Episode Alpha/i }))

    await screen.findByRole("button", { name: /^Episode Alpha$/i })
    expect(screen.getAllByText(/alpha span/i).length).toBeGreaterThan(0)
  })

  it("defers the interactive map and composes geography with the shared exploration scope", async () => {
    render(<App />)

    await screen.findByText("Matching episodes:")
    expect(screen.queryByTestId("gazetteer-map-mock")).not.toBeInTheDocument()

    fireEvent.change(screen.getByRole("combobox", { name: /^Geography coverage filter$/i }), {
      target: { value: "unmapped" },
    })
    await waitFor(() => {
      expect(screen.getByText(/Matching episodes:/).textContent).toContain("1")
    })
    expect(screen.getByText(/geography: unmapped/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /open interactive map/i }))
    expect(await screen.findByTestId("gazetteer-map-mock")).toBeInTheDocument()
  })

  it("scopes search results to the composed exploration scope", async () => {
    render(<App />)

    await screen.findByText("Matching episodes:")
    fireEvent.change(screen.getByLabelText(/Search corpus/i), {
      target: { value: "Alpha" },
    })
    await screen.findByText(/Alpha description/)

    fireEvent.change(screen.getByRole("combobox", { name: /^Geography coverage filter$/i }), {
      target: { value: "unmapped" },
    })

    await waitFor(() => {
      expect(screen.getByText(/Matching episodes:/).textContent).toContain("0")
      expect(screen.queryByText(/Alpha description/)).not.toBeInTheDocument()
      expect(screen.getByText("No results.")).toBeInTheDocument()
    })
  })

  it("starts with side panels collapsed on mobile viewports", async () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn().mockReturnValue({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })
    )

    render(<App />)

    const openFilters = await screen.findByRole("button", { name: /^open filters$/i })
    const openDetails = screen.getByRole("button", { name: /^open details$/i })
    expect(openFilters).toHaveAttribute("aria-controls", "filters-panel")
    expect(openFilters).toHaveAttribute("aria-expanded", "false")
    expect(openDetails).toHaveAttribute("aria-controls", "details-panel")
    expect(openDetails).toHaveAttribute("aria-expanded", "false")
    expect(document.querySelector("#filters-panel")).toHaveAttribute("aria-hidden", "true")
    expect(document.querySelector("#details-panel")).toHaveAttribute("aria-hidden", "true")
    expect(screen.queryByRole("button", { name: "Open filters panel" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Open details panel" })).not.toBeInTheDocument()

    fireEvent.click(openDetails)
    expect(screen.getByRole("button", { name: /^hide details$/i })).toHaveAttribute(
      "aria-expanded",
      "true"
    )
    expect(document.querySelector("#details-panel")).not.toHaveAttribute("aria-hidden")
    expect(screen.getByRole("main", { name: "Historycasts explorer" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { level: 1, name: /HISTORYCASTS/i })).toBeInTheDocument()
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
