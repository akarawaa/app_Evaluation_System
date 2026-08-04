import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import AppHeader from '../components/AppHeader'
import { apiGet, apiSend } from '../lib/api'
import type { TenantDetail as TenantDetailType } from '../types'
import { INVITE_ROLES, ROLE_LABEL } from '../types'

const emptyInvite = { email: '', password: '', role: 'manager' }

export default function TenantDetail() {
  const { id } = useParams<{ id: string }>()
  const [tenant, setTenant] = useState<TenantDetailType | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [invite, setInvite] = useState(emptyInvite)

  const load = () => apiGet<TenantDetailType>(`/api/admin/tenants/${id}`).then(setTenant).catch((e) => setError(String(e)))

  useEffect(() => { load() }, [id])

  const toggleStatus = async () => {
    if (!tenant) return
    setBusy(true); setError(null); setMsg(null)
    try {
      const next = tenant.status === 'active' ? 'suspended' : 'active'
      await apiSend('PATCH', `/api/admin/tenants/${id}/status`, { status: next })
      await load()
      setMsg(next === 'suspended' ? 'ระงับการใช้งานบริษัทนี้แล้ว — ผู้ใช้ทุกคนจะเข้าระบบไม่ได้จนกว่าจะเปิดใช้งานอีกครั้ง' : 'เปิดใช้งานอีกครั้งแล้ว')
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  const sendInvite = async () => {
    if (!invite.email.trim() || invite.password.length < 8) return
    setBusy(true); setError(null); setMsg(null)
    try {
      await apiSend('POST', `/api/admin/tenants/${id}/users`, {
        email: invite.email.trim(), password: invite.password, role: invite.role,
      })
      setInvite(emptyInvite)
      await load()
      setMsg('เชิญผู้ใช้ใหม่แล้ว')
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  if (!tenant) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        {error ? <p className="text-red-600">{error}</p> : <p className="text-slate-500">กำลังโหลด…</p>}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader title={tenant.name} />

      <main className="p-6 space-y-6 max-w-3xl mx-auto">
        {error && <p className="text-red-600 text-sm">{error}</p>}
        {msg && <p className="text-green-700 text-sm">{msg}</p>}

        <section className="bg-white rounded-xl shadow p-5 flex items-center justify-between">
          <div className="text-sm space-y-1">
            <div><span className="text-slate-500">slug:</span> {tenant.slug}</div>
            <div>
              <span className="text-slate-500">สถานะ:</span>{' '}
              <span className={`text-xs px-2 py-0.5 rounded-full ${tenant.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                {tenant.status === 'active' ? 'ใช้งานอยู่' : 'ระงับการใช้งาน'}
              </span>
            </div>
          </div>
          <button onClick={toggleStatus} disabled={busy}
            className={`text-sm rounded px-4 py-1.5 text-white disabled:opacity-50 ${tenant.status === 'active' ? 'bg-red-600' : 'bg-green-600'}`}>
            {tenant.status === 'active' ? 'ระงับการใช้งาน' : 'เปิดใช้งานอีกครั้ง'}
          </button>
        </section>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-3 text-slate-700">เชิญผู้ใช้เข้าระบบ</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <label>
              <span className="block text-slate-500 mb-0.5">อีเมล</span>
              <input type="email" className="border rounded px-2 py-1 w-full" value={invite.email}
                onChange={(e) => setInvite((f) => ({ ...f, email: e.target.value }))} />
            </label>
            <label>
              <span className="block text-slate-500 mb-0.5">รหัสผ่านเริ่มต้น (≥ 8 ตัว)</span>
              <input type="text" className="border rounded px-2 py-1 w-full" value={invite.password}
                onChange={(e) => setInvite((f) => ({ ...f, password: e.target.value }))} />
            </label>
            <label>
              <span className="block text-slate-500 mb-0.5">บทบาท</span>
              <select className="border rounded px-2 py-1 w-full" value={invite.role}
                onChange={(e) => setInvite((f) => ({ ...f, role: e.target.value }))}>
                {INVITE_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
              </select>
            </label>
          </div>
          <button onClick={sendInvite} disabled={busy || !invite.email.trim() || invite.password.length < 8}
            className="mt-4 bg-slate-800 text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
            เชิญเข้าระบบ
          </button>
        </section>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-3 text-slate-700">ผู้ใช้ในบริษัทนี้</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-1 pr-2">ชื่อที่แสดง</th><th>บทบาท</th>
              </tr>
            </thead>
            <tbody>
              {tenant.users.map((u) => (
                <tr key={u.id} className="border-b last:border-0">
                  <td className="py-1.5 pr-2">{u.display_name ?? '—'}</td>
                  <td>{u.roles.map((r) => ROLE_LABEL[r] ?? r).join(', ') || '—'}</td>
                </tr>
              ))}
              {tenant.users.length === 0 && (
                <tr><td colSpan={2} className="py-3 text-slate-400">ยังไม่มีผู้ใช้</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  )
}
