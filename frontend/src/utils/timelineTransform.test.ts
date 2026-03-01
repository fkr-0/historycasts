import { describe, expect, it } from "vitest"
import type { Dataset } from "../types"
import { transformToStackData } from "./timelineTransform"

describe("transformToStackData", () => {
  const createMockDataset = (): Dataset => ({
    meta: {
      schema_version: "1.0",
      generated_at_iso: "2024-01-01T00:00:00Z",
      source_db: "test",
    },
    podcasts: [
      { id: 1, title: "History Podcast", link: "https://example.com" },
      { id: 2, title: "Another Podcast", link: "https://example.com" },
    ],
    episodes: [
      {
        id: 1,
        podcast_id: 1,
        title: "Episode 1",
        pub_date_iso: "2020-01-15T00:00:00Z",
        page_url: "https://example.com/ep1",
      },
      {
        id: 2,
        podcast_id: 1,
        title: "Episode 2",
        pub_date_iso: "2020-02-20T00:00:00Z",
        page_url: "https://example.com/ep2",
      },
      {
        id: 3,
        podcast_id: 2,
        title: "Episode 3",
        pub_date_iso: "2020-03-10T00:00:00Z",
        page_url: "https://example.com/ep3",
      },
    ],
    spans: [
      {
        id: 1,
        episode_id: 1,
        start_iso: "1800-01-01T00:00:00Z",
        end_iso: "1850-12-31T00:00:00Z",
        precision: "year",
        qualifier: "approx",
        score: 0.9,
        source_section: "intro",
        source_text: "In the early 19th century...",
      },
      {
        id: 2,
        episode_id: 1,
        start_iso: "1900-01-01T00:00:00Z",
        end_iso: "1950-12-31T00:00:00Z",
        precision: "year",
        qualifier: "approx",
        score: 0.8,
        source_section: "body",
        source_text: "During the 20th century...",
      },
      {
        id: 3,
        episode_id: 2,
        start_iso: "1750-01-01T00:00:00Z",
        end_iso: "1800-12-31T00:00:00Z",
        precision: "year",
        qualifier: "exact",
        score: 0.95,
        source_section: "intro",
        source_text: "The mid-18th century...",
      },
      {
        id: 4,
        episode_id: 3,
        start_iso: "2000-01-01T00:00:00Z",
        end_iso: "2010-12-31T00:00:00Z",
        precision: "year",
        qualifier: "approx",
        score: 0.7,
        source_section: "body",
        source_text: "In the 2000s...",
      },
    ],
    places: [],
    entities: [],
    episode_keywords: {},
    episode_clusters: {},
    clusters: [],
  })

  it("should groups episodes by podcast correctly", () => {
    const dataset = createMockDataset()
    const episodeIds = [1, 2, 3]

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(2)
    expect(result[0].podcastId).toBe(2)
    expect(result[0].podcastTitle).toBe("Another Podcast")
    expect(result[0].episodes).toHaveLength(1)
    expect(result[0].episodes[0].episodeId).toBe(3)

    expect(result[1].podcastId).toBe(1)
    expect(result[1].podcastTitle).toBe("History Podcast")
    expect(result[1].episodes).toHaveLength(2)
  })

  it("should handle episodes with multiple spans", () => {
    const dataset = createMockDataset()
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(1)
    expect(result[0].episodes).toHaveLength(1)
    expect(result[0].episodes[0].spans).toHaveLength(2)
    expect(result[0].episodes[0].spans[0].spanId).toBe(1)
    expect(result[0].episodes[0].spans[1].spanId).toBe(2)
  })

  it("should handle empty episodes list", () => {
    const dataset = createMockDataset()
    const episodeIds: number[] = []

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(0)
  })

  it("should filter out spans with invalid date ranges", () => {
    const dataset: Dataset = {
      ...createMockDataset(),
      spans: [
        ...createMockDataset().spans,
        {
          id: 99,
          episode_id: 1,
          start_iso: undefined,
          end_iso: undefined,
          precision: "unknown",
          qualifier: "unknown",
          score: 0.5,
          source_section: "unknown",
          source_text: "Invalid span",
        },
        {
          id: 100,
          episode_id: 1,
          start_iso: "invalid-date",
          end_iso: "also-invalid",
          precision: "unknown",
          qualifier: "unknown",
          score: 0.5,
          source_section: "unknown",
          source_text: "Another invalid span",
        },
      ],
    }
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(1)
    expect(result[0].episodes[0].spans).toHaveLength(2)
    expect(result[0].episodes[0].spans.every(span => span.spanId !== 99)).toBe(true)
    expect(result[0].episodes[0].spans.every(span => span.spanId !== 100)).toBe(true)
  })

  it("should sort podcasts by title alphabetically", () => {
    const dataset: Dataset = {
      ...createMockDataset(),
      podcasts: [
        { id: 3, title: "Zebra Podcast" },
        { id: 1, title: "Apple Podcast" },
        { id: 2, title: "Middle Podcast" },
      ],
      episodes: [
        {
          id: 1,
          podcast_id: 3,
          title: "Episode 1",
          pub_date_iso: "2020-01-15T00:00:00Z",
        },
        {
          id: 2,
          podcast_id: 1,
          title: "Episode 2",
          pub_date_iso: "2020-02-20T00:00:00Z",
        },
        {
          id: 3,
          podcast_id: 2,
          title: "Episode 3",
          pub_date_iso: "2020-03-10T00:00:00Z",
        },
      ],
      spans: [],
      places: [],
      entities: [],
      episode_keywords: {},
      episode_clusters: {},
      clusters: [],
      meta: createMockDataset().meta,
    }
    const episodeIds = [1, 2, 3]

    const result = transformToStackData(dataset, episodeIds)

    expect(result[0].podcastTitle).toBe("Apple Podcast")
    expect(result[1].podcastTitle).toBe("Middle Podcast")
    expect(result[2].podcastTitle).toBe("Zebra Podcast")
  })

  it("should sort episodes by publication date (ascending)", () => {
    const dataset = createMockDataset()
    const episodeIds = [1, 2, 3]

    const result = transformToStackData(dataset, episodeIds)

    const historyPodcast = result.find(p => p.podcastId === 1)
    expect(historyPodcast?.episodes[0].episodeId).toBe(1)
    expect(historyPodcast?.episodes[1].episodeId).toBe(2)
  })

  it("should include cluster IDs when available in episode_clusters", () => {
    const dataset: Dataset = {
      ...createMockDataset(),
      episode_clusters: {
        "1": 42,
      },
    }
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    expect(result[0].episodes[0].spans).toHaveLength(2)
    expect(result[0].episodes[0].spans[0].clusterId).toBe(42)
    expect(result[0].episodes[0].spans[1].clusterId).toBe(42)
  })

  it("should handle missing cluster IDs gracefully", () => {
    const dataset = createMockDataset()
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    expect(result[0].episodes[0].spans).toHaveLength(2)
    expect(result[0].episodes[0].spans[0].clusterId).toBeUndefined()
  })

  it("should convert date strings to Date objects", () => {
    const dataset = createMockDataset()
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    const span = result[0].episodes[0].spans[0]
    expect(span.start).toBeInstanceOf(Date)
    expect(span.end).toBeInstanceOf(Date)
    expect(span.start.getTime()).toBe(new Date("1800-01-01T00:00:00Z").getTime())
    expect(span.end.getTime()).toBe(new Date("1850-12-31T00:00:00Z").getTime())
  })

  it("should handle unknown podcast IDs gracefully", () => {
    const dataset = createMockDataset()
    const episodeIds = [999]

    const result = transformToStackData(dataset, episodeIds)

    expect(result).toHaveLength(0)
  })

  it("should handle episodes without spans", () => {
    const dataset = createMockDataset()
    const episodeIds = [1, 2, 3]
    // Remove spans for episode 3
    dataset.spans = dataset.spans.filter(s => s.episode_id !== 3)

    const result = transformToStackData(dataset, episodeIds)

    const anotherPodcast = result.find(p => p.podcastId === 2)
    expect(anotherPodcast?.episodes).toHaveLength(1)
    expect(anotherPodcast?.episodes[0].spans).toHaveLength(0)
  })

  it("should preserve all required span properties", () => {
    const dataset = createMockDataset()
    const episodeIds = [1]

    const result = transformToStackData(dataset, episodeIds)

    const span = result[0].episodes[0].spans[0]
    expect(span.spanId).toBe(1)
    expect(span.score).toBe(0.9)
    expect(span.sourceText).toBe("In the early 19th century...")
  })
})
