import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { apiSend } from '../lib/api'
import { supabase } from '../lib/supabase'

export default function ResetPassword() {
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // Supabase-js reads the recovery token out of the URL and turns it into a
  // real (temporary) session on load — until that lands, updateUser() would
  // fail as "not authenticated", so gate the form on it explicitly.
  const [ready, setReady] = useState(false)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setReady(!!data.session))
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => setReady(!!session))
    return () => sub.subscription.unsubscribe()
  }, [])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password.length < 8) { setError('รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร'); return }
    if (password !== confirm) { setError('รหัสผ่านทั้งสองช่องไม่ตรงกัน'); return }

    setBusy(true)
    const { error: updateError } = await supabase.auth.updateUser({ password })
    if (updateError) {
      setBusy(false)
      setError(updateError.message)
      return
    }
    // Best-effort: log the change + notify the account owner. A failure here
    // must not block the user from reaching the app — the password change
    // itself already succeeded.
    await apiSend('POST', '/api/auth/password-changed').catch(() => undefined)
    setBusy(false)
    navigate('/')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <form onSubmit={submit} className="w-full max-w-sm bg-white p-8 rounded-xl shadow space-y-4">
        <h1 className="text-xl font-semibold text-slate-800">ตั้งรหัสผ่านใหม่</h1>
        {!ready && (
          <p className="text-sm text-amber-600">
            กำลังตรวจสอบลิงก์... ถ้าลิงก์หมดอายุหรือไม่ถูกต้อง กรุณาขอลิงก์ใหม่จากหน้า "ลืมรหัสผ่าน"
          </p>
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <input
          className="w-full border rounded px-3 py-2"
          type="password"
          placeholder="รหัสผ่านใหม่ (อย่างน้อย 8 ตัวอักษร)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={!ready}
          required
        />
        <input
          className="w-full border rounded px-3 py-2"
          type="password"
          placeholder="ยืนยันรหัสผ่านใหม่"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          disabled={!ready}
          required
        />
        <button disabled={busy || !ready} className="w-full bg-slate-800 text-white rounded py-2 disabled:opacity-50">
          {busy ? '...' : 'บันทึกรหัสผ่านใหม่'}
        </button>
      </form>
    </div>
  )
}
