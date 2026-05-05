export type DocModalKind = "readme" | "changelog";

export function resolveDocsPath(kind: DocModalKind, baseUri: string = document.baseURI): string {
  return new URL(`docs/${kind}.html`, baseUri).pathname;
}

export default function DocModal(props: {
  kind: DocModalKind;
  onClose: () => void;
}) {
  const docsUrl = resolveDocsPath(props.kind);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[linear-gradient(160deg,rgba(18,15,29,0.82),rgba(28,24,48,0.74))] p-4 backdrop-blur-[2px]">
      <div className="relative h-[85vh] w-[min(1100px,96vw)] rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/95 p-2 shadow-2xl">
        <button
          type="button"
          onClick={props.onClose}
          className="absolute right-3 top-3 z-10 rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
        >
          close
        </button>
        <iframe
          title={props.kind}
          src={docsUrl}
          className="h-full w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)]"
        />
      </div>
    </div>
  );
}
