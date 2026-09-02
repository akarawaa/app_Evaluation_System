import type { ReactNode } from 'react'

import { cx } from './cx'

/**
 * A titled panel: an <h2> over a bordered card. The dashboard idiom across
 * every HR Suite app is a vertical stack of these ("วันลาคงเหลือ", "คำขอลาของฉัน",
 * ...), so the card chrome + heading spacing live here instead of being
 * re-typed per section.
 *
 * `actions` renders to the right of the title (a link, a small button).
 */
export function Section({
  title,
  actions,
  children,
  className,
}: {
  title: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cx('rounded-card border border-line bg-surface p-6 shadow-card', className)}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-medium text-ink">{title}</h2>
        {actions && <div className="flex items-center gap-3 text-sm">{actions}</div>}
      </div>
      {children}
    </section>
  )
}
