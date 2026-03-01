export type Preset = {
  id: string
  label: string
  filter: {
    q?: string
    incident_type?: string
  }
}

export const PRESETS: Preset[] = [
  { id: 'all', label: 'All', filter: {} },
  { id: 'revolutions', label: 'Revolutions', filter: { incident_type: 'revolution' } },
  { id: 'battles', label: 'Battles', filter: { incident_type: 'battle' } },
  { id: 'disasters', label: 'Disasters', filter: { incident_type: 'disaster' } },
  { id: 'assassinations', label: 'Assassinations', filter: { incident_type: 'assassination' } },
  { id: 'germany', label: 'Germany (text)', filter: { q: 'Berlin' } },
]
