import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { Button, Card } from '../shared/ui'

export default function Login() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Landed here because AuthContext's inactivity timer signed the user out
  // (30 min, no activity) -- say so, otherwise it looks like a random logout.
  const [autoLoggedOut, setAutoLoggedOut] = useState(false)
  useEffect(() => {
    try {
      if (sessionStorage.getItem('auto_logged_out')) {
        setAutoLoggedOut(true)
        sessionStorage.removeItem('auto_logged_out')
      }
    } catch {
      /* private mode -- just skip the message */
    }
  }, [])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    const { error } = await signIn(email, password)
    setBusy(false)
    if (error) setError(error)
    else navigate('/')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas font-sans p-4">
      <Card className="w-full max-w-sm">
        <form onSubmit={submit} className="space-y-4">
          <h1 className="text-xl font-semibold text-ink">E-Appraisal — เข้าสู่ระบบ</h1>
          {autoLoggedOut && (
            <p className="rounded bg-amber-50 px-3 py-2 text-sm text-amber-700">
              ออกจากระบบอัตโนมัติเนื่องจากไม่มีการใช้งานเกิน 30 นาที (เพื่อความปลอดภัยของข้อมูล)
            </p>
          )}
          {error && <p className="text-sm text-danger">{error}</p>}
          <input
            className="w-full rounded border border-line px-3 py-2"
            type="email"
            placeholder="อีเมล"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="w-full rounded border border-line px-3 py-2"
            type="password"
            placeholder="รหัสผ่าน"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? '...' : 'เข้าสู่ระบบ'}
          </Button>
          <p className="text-center text-sm">
            <Link to="/forgot-password" className="text-primary hover:text-primary-hover">
              ลืมรหัสผ่าน?
            </Link>
          </p>
        </form>
      </Card>
    </div>
  )
}
