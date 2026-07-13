import { useEffect, useRef } from "react"
import { Group, type ImperativePanelHandle, Panel, Separator } from "react-resizable-panels"

export default function AppFrame(props: {
  left: React.ReactNode
  center: React.ReactNode
  right: React.ReactNode
  leftCollapsed?: boolean
  rightCollapsed?: boolean
}) {
  const leftPanelRef = useRef<ImperativePanelHandle>(null)
  const rightPanelRef = useRef<ImperativePanelHandle>(null)

  useEffect(() => {
    const panel = leftPanelRef.current
    if (!panel) return
    if (props.leftCollapsed) panel.collapse()
    else panel.expand()
  }, [props.leftCollapsed])

  useEffect(() => {
    const panel = rightPanelRef.current
    if (!panel) return
    if (props.rightCollapsed) panel.collapse()
    else panel.expand()
  }, [props.rightCollapsed])

  return (
    <div className="h-screen">
      <Group direction="horizontal">
        <Panel
          ref={leftPanelRef}
          defaultSize={24}
          minSize={16}
          maxSize={42}
          collapsible
          collapsedSize={4}
          className="overflow-auto border-r border-[color:var(--border)] bg-[color:var(--surface)]/92 p-3"
        >
          {props.left}
        </Panel>

        <Separator className="w-1 cursor-ew-resize bg-[color:var(--border)] transition-colors hover:bg-[color:var(--accent)]" />

        <Panel defaultSize={48} minSize={28} className="overflow-hidden p-3 md:p-4">
          {props.center}
        </Panel>

        <Separator className="w-1 cursor-ew-resize bg-[color:var(--border)] transition-colors hover:bg-[color:var(--accent)]" />

        <Panel
          ref={rightPanelRef}
          defaultSize={28}
          minSize={16}
          maxSize={45}
          collapsible
          collapsedSize={4}
          className="overflow-hidden border-l border-[color:var(--border)] bg-[color:var(--surface)]/92 p-4"
        >
          {props.right}
        </Panel>
      </Group>
    </div>
  )
}
