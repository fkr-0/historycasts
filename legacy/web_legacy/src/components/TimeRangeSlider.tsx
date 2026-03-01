import React, { useMemo } from 'react'
import Slider from 'rc-slider'

const DAY_MS = 24 * 3600 * 1000

function fmt(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10)
}

export default function TimeRangeSlider(props: {
  min: number
  max: number
  value: [number, number]
  onChange: (v: [number, number]) => void
}) {
  const marks = useMemo(() => {
    const out: Record<number, string> = {}
    out[props.min] = fmt(props.min)
    out[props.max] = fmt(props.max)
    return out
  }, [props.min, props.max])

  return (
    <div style={{ padding: '10px 8px 0 8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#444' }}>
        <span>{fmt(props.value[0])}</span>
        <span>{fmt(props.value[1])}</span>
      </div>
      <Slider
        range
        min={props.min}
        max={props.max}
        step={DAY_MS}
        value={props.value}
        onChange={(v) => {
          const arr = v as number[]
          props.onChange([arr[0], arr[1]])
        }}
        marks={marks}
        allowCross={false}
      />
    </div>
  )
}
