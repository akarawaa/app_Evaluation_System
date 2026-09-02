import type { ReactNode } from 'react'

export function EmptyState({ icon, title, hint }: { icon?: ReactNode; title: string; hint?: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-line bg-surface/60 p-10 text-center">
      {icon && <div className="mb-2 text-3xl">{icon}</div>}
      <p className="font-medium text-ink">{title}</p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  )
}
