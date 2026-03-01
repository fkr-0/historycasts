import { describe, expect, it } from "vitest"
import { readFiltersFromUrl, writeFiltersToUrl, type Filters } from "./urlState"

describe("urlState cluster scope", () => {
  it("reads cluster scope and sort from URL", () => {
    window.history.replaceState(
      {},
      "",
      "/?podcast=all&topN=2&axisK=1&cluster=9&clusterTerm=empire&clusterYearMin=1800&clusterYearMax=1810&clusterSort=spread",
    )

    const filters = readFiltersFromUrl()
    expect(filters.clusterId).toBe(9)
    expect(filters.clusterTerm).toBe("empire")
    expect(filters.clusterYearMin).toBe(1800)
    expect(filters.clusterYearMax).toBe(1810)
    expect(filters.clusterSort).toBe("spread")
  })

  it("writes cluster scope and sort to URL", () => {
    window.history.replaceState({}, "", "/")

    const filters: Filters = {
      podcastId: "all",
      q: "",
      kind: "all",
      narrator: "",
      topN: 1,
      axisK: 1,
      clusterId: 7,
      clusterTerm: "constitution",
      clusterYearMin: 1790,
      clusterYearMax: 1820,
      clusterSort: "cohesion",
    }

    writeFiltersToUrl(filters)

    const p = new URL(window.location.href).searchParams
    expect(p.get("cluster")).toBe("7")
    expect(p.get("clusterTerm")).toBe("constitution")
    expect(p.get("clusterYearMin")).toBe("1790")
    expect(p.get("clusterYearMax")).toBe("1820")
    expect(p.get("clusterSort")).toBe("cohesion")
  })
})
