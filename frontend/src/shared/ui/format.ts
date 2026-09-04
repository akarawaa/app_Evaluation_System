// Suite-wide date/time DISPLAY formatting. Pairs with DateInput / TimeInput
// (which handle the *entry* side).
//
// Two hazards this avoids:
//   1. Locale. `toLocaleDateString()` with no explicit format renders in the
//      viewer's locale -- an en-US browser shows mm/dd/yyyy. We force
//      dd/mm/yyyy + 24h regardless, via en-GB + formatToParts.
//   2. Timezone. The backend returns timestamptz as its UTC ISO string
//      ("2026-08-31T17:00:00+00:00" for a Bangkok midnight). Slicing the
//      first 10 chars shows the WRONG calendar day. Always re-render in
//      Asia/Bangkok. (A pure "yyyy-mm-dd" date has no zone -- reformat it
//      directly, don't run it through Date().)

const BKK = 'Asia/Bangkok'
const PLAIN_DATE = /^(\d{4})-(\d{2})-(\d{2})$/

function bkkParts(d: Date, opts: Intl.DateTimeFormatOptions): Record<string, string> {
  const out: Record<string, string> = {}
  for (const p of new Intl.DateTimeFormat('en-GB', { timeZone: BKK, ...opts }).formatToParts(d)) {
    out[p.type] = p.value
  }
  if (out.hour === '24') out.hour = '00' // some engines emit 24 for midnight with hour12:false
  return out
}

/** "yyyy-mm-dd" or an ISO timestamp -> "dd/mm/yyyy" (Bangkok calendar day). */
export function fmtDate(value: string | null | undefined): string {
  if (!value) return '—'
  const m = PLAIN_DATE.exec(value)
  if (m) return `${m[3]}/${m[2]}/${m[1]}`
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const p = bkkParts(d, { day: '2-digit', month: '2-digit', year: 'numeric' })
  return `${p.day}/${p.month}/${p.year}`
}

/** ISO timestamp -> "dd/mm/yyyy HH:MM" (Bangkok, 24h). */
export function fmtDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const p = bkkParts(d, {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  })
  return `${p.day}/${p.month}/${p.year} ${p.hour}:${p.minute}`
}

/** ISO timestamp -> "HH:MM" (Bangkok, 24h). */
export function fmtTime(value: string | null | undefined): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  const p = bkkParts(d, { hour: '2-digit', minute: '2-digit', hour12: false })
  return `${p.hour}:${p.minute}`
}
