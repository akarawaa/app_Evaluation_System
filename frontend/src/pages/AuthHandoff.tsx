import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { supabase } from '../lib/supabase'

// SSO handoff landing (platform-core/docs/PORTAL.md C3). hr-portal redirects
// here with `#token_hash=...` in the URL fragment after verifying the user.
// We exchange it for a real session on THIS origin, then continue.
// Outside ProtectedRoute in App.tsx -- its job is to create the session.
// Self-contained (raw fetch) so it's identical across all sub-apps.
const API = (import.meta.env.VITE_API_BASE_URL as string) ?? ''

export default function AuthHandoff() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const ranOnce = useRef(false)

  useEffect(() => {
    if (ranOnce.current) return
    ranOnce.current = true

    const params = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const tokenHash = params.get('token_hash')
    window.history.replaceState(null, '', window.location.pathname)

    if (!tokenHash) {
      setError('ลิงก์ไม่ถูกต้อง (ไม่พบ token)')
      return
    }

    ;(async () => {
      try {
        const res = await fetch(`${API}/api/auth/exchange`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token_hash: tokenHash }),
        })
        if (!res.ok) throw new Error(`exchange failed (${res.status})`)
        const s = (await res.json()) as { access_token: string; refresh_token: string }
        const { error: setErr } = await supabase.auth.setSession({
          access_token: s.access_token,
          refresh_token: s.refresh_token,
        })
        if (setErr) {
          setError(setErr.message)
          return
        }
        navigate('/', { replace: true })
      } catch (e) {
        setError(e instanceof Error ? e.message : 'เข้าสู่ระบบไม่สำเร็จ')
      }
    })()
  }, [navigate])

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas font-sans p-6 text-center">
      {error ? (
        <div>
          <p className="mb-3 text-danger">{error}</p>
          <a href="/login" className="text-sm text-primary underline">
            ไปหน้าเข้าสู่ระบบ
          </a>
        </div>
      ) : (
        <p className="text-muted">กำลังเข้าสู่ระบบ…</p>
      )}
    </div>
  )
}
