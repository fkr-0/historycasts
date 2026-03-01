import IntentQueueTable from "./IntentQueueTable"
import type { IntentOperation } from "../../intent/types"

type Props = {
  operations: IntentOperation[]
  queued: number
  applied: number
  invalid: number
  cancelled: number
  onClose: () => void
  onReconcile: () => void
  onCleanup: () => void
  onCancel: (opId: string) => void
  onRemove: (opId: string) => void
  onExportJson: () => string
  onExportSql: () => string
}

function downloadText(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export default function IntentQueueModal(props: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="relative h-[85vh] w-[min(1200px,96vw)] rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)] p-3">
        <button
          type="button"
          onClick={props.onClose}
          className="absolute right-3 top-3 rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
        >
          close
        </button>

        <h2 className="m-0 text-lg">Intent Queue</h2>
        <div className="mt-1 text-xs text-[color:var(--muted)]">
          queued {props.queued} · applied {props.applied} · invalid {props.invalid} · cancelled{" "}
          {props.cancelled}
        </div>

        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <button
            type="button"
            className="rounded border border-[color:var(--border)] px-2 py-1"
            onClick={props.onReconcile}
          >
            refresh status
          </button>
          <button
            type="button"
            className="rounded border border-[color:var(--border)] px-2 py-1"
            onClick={props.onCleanup}
          >
            cleanup applied/invalid
          </button>
          <button
            type="button"
            className="rounded border border-[color:var(--border)] px-2 py-1"
            onClick={() => downloadText("intent-queue.json", props.onExportJson())}
          >
            export json
          </button>
          <button
            type="button"
            className="rounded border border-[color:var(--border)] px-2 py-1"
            onClick={() => downloadText("intent-queue.sql", props.onExportSql())}
          >
            export sql
          </button>
          <button
            type="button"
            className="rounded border border-[color:var(--border)] px-2 py-1"
            onClick={() => navigator.clipboard.writeText(props.onExportSql())}
          >
            copy sql
          </button>
        </div>

        <div className="mt-3">
          <IntentQueueTable operations={props.operations} onCancel={props.onCancel} onRemove={props.onRemove} />
        </div>
      </div>
    </div>
  )
}
