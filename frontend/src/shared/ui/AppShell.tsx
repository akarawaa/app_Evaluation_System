import type { ReactNode } from 'react'

/**
 * Standard page frame for every HR Suite app: a shared header (brand + optional
 * nav + optional account widget) over a canvas-coloured main area.
 *
 * Each app supplies its own `nav` (route links) and `account` (user badge /
 * company switcher / logout) -- those differ per app -- but the layout, the
 * mobile wrapping, the colours and the spacing live here, so a header bug is
 * fixed once.
 */
export function AppShell({
  title,
  subtitle,
  nav,
  account,
  children,
  maxWidth = 'max-w-5xl',
}: {
  title: string
  subtitle?: string
  nav?: ReactNode
  account?: ReactNode
  children: ReactNode
  maxWidth?: string
}) {
  return (
    <div className="min-h-screen bg-canvas font-sans text-ink">
      <header className="border-b border-line bg-surface">
        <div
          className={`mx-auto flex ${maxWidth} flex-wrap items-center justify-between gap-x-6 gap-y-3 px-4 py-3`}
        >
          <div className="shrink-0">
            <div className="text-base font-bold text-ink">{title}</div>
            {subtitle && <div className="text-xs text-muted">{subtitle}</div>}
          </div>
          {nav && <nav className="flex flex-wrap items-center gap-4 text-sm">{nav}</nav>}
          {account && <div className="flex flex-wrap items-center gap-3 text-sm">{account}</div>}
        </div>
      </header>
      <main className={`mx-auto ${maxWidth} px-4 py-8`}>{children}</main>
    </div>
  )
}
