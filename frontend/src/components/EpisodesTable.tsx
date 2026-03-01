import { useMemo } from "react"
import type { Dataset } from "../types"
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState
} from "@tanstack/react-table"

type Episode = Dataset["episodes"][number]

const col = createColumnHelper<Episode>()

export default function EpisodesTable(props: {
  dataset: Dataset
  episodes: Episode[]
  selectedEpisodeId: number | null
  onSelectEpisode: (id: number) => void
}) {
  const [sorting, setSorting] = (useMemo(() => [[], () => {}] as unknown as [SortingState, (s: SortingState) => void], []) )
  // NOTE: keep this super light; if you want persistent sorting, lift state to parent.
  // (We can wire it later; leaving minimal to avoid UI bloat.)

  const columns = useMemo(
    () => [
      col.accessor("title", {
        header: "Episode",
        cell: info => (
          <div className="min-w-0">
            <div className="truncate font-semibold">{info.getValue()}</div>
            <div className="truncate text-xs text-[color:var(--muted)]">
              {info.row.original.narrator ?? "?"} · {info.row.original.kind ?? "?"}
            </div>
          </div>
        )
      }),
      col.accessor("pub_date_iso", {
        header: "Published",
        cell: info => (
          <span className="text-xs text-[color:var(--muted)]">
            {new Date(info.getValue()).toLocaleDateString()}
          </span>
        )
      })
    ],
    []
  )

  const table = useReactTable({
    data: props.episodes,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel()
  })

  return (
    <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2">
        <div className="text-sm font-semibold">Episodes</div>
        <div className="text-xs text-[color:var(--muted)]">{props.episodes.length} rows</div>
      </div>

      <div className="max-h-[420px] overflow-auto">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-[color:var(--surface)]/90 backdrop-blur">
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id}>
                {hg.headers.map(h => (
                  <th
                    key={h.id}
                    className="px-3 py-2 text-xs text-[color:var(--muted)]"
                    onClick={h.column.getToggleSortingHandler()}
                  >
                    {flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>

          <tbody>
            {table.getRowModel().rows.map(row => {
              const active = props.selectedEpisodeId === row.original.id
              return (
                <tr
                  key={row.id}
                  className={
                    "cursor-pointer border-t border-[color:var(--border)]/60 " +
                    (active ? "bg-[color:var(--surface-2)]" : "hover:bg-[color:var(--surface)]/80")
                  }
                  onClick={() => props.onSelectEpisode(row.original.id)}
                >
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-3 py-2 align-top">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
