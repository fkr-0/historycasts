// components/HeaderButtons.tsx
import React from "react";

interface Props {
  leftCollapsed: boolean;
  setLeftCollapsed: (v: boolean) => void;
  rightCollapsed: boolean;
  setRightCollapsed: (v: boolean) => void;
  setDocModal: (v: "readme" | "changelog" | null) => void;
}

export default function HeaderButtons({
  leftCollapsed,
  setLeftCollapsed,
  rightCollapsed,
  setRightCollapsed,
  setDocModal,
}: Props) {
  return (
    <div className="absolute right-3 top-3 z-20 flex items-center gap-2">
      <a
        href="https://github.com/example/historycasts"
        target="_blank"
        rel="noreferrer"
        className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
      >
        GH
      </a>
      <a
        href="https://fkr.dev/"
        target="_blank"
        rel="noreferrer"
        className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
      >
        FKR
      </a>
      <button
        type="button"
        onClick={() => setDocModal("readme")}
        className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
      >
        README
      </button>
      <button
        type="button"
        onClick={() => setDocModal("changelog")}
        className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
      >
        CHANGELOG
      </button>
      <button
        type="button"
        onClick={() => setLeftCollapsed((v) => !v)}
        className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
      >
        {leftCollapsed ? "open filters" : "hide filters"}
      </button>
      <button
        type="button"
        onClick={() => setRightCollapsed((v) => !v)}
        className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
      >
        {rightCollapsed ? "open details" : "hide details"}
      </button>
    </div>
  );
}
