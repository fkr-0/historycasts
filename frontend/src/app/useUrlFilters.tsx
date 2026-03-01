import { useEffect, useState } from "react";
import {
  readFiltersFromUrl,
  writeFiltersToUrl,
  type Filters,
} from "../urlState";

export function useUrlFilters() {
  const [filters, setFilters] = useState<Filters>(() => readFiltersFromUrl());

  useEffect(() => {
    writeFiltersToUrl(filters);
  }, [filters]);

  return { filters, setFilters };
}
