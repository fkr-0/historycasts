type Props = {
  queued: number
  applied: number
  invalid: number
  onClick: () => void
}

export default function IntentQueueButton(props: Props) {
  let cls =
    "rounded-md border px-2 py-1 text-xs border-[color:var(--border)] bg-[color:var(--surface)] text-[color:var(--text)]"
  if (props.queued > 0) {
    cls =
      "rounded-md border px-2 py-1 text-xs border-amber-400/50 bg-amber-500/15 text-amber-200"
  } else if (props.applied > 0 || props.invalid > 0) {
    cls =
      "rounded-md border px-2 py-1 text-xs border-emerald-400/50 bg-emerald-500/15 text-emerald-200"
  }

  return (
    <button type="button" onClick={props.onClick} className={cls} title={`${props.queued} queued, ${props.applied} applied, ${props.invalid} invalid`}>
      Changes ({props.queued})
    </button>
  )
}
