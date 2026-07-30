import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { apiDownload, apiGet, apiSend } from '../lib/api'
import type { Employee, EvalDetail, EvalListItem, Template } from '../types'
import { ACK_DECISION_LABEL, STATUS_LABEL } from '../types'

export default function Evaluations() {
  const { me } = useAuth()
  const navigate = useNavigate()
  const [evals, setEvals] = useState<EvalListItem[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [employeeId, setEmployeeId] = useState('')
  const [templateId, setTemplateId] = useState('')
  const [kind, setKind] = useState('annual')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [exportStatus, setExportStatus] = useState('')
  const [exportFrom, setExportFrom] = useState('')
  const [exportTo, setExportTo] = useState('')
  const [exporting, setExporting] = useState(false)

  const load = () => apiGet<EvalListItem[]>('/api/evaluations').then(setEvals).catch((e) => setError(String(e)))

  useEffect(() => {
    load()
    apiGet<Employee[]>('/api/employees').then(setEmployees).catch(() => undefined)
    apiGet<Template[]>('/api/templates').then(setTemplates).catch(() => undefined)
  }, [])

  const create = async () => {
    if (!employeeId || !templateId) return
    setBusy(true)
    setError(null)
    try {
      const ev = await apiSend<EvalDetail>('POST', '/api/evaluations', {
        employee_id: employeeId,
        template_id: templateId,
        kind,
      })
      navigate(`/evaluations/${ev.id}`)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  const empName = (id: string) => employees.find((e) => e.id === id)?.full_name ?? id.slice(0, 8)

  const exportExcel = async () => {
    setExporting(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (exportStatus) params.set('status', exportStatus)
      if (exportFrom) params.set('date_from', exportFrom)
      if (exportTo) params.set('date_to', exportTo)
      const qs = params.toString()
      await apiDownload(`/api/evaluations/export${qs ? `?${qs}` : ''}`, 'evaluations-export.xlsx')
    } catch (e) {
      setError(String(e))
    } finally {
      setExporting(false)
    }
  }

  // Mirrors the backend's create() check exactly (services/evaluations.py):
  // super_admin, hr_admin, or the direct supervisor of at least one employee.
  const isHrOrAbove = !!me && (me.is_super_admin || me.roles.includes('hr_admin'))
  const creatableEmployees = isHrOrAbove
    ? employees
    : me?.employee_id
      ? employees.filter((e) => e.supervisor_id === me.employee_id)
      : []
  const canCreate = isHrOrAbove || creatableEmployees.length > 0

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b px-6 py-3 flex justify-between items-center">
        <h1 className="font-semibold text-slate-800">ใบประเมินผล</h1>
        <nav className="flex items-center gap-4">
          <Link to="/evaluations/compare" className="text-sm text-blue-600 hover:text-blue-800">เปรียบเทียบผลประเมิน</Link>
          <Link to="/inbox" className="text-sm text-blue-600 hover:text-blue-800">งานที่รอฉัน</Link>
          <Link to="/" className="text-sm text-slate-600 hover:text-slate-900">← แดชบอร์ด</Link>
        </nav>
      </header>

      <main className="p-6 space-y-6 max-w-4xl mx-auto">
        {error && <p className="text-red-600 text-sm">{error}</p>}

        {canCreate && (
          <section className="bg-white rounded-xl shadow p-5">
            <h2 className="font-medium mb-3 text-slate-700">สร้างใบประเมิน (หัวหน้างาน)</h2>
            <div className="flex flex-wrap gap-2 items-end">
              <label className="text-sm">
                <span className="block text-slate-500">พนักงาน</span>
                <select className="border rounded px-2 py-1 min-w-48" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
                  <option value="">— เลือก —</option>
                  {creatableEmployees.map((e) => (
                    <option key={e.id} value={e.id}>{e.emp_code} · {e.full_name}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                <span className="block text-slate-500">แบบฟอร์ม</span>
                <select className="border rounded px-2 py-1 min-w-48" value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
                  <option value="">— เลือก —</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                <span className="block text-slate-500">ชนิด</span>
                <select className="border rounded px-2 py-1" value={kind} onChange={(e) => setKind(e.target.value)}>
                  <option value="annual">ประจำปี</option>
                  <option value="probation">ทดลองงาน</option>
                </select>
              </label>
              <button onClick={create} disabled={busy || !employeeId || !templateId}
                className="bg-slate-800 text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
                สร้าง
              </button>
            </div>
          </section>
        )}

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-3 text-slate-700">ส่งออกคะแนนเป็น Excel</h2>
          <div className="flex flex-wrap gap-2 items-end">
            <label className="text-sm">
              <span className="block text-slate-500">สถานะ</span>
              <select className="border rounded px-2 py-1" value={exportStatus} onChange={(e) => setExportStatus(e.target.value)}>
                <option value="">ทั้งหมด</option>
                {Object.entries(STATUS_LABEL).map(([k, label]) => (
                  <option key={k} value={k}>{label}</option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="block text-slate-500">ตั้งแต่วันที่</span>
              <input type="date" className="border rounded px-2 py-1" value={exportFrom} onChange={(e) => setExportFrom(e.target.value)} />
            </label>
            <label className="text-sm">
              <span className="block text-slate-500">ถึงวันที่</span>
              <input type="date" className="border rounded px-2 py-1" value={exportTo} onChange={(e) => setExportTo(e.target.value)} />
            </label>
            <button onClick={exportExcel} disabled={exporting}
              className="bg-blue-600 text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
              {exporting ? 'กำลังส่งออก…' : 'ดาวน์โหลด Excel'}
            </button>
          </div>
        </section>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-3 text-slate-700">รายการใบประเมิน</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-1">พนักงาน</th><th>ชนิด</th><th>สถานะ</th><th>คะแนน</th><th>%</th><th>การรับทราบ</th>
              </tr>
            </thead>
            <tbody>
              {evals.map((ev) => (
                <tr key={ev.id} className="border-b last:border-0 hover:bg-slate-50 cursor-pointer"
                    onClick={() => navigate(`/evaluations/${ev.id}`)}>
                  <td className="py-1.5">{empName(ev.employee_id)}</td>
                  <td>{ev.kind === 'annual' ? 'ประจำปี' : 'ทดลองงาน'}</td>
                  <td>{STATUS_LABEL[ev.status] ?? ev.status}</td>
                  <td>{ev.eval_score ?? '—'}{ev.eval_max ? ` / ${ev.eval_max}` : ''}</td>
                  <td>{ev.percentage != null ? `${ev.percentage}%` : '—'}</td>
                  <td>
                    {ev.acknowledgement_decision
                      ? <span className="text-green-700">{ACK_DECISION_LABEL[ev.acknowledgement_decision] ?? ev.acknowledgement_decision}</span>
                      : ['dept_approved', 'md_approved', 'finalized'].includes(ev.status)
                        ? <span className="text-amber-600">รอรับทราบ</span>
                        : <span className="text-slate-300">—</span>}
                  </td>
                </tr>
              ))}
              {evals.length === 0 && (
                <tr><td colSpan={6} className="py-3 text-slate-400">ยังไม่มีใบประเมิน</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  )
}
