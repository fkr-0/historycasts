import { useMemo } from "react"
import type { Dataset } from "../../types"
import { colorForCluster } from "../../visual/clusterVisuals"
import ClusterLegend from "../ClusterLegend"
import ClusterQualityScatter from "./ClusterQualityScatter"

export type ClusterSort = "size" | "cohesion" | "distinctiveness" | "spread"

interface ClusterMetricRow {
  id: number
  label: string
  nMembers: number
  cohesion: number
  distinctiveness: number
  spread: number
  historicalYear?: number
  topTerms: string[]
}

export default function ClusterIndexView(props: {
  dataset: Dataset
  sortBy: ClusterSort
  onSortChange: (sort: ClusterSort) => void
  onSelectCluster: (clusterId: number) => void
}) {
  const rows = useMemo<ClusterMetricRow[]>(() => {
    const stats = new Map((props.dataset.cluster_stats ?? []).map(s => [s.cluster_id, s]))
    return props.dataset.clusters.map(c => {
      const s = stats.get(c.cluster.id)
      return {
        id: c.cluster.id,
        label: c.cluster.label?.trim() || `Cluster ${c.cluster.id}`,
        nMembers: c.cluster.n_members,
        cohesion: s?.cohesion_proxy ?? 0,
        distinctiveness: s?.distinctiveness_proxy ?? 0,
        spread: s?.temporal_span_years ?? 0,
        historicalYear: s?.median_historical_year ?? c.cluster.centroid_mid_year,
        topTerms: c.top_keywords.slice(0, 5).map(t => t.phrase),
      }
    })
  }, [props.dataset.cluster_stats, props.dataset.clusters])

  const sortedRows = useMemo(() => {
    const out = rows.slice()
    out.sort((a, b) => {
      switch (props.sortBy) {
        case "cohesion":
          return b.cohesion - a.cohesion || b.nMembers - a.nMembers
        case "distinctiveness":
          return b.distinctiveness - a.distinctiveness || b.cohesion - a.cohesion
        case "spread":
          return b.spread - a.spread || b.nMembers - a.nMembers
        default:
          return b.nMembers - a.nMembers || b.cohesion - a.cohesion
      }
    })
    return out
  }, [props.sortBy, rows])

  return (
    <div className="grid h-full min-h-0 gap-3 overflow-auto">
      <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 text-lg">Clusters</h2>
          <label className="text-xs text-[color:var(--muted)]">
            Sort clusters
            <select
              aria-label="Sort clusters"
              className="ml-2"
              value={props.sortBy}
              onChange={e => props.onSortChange(e.target.value as ClusterSort)}
            >
              <option value="size">size</option>
              <option value="cohesion">cohesion</option>
              <option value="distinctiveness">distinctiveness</option>
              <option value="spread">spread</option>
            </select>
          </label>
        </div>

        <div className="mb-3">
          <ClusterQualityScatter points={rows} onSelectCluster={props.onSelectCluster} />
        </div>

        <div className="mb-3">
          <ClusterLegend dataset={props.dataset} />
        </div>

        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {sortedRows.map(row => (
            <div
              key={row.id}
              className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2"
            >
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="flex items-center gap-1.5 text-sm font-semibold">
                    <span
                      aria-hidden="true"
                      className="inline-block h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: colorForCluster(row.id) }}
                    />
                    <span>
                      #{row.id} {row.label}
                    </span>
                  </div>
                  <div className="text-xs text-[color:var(--muted)]">{row.nMembers} episodes</div>
                </div>
                <button
                  type="button"
                  className="rounded border border-[color:var(--border)] px-2 py-1 text-xs"
                  aria-label={`Open cluster #${row.id}`}
                  onClick={() => props.onSelectCluster(row.id)}
                >
                  open
                </button>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-1 text-xs xl:grid-cols-4">
                <div className="rounded border border-[color:var(--border)]/70 p-1">
                  <div className="text-[color:var(--muted)]">cohesion</div>
                  <div className="font-semibold">{row.cohesion.toFixed(2)}</div>
                </div>
                <div className="rounded border border-[color:var(--border)]/70 p-1">
                  <div className="text-[color:var(--muted)]">distinctiveness</div>
                  <div className="font-semibold">{row.distinctiveness.toFixed(2)}</div>
                </div>
                <div className="rounded border border-[color:var(--border)]/70 p-1">
                  <div className="text-[color:var(--muted)]">spread</div>
                  <div className="font-semibold">{row.spread.toFixed(0)}</div>
                </div>
                <div className="rounded border border-[color:var(--border)]/70 p-1">
                  <div className="text-[color:var(--muted)]">historical center</div>
                  <div className="font-semibold">
                    {row.historicalYear == null ? "—" : Math.round(row.historicalYear)}
                  </div>
                </div>
              </div>
              {(row.nMembers < 3 || row.cohesion < 0.12 || row.spread > 500) && (
                <div className="mt-2 flex flex-wrap gap-1 text-[11px]">
                  {row.nMembers < 3 && (
                    <span className="rounded border border-[color:var(--border)] px-1.5 py-0.5">
                      tiny cluster
                    </span>
                  )}
                  {row.cohesion < 0.12 && (
                    <span className="rounded border border-[color:var(--border)] px-1.5 py-0.5">
                      low semantic cohesion
                    </span>
                  )}
                  {row.spread > 500 && (
                    <span className="rounded border border-[color:var(--border)] px-1.5 py-0.5">
                      very broad period
                    </span>
                  )}
                </div>
              )}
              <div className="mt-2 text-xs text-[color:var(--muted)]">
                {row.topTerms.join(" · ") || "(no terms)"}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
