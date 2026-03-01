import { useEffect, useState } from "react";
import type { Dataset } from "../types";
import { loadDataset } from "./loadDataset";

export function useDataset() {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    loadDataset()
      .then(setDataset)
      .catch((e) => setErr(String(e)));
  }, []);

  return { dataset, err };
}
