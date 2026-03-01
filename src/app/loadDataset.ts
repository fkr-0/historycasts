import type { Dataset } from "../types";

export async function loadDataset(): Promise<Dataset> {
  const res = await fetch("/dataset.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load dataset.json: ${res.status}`);
  return (await res.json()) as Dataset;
}
