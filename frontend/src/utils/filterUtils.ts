// utils/filterUtils.ts
import type { Dataset } from "../types"
import type { Filters } from "../urlState"

export function filterEpisodes(dataset: Dataset | null, filters: Filters) {
  if (!dataset) return []
  const q = filters.q.trim().toLowerCase()
  const narr = filters.narrator.trim().toLowerCase()
  const kind = filters.kind
  const clusterId = filters.clusterId

  return dataset.episodes.filter(e => {
    if (filters.podcastId !== "all" && e.podcast_id !== filters.podcastId) return false
    if (q && !e.title.toLowerCase().includes(q)) return false
    if (kind !== "all" && (e.kind ?? "") !== kind) return false
    if (narr && !(e.narrator ?? "").toLowerCase().includes(narr)) return false
    if (clusterId != null) {
      const cid = dataset.episode_clusters[String(e.id)]
      if (cid !== clusterId) return false
    }
    return true
  })
}
