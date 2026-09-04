import { useEffect, useState } from 'react'

import { cx } from './cx'

// A native <input type="time"> renders as 12h AM/PM on an en-US browser and
// there's no attribute/CSS to force 24h. The suite wants 24h everywhere.
//
// This is a plain text field: the user types the time and it normalises to
// "HH:MM" (24h) on blur / Enter. Accepts "0830", "830", "8:30", "8", "8.30".
// Same value/onChange contract as before (a "HH:MM" string) -- onChange
// fires with the normalised value on commit, and with "" when cleared.
// No native clock wheel; typing a shift time is faster than spinning one.
export function parseTime(raw: string): string | null {
  const s = raw.trim()
  if (!s) return null
  let h: number
  let m: number
  const sep = s.match(/[:.\s]/)
  if (sep) {
    const [hp, mp = '0'] = s.split(/[:.\s]/)
    h = parseInt(hp, 10)
    m = parseInt(mp, 10)
  } else {
    const d = s.replace(/\D/g, '')
    if (!d) return null
    if (d.length <= 2) {
      h = parseInt(d, 10)
      m = 0
    } else {
      h = parseInt(d.slice(0, d.length - 2), 10)
      m = parseInt(d.slice(-2), 10)
    }
  }
  if (Number.isNaN(h) || Number.isNaN(m) || h < 0 || h > 23 || m < 0 || m > 59) return null
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

export function TimeInput({
  value,
  onChange,
  required,
  disabled,
  placeholder,
  className,
}: {
  value: string
  onChange: (value: string) => void
  required?: boolean
  disabled?: boolean
  placeholder?: string
  className?: string
}) {
  const [text, setText] = useState(value)
  useEffect(() => {
    setText(value)
  }, [value])

  const commit = () => {
    const parsed = parseTime(text)
    if (parsed === null) {
      if (!text.trim()) {
        setText('')
        onChange('')
      } else {
        setText(value) // revert to the last good value
      }
      return
    }
    setText(parsed)
    if (parsed !== value) onChange(parsed)
  }

  return (
    <input
      type="text"
      inputMode="numeric"
      maxLength={5}
      value={text}
      required={required}
      disabled={disabled}
      placeholder={placeholder ?? 'ชม:นาที'}
      pattern="([01]?\d|2[0-3]):[0-5]\d"
      onChange={(e) => setText(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          e.preventDefault()
          commit()
        }
      }}
      className={cx(className ?? 'rounded border border-line px-2 py-1.5', 'tabular-nums')}
    />
  )
}
