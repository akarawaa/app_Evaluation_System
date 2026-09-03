import { useEffect, useMemo, useState } from 'react'
import AppHeader from '../components/AppHeader'
import { apiGet } from '../lib/api'
import type { CompareResult, Employee, EvalListItem } from '../types'
import { STATUS_LABEL } from '../types'

const MIN_SELECT = 2
const MAX_SELECT = 5

export default function Compare() {
  const [evals, setEvals] = useState<EvalListItem[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [result, setResult] = useState<CompareResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    apiGet<EvalListItem[]>('/api/evaluations').then(setEvals).catch((e) => setError(String(e)))
    apiGet<Employee[]>('/api/employees').then(setEmployees).catch(() => undefined)
  }, [])

  const empName = (id: string) => employees.find((e) => e.id === id)?.full_name ?? id.slice(0, 8)
  const empCode = (id: string) => employees.find((e) => e.id === id)?.emp_code ?? ''

  const toggle = (id: string) => {
    setSelected((s) => {
      if (s.includes(id)) return s.filter((x) => x !== id)
      if (s.length >= MAX_SELECT) return s
      return [...s, id]
    })
  }

  const compare = async () => {
    if (selected.length < MIN_SELECT || selected.length > MAX_SELECT) return
    setBusy(true); setError(null); setResult(null)
    try {
      const params = new URLSearchParams()
      selected.forEach((id) => params.append('ids', id))
      const data = await apiGet<CompareResult>(`/api/evaluations/compare?${params.toString()}`)
      setResult(data)
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  const sortedEvals = useMemo(
    () => [...evals].sort((a, b) => empName(a.employee_id).localeCompare(empName(b.employee_id))),
    [evals, employees],
  )

  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader title="เปรียบเทียบผลประเมิน" />

      <main className="p-6 space-y-6 max-w-5xl mx-auto">
        {error && <p className="text-danger text-sm">{error}</p>}

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-1 text-ink">เลือกใบประเมินที่จะเปรียบเทียบ ({MIN_SELECT}-{MAX_SELECT} ใบ)</h2>
          <p className="text-xs text-muted mb-3">
            เลือกได้ทั้งสองแบบ: <b>เทียบพนักงานหลายคนในรอบเดียวกัน</b> (เลือกคนละ 1 ใบ) หรือ
            {' '}<b>เทียบพนักงานคนเดียวกันข้ามหลายรอบ</b> (เลือกใบของคนเดียวกันหลายใบ) — เห็นเฉพาะใบที่มีสิทธิ์ดูเท่านั้น
          </p>
          <div className="max-h-72 overflow-y-auto border rounded">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-canvas">
                <tr className="text-left text-muted border-b">
                  <th className="py-1 px-2 w-8"></th>
                  <th className="px-2">พนักงาน</th><th>ชนิด</th><th>สถานะ</th><th>%</th>
                </tr>
              </thead>
              <tbody>
                {sortedEvals.map((ev) => (
                  <tr key={ev.id} className="border-b last:border-0 hover:bg-canvas cursor-pointer"
                      onClick={() => toggle(ev.id)}>
                    <td className="py-1.5 px-2">
                      <input type="checkbox" checked={selected.includes(ev.id)}
                        disabled={!selected.includes(ev.id) && selected.length >= MAX_SELECT}
                        onChange={() => toggle(ev.id)} onClick={(e) => e.stopPropagation()} />
                    </td>
                    <td className="px-2">{empCode(ev.employee_id)} · {empName(ev.employee_id)}</td>
                    <td>{ev.kind === 'annual' ? 'ประจำปี' : 'ทดลองงาน'}</td>
                    <td>{STATUS_LABEL[ev.status] ?? ev.status}</td>
                    <td>{ev.percentage != null ? `${ev.percentage}%` : '—'}</td>
                  </tr>
                ))}
                {sortedEvals.length === 0 && (
                  <tr><td colSpan={5} className="py-3 text-center text-faint">ยังไม่มีใบประเมิน</td></tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex items-center gap-3">
            <button onClick={compare} disabled={busy || selected.length < MIN_SELECT || selected.length > MAX_SELECT}
              className="bg-primary text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
              {busy ? 'กำลังเปรียบเทียบ…' : `เปรียบเทียบ (${selected.length} ใบ)`}
            </button>
            <span className="text-xs text-faint">เลือกแล้ว {selected.length}/{MAX_SELECT}</span>
          </div>
        </section>

        {result && (
          <section className="bg-surface rounded-card shadow p-5 overflow-x-auto">
            <h2 className="font-medium mb-3 text-ink">ผลเปรียบเทียบ</h2>
            <table className="text-sm border-collapse min-w-full">
              <thead>
                <tr>
                  <th className="text-left text-muted border-b py-1 pr-3 sticky left-0 bg-surface">หัวข้อ</th>
                  {result.columns.map((c) => (
                    <th key={c.evaluation_id} className="text-left text-ink border-b py-1 px-3 min-w-40">
                      <div className="font-medium">{c.emp_code} · {c.full_name}</div>
                      <div className="text-xs text-faint font-normal">
                        {c.kind === 'annual' ? 'ประจำปี' : 'ทดลองงาน'} · {STATUS_LABEL[c.status] ?? c.status} · {c.created_at}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="bg-canvas font-medium">
                  <td className="py-1.5 pr-3 sticky left-0 bg-canvas">คะแนนประเมิน</td>
                  {result.columns.map((c) => (
                    <td key={c.evaluation_id} className="px-3">{c.eval_score ?? '—'} / {c.eval_max ?? '—'}</td>
                  ))}
                </tr>
                <tr className="bg-canvas font-medium">
                  <td className="py-1.5 pr-3 sticky left-0 bg-canvas">คะแนนการมา-ลา</td>
                  {result.columns.map((c) => (
                    <td key={c.evaluation_id} className="px-3">{c.attendance_score ?? '—'} / 40</td>
                  ))}
                </tr>
                <tr className="bg-canvas font-medium border-b-2">
                  <td className="py-1.5 pr-3 sticky left-0 bg-canvas">รวม / ร้อยละ</td>
                  {result.columns.map((c) => (
                    <td key={c.evaluation_id} className="px-3">
                      {c.total_score ?? '—'} ({c.percentage != null ? `${c.percentage}%` : '—'})
                    </td>
                  ))}
                </tr>
                {result.rows.map((row, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-1 pr-3 sticky left-0 bg-surface">
                      <div className="text-ink">{row.item_name}</div>
                      <div className="text-xs text-faint">{row.category_name}</div>
                    </td>
                    {result.columns.map((c) => (
                      <td key={c.evaluation_id} className="px-3">
                        {row.scores[c.evaluation_id] ?? '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>
    </div>
  )
}
