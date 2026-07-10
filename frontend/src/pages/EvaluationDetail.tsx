import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { apiDownload, apiGet, apiSend } from '../lib/api'
import type { EvalDetail } from '../types'
import { STATUS_LABEL } from '../types'

const SCORE_OPTIONS = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]

export default function EvaluationDetail() {
  const { me } = useAuth()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [ev, setEv] = useState<EvalDetail | null>(null)
  const [scores, setScores] = useState<Record<string, number>>({})
  const [comments, setComments] = useState<Record<number, string>>({})
  const [attendance, setAttendance] = useState<number | ''>('')
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = () =>
    apiGet<EvalDetail>(`/api/evaluations/${id}`).then((d) => {
      setEv(d)
      setScores(Object.fromEntries(d.items.filter((i) => i.score != null).map((i) => [i.id, Number(i.score)])))
      setComments(Object.fromEntries(d.comments.map((c) => [c.category_order, c.comment ?? ''])))
      setAttendance(d.attendance?.attendance_score ?? '')
    }).catch((e) => setError(String(e)))

  useEffect(() => { load() }, [id])

  const editable = ev?.status === 'draft' || ev?.status === 'returned'

  // Mirrors backend authorization exactly (services/evaluations.py, incl. the
  // _same_employee guard: two unset employee_ids must never compare equal —
  // a freshly invited profile with no employee_id linked must not appear to
  // "match" a subject whose manager_id also happens to be unset).
  //   score/submit          -> _require_evaluator: super_admin or the assigned evaluator (NOT hr_admin)
  //   approve/return (submitted)     -> the subject's manager (emp_manager_id) or super_admin
  //   approve/return (dept_approved) -> role 'md' or super_admin
  //   finalize/return (md_approved)  -> role 'hr_admin' or super_admin
  const sameEmployee = (a: string | null | undefined, b: string | null | undefined) => !!a && !!b && a === b
  const isEvaluator = !!me && !!ev && (me.is_super_admin || sameEmployee(me.employee_id, ev.evaluator_id))
  const isDeptApprover = !!me && !!ev && (me.is_super_admin || sameEmployee(me.employee_id, ev.emp_manager_id))
  const isMd = !!me && (me.is_super_admin || me.roles.includes('md'))
  const isHr = !!me && (me.is_super_admin || me.roles.includes('hr_admin'))
  const canEditNow = editable && isEvaluator

  const categories = useMemo(() => {
    const map = new Map<number, { name: string; items: EvalDetail['items'] }>()
    ev?.items.forEach((i) => {
      if (!map.has(i.category_order)) map.set(i.category_order, { name: i.category_name, items: [] })
      map.get(i.category_order)!.items.push(i)
    })
    return [...map.entries()].sort((a, b) => a[0] - b[0])
  }, [ev])

  const act = async (fn: () => Promise<unknown>, okMsg: string) => {
    setBusy(true); setError(null); setMsg(null)
    try { await fn(); await load(); setMsg(okMsg) }
    catch (e) { setError(String(e)) }
    finally { setBusy(false) }
  }

  const save = () =>
    act(() => apiSend('PUT', `/api/evaluations/${id}/scores`, {
      scores: Object.entries(scores).map(([evaluation_item_id, score]) => ({ evaluation_item_id, score })),
      comments: Object.entries(comments).map(([category_order, comment]) => ({ category_order: Number(category_order), comment })),
      attendance: attendance === '' ? null : { attendance_score: Number(attendance) },
    }), 'บันทึกคะแนนแล้ว')

  const transition = (path: string, okMsg: string) =>
    act(() => apiSend('POST', `/api/evaluations/${id}/${path}`, {}), okMsg)

  if (!ev) {
    return (
      <div className="min-h-screen bg-slate-50 p-6">
        {error ? <p className="text-red-600">{error}</p> : <p className="text-slate-500">กำลังโหลด…</p>}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b px-6 py-3 flex justify-between items-center">
        <h1 className="font-semibold text-slate-800">รายละเอียดใบประเมิน</h1>
        <div className="flex items-center gap-4">
          <button
            onClick={() => apiDownload(`/api/evaluations/${id}/pdf`, `evaluation-${id}.pdf`).catch((e) => setError(String(e)))}
            className="text-sm text-blue-600 hover:text-blue-800">ดาวน์โหลด PDF</button>
          <button onClick={() => navigate('/evaluations')} className="text-sm text-slate-600 hover:text-slate-900">← กลับ</button>
        </div>
      </header>

      <main className="p-6 space-y-5 max-w-3xl mx-auto">
        {error && <p className="text-red-600 text-sm">{error}</p>}
        {msg && <p className="text-green-700 text-sm">{msg}</p>}

        <section className="bg-white rounded-xl shadow p-5 flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <div><span className="text-slate-500">สถานะ:</span> <b>{STATUS_LABEL[ev.status] ?? ev.status}</b></div>
          <div><span className="text-slate-500">ชนิด:</span> {ev.kind === 'annual' ? 'ประจำปี' : 'ทดลองงาน'}</div>
          <div><span className="text-slate-500">คะแนน:</span> {ev.eval_score ?? '—'}{ev.eval_max ? ` / ${ev.eval_max}` : ''}</div>
          <div><span className="text-slate-500">รวม+มาลา:</span> {ev.total_score ?? '—'}</div>
          <div><span className="text-slate-500">คิดเป็น:</span> {ev.percentage != null ? `${ev.percentage}%` : '—'}</div>
        </section>

        {categories.map(([order, cat]) => (
          <section key={order} className="bg-white rounded-xl shadow p-5">
            <h3 className="font-medium text-slate-700 mb-2">{order}. {cat.name}</h3>
            <div className="space-y-1.5">
              {cat.items.map((it) => (
                <div key={it.id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-slate-600">{it.item_name}</span>
                  <select
                    className="border rounded px-2 py-1 w-20 disabled:bg-slate-100"
                    disabled={!canEditNow}
                    value={scores[it.id] ?? ''}
                    onChange={(e) => setScores((s) => ({ ...s, [it.id]: Number(e.target.value) }))}
                  >
                    <option value="">—</option>
                    {SCORE_OPTIONS.map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
              ))}
            </div>
            <textarea
              className="mt-3 w-full border rounded px-2 py-1 text-sm disabled:bg-slate-100"
              placeholder="ข้อคิดเห็นเพิ่มเติม"
              rows={2}
              disabled={!canEditNow}
              value={comments[order] ?? ''}
              onChange={(e) => setComments((c) => ({ ...c, [order]: e.target.value }))}
            />
          </section>
        ))}

        <section className="bg-white rounded-xl shadow p-5 text-sm">
          <h3 className="font-medium text-slate-700 mb-2">คะแนนการมา-ลา (เต็ม 40)</h3>
          <input
            type="number" min={0} max={40}
            className="border rounded px-2 py-1 w-28 disabled:bg-slate-100"
            disabled={!canEditNow}
            value={attendance}
            onChange={(e) => setAttendance(e.target.value === '' ? '' : Number(e.target.value))}
          />
        </section>

        <section className="flex flex-wrap gap-2">
          {canEditNow && (
            <>
              <button onClick={save} disabled={busy} className="bg-slate-700 text-white rounded px-4 py-2 text-sm disabled:opacity-50">บันทึกคะแนน</button>
              <button onClick={() => transition('submit', 'ส่งประเมินแล้ว')} disabled={busy} className="bg-blue-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50">ส่งประเมิน</button>
            </>
          )}
          {ev.status === 'submitted' && isDeptApprover && (
            <>
              <button onClick={() => transition('approve', 'อนุมัติแล้ว')} disabled={busy} className="bg-green-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50">อนุมัติ</button>
              <button onClick={() => transition('return', 'ตีกลับแล้ว')} disabled={busy} className="bg-amber-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50">ตีกลับ</button>
            </>
          )}
          {ev.status === 'dept_approved' && isMd && (
            <>
              <button onClick={() => transition('approve', 'อนุมัติแล้ว')} disabled={busy} className="bg-green-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50">อนุมัติ</button>
              <button onClick={() => transition('return', 'ตีกลับแล้ว')} disabled={busy} className="bg-amber-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50">ตีกลับ</button>
            </>
          )}
          {ev.status === 'md_approved' && isHr && (
            <>
              <button onClick={() => transition('finalize', 'ปิดใบแล้ว')} disabled={busy} className="bg-green-700 text-white rounded px-4 py-2 text-sm disabled:opacity-50">สรุป/ปิดใบ (HR)</button>
              <button onClick={() => transition('return', 'ตีกลับแล้ว')} disabled={busy} className="bg-amber-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50">ตีกลับ</button>
            </>
          )}
          {editable && !isEvaluator && (
            <p className="text-sm text-slate-400 self-center">รอหัวหน้างานที่ได้รับมอบหมายให้คะแนน</p>
          )}
          {ev.status === 'submitted' && !isDeptApprover && (
            <p className="text-sm text-slate-400 self-center">รอผจก.แผนกอนุมัติ</p>
          )}
          {ev.status === 'dept_approved' && !isMd && (
            <p className="text-sm text-slate-400 self-center">รอ MD อนุมัติ</p>
          )}
          {ev.status === 'md_approved' && !isHr && (
            <p className="text-sm text-slate-400 self-center">รอฝ่ายบุคคลสรุป/ปิดใบ</p>
          )}
        </section>

        {ev.approvals.length > 0 && (
          <section className="bg-white rounded-xl shadow p-5 text-sm">
            <h3 className="font-medium text-slate-700 mb-2">ประวัติอนุมัติ</h3>
            <ul className="space-y-1 text-slate-600">
              {ev.approvals.map((a, i) => (
                <li key={i}>{a.step} — {a.decision === 'approved' ? 'อนุมัติ' : 'ตีกลับ'}{a.comment ? ` (${a.comment})` : ''}</li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  )
}
