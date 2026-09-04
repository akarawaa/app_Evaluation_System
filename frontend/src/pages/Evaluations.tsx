import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import AppHeader from '../components/AppHeader'
import { useAuth } from '../context/AuthContext'
import { apiDownload, apiGet, apiSend } from '../lib/api'
import { DateInput } from '../shared/ui'
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
  const [checkpoint, setCheckpoint] = useState('')
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
    if (kind === 'probation' && !checkpoint) return
    setBusy(true)
    setError(null)
    try {
      const ev = await apiSend<EvalDetail>('POST', '/api/evaluations', {
        employee_id: employeeId,
        template_id: templateId,
        kind,
        // probation requires a checkpoint (DB constraint eval_kind_checkpoint);
        // annual must not send one.
        probation_checkpoint: kind === 'probation' ? checkpoint : undefined,
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
    <div className="min-h-screen bg-canvas">
      <AppHeader title="ใบประเมินผล" />

      <main className="p-6 space-y-6 max-w-4xl mx-auto">
        {error && <p className="text-danger text-sm">{error}</p>}

        {canCreate && (
          <section className="bg-surface rounded-card shadow p-5">
            <h2 className="font-medium text-ink">สร้างใบประเมิน</h2>
            <p className="text-xs text-muted mb-3">
              {isHrOrAbove ? 'สร้างแทนพนักงานคนใดก็ได้ในบริษัท — ผู้ให้คะแนนจริงคือหัวหน้างานที่ผูกไว้กับพนักงานคนนั้น' : 'สร้างสำหรับลูกน้องของคุณ'}
            </p>
            <div className="flex flex-wrap gap-2 items-end">
              <label className="text-sm">
                <span className="block text-muted">พนักงาน</span>
                <select className="border rounded px-2 py-1 min-w-48" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
                  <option value="">— เลือก —</option>
                  {creatableEmployees.map((e) => (
                    <option key={e.id} value={e.id}>{e.emp_code} · {e.full_name}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                <span className="block text-muted">แบบฟอร์ม</span>
                <select className="border rounded px-2 py-1 min-w-48" value={templateId} onChange={(e) => setTemplateId(e.target.value)}>
                  <option value="">— เลือก —</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                <span className="block text-muted">ชนิด</span>
                <select className="border rounded px-2 py-1" value={kind}
                  onChange={(e) => { setKind(e.target.value); if (e.target.value === 'annual') setCheckpoint('') }}>
                  <option value="annual">ประจำปี</option>
                  <option value="probation">ทดลองงาน</option>
                </select>
              </label>
              {kind === 'probation' && (
                <label className="text-sm">
                  <span className="block text-muted">ช่วงประเมิน (วัน)</span>
                  <select className="border rounded px-2 py-1" value={checkpoint} onChange={(e) => setCheckpoint(e.target.value)}>
                    <option value="">— เลือก —</option>
                    <option value="30">30 วัน</option>
                    <option value="60">60 วัน</option>
                    <option value="90">90 วัน</option>
                    <option value="119">119 วัน</option>
                  </select>
                </label>
              )}
              <button onClick={create} disabled={busy || !employeeId || !templateId || (kind === 'probation' && !checkpoint)}
                className="bg-primary text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
                สร้าง
              </button>
            </div>
          </section>
        )}

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-3 text-ink">ส่งออกคะแนนเป็น Excel</h2>
          <div className="flex flex-wrap gap-2 items-end">
            <label className="text-sm">
              <span className="block text-muted">สถานะ</span>
              <select className="border rounded px-2 py-1" value={exportStatus} onChange={(e) => setExportStatus(e.target.value)}>
                <option value="">ทั้งหมด</option>
                {Object.entries(STATUS_LABEL).map(([k, label]) => (
                  <option key={k} value={k}>{label}</option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="block text-muted">ตั้งแต่วันที่</span>
              <DateInput className="border rounded px-2 py-1 w-32" value={exportFrom} onChange={setExportFrom} />
            </label>
            <label className="text-sm">
              <span className="block text-muted">ถึงวันที่</span>
              <DateInput className="border rounded px-2 py-1 w-32" value={exportTo} onChange={setExportTo} min={exportFrom} />
            </label>
            <button onClick={exportExcel} disabled={exporting}
              className="bg-primary text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
              {exporting ? 'กำลังส่งออก…' : 'ดาวน์โหลด Excel'}
            </button>
          </div>
        </section>

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-3 text-ink">รายการใบประเมิน</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b">
                <th className="py-1">พนักงาน</th><th>ชนิด</th><th>สถานะ</th><th>คะแนน</th><th>%</th><th>การรับทราบ</th>
              </tr>
            </thead>
            <tbody>
              {evals.map((ev) => (
                <tr key={ev.id} className="border-b last:border-0 hover:bg-canvas cursor-pointer"
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
                        : <span className="text-faint">—</span>}
                  </td>
                </tr>
              ))}
              {evals.length === 0 && (
                <tr><td colSpan={6} className="py-3 text-faint">ยังไม่มีใบประเมิน</td></tr>
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  )
}
