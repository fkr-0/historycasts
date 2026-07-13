import type { KeyboardEvent } from "react"
import { colorForCluster } from "../../visual/clusterVisuals"

export interface ClusterQualityPoint {
  id: number
  label: string
  nMembers: number
  cohesion: number
  distinctiveness: number
  spread: number
  historicalYear?: number
}

const WIDTH = 720
const HEIGHT = 280
const MARGIN = { top: 20, right: 24, bottom: 48, left: 56 }
const COHESION_REFERENCE = 0.2
const SPREAD_REFERENCE = 250

export default function ClusterQualityScatter(props: {
  points: ClusterQualityPoint[]
  onSelectCluster: (clusterId: number) => void
}) {
  if (props.points.length === 0) return null

  const plotWidth = WIDTH - MARGIN.left - MARGIN.right
  const plotHeight = HEIGHT - MARGIN.top - MARGIN.bottom
  const maxSpread = Math.max(1, ...props.points.map(point => point.spread))
  const maxMembers = Math.max(1, ...props.points.map(point => point.nMembers))
  const spreadTicks = Array.from(new Set([0, 10, 50, 100, 250, 500, Math.ceil(maxSpread)]))
    .filter(value => value <= maxSpread)
    .sort((left, right) => left - right)

  const x = (spread: number) =>
    MARGIN.left + (Math.log1p(Math.max(0, spread)) / Math.log1p(maxSpread)) * plotWidth
  const y = (cohesion: number) => MARGIN.top + (1 - Math.max(0, Math.min(1, cohesion))) * plotHeight
  const radius = (members: number) => 5 + Math.sqrt(members / maxMembers) * 10
  const opacity = (distinctiveness: number) =>
    0.35 + Math.max(0, Math.min(1, distinctiveness)) * 0.6
  const activate = (event: KeyboardEvent<SVGCircleElement>, clusterId: number) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      props.onSelectCluster(clusterId)
    }
  }

  return (
    <figure className="m-0 rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
      <figcaption className="mb-1 text-xs text-[color:var(--muted)]">
        Better-defined clusters sit toward the upper left. Circle size represents episode count and
        opacity represents distinctiveness; select a circle to inspect it.
      </figcaption>
      <svg
        aria-label="Cluster quality comparison"
        className="block h-auto w-full"
        role="img"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      >
        {[0, 0.5, 1].map(value => {
          const rowY = y(value)
          return (
            <g key={value}>
              <line
                stroke="currentColor"
                strokeOpacity="0.14"
                x1={MARGIN.left}
                x2={WIDTH - MARGIN.right}
                y1={rowY}
                y2={rowY}
              />
              <text
                fill="currentColor"
                fontSize="11"
                textAnchor="end"
                x={MARGIN.left - 8}
                y={rowY + 4}
              >
                {value.toFixed(1)}
              </text>
            </g>
          )
        })}
        {spreadTicks.map(value => {
          const columnX = x(value)
          return (
            <g key={value}>
              <line
                stroke="currentColor"
                strokeOpacity="0.1"
                x1={columnX}
                x2={columnX}
                y1={MARGIN.top}
                y2={HEIGHT - MARGIN.bottom}
              />
              <text
                fill="currentColor"
                fontSize="10"
                textAnchor="middle"
                x={columnX}
                y={HEIGHT - MARGIN.bottom + 16}
              >
                {value}
              </text>
            </g>
          )
        })}
        <line
          aria-label="Cohesion reference"
          stroke="currentColor"
          strokeDasharray="5 4"
          strokeOpacity="0.42"
          x1={MARGIN.left}
          x2={WIDTH - MARGIN.right}
          y1={y(COHESION_REFERENCE)}
          y2={y(COHESION_REFERENCE)}
        />
        {maxSpread >= SPREAD_REFERENCE && (
          <line
            aria-label="Historical spread reference"
            stroke="currentColor"
            strokeDasharray="5 4"
            strokeOpacity="0.42"
            x1={x(SPREAD_REFERENCE)}
            x2={x(SPREAD_REFERENCE)}
            y1={MARGIN.top}
            y2={HEIGHT - MARGIN.bottom}
          />
        )}
        <line
          stroke="currentColor"
          strokeOpacity="0.5"
          x1={MARGIN.left}
          x2={MARGIN.left}
          y1={MARGIN.top}
          y2={HEIGHT - MARGIN.bottom}
        />
        <line
          stroke="currentColor"
          strokeOpacity="0.5"
          x1={MARGIN.left}
          x2={WIDTH - MARGIN.right}
          y1={HEIGHT - MARGIN.bottom}
          y2={HEIGHT - MARGIN.bottom}
        />
        <text
          fill="currentColor"
          fontSize="12"
          textAnchor="middle"
          x={MARGIN.left + plotWidth / 2}
          y={HEIGHT - 12}
        >
          Historical spread in years (log scale)
        </text>
        <text
          fill="currentColor"
          fontSize="12"
          textAnchor="middle"
          transform={`rotate(-90 16 ${MARGIN.top + plotHeight / 2})`}
          x={16}
          y={MARGIN.top + plotHeight / 2}
        >
          Semantic cohesion
        </text>

        {props.points.map(point => {
          const cx = x(point.spread)
          const cy = y(point.cohesion)
          return (
            <g key={point.id}>
              {/* biome-ignore lint/a11y/useSemanticElements: SVG has no native button element; keyboard and accessible naming are provided. */}
              <circle
                aria-label={`Inspect cluster #${point.id} in comparison chart`}
                cx={cx}
                cy={cy}
                fill={colorForCluster(point.id)}
                fillOpacity={opacity(point.distinctiveness)}
                onClick={() => props.onSelectCluster(point.id)}
                onKeyDown={event => activate(event, point.id)}
                r={radius(point.nMembers)}
                role="button"
                stroke="currentColor"
                strokeWidth="1.5"
                tabIndex={0}
              >
                <title>
                  {`#${point.id} ${point.label}: ${point.nMembers} episodes, cohesion ${point.cohesion.toFixed(2)}, distinctiveness ${point.distinctiveness.toFixed(2)}, spread ${point.spread} years${point.historicalYear == null ? "" : `, center ${point.historicalYear}`}`}
                </title>
              </circle>
              <text
                fill="currentColor"
                fontSize="10"
                fontWeight="700"
                pointerEvents="none"
                textAnchor="middle"
                x={cx}
                y={cy + 3.5}
              >
                {point.id}
              </text>
            </g>
          )
        })}
      </svg>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[color:var(--muted)]">
        <span>Dashed guides: cohesion 0.20, spread 250 years</span>
        <span>Fainter circles are less distinctive</span>
      </div>
    </figure>
  )
}
