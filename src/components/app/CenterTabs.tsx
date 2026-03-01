import type { CenterTab } from "../../state/tabs";

export default function CenterTabs(props: {
  tabs: CenterTab[];
  activeTabId: CenterTab["id"];
  onActivate: (id: CenterTab["id"]) => void;
  onClose: (id: CenterTab["id"]) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/65 p-2">
      {props.tabs.map((tab) => (
        <div key={tab.id} className="inline-flex items-center gap-1">
          <button
            type="button"
            onClick={() => props.onActivate(tab.id)}
            className={`rounded-lg border px-2 py-1 text-xs ${
              tab.id === props.activeTabId
                ? "border-[color:var(--accent)] bg-[color:var(--surface-2)]"
                : "border-[color:var(--border)] bg-[color:var(--surface)]"
            }`}
          >
            {tab.title}
          </button>

          {tab.id !== "explore" && (
            <button
              type="button"
              aria-label={`Close ${tab.title} tab`}
              className="rounded-md border border-[color:var(--border)] px-1 text-[color:var(--muted)]"
              onClick={() => props.onClose(tab.id)}
            >
              ×
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
