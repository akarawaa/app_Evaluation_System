import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import AppHeader from '../components/AppHeader'
import { useAuth } from '../context/AuthContext'
import { apiGet } from '../lib/api'
import type { InboxItem } from '../types'
import { ACTION_LABEL, LEVEL_LABEL } from '../types'

type Employee = {
  id: string
  emp_code: string
  full_name: string
  level: string
  status: string
}

export default function Dashboard() {
  const { me } = useAuth()
  const [employees, setEmployees] = useState<Employee[]>([])
  const [inbox, setInbox] = useState<InboxItem[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiGet<Employee[]>('/api/employees').then(setEmployees).catch((e) => setError(String(e)))
    // Best-effort: an empty inbox just means no CTA card below, not an error
    // worth surfacing on the landing page.
    apiGet<InboxItem[]>('/api/evaluations/inbox').then(setInbox).catch(() => undefined)
  }, [])

  const isHrAdmin = me?.roles.includes('hr_admin') || me?.is_super_admin

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />

      <main className="p-6 space-y-6 max-w-3xl mx-auto">
        {error && <p className="text-red-600">{error}</p>}

        {inbox.length > 0 && (
          <Link to="/inbox" className="block bg-white rounded-xl shadow border border-blue-200 p-5 hover:border-blue-400 transition-colors">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-medium text-slate-800">งานรอดำเนินการของคุณ</h2>
                  <span className="text-xs font-semibold bg-blue-600 text-white rounded-full px-2 py-0.5">{inbox.length}</span>
                </div>
                <p className="text-sm text-slate-500 mt-1">
                  {inbox.slice(0, 2).map((it) => `${it.full_name} ${ACTION_LABEL[it.action]}`).join(' · ')}
                  {inbox.length > 2 ? ` และอีก ${inbox.length - 2} รายการ` : ''}
                </p>
              </div>
              <span className="text-sm text-blue-600 font-medium whitespace-nowrap">ไปที่งานที่รอฉัน →</span>
            </div>
          </Link>
        )}

        {me && (
          <section className="bg-white rounded-xl shadow p-5">
            <h2 className="font-medium mb-2 text-slate-700">ผู้ใช้ปัจจุบัน</h2>
            <dl className="text-sm text-slate-600 space-y-1">
              <div>อีเมล: {me.email}</div>
              <div>บริษัท: {me.company_name ?? (me.is_super_admin ? 'ทุกบริษัท (super_admin)' : '—')}</div>
              {me.branch_name && <div>สาขา: {me.branch_name}</div>}
              <div>
                roles: {me.roles.join(', ') || '—'}
                {me.is_super_admin ? ' (super_admin)' : ''}
              </div>
            </dl>
          </section>
        )}

        <section className="bg-white rounded-xl shadow p-5">
          <div className="flex justify-between items-center mb-3">
            <h2 className="font-medium text-slate-700">พนักงาน (เห็นเฉพาะ tenant ของคุณ)</h2>
            {isHrAdmin && (
              <Link to="/people" className="text-xs text-blue-600 hover:text-blue-800">จัดการพนักงาน &amp; สาขา →</Link>
            )}
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-1">รหัส</th>
                <th>ชื่อ</th>
                <th>ประเภทแบบประเมิน</th>
                <th>สถานะ</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((e) => (
                <tr key={e.id} className="border-b last:border-0">
                  <td className="py-1">{e.emp_code}</td>
                  <td>{e.full_name}</td>
                  <td>{LEVEL_LABEL[e.level] ?? e.level}</td>
                  <td>{e.status}</td>
                </tr>
              ))}
              {employees.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-3 text-slate-400">
                    ไม่มีข้อมูล
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  )
}
