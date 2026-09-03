import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import AppHeader from '../components/AppHeader'
import { apiGet, apiSend } from '../lib/api'
import type { Tenant } from '../types'

const emptyForm = { name: '', slug: '', hr_email: '', hr_password: '' }

export default function Tenants() {
  const navigate = useNavigate()
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState(emptyForm)

  const load = () => apiGet<Tenant[]>('/api/admin/tenants').then(setTenants).catch((e) => setError(String(e)))

  useEffect(() => { load() }, [])

  const create = async () => {
    const { name, slug, hr_email, hr_password } = form
    if (!name.trim() || !slug.trim() || !hr_email.trim() || hr_password.length < 8) return
    setBusy(true); setError(null); setMsg(null)
    try {
      await apiSend('POST', '/api/admin/tenants', {
        name: name.trim(), slug: slug.trim(), hr_email: hr_email.trim(), hr_password,
      })
      setForm(emptyForm)
      await load()
      setMsg('สร้างบริษัทใหม่แล้ว พร้อมโคลนแบบประเมินมาตรฐานและบัญชี HR ผู้ดูแลคนแรก')
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader title="จัดการบริษัท (Tenants)" />

      <main className="p-6 space-y-6 max-w-4xl mx-auto">
        {error && <p className="text-danger text-sm">{error}</p>}
        {msg && <p className="text-green-700 text-sm">{msg}</p>}

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-3 text-ink">สร้างบริษัทใหม่</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <label>
              <span className="block text-muted mb-0.5">ชื่อบริษัท</span>
              <input className="border rounded px-2 py-1 w-full" value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">slug (a-z0-9- เท่านั้น)</span>
              <input className="border rounded px-2 py-1 w-full" value={form.slug}
                onChange={(e) => setForm((f) => ({ ...f, slug: e.target.value.toLowerCase() }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">อีเมล HR ผู้ดูแลคนแรก</span>
              <input type="email" className="border rounded px-2 py-1 w-full" value={form.hr_email}
                onChange={(e) => setForm((f) => ({ ...f, hr_email: e.target.value }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">รหัสผ่านเริ่มต้น (≥ 8 ตัว)</span>
              <input type="text" className="border rounded px-2 py-1 w-full" value={form.hr_password}
                onChange={(e) => setForm((f) => ({ ...f, hr_password: e.target.value }))} />
            </label>
          </div>
          <button onClick={create} disabled={busy}
            className="mt-4 bg-primary text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
            สร้างบริษัท
          </button>
        </section>

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-3 text-ink">รายชื่อบริษัท</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b">
                <th className="py-1 pr-2">ชื่อ</th><th className="pr-2">slug</th>
                <th className="pr-2">พนักงาน</th><th className="pr-2">ผู้ใช้ระบบ</th><th className="pr-2">สถานะ</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id} className="border-b last:border-0 hover:bg-canvas cursor-pointer"
                    onClick={() => navigate(`/tenants/${t.id}`)}>
                  <td className="py-1.5 pr-2">{t.name}</td>
                  <td className="pr-2 text-muted">{t.slug}</td>
                  <td className="pr-2">{t.employee_count}</td>
                  <td className="pr-2">{t.user_count}</td>
                  <td className="pr-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${t.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-danger-soft text-danger'}`}>
                      {t.status === 'active' ? 'ใช้งานอยู่' : 'ระงับการใช้งาน'}
                    </span>
                  </td>
                </tr>
              ))}
              {tenants.length === 0 && (
                <tr><td colSpan={5} className="py-3 text-faint">ยังไม่มีบริษัท</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  )
}
