import { useDeferredValue, useEffect, useRef, useState } from "react"
import {
  buildSearchIndex,
  search as runSearch,
  type SearchHit,
  type SearchIndex,
} from "../search/searchIndex"
import type { Dataset } from "../types"

export type SearchMode = "preview" | "pinned"

export function useSearch(dataset: Dataset | null, query: string) {
  const [mode, setMode] = useState<SearchMode>("preview")
  const [index, setIndex] = useState<SearchIndex | null>(null)
  const [hits, setHits] = useState<SearchHit[]>([])
  const deferredQuery = useDeferredValue(query)

  // Optional: consumers can use this to scroll when pin/select happens.
  const rightPanelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!dataset) {
      setIndex(null)
      return
    }

    // Let the shell paint before building the richer MiniSearch index. Basic
    // cross-filtering already uses the lightweight exploration index.
    const timer = window.setTimeout(() => setIndex(buildSearchIndex(dataset)), 0)
    return () => window.clearTimeout(timer)
  }, [dataset])

  useEffect(() => {
    if (!index) return

    const q = deferredQuery.trim()
    if (!q) {
      setHits([])
      setMode("preview")
      return
    }

    setHits(runSearch(index, q, 80))
    setMode(m => (m === "pinned" ? "pinned" : "preview"))
  }, [index, deferredQuery])

  function clear() {
    setHits([])
    setMode("preview")
  }

  function pin() {
    if (!query.trim()) return
    setMode("pinned")
    rightPanelRef.current?.scrollTo({ top: 0, behavior: "smooth" })
  }

  return {
    query,
    mode,
    hits,
    clear,
    pin,
    rightPanelRef,
  }
}
