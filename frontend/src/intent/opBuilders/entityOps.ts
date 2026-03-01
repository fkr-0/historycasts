import type { IntentOperation } from "../types"

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID()
  return `op-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function buildEntityKindUpdateOp(args: {
  entityId: number
  kind: string
  prevKind?: string | null
}): IntentOperation {
  const { entityId, kind, prevKind } = args
  return {
    op_id: newId(),
    created_at: new Date().toISOString(),
    entity_type: "entity",
    entity_id: entityId,
    op_type: "update",
    payload: { fields: { kind } },
    preconditions: prevKind == null ? undefined : { kind: prevKind },
    status: "queued",
    sql_preview: `UPDATE entities SET kind='${String(kind).replaceAll("'", "''")}' WHERE id=${entityId};`,
  }
}
