import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { supabase } from '../lib/supabase'
import { Button, Card } from '../shared/ui'

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
    <div className="flex min-h-screen items-center justify-center bg-canvas font-sans p-4">
      <Card className="w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold text-ink">ลืมรหัสผ่าน</h1>
        {sent ? (
          <>
            <p className="text-sm text-muted">
              ถ้ามีบัญชีนี้อยู่ในระบบ เราได้ส่งลิงก์สำหรับตั้งรหัสผ่านใหม่ไปที่อีเมลนี้แล้ว
              กรุณาตรวจสอบกล่องจดหมาย (และโฟลเดอร์สแปม) ลิงก์จะหมดอายุใน 30 นาที
            </p>
            <Link to="/login" className="block text-center text-sm text-primary hover:text-primary-hover">
              ← กลับไปเข้าสู่ระบบ
            </Link>
          </>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <p className="text-sm text-muted">กรอกอีเมลที่ใช้เข้าสู่ระบบ เราจะส่งลิงก์สำหรับตั้งรหัสผ่านใหม่ให้</p>
            <input
              className="w-full rounded border border-line px-3 py-2"
              type="email"
              placeholder="อีเมล"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? '...' : 'ส่งลิงก์รีเซ็ตรหัสผ่าน'}
            </Button>
            <Link to="/login" className="block text-center text-sm text-primary hover:text-primary-hover">
              ← กลับไปเข้าสู่ระบบ
            </Link>
          </form>
        )}
      </Card>
    </div>
  )
}
