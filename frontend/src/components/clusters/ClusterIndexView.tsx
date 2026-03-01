import { useMemo } from "react"
import type { Dataset } from "../../types"

export type ClusterSort = "size" | "cohesion" | "novelty" | "spread"

interface ClusterMetricRow {
  id: number
  label: string
  nMembers: number
  cohesion: number
  novelty: number
  spread: number
  topTerms: string[]
}

export default function ClusterIndexView(props: {
  dataset: Dataset
  sortBy: ClusterSort
  onSortChange: (sort: ClusterSort) => void
  onSelectCluster: (clusterId: number) => void
}) {
  const rows = useMemo<ClusterMetricRow[]>(() => {
    const stats = new Map((props.dataset.cluster_stats ?? []).map((s) => [s.cluster_id, s]))
    return props.dataset.clusters.map((c) => {
      const s = stats.get(c.cluster.id)
      return {
        id: c.cluster.id,
        label: c.cluster.label?.trim() || `Cluster ${c.cluster.id}`,
        nMembers: c.cluster.n_members,
        cohesion: s?.cohesion_proxy ?? 0,
        novelty: s ? 1 - (s.dominant_podcast_share ?? 1) : 0,
        spread: s?.temporal_span_years ?? 0,
        topTerms: c.top_keywords.slice(0, 5).map((t) => t.phrase),
      }
    })
  }, [props.dataset.cluster_stats, props.dataset.clusters])

  const sortedRows = useMemo(() => {
    const out = rows.slice()
    out.sort((a, b) => {
      switch (props.sortBy) {
        case "cohesion":
          return b.cohesion - a.cohesion || b.nMembers - a.nMembers
        case "novelty":
          return b.novelty - a.novelty || b.cohesion - a.cohesion
        case "spread":
          return b.spread - a.spread || b.nMembers - a.nMembers
        case "size":
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
              onChange={(e) => props.onSortChange(e.target.value as ClusterSort)}
            >
              <option value="size">size</option>
              <option value="cohesion">cohesion</option>
              <option value="novelty">novelty</option>
              <option value="spread">spread</option>
            </select>
          </label>
        </div>

        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {sortedRows.map((row) => (
            <div key={row.id} className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-semibold">#{row.id} {row.label}</div>
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
              <div className="mt-2 grid grid-cols-3 gap-1 text-xs">
                <div className="rounded border border-[color:var(--border)]/70 p-1">
                  <div className="text-[color:var(--muted)]">cohesion</div>
                  <div className="font-semibold">{row.cohesion.toFixed(2)}</div>
                </div>
                <div className="rounded border border-[color:var(--border)]/70 p-1">
                  <div className="text-[color:var(--muted)]">novelty</div>
                  <div className="font-semibold">{row.novelty.toFixed(2)}</div>
                </div>
                <div className="rounded border border-[color:var(--border)]/70 p-1">
                  <div className="text-[color:var(--muted)]">spread</div>
                  <div className="font-semibold">{row.spread.toFixed(0)}</div>
                </div>
              </div>
              <div className="mt-2 text-xs text-[color:var(--muted)]">{row.topTerms.join(" · ") || "(no terms)"}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
