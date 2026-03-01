import type { Dataset } from "../types"
import type { SearchHit } from "../search/searchIndex"

function fmtType(t: string) {
  return t.replaceAll("_", " ")
}

export default function SearchResultsPanel(props: {
  dataset: Dataset
  query: string
  hits: SearchHit[]
  mode: "preview" | "pinned"
  onSelectEpisode: (episodeId: number) => void
  onSelectCluster: (clusterId: number) => void
}) {
  if (!props.query.trim()) return null
  if (!props.hits.length) {
    return (
      <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <div className="text-sm font-semibold">Search</div>
        <div className="mt-1 text-xs text-[color:var(--muted)]">No results.</div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-sm font-semibold">
          {props.mode === "pinned" ? "Search results" : "Search preview"}
        </div>
        <div className="text-xs text-[color:var(--muted)]">
          {props.hits.length} hits
        </div>
      </div>

      <div className="mt-2 grid gap-2">
        {props.hits.slice(0, props.mode === "preview" ? 8 : 50).map(hit => {
          const d = hit.doc
          const episodeId = d.episodeId
          const clusterId = d.clusterId
          return (
            <button
              key={hit.id}
              type="button"
              className="text-left rounded-lg border border-[color:var(--border)] bg-[color:var(--surface)] px-3 py-2 hover:bg-[color:var(--surface)]/80"
              onClick={() => {
                if (typeof episodeId === "number") props.onSelectEpisode(episodeId)
                else if (typeof clusterId === "number") props.onSelectCluster(clusterId)
              }}
            >
              <div className="flex items-baseline justify-between gap-2">
                <div className="truncate text-sm font-semibold">
                  {d.title ?? d.text.slice(0, 80)}
                </div>
                <div className="shrink-0 text-[10px] text-[color:var(--muted)]">
                  {fmtType(d.type)} · {hit.score.toFixed(2)}
                </div>
              </div>
              <div className="mt-1 line-clamp-2 text-xs text-[color:var(--muted)]">
                {d.text}
              </div>
            </button>
          )
        })}
      </div>

      {props.mode === "preview" ? (
        <div className="mt-2 text-xs text-[color:var(--muted)]">
          Press <span className="font-semibold">Enter</span> to pin results.
        </div>
      ) : null}
    </div>
  )
}
