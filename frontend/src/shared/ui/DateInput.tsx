import { useRef } from 'react'

import { cx } from './cx'

// A native <input type="date"> renders its text (and the segments while
// focused) in the BROWSER's own locale format -- not the page `lang`, not
// CSS, nothing the app controls. On an en-US browser that's mm/dd/yyyy.
// Thai users reading mm/dd/yyyy misread it as dd/mm/yyyy (or vice versa) --
// a real ambiguity risk in a leave / attendance / appraisal system.
//
// Fix: keep the native input (so we still get the browser's calendar picker
// + keyboard support), visually hide it, and paint OUR OWN dd/mm/yyyy text
// on top. Same value/onChange contract every caller uses: plain "yyyy-mm-dd"
// strings, matching the API everywhere in the suite. Clicking the visible
// field calls the native input's showPicker() so the calendar still opens --
// a calendar GRID isn't ambiguous, only the raw numeric text was.
function formatDdMmYyyy(iso: string): string {
  if (!iso) return ''
  const [y, m, d] = iso.split('-')
  return y && m && d ? `${d}/${m}/${y}` : ''
}

export function DateInput({
  value,
  onChange,
  min,
  max,
  required,
  disabled,
  className,
}: {
  value: string
  onChange: (value: string) => void
  min?: string
  max?: string
  required?: boolean
  disabled?: boolean
  className?: string
}) {
  const nativeRef = useRef<HTMLInputElement>(null)

  const openPicker = () => {
    if (disabled) return
    const el = nativeRef.current
    if (!el) return
    // showPicker() needs a user gesture and isn't in every browser
    // (older Firefox); fall back to focus(), which still opens it there.
    if (typeof el.showPicker === 'function') {
      try {
        el.showPicker()
        return
      } catch {
        /* fall through */
      }
    }
    el.focus()
  }

  return (
    <div className="relative">
      <input
        type="text"
        readOnly
        disabled={disabled}
        value={formatDdMmYyyy(value)}
        placeholder="วว/ดด/ปปปป"
        onClick={openPicker}
        onFocus={openPicker}
        className={cx(
          className ?? 'w-full rounded border border-line px-3 py-2 bg-surface',
          !disabled && 'cursor-pointer',
        )}
      />
      <input
        ref={nativeRef}
        type="date"
        value={value}
        min={min}
        max={max}
        required={required}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        tabIndex={-1}
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-0"
      />
    </div>
  )
}
