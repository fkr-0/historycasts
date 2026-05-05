export interface TimelineBarBlockProps {
  x: number
  y: number
  width: number
  height: number
  fill: string
  stroke?: string
  strokeWidth?: number
  rx?: number
  opacity?: number
  title?: string
}

export default function TimelineBarBlock(props: TimelineBarBlockProps): JSX.Element {
  const {
    x,
    y,
    width,
    height,
    fill,
    stroke = "rgba(255,255,255,0.2)",
    strokeWidth = 0.5,
    rx = 1.5,
    opacity = 1,
    title,
  } = props
  return (
    <rect
      x={x}
      y={y}
      width={Math.max(0, width)}
      height={Math.max(0, height)}
      fill={fill}
      stroke={stroke}
      strokeWidth={strokeWidth}
      rx={rx}
      opacity={opacity}
    >
      {title ? <title>{title}</title> : null}
    </rect>
  )
}
