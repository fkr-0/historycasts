import React from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import SavedFiltersPanel from './SavedFiltersPanel'
import type { EpisodeFilter } from '../types'

function mkFilter(overrides: Partial<EpisodeFilter> = {}): EpisodeFilter {
  return {
    podcast_id: '',
    incident_type: '',
    q: '',
    date_start: null,
    date_end: null,
    bbox: null,
    ...overrides,
  }
}

describe('SavedFiltersPanel', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('saves current filter to localStorage and can apply it', async () => {
    const user = userEvent.setup()
    const onApply = vi.fn()

    render(
      <SavedFiltersPanel
        current={mkFilter({ podcast_id: 'drig', incident_type: 'battle', q: 'verdun', date_start: '2023-01-01', date_end: '2023-12-31' })}
        onApply={onApply}
      />,
    )

    await user.type(screen.getByLabelText('Name'), 'my investigation')
    await user.click(screen.getByRole('button', { name: 'Save current filter' }))

    const raw = localStorage.getItem('podcast-atlas.savedFilters.v1')
    expect(raw).toBeTruthy()
    const arr = JSON.parse(raw!)
    expect(Array.isArray(arr)).toBe(true)
    expect(arr.length).toBe(1)
    expect(arr[0].name).toBe('my investigation')
    expect(arr[0].filter.podcast_id).toBe('drig')

    // Apply
    await user.click(screen.getByRole('button', { name: 'Apply' }))
    expect(onApply).toHaveBeenCalledTimes(1)
    expect(onApply.mock.calls[0][0]).toMatchObject({ podcast_id: 'drig', incident_type: 'battle', q: 'verdun' })
  })

  it('exports and imports a v1 payload', async () => {
    const user = userEvent.setup()
    const onApply = vi.fn()

    render(<SavedFiltersPanel current={mkFilter()} onApply={onApply} />)

    await user.type(screen.getByLabelText('Name'), 'first')
    await user.click(screen.getByRole('button', { name: 'Save current filter' }))

    await user.click(screen.getByRole('button', { name: 'Export' }))
    const exportBox = screen
      .getAllByRole('textbox')
      .find((el) => (el as HTMLElement).tagName === 'TEXTAREA') as HTMLTextAreaElement
    const payload = JSON.parse(exportBox.value)
    expect(payload.version).toBe(1)
    expect(payload.saved.length).toBe(1)

    // Import the same payload again (should remain stable)
    await user.click(screen.getByRole('button', { name: 'Import' }))
    const importAreas = screen
      .getAllByRole('textbox')
      .filter((el) => (el as HTMLElement).tagName === 'TEXTAREA')
    const importBox = importAreas[importAreas.length - 1] as HTMLTextAreaElement
    fireEvent.change(importBox, { target: { value: JSON.stringify(payload) } })
    await user.click(screen.getByRole('button', { name: 'Import now' }))

    // Still one item (merged by id)
    const raw = localStorage.getItem('podcast-atlas.savedFilters.v1')
    const arr = JSON.parse(raw!)
    expect(arr.length).toBe(1)
  })
})
