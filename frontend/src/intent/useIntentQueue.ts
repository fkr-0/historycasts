import { useCallback, useMemo, useState } from "react"
import type { Dataset } from "../types"
import { reconcileQueue } from "./reconcile"
import { loadIntentMeta, loadIntentQueue, saveIntentMeta, saveIntentQueue } from "./storage"
import type { IntentOperation } from "./types"

function toSql(ops: IntentOperation[]): string {
  const lines: string[] = ["BEGIN;"]
  for (const op of ops) {
    lines.push(`-- op ${op.op_id} (${op.op_type})`)
    if (op.sql_preview) {
      lines.push(op.sql_preview)
      continue
    }
    lines.push(`-- no sql preview for ${op.entity_type}:${String(op.entity_id ?? "")}`)
  }
  lines.push("COMMIT;")
  return `${lines.join("\n")}\n`
}

export function useIntentQueue(dataset: Dataset | null) {
  const [operations, setOperations] = useState<IntentOperation[]>(() => loadIntentQueue())
  const [meta, setMeta] = useState(() => loadIntentMeta())

  const persist = useCallback((next: IntentOperation[]) => {
    setOperations(next)
    saveIntentQueue(next)
  }, [])

  const addOperation = useCallback(
    (op: IntentOperation) => {
      persist([...operations, op])
    },
    [operations, persist]
  )

  const reconcile = useCallback(() => {
    if (!dataset) return
    const next = reconcileQueue(dataset, operations)
    persist(next)
    const nextMeta = {
      ...meta,
      schema_version: dataset.meta.schema_version,
      last_reconcile_at: new Date().toISOString(),
    }
    setMeta(nextMeta)
    saveIntentMeta(nextMeta)
  }, [dataset, meta, operations, persist])

  const cancel = useCallback(
    (opId: string) => {
      const next = operations.map(op =>
        op.op_id === opId ? { ...op, status: "cancelled" as const, status_reason: "cancelled by user" } : op
      )
      persist(next)
    },
    [operations, persist]
  )

  const remove = useCallback(
    (opId: string) => {
      persist(operations.filter(op => op.op_id !== opId))
    },
    [operations, persist]
  )

  const cleanup = useCallback(() => {
    persist(operations.filter(op => op.status === "queued"))
  }, [operations, persist])

  const queueCounts = useMemo(() => {
    const counts = { queued: 0, applied: 0, invalid: 0, cancelled: 0 }
    for (const op of operations) counts[op.status] += 1
    return counts
  }, [operations])

  const exportJson = useCallback(() => {
    return JSON.stringify({ operations, meta }, null, 2)
  }, [meta, operations])

  const exportSql = useCallback(() => {
    return toSql(operations.filter(op => op.status !== "cancelled"))
  }, [operations])

  return {
    operations,
    queueCounts,
    addOperation,
    reconcile,
    cancel,
    remove,
    cleanup,
    exportJson,
    exportSql,
  }
}
