import type { Dataset } from "../types"

export interface ClusterLegendRow {
  id: number
  label: string
  memberCount: number
  color: string
}

export function colorForCluster(clusterId: number): string {
  const hue = (clusterId * 47) % 360
  return `hsl(${hue},65%,45%)`
}

export function clusterLabel(dataset: Dataset, clusterId: number): string {
  const cluster = dataset.clusters.find(c => c.cluster.id === clusterId)
  const label = cluster?.cluster.label?.trim()
  return label || `Cluster #${clusterId}`
}

export function clusterLegendRows(
  dataset: Dataset,
  clusterIds?: Iterable<number>
): ClusterLegendRow[] {
  const allowed = clusterIds ? new Set(clusterIds) : null
  return dataset.clusters
    .filter(c => !allowed || allowed.has(c.cluster.id))
    .map(c => ({
      id: c.cluster.id,
      label: clusterLabel(dataset, c.cluster.id),
      memberCount: c.cluster.n_members,
      color: colorForCluster(c.cluster.id),
    }))
    .sort((a, b) => a.id - b.id)
}
