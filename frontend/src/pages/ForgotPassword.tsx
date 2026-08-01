import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { supabase } from '../lib/supabase'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  // Same message whether or not the account exists — never let this page
  // reveal which emails are registered.
  const [sent, setSent] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    setBusy(false)
    setSent(true)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm bg-white p-8 rounded-xl shadow space-y-4">
        <h1 className="text-xl font-semibold text-slate-800">ลืมรหัสผ่าน</h1>
        {sent ? (
          <>
            <p className="text-sm text-slate-600">
              ถ้ามีบัญชีนี้อยู่ในระบบ เราได้ส่งลิงก์สำหรับตั้งรหัสผ่านใหม่ไปที่อีเมลนี้แล้ว
              กรุณาตรวจสอบกล่องจดหมาย (และโฟลเดอร์สแปม) ลิงก์จะหมดอายุใน 30 นาที
            </p>
            <Link to="/login" className="block text-center text-sm text-blue-600 hover:text-blue-800">← กลับไปเข้าสู่ระบบ</Link>
          </>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <p className="text-sm text-slate-600">กรอกอีเมลที่ใช้เข้าสู่ระบบ เราจะส่งลิงก์สำหรับตั้งรหัสผ่านใหม่ให้</p>
            <input
              className="w-full border rounded px-3 py-2"
              type="email"
              placeholder="อีเมล"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <button disabled={busy} className="w-full bg-slate-800 text-white rounded py-2 disabled:opacity-50">
              {busy ? '...' : 'ส่งลิงก์รีเซ็ตรหัสผ่าน'}
            </button>
            <Link to="/login" className="block text-center text-sm text-blue-600 hover:text-blue-800">← กลับไปเข้าสู่ระบบ</Link>
          </form>
        )}
      </div>
    </div>
  )
}
