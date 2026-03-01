import { useEffect, useRef } from "react"

export default function SearchBar(props: {
  value: string
  onChange: (v: string) => void
  onEnter: () => void
  onClear: () => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "/" && (e.target as HTMLElement)?.tagName !== "INPUT") {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  return (
    <div className="flex items-center gap-2 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-2">
      <input
        ref={inputRef}
        value={props.value}
        onChange={e => props.onChange(e.target.value)}
        onKeyDown={e => {
          if (e.key === "Enter") props.onEnter()
          if (e.key === "Escape") props.onClear()
        }}
        placeholder='Search ("/" to focus) — fulltext across descriptions/spans/clusters…'
        className="w-full bg-transparent px-2 py-1 outline-none"
      />
      {props.value ? (
        <button
          type="button"
          onClick={props.onClear}
          className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
        >
          clear
        </button>
      ) : null}
    </div>
  )
}
