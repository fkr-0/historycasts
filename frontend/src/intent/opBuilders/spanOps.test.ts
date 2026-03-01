import { describe, expect, it } from "vitest"
import { buildSpanStartYearUpdateOp } from "./spanOps"

describe("spanOps", () => {
  it("builds span start year update op", () => {
    const op = buildSpanStartYearUpdateOp({
      spanId: 44,
      startIso: "1900-01-01",
      prevStartIso: "1899-01-01",
    })
    expect(op.entity_type).toBe("span")
    expect(op.entity_id).toBe(44)
    expect(op.payload).toEqual({ fields: { start_iso: "1900-01-01" } })
    expect(op.sql_preview).toContain("UPDATE time_spans")
  })
})
