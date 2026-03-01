import type { IntentOperation } from "../types"

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID()
  return `op-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function buildSpanStartYearUpdateOp(args: {
  spanId: number
  startIso: string
  prevStartIso?: string | null
}): IntentOperation {
  const { spanId, startIso, prevStartIso } = args
  return {
    op_id: newId(),
    created_at: new Date().toISOString(),
    entity_type: "span",
    entity_id: spanId,
    op_type: "update",
    payload: { fields: { start_iso: startIso } },
    preconditions: prevStartIso == null ? undefined : { start_iso: prevStartIso },
    status: "queued",
    sql_preview: `UPDATE time_spans SET start_iso='${startIso}' WHERE id=${spanId};`,
  }
}
