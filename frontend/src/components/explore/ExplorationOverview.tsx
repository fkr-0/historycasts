import type { KeyboardEvent } from "react"
import { useMemo } from "react"
import type { Dataset } from "../../types"
import { buildExplorationMetrics, type HistoricalBin } from "../../utils/explorationMetrics"

function percent(value: number, total: number): number {
  return total <= 0 ? 0 : Math.round((value / total) * 100)
}

function yearLabel(year: number): string {
  return year < 0 ? `${Math.abs(year)} BCE` : String(year)
}

function rangeLabel(bin: HistoricalBin): string {
  if (bin.startYear === bin.endYear) return yearLabel(bin.startYear)
  return `${yearLabel(bin.startYear)}–${yearLabel(bin.endYear)}`
}

export default function ExplorationOverview(props: {
  dataset: Dataset
  episodes: Dataset["episodes"]
  activeYearRange: [number, number]
  onSelectYearRange: (range: [number, number]) => void
}) {
  const metrics = useMemo(
    () => buildExplorationMetrics(props.dataset, props.episodes),
    [props.dataset, props.episodes]
  )
  const maxBinCount = Math.max(1, ...metrics.historicalBins.map(bin => bin.count))
  const maxPodcastEpisodes = Math.max(1, ...metrics.podcastCoverage.map(row => row.episodes))

  const activateBin = (event: KeyboardEvent<HTMLButtonElement>, bin: HistoricalBin) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      props.onSelectYearRange([bin.startYear, bin.endYear])
    }
  }

  const coverageCards = [
    {
      label: "Visible episodes",
      value: metrics.coverage.visibleEpisodes,
      detail: `${props.activeYearRange[0]}–${props.activeYearRange[1]}`,
    },
    {
      label: "Historically dated",
      value: metrics.coverage.datedEpisodes,
      detail: `${percent(metrics.coverage.datedEpisodes, metrics.coverage.visibleEpisodes)}% coverage`,
    },
    {
      label: "Mapped",
      value: metrics.coverage.mappedEpisodes,
      detail: `${percent(metrics.coverage.mappedEpisodes, metrics.coverage.visibleEpisodes)}% coverage`,
    },
    {
      label: "Clustered",
      value: metrics.coverage.clusteredEpisodes,
      detail: `${percent(metrics.coverage.clusteredEpisodes, metrics.coverage.visibleEpisodes)}% coverage`,
    },
  ]

  return (
    <section
      aria-label="Exploration overview"
      className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3"
    >
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="m-0 text-lg">Dataset overview</h2>
          <p className="m-0 text-xs text-[color:var(--muted)]">
            Coverage and historical shape for the currently filtered episodes.
          </p>
        </div>
        <div className="rounded-full border border-[color:var(--border)] px-2 py-1 text-xs text-[color:var(--muted)]">
          {props.dataset.podcasts.length} sources · {props.dataset.episodes.length} total episodes
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {coverageCards.map(card => (
          <div
            key={card.label}
            className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)]/70 p-2"
          >
            <div className="text-xs text-[color:var(--muted)]">{card.label}</div>
            <div className="text-2xl font-semibold tabular-nums">{card.value}</div>
            <div className="text-[11px] text-[color:var(--muted)]">{card.detail}</div>
          </div>
        ))}
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.45fr)_minmax(300px,1fr)]">
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)]/55 p-3">
          <div className="mb-2 flex items-baseline justify-between gap-2">
            <div>
              <h3 className="m-0 text-sm">Historical distribution</h3>
              <div className="text-[11px] text-[color:var(--muted)]">
                Best supported historical span per episode; select a bar to zoom.
              </div>
            </div>
            <span className="text-xs tabular-nums text-[color:var(--muted)]">
              {metrics.historicalYearCount} dated
            </span>
          </div>

          {metrics.historicalBins.length === 0 ? (
            <div className="grid min-h-40 place-items-center rounded border border-dashed border-[color:var(--border)] text-sm text-[color:var(--muted)]">
              No usable historical dates in this selection.
            </div>
          ) : (
            <fieldset
              aria-label="Historical episode distribution"
              className="m-0 flex h-44 min-w-0 items-end gap-1 border-0 border-b border-[color:var(--border)] px-1 pt-3"
            >
              {metrics.historicalBins.map((bin, index) => {
                const height = Math.max(4, (bin.count / maxBinCount) * 100)
                const showLabel =
                  index === 0 ||
                  index === metrics.historicalBins.length - 1 ||
                  index % Math.max(1, Math.ceil(metrics.historicalBins.length / 6)) === 0
                return (
                  <button
                    key={bin.startYear}
                    type="button"
                    aria-label={`${rangeLabel(bin)}: ${bin.count} episodes; zoom to this range`}
                    className="group relative flex h-full min-w-0 flex-1 items-end border-0 bg-transparent p-0"
                    onClick={() => props.onSelectYearRange([bin.startYear, bin.endYear])}
                    onKeyDown={event => activateBin(event, bin)}
                    title={`${rangeLabel(bin)}: ${bin.count} episodes`}
                  >
                    <span
                      aria-hidden="true"
                      className="block w-full rounded-t bg-[color:var(--accent)]/70 transition group-hover:bg-[color:var(--accent)]"
                      style={{ height: `${height}%` }}
                    />
                    {showLabel && (
                      <span className="pointer-events-none absolute top-full mt-1 -translate-x-1/2 whitespace-nowrap text-[9px] text-[color:var(--muted)] first:translate-x-0">
                        {yearLabel(bin.startYear)}
                      </span>
                    )}
                  </button>
                )
              })}
            </fieldset>
          )}
        </div>

        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)]/55 p-3">
          <h3 className="m-0 text-sm">Source coverage</h3>
          <div className="mb-2 text-[11px] text-[color:var(--muted)]">
            Relative episode volume with dated, mapped, and clustered coverage.
          </div>
          <div className="grid gap-2">
            {metrics.podcastCoverage.map(row => (
              <div key={row.podcastId} className="grid gap-1">
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="truncate" title={row.title}>
                    {row.title}
                  </span>
                  <span className="tabular-nums text-[color:var(--muted)]">{row.episodes}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-[color:var(--bg-0)]/70">
                  <div
                    className="h-full rounded-full bg-[color:var(--accent-2)]"
                    style={{ width: `${(row.episodes / maxPodcastEpisodes) * 100}%` }}
                  />
                </div>
                <div className="flex flex-wrap gap-x-3 text-[10px] text-[color:var(--muted)]">
                  <span>dated {percent(row.dated, row.episodes)}%</span>
                  <span>mapped {percent(row.mapped, row.episodes)}%</span>
                  <span>clustered {percent(row.clustered, row.episodes)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
