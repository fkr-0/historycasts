import { describe, expect, it } from "vitest"
import { buildEpisodeFieldUpdateOp } from "./episodeOps"

describe("episodeOps", () => {
  it("builds episode update op", () => {
    const op = buildEpisodeFieldUpdateOp({
      episodeId: 12,
      field: "kind",
      value: "regular",
      precondition: "special",
    })
    expect(op.entity_type).toBe("episode")
    expect(op.entity_id).toBe(12)
    expect(op.op_type).toBe("update")
    expect(op.status).toBe("queued")
    expect(op.payload).toEqual({ fields: { kind: "regular" } })
    expect(op.preconditions).toEqual({ kind: "special" })
    expect(op.sql_preview).toContain("UPDATE episodes")
  })
})
