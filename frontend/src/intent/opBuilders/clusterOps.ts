import type { IntentOperation } from "../types"

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID()
  return `op-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function buildClusterRelabelOp(args: {
  clusterId: number
  label: string
  prevLabel?: string | null
}): IntentOperation {
  const { clusterId, label, prevLabel } = args
  return {
    op_id: newId(),
    created_at: new Date().toISOString(),
    entity_type: "cluster",
    entity_id: clusterId,
    op_type: "update",
    payload: { fields: { label } },
    preconditions: prevLabel == null ? undefined : { label: prevLabel },
    status: "queued",
    sql_preview: `UPDATE clusters SET label='${String(label).replaceAll("'", "''")}' WHERE id=${clusterId};`,
  }
}

export function buildClusterEpisodeUnlinkOp(args: {
  episodeId: number
  clusterId: number
}): IntentOperation {
  const { episodeId, clusterId } = args
  return {
    op_id: newId(),
    created_at: new Date().toISOString(),
    entity_type: "relation",
    entity_id: episodeId,
    op_type: "unlink",
    payload: { table: "episode_clusters", left_id: episodeId, right_id: clusterId, left_col: "episode_id", right_col: "cluster_id" },
    status: "queued",
    sql_preview: `DELETE FROM episode_clusters WHERE episode_id=${episodeId} AND cluster_id=${clusterId};`,
  }
}
