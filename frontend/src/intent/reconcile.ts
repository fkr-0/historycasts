import type { Dataset } from "../types"
import type { IntentOperation } from "./types"

function getEntityRecord(dataset: Dataset, op: IntentOperation): Record<string, unknown> | undefined {
  const id = op.entity_id
  if (id == null) return undefined

  switch (op.entity_type) {
    case "episode":
      return dataset.episodes.find(e => e.id === Number(id))
    case "span":
      return dataset.spans.find(s => s.id === Number(id))
    case "place":
      return dataset.places.find(p => p.id === Number(id))
    case "entity":
      return dataset.entities.find(e => e.id === Number(id))
    case "cluster":
      return dataset.clusters.find(c => c.cluster.id === Number(id))?.cluster
    case "relation": {
      const clusterId = dataset.episode_clusters[String(id)]
      if (clusterId == null) return undefined
      return { episode_id: Number(id), cluster_id: clusterId }
    }
    default:
      return undefined
  }
}

function isUpdateApplied(record: Record<string, unknown> | undefined, op: IntentOperation): boolean {
  if (!record) return false
  const fields = (op.payload.fields ?? op.payload) as Record<string, unknown>
  return Object.entries(fields).every(([k, v]) => record[k] === v)
}

export function reconcileOperation(dataset: Dataset, op: IntentOperation): IntentOperation {
  if (op.status === "cancelled") return op
  const record = getEntityRecord(dataset, op)

  if (op.op_type === "update") {
    if (isUpdateApplied(record, op)) return { ...op, status: "applied", status_reason: "values already match" }
    if (!record) return { ...op, status: "invalid", status_reason: "target row missing" }
    return { ...op, status: "queued", status_reason: "not yet applied" }
  }

  if (op.op_type === "delete") {
    if (!record) return { ...op, status: "applied", status_reason: "row absent" }
    return { ...op, status: "queued", status_reason: "row still present" }
  }

  if (op.op_type === "insert" || op.op_type === "link") {
    if (record) return { ...op, status: "applied", status_reason: "target exists" }
    return { ...op, status: "queued", status_reason: "target not found yet" }
  }

  if (op.op_type === "unlink") {
    if (!record) return { ...op, status: "applied", status_reason: "relation removed" }
    return { ...op, status: "queued", status_reason: "relation still exists" }
  }

  return { ...op, status: "invalid", status_reason: "unsupported op type" }
}

export function reconcileQueue(dataset: Dataset, ops: IntentOperation[]): IntentOperation[] {
  return ops.map(op => reconcileOperation(dataset, op))
}
