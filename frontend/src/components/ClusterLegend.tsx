import type { Dataset } from "../types"
import { clusterLegendRows } from "../visual/clusterVisuals"

export default function ClusterLegend(props: { dataset: Dataset; clusterIds?: Iterable<number> }) {
  const rows = clusterLegendRows(props.dataset, props.clusterIds)

  if (rows.length === 0) return null

  return (
    <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)]/70 p-2">
      <div className="mb-1 text-xs font-semibold text-[color:var(--muted)]">Cluster legend</div>
      <div className="flex flex-wrap gap-1.5">
        {rows.map(row => (
          <div
            key={row.id}
            className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
          >
            <span
              aria-hidden="true"
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: row.color }}
            />
            <span className="font-semibold">#{row.id}</span>
            <span>{row.label}</span>
            <span className="text-[color:var(--muted)]">{row.memberCount} eps</span>
          </div>
        ))}
      </div>
    </div>
  )
}
