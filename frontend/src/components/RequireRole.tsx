import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

/** Gate a route to specific roles, mirroring the backend's require_roles()
 * semantics (super_admin always passes). Renders a clear "no access" state
 * instead of a page full of 403s from every API call underneath it. */
export default function RequireRole({ anyOf, children }: { anyOf: string[]; children: ReactNode }) {
  const { me, meLoading, meError, refreshMe } = useAuth()

  if (meLoading) return <div className="p-8 text-muted">กำลังโหลด…</div>

  // me is null either because loading it failed (network/cold-start -- not a
  // real permissions answer) or because the user genuinely has no role here.
  // Only the latter is "no permission".
  if (me === null && meError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas p-6">
        <div className="text-center space-y-2">
          <p className="text-muted">เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ ลองใหม่อีกครั้ง</p>
          <p className="text-faint text-xs">{meError}</p>
          <button onClick={() => refreshMe()} className="text-primary hover:text-primary-hover text-sm">
            ลองใหม่
          </button>
        </div>
      </div>
    )
  }

  const allowed = !!me && (me.is_super_admin || anyOf.some((r) => me.roles.includes(r)))
  if (!allowed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas p-6">
        <div className="text-center space-y-2">
          <p className="text-muted">คุณไม่มีสิทธิ์เข้าถึงหน้านี้</p>
          <Link to="/" className="text-primary hover:text-primary-hover text-sm">← กลับแดชบอร์ด</Link>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
