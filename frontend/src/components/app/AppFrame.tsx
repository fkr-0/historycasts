import { Group, Panel, Separator } from "react-resizable-panels";

export default function AppFrame(props: {
  left: React.ReactNode;
  center: React.ReactNode;
  right: React.ReactNode;
}) {
  return (
    <div className="h-screen">
      <Group direction="horizontal">
        <Panel
          defaultSize="22%"
          minSize="12%"
          maxSize="42%"
          className="overflow-auto border-r border-[color:var(--border)] bg-[color:var(--surface)]/92 p-3"
        >
          {props.left}
        </Panel>

        <Separator className="w-1 cursor-ew-resize bg-[color:var(--border)] transition-colors hover:bg-[color:var(--accent)]" />

        <Panel defaultSize="53%" minSize="22%" className="overflow-hidden p-3 md:p-4">
          {props.center}
        </Panel>

        <Separator className="w-1 cursor-ew-resize bg-[color:var(--border)] transition-colors hover:bg-[color:var(--accent)]" />

        <Panel
          defaultSize="25%"
          minSize="12%"
          maxSize="45%"
          className="overflow-hidden border-l border-[color:var(--border)] bg-[color:var(--surface)]/92 p-4"
        >
          {props.right}
        </Panel>
      </Group>
    </div>
  );
}
