import { useEffect, useState } from "react"
import { type Filters, readFiltersFromUrl, writeFiltersToUrl } from "../urlState"

export function useUrlFilters() {
  const [filters, setFilters] = useState<Filters>(() => readFiltersFromUrl())

  useEffect(() => {
    writeFiltersToUrl(filters)
  }, [filters])

  return { filters, setFilters }
}
