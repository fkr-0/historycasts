import { describe, expect, it } from "vitest"
import { buildClusterEpisodeUnlinkOp, buildClusterRelabelOp } from "./clusterOps"

describe("clusterOps", () => {
  it("builds cluster relabel op", () => {
    const op = buildClusterRelabelOp({ clusterId: 5, label: "New Label", prevLabel: "Old" })
    expect(op.entity_type).toBe("cluster")
    expect(op.entity_id).toBe(5)
    expect(op.op_type).toBe("update")
    expect(op.payload).toEqual({ fields: { label: "New Label" } })
    expect(op.sql_preview).toContain("UPDATE clusters")
  })

  it("builds relation unlink op", () => {
    const op = buildClusterEpisodeUnlinkOp({ episodeId: 33, clusterId: 5 })
    expect(op.entity_type).toBe("relation")
    expect(op.entity_id).toBe(33)
    expect(op.op_type).toBe("unlink")
    expect(op.payload).toMatchObject({ left_id: 33, right_id: 5 })
    expect(op.sql_preview).toContain("DELETE FROM episode_clusters")
  })
})
