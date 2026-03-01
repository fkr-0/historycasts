import { axisBottom, axisLeft, select } from "d3"
import { useEffect, useMemo, useRef, useState } from "react"
import type { Dataset } from "../types"
import { createScales, type Scales } from "../utils/timelineScales"
import type { D3StackData } from "../utils/timelineTransform"
import { transformToStackData } from "../utils/timelineTransform"

type Episode = Dataset["episodes"][number]

export interface StackedBarTimelineProps {
  dataset: Dataset
  episodes: Episode[]
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
  scrubYear?: number
  onScrubYear: (y?: number) => void
  visibleYearRange?: [number, number]
  axisDensityK?: number
}

const MARGIN = { top: 20, right: 20, bottom: 40, left: 60 }

export default function StackedBarTimeline(props: StackedBarTimelineProps): JSX.Element {
  const {
    dataset,
    episodes,
    selectedEpisodeId,
    onSelectEpisode,
    scrubYear,
    visibleYearRange,
    axisDensityK = 1,
  } = props

  const svgRef = useRef<SVGSVGElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 400 })

  // Hover state for episode detail card
  const [hoverData, setHoverData] = useState<{
    x: number
    y: number
    episodeId: number
    episodeTitle: string
    spanStart: Date
    spanEnd: Date
    score: number
    sourceText: string
    clusterId?: number
  } | null>(null)

  // Transform data to D3 stack format
  const stackData: D3StackData[] = useMemo(() => {
    const episodeIds = episodes.map(ep => ep.id)
    return transformToStackData(dataset, episodeIds)
  }, [dataset, episodes])

  // Create a lookup map for episode titles
  const episodeTitleMap = useMemo(() => {
    const map = new Map<number, string>()
    for (const podcast of stackData) {
      for (const episode of podcast.episodes) {
        map.set(episode.episodeId, episode.title)
      }
    }
    return map
  }, [stackData])

  // Create scales
  const scales: Scales = useMemo(() => {
    return createScales(stackData, dimensions.width, dimensions.height, MARGIN, visibleYearRange)
  }, [stackData, dimensions, visibleYearRange])

  // Handle resize with ResizeObserver
  useEffect(() => {
    const svgElement = svgRef.current
    if (!svgElement) return

    const resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        setDimensions({ width, height })
      }
    })

    resizeObserver.observe(svgElement)

    return () => {
      resizeObserver.disconnect()
    }
  }, [])

  // D3 rendering
  useEffect(() => {
    const svgElement = svgRef.current
    if (!svgElement) return

    // Handle empty data
    if (stackData.length === 0) {
      select(svgElement).selectAll("*").remove()
      return
    }

    const { xScale, yScale } = scales
    const minBarWidth = 1

    // Helper function to calculate opacity based on scrub year
    function opacityByYear(spanStart: Date, spanEnd: Date, scrubYear?: number): number {
      if (scrubYear == null || Number.isNaN(scrubYear)) return 0.85
      const mid = spanStart.getTime() + (spanEnd.getTime() - spanStart.getTime()) / 2
      const midYear = new Date(mid).getUTCFullYear()
      const d = Math.abs(midYear - scrubYear)
      const sigma = 40
      const w = Math.exp(-(d * d) / (2 * sigma * sigma))
      return 0.15 + 0.85 * w
    }

    function spanRectX(start: Date, end: Date): number {
      const a = xScale(start)
      const b = xScale(end)
      return Math.min(a, b)
    }

    function spanRectWidth(start: Date, end: Date): number {
      const a = xScale(start)
      const b = xScale(end)
      const w = Math.abs(b - a)
      if (!Number.isFinite(w)) return minBarWidth
      return Math.max(minBarWidth, w)
    }

    const contentWidth = Math.max(120, dimensions.width - MARGIN.left - MARGIN.right)
    const domainMinYear = visibleYearRange?.[0] ?? xScale.domain()[0].getUTCFullYear()
    const domainMaxYear = visibleYearRange?.[1] ?? xScale.domain()[1].getUTCFullYear()
    const yearsSpan = Math.max(1, domainMaxYear - domainMinYear)
    const targetTicks = Math.max(2, Math.floor(contentWidth / Math.max(45, 80 * axisDensityK)))
    const rawStep = yearsSpan / targetTicks
    const base = 10 ** Math.floor(Math.log10(Math.max(rawStep, 1)))
    const candidates = [1, 2, 5].map(v => v * base)
    const step = candidates.find(c => c >= rawStep) ?? 10 * base

    const axisYears: number[] = []
    const first = Math.ceil(domainMinYear / step) * step
    for (let y = first; y <= domainMaxYear; y += step) axisYears.push(y)
    if (!axisYears.includes(domainMinYear)) axisYears.unshift(domainMinYear)
    if (!axisYears.includes(domainMaxYear)) axisYears.push(domainMaxYear)

    const axisTickDates = axisYears.map(y => new Date(Date.UTC(y, 0, 1)))

    // Clear previous content
    select(svgElement).selectAll("*").remove()

    // Create main SVG with proper dimensions
    const svg = select(svgElement).attr("width", dimensions.width).attr("height", dimensions.height)

    // Create main group with margin transform
    const mainGroup = svg.append("g").attr("transform", `translate(${MARGIN.left}, ${MARGIN.top})`)

    // Create podcast groups using D3 data binding
    const podcastGroups = mainGroup
      .selectAll<SVGGElement, D3StackData>(".podcast-group")
      .data(stackData)
      .join("g")
      .attr("class", "podcast-group")
      .attr("transform", d => `translate(0, ${yScale(d.podcastTitle) ?? 0})`)

    // For each podcast group, render span rects
    podcastGroups.each(function (podcastData) {
      const podcastGroup = select(this)

      // Collect all spans from all episodes
      const allSpans: Array<{
        span: D3StackData["episodes"][number]["spans"][number]
        episodeId: number
      }> = []

      for (const episode of podcastData.episodes) {
        for (const span of episode.spans) {
          allSpans.push({ span, episodeId: episode.episodeId })
        }
      }

      // Sort spans by start time
      allSpans.sort((a, b) => a.span.start.getTime() - b.span.start.getTime())

      // Create unique colors per episode using HSL
      const episodeColors = new Map<number, string>()
      for (const episode of podcastData.episodes) {
        const hue = (episode.episodeId * 47) % 360
        episodeColors.set(episode.episodeId, `hsl(${hue}, 70%, 55%)`)
      }

      // Render span rects using D3 data binding with enter/update/exit pattern
      podcastGroup
        .selectAll<SVGRectElement, (typeof allSpans)[number]>("rect.span-rect")
        .data(allSpans)
        .join(
          enter =>
            enter
              .append("rect")
              .attr("class", "span-rect")
              .attr("x", d => spanRectX(d.span.start, d.span.end))
              .attr("width", d => spanRectWidth(d.span.start, d.span.end))
              .attr("y", 0)
              .attr("height", yScale.bandwidth())
              .attr("fill", d => episodeColors.get(d.episodeId) ?? "#ccc")
              .attr("stroke", "white")
              .attr("stroke-width", d => (d.episodeId === selectedEpisodeId ? 3 : 1))
              .attr("rx", 2)
              .attr("cursor", "pointer")
              .attr("opacity", d => opacityByYear(d.span.start, d.span.end, scrubYear))
              .on("click", (_event, d) => onSelectEpisode(d.episodeId))
              .on("mouseover", (event, d) => {
                const episodeTitle = episodeTitleMap.get(d.episodeId) ?? `Episode ${d.episodeId}`
                setHoverData({
                  x: event.clientX,
                  y: event.clientY,
                  episodeId: d.episodeId,
                  episodeTitle,
                  spanStart: d.span.start,
                  spanEnd: d.span.end,
                  score: d.span.score,
                  sourceText: d.span.sourceText,
                  clusterId: d.span.clusterId,
                })
              })
              .on("mouseout", () => {
                setHoverData(null)
              }),
          update =>
            update
              .attr("x", d => spanRectX(d.span.start, d.span.end))
              .attr("width", d => spanRectWidth(d.span.start, d.span.end))
              .attr("y", 0)
              .attr("height", yScale.bandwidth())
              .attr("stroke-width", d => (d.episodeId === selectedEpisodeId ? 3 : 1))
              .transition()
              .duration(150)
              .attr("opacity", d => opacityByYear(d.span.start, d.span.end, scrubYear)),
          exit => exit.transition().duration(150).attr("opacity", 0).remove()
        )
    })

    // Add x-axis
    const xAxisGroup = mainGroup
      .append("g")
      .attr("class", "x-axis")
      .attr("transform", `translate(0, ${dimensions.height - MARGIN.top - MARGIN.bottom})`)

    const xAxis = axisBottom(xScale)
      .tickValues(axisTickDates)
      .tickFormat(d => {
        const date = d as Date
        const y = date.getUTCFullYear()
        return y < 0 ? `${Math.abs(y)} BCE` : `${y}`
      })

    xAxisGroup.call(xAxis)

    // Style x-axis
    xAxisGroup.selectAll(".domain, .tick line").attr("stroke", "rgba(230, 230, 250, 0.35)")
    xAxisGroup
      .selectAll(".tick text")
      .attr("fill", "rgba(230, 230, 250, 0.9)")
      .attr("font-size", "12px")

    // Add y-axis
    const yAxisGroup = mainGroup.append("g").attr("class", "y-axis")

    const yAxis = axisLeft(yScale)

    yAxisGroup.call(yAxis)

    // Style y-axis
    yAxisGroup.selectAll(".domain, .tick line").attr("stroke", "rgba(230, 230, 250, 0.35)")
    yAxisGroup
      .selectAll(".tick text")
      .attr("fill", "rgba(230, 230, 250, 0.9)")
      .attr("font-size", "12px")
  }, [
    stackData,
    scales,
    dimensions,
    onSelectEpisode,
    episodeTitleMap,
    scrubYear,
    selectedEpisodeId,
    visibleYearRange,
    axisDensityK,
  ])

  return (
    <>
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        style={{ display: "block", overflow: "visible", background: "transparent" }}
        data-testid="stacked-bar-timeline"
      />
      {hoverData && (
        <div
          style={{
            position: "fixed",
            left: hoverData.x + 14,
            top: hoverData.y + 14,
            maxWidth: 380,
            background: "rgba(25, 20, 44, 0.96)",
            border: "1px solid rgba(164, 144, 194, 0.35)",
            borderRadius: 10,
            padding: 10,
            boxShadow: "0 14px 36px rgba(0,0,0,0.45)",
            zIndex: 9999,
            pointerEvents: "none",
            color: "#e6e6fa",
          }}
        >
          <div style={{ fontWeight: 700 }}>{hoverData.episodeTitle}</div>
          <div style={{ fontSize: 12, color: "#c8bbdc", marginTop: 4 }}>
            span: {hoverData.spanStart.getFullYear()}–{hoverData.spanEnd.getFullYear()}
          </div>
          {hoverData.clusterId != null && (
            <div style={{ fontSize: 12, color: "#c8bbdc", marginTop: 4 }}>
              cluster: <b>#{hoverData.clusterId}</b>
            </div>
          )}
          <div style={{ fontSize: 12, marginTop: 8, color: "#c8bbdc" }}>
            score: {hoverData.score.toFixed(2)}
          </div>
          <div style={{ fontSize: 12, marginTop: 4 }}>{hoverData.sourceText}</div>
          <div style={{ fontSize: 11, marginTop: 8, color: "#a490c2" }}>
            click to open details →
          </div>
        </div>
      )}
    </>
  )
}
