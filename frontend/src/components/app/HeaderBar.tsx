import SearchBar from "../SearchBar";
import type { ReactNode } from "react";

export type HeaderBarProps = {
  searchValue: string;
  onSearchChange: (v: string) => void;
  onSearchEnter: () => void;
  onSearchClear: () => void;

  leftCollapsed: boolean;
  rightCollapsed: boolean;
  onToggleLeft: () => void;
  onToggleRight: () => void;

  onOpenReadme: () => void;
  onOpenChangelog: () => void;
  intentControls?: ReactNode;
};

export default function HeaderBar(props: HeaderBarProps) {
  return (
    <div className="sticky top-0 z-30 -mx-3 -mt-3 mb-3 border-b border-[color:var(--border)] bg-[color:var(--surface)]/90 p-3 backdrop-blur">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-[260px] flex-1">
          <SearchBar
            value={props.searchValue}
            onChange={props.onSearchChange}
            onEnter={props.onSearchEnter}
            onClear={props.onSearchClear}
          />
        </div>

        <div className="ml-auto flex items-center gap-2">
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
            onClick={props.onOpenReadme}
            className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
          >
            README
          </button>
          <button
            type="button"
            onClick={props.onOpenChangelog}
            className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
          >
            CHANGELOG
          </button>
          {props.intentControls}
          <button
            type="button"
            onClick={props.onToggleLeft}
            className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
          >
            {props.leftCollapsed ? "open filters" : "hide filters"}
          </button>
          <button
            type="button"
            onClick={props.onToggleRight}
            className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface)] px-2 py-1 text-xs"
          >
            {props.rightCollapsed ? "open details" : "hide details"}
          </button>
        </div>
      </div>
    </div>
  );
}
