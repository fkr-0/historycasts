export type IntentEntityType =
  | "episode"
  | "span"
  | "place"
  | "entity"
  | "cluster"
  | "keyword"
  | "relation"

export type IntentOpType = "insert" | "update" | "delete" | "link" | "unlink"
export type IntentStatus = "queued" | "applied" | "invalid" | "cancelled"

export interface IntentOperation {
  op_id: string
  created_at: string
  actor?: string
  entity_type: IntentEntityType
  entity_id?: number | string
  op_type: IntentOpType
  payload: Record<string, unknown>
  preconditions?: Record<string, unknown>
  status: IntentStatus
  status_reason?: string
  sql_preview?: string
}

export interface IntentQueueMeta {
  version: 1
  schema_version?: string
  app_version?: string
  last_reconcile_at?: string
}

export interface IntentQueueSnapshot {
  operations: IntentOperation[]
  meta: IntentQueueMeta
}
