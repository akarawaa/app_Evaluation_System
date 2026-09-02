import type { ReactNode } from 'react'

import { Button } from './Button'

/**
 * Inline confirm dialog. Use this instead of window.confirm() -- native
 * dialogs are unreliable in LIFF / sandboxed webviews (CONVENTIONS §8.2).
 * Controlled: parent holds `open` and clears it in onConfirm / onCancel.
 */
export function Confirm({
  open,
  title,
  body,
  confirmLabel = 'ยืนยัน',
  cancelLabel = 'ยกเลิก',
  danger = false,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  body?: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-sm rounded-card border border-line bg-surface p-5 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="font-semibold text-ink">{title}</p>
        {body && <div className="mt-2 text-sm text-muted">{body}</div>}
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
