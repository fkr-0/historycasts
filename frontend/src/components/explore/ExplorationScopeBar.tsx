import type { Dataset } from "../../types"
import type { Filters } from "../../urlState"

function shortHash(value?: string): string {
  if (!value) return "not recorded"
  return value.length > 16 ? `${value.slice(0, 12)}…` : value
}

function yearLabel(year: number): string {
  return year < 0 ? `${Math.abs(year)} BCE` : String(year)
}

export default function ExplorationScopeBar(props: {
  dataset: Dataset
  filters: Filters
  matchingCount: number
  activeYearRange: [number, number]
  onChange: (next: Filters) => void
  onReset: () => void
}) {
  const coverage = props.dataset.meta.coverage
  const total = coverage?.episodes_total ?? props.dataset.episodes.length
  const podcast =
    props.filters.podcastId === "all"
      ? undefined
      : props.dataset.podcasts.find(row => row.id === props.filters.podcastId)?.title
  const hasExplicitYear = props.filters.yearMin != null || props.filters.yearMax != null
  const activeScopes = [
    props.filters.q ? `search: ${props.filters.q}` : undefined,
    podcast ? `podcast: ${podcast}` : undefined,
    props.filters.kind !== "all" ? `kind: ${props.filters.kind}` : undefined,
    props.filters.narrator ? `narrator: ${props.filters.narrator}` : undefined,
    props.filters.clusterId != null ? `cluster #${props.filters.clusterId}` : undefined,
    (props.filters.geo ?? "all") !== "all" ? `geography: ${props.filters.geo}` : undefined,
    hasExplicitYear
      ? `time: ${yearLabel(props.activeYearRange[0])}–${yearLabel(props.activeYearRange[1])}`
      : undefined,
    props.filters.tableSort
      ? `table: ${props.filters.tableSort === "pub_date_iso" ? "published" : "title"} ${props.filters.tableDir ?? "asc"}`
      : undefined,
  ].filter((scope): scope is string => Boolean(scope))

  return (
    <section
      aria-label="Active exploration scope"
      className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/70 p-3"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-sm font-semibold">Active scope</div>
          <div className="text-[11px] text-[color:var(--muted)]">
            {props.matchingCount} of {total} episodes remain in the composed exploration scope.
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs text-[color:var(--muted)]">
            Geography
            <select
              aria-label="Geography coverage scope"
              className="ml-2 py-1 text-xs"
              value={props.filters.geo ?? "all"}
              onChange={event =>
                props.onChange({
                  ...props.filters,
                  geo: event.target.value as "all" | "mapped" | "unmapped",
                })
              }
            >
              <option value="all">all episodes</option>
              <option value="mapped">mapped only</option>
              <option value="unmapped">unmapped only</option>
            </select>
          </label>
          <button type="button" onClick={props.onReset} className="text-xs">
            Clear scope
          </button>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5 text-[11px]">
        {activeScopes.length === 0 ? (
          <span className="rounded-full border border-[color:var(--border)] px-2 py-1 text-[color:var(--muted)]">
            all episodes
          </span>
        ) : (
          activeScopes.map(scope => (
            <span
              key={scope}
              className="rounded-full border border-[color:var(--border)] bg-[color:var(--surface-2)]/70 px-2 py-1"
            >
              {scope}
            </span>
          ))
        )}
      </div>

      {coverage && (
        <div className="mt-2 text-[11px] text-[color:var(--muted)]">
          Corpus coverage: {coverage.episodes_dated}/{coverage.episodes_total} dated ·{" "}
          <strong className="font-semibold text-[color:var(--text)]">
            {coverage.episodes_mapped}/{coverage.episodes_total} mapped
          </strong>{" "}
          · {coverage.episodes_unmapped} unmapped · {coverage.episodes_clustered} clustered.
          Unmapped episodes remain in search, timeline, and table unless explicitly scoped out.
        </div>
      )}

      <details className="mt-2 text-[11px] text-[color:var(--muted)]">
        <summary className="cursor-pointer select-none">Data provenance</summary>
        <div className="mt-1 grid gap-0.5 pl-3">
          <span>generated {new Date(props.dataset.meta.generated_at_iso).toLocaleString()}</span>
          <span>source {props.dataset.meta.source_db || "not recorded"}</span>
          <span title={props.dataset.meta.source_db_sha256}>
            source revision {shortHash(props.dataset.meta.source_db_sha256)}
          </span>
          {props.dataset.meta.dataset_revision && (
            <span>dataset revision {props.dataset.meta.dataset_revision}</span>
          )}
        </div>
      </details>
    </section>
  )
}
