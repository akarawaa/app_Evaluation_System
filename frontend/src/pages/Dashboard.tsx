import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import CurrentUserBadge from '../components/CurrentUserBadge'
import { useAuth } from '../context/AuthContext'
import { apiGet } from '../lib/api'

type Employee = {
  id: string
  emp_code: string
  full_name: string
  level: string
  status: string
}

export default function Dashboard() {
  const { me, signOut } = useAuth()
  const [employees, setEmployees] = useState<Employee[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiGet<Employee[]>('/api/employees').then(setEmployees).catch((e) => setError(String(e)))
  }, [])

  const isHrAdmin = me?.roles.includes('hr_admin') || me?.is_super_admin

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b px-6 py-3 flex justify-between items-center">
        <h1 className="font-semibold text-slate-800">E-Appraisal</h1>
        <nav className="flex items-center gap-4">
          <Link to="/inbox" className="text-sm text-blue-600 hover:text-blue-800">งานที่รอฉัน</Link>
          <Link to="/evaluations" className="text-sm text-blue-600 hover:text-blue-800">ใบประเมินผล</Link>
          {isHrAdmin && (
            <Link to="/people" className="text-sm text-blue-600 hover:text-blue-800">พนักงาน &amp; สาขา</Link>
          )}
          {me?.is_super_admin && (
            <Link to="/tenants" className="text-sm text-blue-600 hover:text-blue-800">จัดการบริษัท</Link>
          )}
          <CurrentUserBadge />
          <button onClick={signOut} className="text-sm text-slate-600 hover:text-slate-900">
            ออกจากระบบ
          </button>
        </nav>
      </header>

      <main className="p-6 space-y-6 max-w-3xl mx-auto">
        {error && <p className="text-red-600">{error}</p>}

        {me && (
          <section className="bg-white rounded-xl shadow p-5">
            <h2 className="font-medium mb-2 text-slate-700">ผู้ใช้ปัจจุบัน</h2>
            <dl className="text-sm text-slate-600 space-y-1">
              <div>อีเมล: {me.email}</div>
              <div>
                company_id: <code>{me.company_id ?? '—'}</code>
              </div>
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
                <th>ระดับ</th>
                <th>สถานะ</th>
              </tr>
            </thead>
            <tbody>
              {employees.map((e) => (
                <tr key={e.id} className="border-b last:border-0">
                  <td className="py-1">{e.emp_code}</td>
                  <td>{e.full_name}</td>
                  <td>{e.level}</td>
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
