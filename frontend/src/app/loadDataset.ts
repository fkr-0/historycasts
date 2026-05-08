import type { Dataset } from "../types"

export async function loadDataset(): Promise<Dataset> {
  const datasetUrl = new URL("dataset.json", document.baseURI).pathname
  const res = await fetch(datasetUrl, { cache: "no-store" })
  if (!res.ok) throw new Error(`Failed to load dataset.json: ${res.status}`)
  return (await res.json()) as Dataset
}
