import { useEffect, useMemo, useRef, useState } from "react";
import type { Dataset } from "../types";
import {
  buildSearchIndex,
  search as runSearch,
  type SearchHit,
  type SearchIndex,
} from "../search/searchIndex";

export type SearchMode = "preview" | "pinned";

export function useSearch(dataset: Dataset | null) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("preview");
  const [index, setIndex] = useState<SearchIndex | null>(null);
  const [hits, setHits] = useState<SearchHit[]>([]);

  // Optional: consumers can use this to scroll when pin/select happens.
  const rightPanelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!dataset) return;
    setIndex(buildSearchIndex(dataset));
  }, [dataset]);

  useEffect(() => {
    if (!index) return;

    const q = query.trim();
    if (!q) {
      setHits([]);
      setMode("preview");
      return;
    }

    setHits(runSearch(index, q, 80));
    setMode((m) => (m === "pinned" ? "pinned" : "preview"));
  }, [index, query]);

  function clear() {
    setQuery("");
    setHits([]);
    setMode("preview");
  }

  function pin() {
    if (!query.trim()) return;
    setMode("pinned");
    rightPanelRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }

  return {
    query,
    setQuery,
    mode,
    hits,
    clear,
    pin,
    rightPanelRef,
  };
}
