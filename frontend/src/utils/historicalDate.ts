const ISO_YMD_RE = /^([+-]?\d{1,9})-(\d{2})-(\d{2})(?:$|T)/

export function parseIsoYear(iso?: string): number | null {
  if (!iso) return null
  const m = ISO_YMD_RE.exec(iso.trim())
  if (!m) return null
  const year = Number.parseInt(m[1], 10)
  return Number.isFinite(year) ? year : null
}

export function parseIsoDateUtc(iso?: string): Date | null {
  if (!iso) return null
  const m = ISO_YMD_RE.exec(iso.trim())
  if (!m) return null

  const year = Number.parseInt(m[1], 10)
  const month = Number.parseInt(m[2], 10)
  const day = Number.parseInt(m[3], 10)
  if (!Number.isFinite(year) || month < 1 || month > 12 || day < 1 || day > 31) return null

  const d = new Date(Date.UTC(0, month - 1, day))
  d.setUTCFullYear(year, month - 1, day)
  if (d.getUTCMonth() !== month - 1 || d.getUTCDate() !== day) return null
  return d
}
