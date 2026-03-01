import { describe, expect, it } from "vitest"
import { buildEntityKindUpdateOp } from "./entityOps"

describe("entityOps", () => {
  it("builds entity kind update op", () => {
    const op = buildEntityKindUpdateOp({ entityId: 9, kind: "person", prevKind: "org" })
    expect(op.entity_type).toBe("entity")
    expect(op.entity_id).toBe(9)
    expect(op.payload).toEqual({ fields: { kind: "person" } })
    expect(op.sql_preview).toContain("UPDATE entities")
  })
})
