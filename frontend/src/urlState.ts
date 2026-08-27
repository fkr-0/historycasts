export type Filters = {
  podcastId: number | "all"
  q: string
  kind: string | "all"
  narrator: string
  geo?: "all" | "mapped" | "unmapped"
  clusterId?: number
  clusterTerm?: string
  clusterYearMin?: number
  clusterYearMax?: number
  clusterSort?: "size" | "cohesion" | "distinctiveness" | "spread"
  topN: number
  year?: number
  yearMin?: number
  yearMax?: number
  axisK: number
  tableSort?: "title" | "pub_date_iso"
  tableDir?: "asc" | "desc"
}

const parseGeo = (value: string | null): Filters["geo"] => {
  return value === "mapped" || value === "unmapped" ? value : "all"
}

const parseTableSort = (value: string | null): Filters["tableSort"] => {
  return value === "title" || value === "pub_date_iso" ? value : undefined
}

const parseTableDir = (value: string | null): Filters["tableDir"] => {
  return value === "asc" || value === "desc" ? value : undefined
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
  // Preserve old shared URLs while exposing the corrected metric name.
  if (value === "novelty") return "distinctiveness"
  if (
    value === "size" ||
    value === "cohesion" ||
    value === "distinctiveness" ||
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
    geo: parseGeo(p.get("geo")),
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
    tableSort: parseTableSort(p.get("tableSort")),
    tableDir: parseTableDir(p.get("tableDir")),
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

  if (f.geo && f.geo !== "all") p.set("geo", f.geo)
  else p.delete("geo")

  if (f.clusterId != null && !Number.isNaN(f.clusterId)) p.set("cluster", String(f.clusterId))
  else p.delete("cluster")

  if (f.clusterTerm) p.set("clusterTerm", f.clusterTerm)
  else p.delete("clusterTerm")

  if (f.clusterYearMin != null && !Number.isNaN(f.clusterYearMin))
    p.set("clusterYearMin", String(f.clusterYearMin))
  else p.delete("clusterYearMin")

  if (f.clusterYearMax != null && !Number.isNaN(f.clusterYearMax))
    p.set("clusterYearMax", String(f.clusterYearMax))
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

  if (f.tableSort) p.set("tableSort", f.tableSort)
  else p.delete("tableSort")

  if (f.tableDir) p.set("tableDir", f.tableDir)
  else p.delete("tableDir")

  window.history.replaceState({}, "", u.toString())
}

export function resetExplorationScope(filters: Filters): Filters {
  return {
    ...filters,
    podcastId: "all",
    q: "",
    kind: "all",
    narrator: "",
    geo: "all",
    clusterId: undefined,
    clusterTerm: "",
    clusterYearMin: undefined,
    clusterYearMax: undefined,
    year: undefined,
    yearMin: undefined,
    yearMax: undefined,
    tableSort: undefined,
    tableDir: undefined,
  }
}
