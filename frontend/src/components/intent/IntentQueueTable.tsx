import type { IntentOperation } from "../../intent/types"

type Props = {
  operations: IntentOperation[]
  onCancel: (opId: string) => void
  onRemove: (opId: string) => void
}

export default function IntentQueueTable(props: Props) {
  return (
    <div className="max-h-[50vh] overflow-auto rounded-lg border border-[color:var(--border)]">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-[color:var(--surface)]">
          <tr>
            <th className="px-2 py-1">status</th>
            <th className="px-2 py-1">entity</th>
            <th className="px-2 py-1">type</th>
            <th className="px-2 py-1">created</th>
            <th className="px-2 py-1">reason</th>
            <th className="px-2 py-1">actions</th>
          </tr>
        </thead>
        <tbody>
          {props.operations.map(op => (
            <tr key={op.op_id} className="border-t border-[color:var(--border)] align-top">
              <td className="px-2 py-1">{op.status}</td>
              <td className="px-2 py-1">
                {op.entity_type}:{String(op.entity_id ?? "-")}
              </td>
              <td className="px-2 py-1">{op.op_type}</td>
              <td className="px-2 py-1">{new Date(op.created_at).toLocaleString()}</td>
              <td className="px-2 py-1 text-[color:var(--muted)]">{op.status_reason ?? "-"}</td>
              <td className="px-2 py-1">
                <div className="flex gap-1">
                  <button
                    type="button"
                    className="rounded border border-[color:var(--border)] px-1"
                    onClick={() => props.onCancel(op.op_id)}
                    disabled={op.status !== "queued"}
                  >
                    cancel
                  </button>
                  <button
                    type="button"
                    className="rounded border border-[color:var(--border)] px-1"
                    onClick={() => props.onRemove(op.op_id)}
                  >
                    remove
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
