import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import AppHeader from '../components/AppHeader'
import { apiGet, apiSend } from '../lib/api'
import type { TenantDetail as TenantDetailType } from '../types'
import { INVITE_ROLES, ROLE_LABEL } from '../types'

const emptyInvite = { email: '', password: '', role: 'manager' }
const emptyGrant = { email: '', role: 'hr_admin' }

export default function TenantDetail() {
  const { id } = useParams<{ id: string }>()
  const [tenant, setTenant] = useState<TenantDetailType | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [invite, setInvite] = useState(emptyInvite)
  const [grant, setGrant] = useState(emptyGrant)

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

  const toggleUserStatus = async (u: { id: string; active: boolean }) => {
    setBusy(true); setError(null); setMsg(null)
    try {
      await apiSend('PATCH', `/api/users/${u.id}/status?company_id=${id}`, { active: !u.active })
      await load()
      setMsg(u.active ? 'ปิดใช้งานบัญชีแล้ว' : 'เปิดใช้งานบัญชีแล้ว')
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  const sendGrant = async () => {
    if (!grant.email.trim()) return
    setBusy(true); setError(null); setMsg(null)
    try {
      await apiSend('POST', `/api/admin/tenants/${id}/users/grant`, {
        email: grant.email.trim(), role: grant.role,
      })
      setGrant(emptyGrant)
      await load()
      setMsg('ให้สิทธิ์ผู้ใช้เดิมเข้าบริษัทนี้แล้ว — เขาจะเห็นตัวเลือกสลับบริษัทในเมนูด้านบนหลัง login ใหม่')
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  if (!tenant) {
    return (
      <div className="min-h-screen bg-canvas p-6">
        {error ? <p className="text-danger">{error}</p> : <p className="text-muted">กำลังโหลด…</p>}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader title={tenant.name} />

      <main className="p-6 space-y-6 max-w-3xl mx-auto">
        {error && <p className="text-danger text-sm">{error}</p>}
        {msg && <p className="text-green-700 text-sm">{msg}</p>}

        <section className="bg-surface rounded-card shadow p-5 flex items-center justify-between">
          <div className="text-sm space-y-1">
            <div><span className="text-muted">slug:</span> {tenant.slug}</div>
            <div>
              <span className="text-muted">สถานะ:</span>{' '}
              <span className={`text-xs px-2 py-0.5 rounded-full ${tenant.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-danger-soft text-danger'}`}>
                {tenant.status === 'active' ? 'ใช้งานอยู่' : 'ระงับการใช้งาน'}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to={`/people?company_id=${tenant.id}&company_name=${encodeURIComponent(tenant.name)}`}
              className="text-sm text-primary hover:text-primary-hover font-medium"
            >
              จัดการพนักงาน & สาขาของบริษัทนี้ →
            </Link>
            <button onClick={toggleStatus} disabled={busy}
              className={`text-sm rounded px-4 py-1.5 text-white disabled:opacity-50 ${tenant.status === 'active' ? 'bg-danger' : 'bg-green-600'}`}>
              {tenant.status === 'active' ? 'ระงับการใช้งาน' : 'เปิดใช้งานอีกครั้ง'}
            </button>
          </div>
        </section>

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-3 text-ink">เชิญผู้ใช้เข้าระบบ</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <label>
              <span className="block text-muted mb-0.5">อีเมล</span>
              <input type="email" className="border rounded px-2 py-1 w-full" value={invite.email}
                onChange={(e) => setInvite((f) => ({ ...f, email: e.target.value }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">รหัสผ่านเริ่มต้น (≥ 8 ตัว)</span>
              <input type="text" className="border rounded px-2 py-1 w-full" value={invite.password}
                onChange={(e) => setInvite((f) => ({ ...f, password: e.target.value }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">บทบาท</span>
              <select className="border rounded px-2 py-1 w-full" value={invite.role}
                onChange={(e) => setInvite((f) => ({ ...f, role: e.target.value }))}>
                {INVITE_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
              </select>
            </label>
          </div>
          <button onClick={sendInvite} disabled={busy || !invite.email.trim() || invite.password.length < 8}
            className="mt-4 bg-primary text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
            เชิญเข้าระบบ
          </button>
        </section>

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-1 text-ink">ให้สิทธิ์ผู้ใช้เดิมเข้าบริษัทนี้</h2>
          <p className="text-xs text-muted mb-3">
            สำหรับคนที่มีบัญชี login อยู่แล้ว (เช่น ดูแลหลายบริษัท) — ไม่สร้างบัญชีใหม่ แค่เพิ่มสิทธิ์ในบริษัทนี้
          </p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <label>
              <span className="block text-muted mb-0.5">อีเมลบัญชีที่มีอยู่แล้ว</span>
              <input type="email" className="border rounded px-2 py-1 w-full" value={grant.email}
                onChange={(e) => setGrant((f) => ({ ...f, email: e.target.value }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">บทบาทในบริษัทนี้</span>
              <select className="border rounded px-2 py-1 w-full" value={grant.role}
                onChange={(e) => setGrant((f) => ({ ...f, role: e.target.value }))}>
                {INVITE_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
              </select>
            </label>
          </div>
          <button onClick={sendGrant} disabled={busy || !grant.email.trim()}
            className="mt-4 bg-primary text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
            ให้สิทธิ์เข้าบริษัทนี้
          </button>
        </section>

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-3 text-ink">ผู้ใช้ในบริษัทนี้</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b">
                <th className="py-1 pr-2">ชื่อที่แสดง</th><th>บทบาท</th><th>สถานะ</th><th></th>
              </tr>
            </thead>
            <tbody>
              {tenant.users.map((u) => (
                <tr key={u.id} className="border-b last:border-0">
                  <td className="py-1.5 pr-2">{u.display_name ?? '—'}</td>
                  <td>{u.roles.map((r) => ROLE_LABEL[r] ?? r).join(', ') || '—'}</td>
                  <td>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${u.active ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-muted'}`}>
                      {u.active ? 'ใช้งานอยู่' : 'ปิดใช้งาน'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap">
                    <button onClick={() => toggleUserStatus(u)} disabled={busy} className="text-muted text-xs font-medium disabled:opacity-50">
                      {u.active ? 'ปิดใช้งาน' : 'เปิดใช้งาน'}
                    </button>
                  </td>
                </tr>
              ))}
              {tenant.users.length === 0 && (
                <tr><td colSpan={4} className="py-3 text-faint">ยังไม่มีผู้ใช้</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  )
}
