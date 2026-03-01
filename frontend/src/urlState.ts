export type Filters = {
  podcastId: number | "all"
  q: string
  kind: string | "all"
  narrator: string
  clusterId?: number
  clusterTerm?: string
  clusterYearMin?: number
  clusterYearMax?: number
  clusterSort?: "size" | "cohesion" | "novelty" | "spread"
  topN: number
  year?: number
  yearMin?: number
  yearMax?: number
  axisK: number
}

const num = (v: string | null) => (v == null || v.trim() === "" ? undefined : Number(v))
const parseKind = (value: string | null): Filters["kind"] => {
  if (
    value === "all" ||
    value === "regular" ||
    value === "book" ||
    value === "meta" ||
    value === "special"
  ) {
    return value
  }
  return "all"
}

const parseClusterSort = (value: string | null): Filters["clusterSort"] => {
  if (
    value === "size" ||
    value === "cohesion" ||
    value === "novelty" ||
    value === "spread"
  ) {
    return value
  }
  return "size"
}

export function readFiltersFromUrl(): Filters {
  const u = new URL(window.location.href)
  const p = u.searchParams
  const podcastRaw = p.get("podcast") ?? "all"
  const podcastId = podcastRaw === "all" ? "all" : Number(podcastRaw)

  return {
    podcastId,
    q: p.get("q") ?? "",
    kind: parseKind(p.get("kind")),
    narrator: p.get("narrator") ?? "",
    clusterId: num(p.get("cluster")),
    clusterTerm: p.get("clusterTerm") ?? "",
    clusterYearMin: num(p.get("clusterYearMin")),
    clusterYearMax: num(p.get("clusterYearMax")),
    clusterSort: parseClusterSort(p.get("clusterSort")),
    topN: Math.max(1, Math.min(6, Number(p.get("topN") ?? "1"))),
    year: num(p.get("year")),
    yearMin: num(p.get("yearMin")),
    yearMax: num(p.get("yearMax")),
    axisK: Math.max(0.3, Math.min(3, Number(p.get("axisK") ?? "1"))),
  }
}

export function writeFiltersToUrl(f: Filters) {
  const u = new URL(window.location.href)
  const p = u.searchParams

  p.set("podcast", String(f.podcastId))

  if (f.q) p.set("q", f.q)
  else p.delete("q")

  if (f.kind !== "all") p.set("kind", f.kind)
  else p.delete("kind")

  if (f.narrator) p.set("narrator", f.narrator)
  else p.delete("narrator")

  if (f.clusterId != null && !Number.isNaN(f.clusterId)) p.set("cluster", String(f.clusterId))
  else p.delete("cluster")

  if (f.clusterTerm) p.set("clusterTerm", f.clusterTerm)
  else p.delete("clusterTerm")

  if (f.clusterYearMin != null && !Number.isNaN(f.clusterYearMin)) p.set("clusterYearMin", String(f.clusterYearMin))
  else p.delete("clusterYearMin")

  if (f.clusterYearMax != null && !Number.isNaN(f.clusterYearMax)) p.set("clusterYearMax", String(f.clusterYearMax))
  else p.delete("clusterYearMax")

  if (f.clusterSort) p.set("clusterSort", f.clusterSort)
  else p.delete("clusterSort")

  p.set("topN", String(f.topN))

  if (f.year != null && !Number.isNaN(f.year)) p.set("year", String(f.year))
  else p.delete("year")

  if (f.yearMin != null && !Number.isNaN(f.yearMin)) p.set("yearMin", String(f.yearMin))
  else p.delete("yearMin")

  if (f.yearMax != null && !Number.isNaN(f.yearMax)) p.set("yearMax", String(f.yearMax))
  else p.delete("yearMax")

  p.set("axisK", String(f.axisK))

  window.history.replaceState({}, "", u.toString())
}
