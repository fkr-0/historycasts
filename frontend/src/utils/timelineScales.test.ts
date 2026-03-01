import { describe, expect, it } from "vitest"
import { createPodcastScale, createScales, createTimeScale } from "./timelineScales"
import type { D3StackData } from "./timelineTransform"

describe("timelineScales", () => {
  const createMockData = (): D3StackData[] => [
    {
      podcastId: 1,
      podcastTitle: "History Podcast",
      episodes: [
        {
          episodeId: 1,
          title: "Episode 1",
          pubDate: "2020-01-15T00:00:00Z",
          spans: [
            {
              spanId: 1,
              start: new Date("1800-01-01T00:00:00Z"),
              end: new Date("1850-12-31T00:00:00Z"),
              score: 0.9,
              sourceText: "In the early 19th century...",
            },
            {
              spanId: 2,
              start: new Date("1900-01-01T00:00:00Z"),
              end: new Date("1950-12-31T00:00:00Z"),
              score: 0.8,
              sourceText: "During the 20th century...",
            },
          ],
        },
      ],
    },
    {
      podcastId: 2,
      podcastTitle: "Another Podcast",
      episodes: [
        {
          episodeId: 2,
          title: "Episode 2",
          pubDate: "2020-02-20T00:00:00Z",
          spans: [
            {
              spanId: 3,
              start: new Date("1750-01-01T00:00:00Z"),
              end: new Date("1800-12-31T00:00:00Z"),
              score: 0.95,
              sourceText: "The mid-18th century...",
            },
          ],
        },
      ],
    },
  ]

  describe("createTimeScale", () => {
    it("should create time scale with correct domain from span dates", () => {
      const data = createMockData()
      const width = 800
      const margin = { left: 50, right: 50 }

      const scale = createTimeScale(data, width, margin)

      // Check that the domain covers the earliest start and latest end
      const [minDate, maxDate] = scale.domain()
      expect(minDate.getTime()).toBeLessThanOrEqual(new Date("1750-01-01T00:00:00Z").getTime())
      expect(maxDate.getTime()).toBeGreaterThanOrEqual(new Date("1950-12-31T00:00:00Z").getTime())
    })

    it("should create time scale with correct range accounting for margins", () => {
      const data = createMockData()
      const width = 800
      const margin = { left: 50, right: 50 }

      const scale = createTimeScale(data, width, margin)

      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.left)
      expect(maxRange).toBe(width - margin.right)
    })

    it("should handle empty data by returning default scale", () => {
      const data: D3StackData[] = []
      const width = 800
      const margin = { left: 50, right: 50 }

      const scale = createTimeScale(data, width, margin)

      // Should return a valid scale even with empty data
      expect(scale).toBeDefined()
      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.left)
      expect(maxRange).toBe(width - margin.right)
    })

    it("should handle data with no spans", () => {
      const data: D3StackData[] = [
        {
          podcastId: 1,
          podcastTitle: "Empty Podcast",
          episodes: [
            {
              episodeId: 1,
              title: "Empty Episode",
              pubDate: "2020-01-15T00:00:00Z",
              spans: [],
            },
          ],
        },
      ]
      const width = 800
      const margin = { left: 50, right: 50 }

      const scale = createTimeScale(data, width, margin)

      // Should return a valid scale even with no spans
      expect(scale).toBeDefined()
      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.left)
      expect(maxRange).toBe(width - margin.right)
    })
  })

  describe("createPodcastScale", () => {
    it("should create band scale for podcasts using their titles", () => {
      const data = createMockData()
      const height = 600
      const margin = { top: 50, bottom: 50 }

      const scale = createPodcastScale(data, height, margin)

      // Domain should contain podcast titles
      const domain = scale.domain()
      expect(domain).toContain("History Podcast")
      expect(domain).toContain("Another Podcast")
    })

    it("should create band scale with correct range accounting for margins", () => {
      const data = createMockData()
      const height = 600
      const margin = { top: 50, bottom: 50 }

      const scale = createPodcastScale(data, height, margin)

      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.top)
      expect(maxRange).toBe(height - margin.bottom)
    })

    it("should handle single podcast", () => {
      const data: D3StackData[] = [
        {
          podcastId: 1,
          podcastTitle: "Solo Podcast",
          episodes: [
            {
              episodeId: 1,
              title: "Episode 1",
              pubDate: "2020-01-15T00:00:00Z",
              spans: [
                {
                  spanId: 1,
                  start: new Date("1800-01-01T00:00:00Z"),
                  end: new Date("1850-12-31T00:00:00Z"),
                  score: 0.9,
                  sourceText: "Test",
                },
              ],
            },
          ],
        },
      ]
      const height = 600
      const margin = { top: 50, bottom: 50 }

      const scale = createPodcastScale(data, height, margin)

      expect(scale.domain()).toEqual(["Solo Podcast"])
      // Bandwidth should be positive and reasonable
      expect(scale.bandwidth()).toBeGreaterThan(0)
    })

    it("should handle empty data by returning empty domain scale", () => {
      const data: D3StackData[] = []
      const height = 600
      const margin = { top: 50, bottom: 50 }

      const scale = createPodcastScale(data, height, margin)

      expect(scale.domain()).toEqual([])
      const [minRange, maxRange] = scale.range()
      expect(minRange).toBe(margin.top)
      expect(maxRange).toBe(height - margin.bottom)
    })
  })

  describe("createScales", () => {
    it("should create both x and y scales with correct configuration", () => {
      const data = createMockData()
      const width = 800
      const height = 600
      const margin = { top: 50, right: 50, bottom: 50, left: 50 }

      const scales = createScales(data, width, height, margin)

      expect(scales.xScale).toBeDefined()
      expect(scales.yScale).toBeDefined()

      // Check xScale range
      const [xMin, xMax] = scales.xScale.range()
      expect(xMin).toBe(margin.left)
      expect(xMax).toBe(width - margin.right)

      // Check yScale range
      const [yMin, yMax] = scales.yScale.range()
      expect(yMin).toBe(margin.top)
      expect(yMax).toBe(height - margin.bottom)
    })

    it("should have xScale domain that covers all span dates", () => {
      const data = createMockData()
      const width = 800
      const height = 600
      const margin = { top: 50, right: 50, bottom: 50, left: 50 }

      const scales = createScales(data, width, height, margin)

      const [minDate, maxDate] = scales.xScale.domain()
      expect(minDate.getTime()).toBeLessThanOrEqual(new Date("1750-01-01T00:00:00Z").getTime())
      expect(maxDate.getTime()).toBeGreaterThanOrEqual(new Date("1950-12-31T00:00:00Z").getTime())
    })

    it("should have yScale domain with all podcast titles", () => {
      const data = createMockData()
      const width = 800
      const height = 600
      const margin = { top: 50, right: 50, bottom: 50, left: 50 }

      const scales = createScales(data, width, height, margin)

      expect(scales.yScale.domain()).toContain("History Podcast")
      expect(scales.yScale.domain()).toContain("Another Podcast")
    })

    it("should handle empty data gracefully", () => {
      const data: D3StackData[] = []
      const width = 800
      const height = 600
      const margin = { top: 50, right: 50, bottom: 50, left: 50 }

      const scales = createScales(data, width, height, margin)

      expect(scales.xScale).toBeDefined()
      expect(scales.yScale).toBeDefined()
      expect(scales.yScale.domain()).toEqual([])
    })
  })
})
