import { useMemo, useState } from "react"
import type { Dataset } from "../types"
import type { Filters } from "../urlState"
import type { IntentOperation } from "../intent/types"
import { buildClusterEpisodeUnlinkOp, buildClusterRelabelOp } from "../intent/opBuilders/clusterOps"

export default function ClusterPanel(props: {
  dataset: Dataset
  filters: Filters
  onSelectCluster: (clusterId: number) => void
  onClearCluster: () => void
  onQueueOperation?: (op: IntentOperation) => void
}) {
  const [open, setOpen] = useState(true)
  const clusters = useMemo(() => {
    const pid = props.filters.podcastId
    return props.dataset.clusters
      .filter(c => (pid === "all" ? true : c.cluster.podcast_id === pid))
      .sort((a, b) => b.cluster.n_members - a.cluster.n_members)
  }, [props.dataset, props.filters.podcastId])

  return (
    <div>
      <div className="flex items-center justify-between">
        <h3 className="m-0 text-base font-semibold">Clusters</h3>
        <button type="button" onClick={() => setOpen(v => !v)} className="text-xs">
          {open ? "hide" : "show"}
        </button>
      </div>

      {props.filters.clusterId != null && (
        <div className="mt-2">
          <div className="text-xs text-[color:var(--muted)]">
            active cluster: {props.filters.clusterId}
          </div>
          <button type="button" onClick={props.onClearCluster} className="mt-1 text-xs">
            clear cluster filter
          </button>
        </div>
      )}

      {open && (
        <div className="mt-2 grid gap-2">
          {clusters.slice(0, 24).map(c => (
            <div
              key={c.cluster.id}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2"
            >
              <button
                type="button"
                className="w-full text-left"
                onClick={() => props.onSelectCluster(c.cluster.id)}
              >
                <div className="flex justify-between">
                  <b>#{c.cluster.id}</b>
                  <span className="text-xs text-[color:var(--muted)]">{c.cluster.n_members} eps</span>
                </div>
                <div className="text-xs text-[color:var(--muted)]">
                  centroid: {c.cluster.centroid_mid_year.toFixed(0)} ·{" "}
                  {c.cluster.centroid_lat.toFixed(1)}, {c.cluster.centroid_lon.toFixed(1)}
                </div>
                <div className="mt-1.5 text-xs">
                  <div className="text-[color:var(--muted)]">top keywords</div>
                  <div>
                    {c.top_keywords
                      .slice(0, 5)
                      .map(k => k.phrase)
                      .join(" · ")}
                  </div>
                </div>
              </button>
              {props.onQueueOperation && (
                <div className="mt-2 flex gap-1 text-xs">
                  <button
                    type="button"
                    className="rounded border border-[color:var(--border)] px-1"
                    onClick={() => {
                      const next = prompt("Set cluster label", c.cluster.label ?? `Cluster ${c.cluster.id}`)
                      if (!next) return
                      props.onQueueOperation(
                        buildClusterRelabelOp({
                          clusterId: c.cluster.id,
                          label: next,
                          prevLabel: c.cluster.label ?? null,
                        })
                      )
                    }}
                  >
                    queue relabel
                  </button>
                  <button
                    type="button"
                    className="rounded border border-[color:var(--border)] px-1"
                    onClick={() => {
                      const episodeId = prompt("Episode id to unlink from this cluster")
                      if (!episodeId) return
                      const id = Number(episodeId)
                      if (!Number.isFinite(id)) return
                      props.onQueueOperation(
                        buildClusterEpisodeUnlinkOp({ episodeId: id, clusterId: c.cluster.id })
                      )
                    }}
                  >
                    queue episode unlink
                  </button>
                </div>
              )}
            </div>
          ))}
          {clusters.length > 24 && (
            <div className="text-xs text-[color:var(--muted)]">showing top 24 clusters</div>
          )}
        </div>
      )}
    </div>
  )
}
