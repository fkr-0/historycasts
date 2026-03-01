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
          defaultSize={22}
          minSize={15}
          maxSize={38}
          className="overflow-auto border-r border-[color:var(--border)] bg-[color:var(--surface)]/92 p-3"
          style={{ transition: "flex-grow 220ms ease, flex-basis 220ms ease" }}
        >
          {props.left}
        </Panel>

        <Separator className="w-1 bg-[color:var(--border)] transition-colors hover:bg-[color:var(--accent)]" />

        <Panel defaultSize={53} minSize={34} className="overflow-hidden p-3 md:p-4">
          {props.center}
        </Panel>

        <Separator className="w-1 bg-[color:var(--border)] transition-colors hover:bg-[color:var(--accent)]" />

        <Panel
          defaultSize={25}
          minSize={16}
          maxSize={40}
          className="overflow-hidden border-l border-[color:var(--border)] bg-[color:var(--surface)]/92 p-4"
          style={{ transition: "flex-grow 220ms ease, flex-basis 220ms ease" }}
        >
          {props.right}
        </Panel>
      </Group>
    </div>
  );
}
