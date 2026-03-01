import type { IntentOperation } from "../types"

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID()
  return `op-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function buildEpisodeFieldUpdateOp(args: {
  episodeId: number
  field: "title" | "narrator" | "kind" | "description_pure"
  value: string
  precondition?: string | null
}): IntentOperation {
  const { episodeId, field, value, precondition } = args
  return {
    op_id: newId(),
    created_at: new Date().toISOString(),
    entity_type: "episode",
    entity_id: episodeId,
    op_type: "update",
    payload: { fields: { [field]: value } },
    preconditions: precondition == null ? undefined : { [field]: precondition },
    status: "queued",
    sql_preview: `UPDATE episodes SET ${field}='${String(value).replaceAll("'", "''")}' WHERE id=${episodeId};`,
  }
}
