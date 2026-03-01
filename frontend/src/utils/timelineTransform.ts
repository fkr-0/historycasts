import type { Dataset } from "../types"

export interface D3StackData {
  podcastId: number
  podcastTitle: string
  episodes: Array<{
    episodeId: number
    title: string
    pubDate: string
    spans: Array<{
      spanId: number
      start: Date
      end: Date
      score: number
      sourceText: string
      clusterId?: number
    }>
  }>
}

function isValidDate(dateString: string | undefined): dateString is string {
  if (!dateString) return false
  const date = new Date(dateString)
  return date instanceof Date && !Number.isNaN(date.getTime())
}

export function transformToStackData(dataset: Dataset, episodeIds: number[]): D3StackData[] {
  if (episodeIds.length === 0) {
    return []
  }

  // Create a map of episodes by ID
  const episodesMap = new Map(
    dataset.episodes.filter(ep => episodeIds.includes(ep.id)).map(ep => [ep.id, ep])
  )

  // Create a map of podcasts by ID
  const podcastsMap = new Map(dataset.podcasts.map(p => [p.id, p]))

  // Group episodes by podcast
  const podcastEpisodesMap = new Map<number, Set<number>>()

  for (const episodeId of episodeIds) {
    const episode = episodesMap.get(episodeId)
    if (episode) {
      const podcastId = episode.podcast_id
      if (!podcastEpisodesMap.has(podcastId)) {
        podcastEpisodesMap.set(podcastId, new Set())
      }
      podcastEpisodesMap.get(podcastId)?.add(episodeId)
    }
  }

  // Create the result array
  const result: D3StackData[] = []

  for (const [podcastId, episodeIdSet] of podcastEpisodesMap.entries()) {
    const podcast = podcastsMap.get(podcastId)
    if (!podcast) continue

    // Get episodes for this podcast and sort by pub date
    const episodes: D3StackData["episodes"] = []
    const episodeIdsForPodcast = Array.from(episodeIdSet)

    for (const episodeId of episodeIdsForPodcast) {
      const episode = episodesMap.get(episodeId)
      if (!episode) continue

      // Get spans for this episode (only those with valid dates)
      const validSpans = dataset.spans.filter(
        span =>
          span.episode_id === episodeId && isValidDate(span.start_iso) && isValidDate(span.end_iso)
      )

      const spans = validSpans.map(span => {
        const a = new Date(span.start_iso)
        const b = new Date(span.end_iso)
        const start = a.getTime() <= b.getTime() ? a : b
        const end = a.getTime() <= b.getTime() ? b : a
        return {
          spanId: span.id,
          start,
          end,
          score: span.score,
          sourceText: span.source_text,
          clusterId: dataset.episode_clusters[String(episodeId)],
        }
      })

      episodes.push({
        episodeId: episode.id,
        title: episode.title,
        pubDate: episode.pub_date_iso,
        spans,
      })
    }

    // Sort episodes by publication date
    episodes.sort((a, b) => {
      const dateA = new Date(a.pubDate).getTime()
      const dateB = new Date(b.pubDate).getTime()
      return dateA - dateB
    })

    result.push({
      podcastId,
      podcastTitle: podcast.title,
      episodes,
    })
  }

  // Sort podcasts by title
  result.sort((a, b) => a.podcastTitle.localeCompare(b.podcastTitle))

  return result
}
