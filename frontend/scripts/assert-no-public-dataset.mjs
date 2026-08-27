import { existsSync } from "node:fs"
import { fileURLToPath } from "node:url"

const publicDataset = fileURLToPath(new URL("../public/dataset.json", import.meta.url))

if (existsSync(publicDataset)) {
  console.error(
    "frontend/public/dataset.json is forbidden: run the canonical podcast-atlas build-static pipeline to generate dist/dataset.json from the selected SQLite DB."
  )
  process.exit(1)
}
