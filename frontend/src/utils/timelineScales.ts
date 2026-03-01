import { type ScaleBand, type ScaleTime, scaleBand, scaleTime } from "d3"
import type { D3StackData } from "./timelineTransform"

export interface Scales {
  xScale: ScaleTime<number, number>
  yScale: ScaleBand<string>
}

interface Margin {
  top: number
  right: number
  bottom: number
  left: number
}

interface HorizontalMargin {
  left: number
  right: number
}

interface VerticalMargin {
  top: number
  bottom: number
}

/**
 * Extracts the minimum and maximum dates from all spans in the dataset.
 * Returns undefined if no spans are found.
 */
function extractDateRange(data: D3StackData[]): [Date, Date] | undefined {
  if (data.length === 0) {
    return undefined
  }

  const allDates: Date[] = []

  for (const podcast of data) {
    for (const episode of podcast.episodes) {
      for (const span of episode.spans) {
        allDates.push(span.start, span.end)
      }
    }
  }

  if (allDates.length === 0) {
    return undefined
  }

  const minDate = new Date(Math.min(...allDates.map(d => d.getTime())))
  const maxDate = new Date(Math.max(...allDates.map(d => d.getTime())))

  return [minDate, maxDate]
}

/**
 * Creates a D3 time scale for the x-axis.
 * The scale domain is determined by the earliest start and latest end dates across all spans.
 *
 * @param data - The transformed stack data
 * @param width - The total width of the chart
 * @param margin - The horizontal margins (left and right)
 * @returns A D3 scaleTime with appropriate domain and range
 */
export function createTimeScale(
  data: D3StackData[],
  width: number,
  margin: HorizontalMargin,
  explicitYearRange?: [number, number]
): ScaleTime<number, number> {
  const safeWidth = Math.max(width, margin.left + margin.right + 20)
  const range: [number, number] = [margin.left, safeWidth - margin.right]

  const dateRange = extractDateRange(data)
  if (explicitYearRange) {
    const [startYear, endYear] = explicitYearRange
    return scaleTime()
      .range(range)
      .domain([new Date(Date.UTC(startYear, 0, 1)), new Date(Date.UTC(endYear, 11, 31))])
  }

  if (dateRange === undefined) {
    // Return a scale with a default domain when no data is available
    return scaleTime()
      .range(range)
      .domain([new Date(0), new Date(1)])
  }

  return scaleTime().range(range).domain(dateRange)
}

/**
 * Creates a D3 band scale for the y-axis using podcast titles.
 *
 * @param data - The transformed stack data
 * @param height - The total height of the chart
 * @param margin - The vertical margins (top and bottom)
 * @returns A D3 scaleBand with podcast titles as domain
 */
export function createPodcastScale(
  data: D3StackData[],
  height: number,
  margin: VerticalMargin
): ScaleBand<string> {
  const safeHeight = Math.max(height, margin.top + margin.bottom + 20)
  const range: [number, number] = [margin.top, safeHeight - margin.bottom]

  // Extract podcast titles from data
  const domain = data.map(d => d.podcastTitle)

  return scaleBand().range(range).domain(domain).padding(0.1)
}

/**
 * Creates both x (time) and y (band) scales for the timeline visualization.
 *
 * @param data - The transformed stack data
 * @param width - The total width of the chart
 * @param height - The total height of the chart
 * @param margin - The margin object with all sides
 * @returns An object containing both xScale and yScale
 */
export function createScales(
  data: D3StackData[],
  width: number,
  height: number,
  margin: Margin,
  explicitYearRange?: [number, number]
): Scales {
  const xScale = createTimeScale(
    data,
    width,
    { left: margin.left, right: margin.right },
    explicitYearRange
  )
  const yScale = createPodcastScale(data, height, { top: margin.top, bottom: margin.bottom })

  return { xScale, yScale }
}
