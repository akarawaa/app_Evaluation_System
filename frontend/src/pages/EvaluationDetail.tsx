import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import CurrentUserBadge from '../components/CurrentUserBadge'
import { useAuth } from '../context/AuthContext'
import { apiDownload, apiGet, apiSend, apiSendForm } from '../lib/api'
import type { EvalDetail } from '../types'
import { ACK_DECISION_LABEL, STATUS_LABEL } from '../types'

const SCORE_OPTIONS = [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]

export default function EvaluationDetail() {
  const { me } = useAuth()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [ev, setEv] = useState<EvalDetail | null>(null)
  const [scores, setScores] = useState<Record<string, number>>({})
  const [comments, setComments] = useState<Record<number, string>>({})
  const [att, setAtt] = useState({ sick_days: 0, personal_days: 0, late_count: 0, late_minutes: 0, absent_days: 0 })
  const [attOverride, setAttOverride] = useState<number | ''>('')
  const [ackForm, setAckForm] = useState({ decision: 'acknowledged', comment: '', witness_name: '', signed_at: '' })
  const [ackFile, setAckFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = () =>
    apiGet<EvalDetail>(`/api/evaluations/${id}`).then((d) => {
      setEv(d)
      setScores(Object.fromEntries(d.items.filter((i) => i.score != null).map((i) => [i.id, Number(i.score)])))
      setComments(Object.fromEntries(d.comments.map((c) => [c.category_order, c.comment ?? ''])))
      if (d.attendance) {
        const { sick_days, personal_days, late_count, late_minutes, absent_days } = d.attendance
        setAtt({ sick_days, personal_days, late_count, late_minutes, absent_days })
        setAttOverride(d.attendance.attendance_score_overridden ? d.attendance.attendance_score ?? '' : '')
      }
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
  // GM/MD are interchangeable at the top approval stage.
  const isMd = !!me && (me.is_super_admin || me.roles.includes('md') || me.roles.includes('gm'))
  const isHr = !!me && (me.is_super_admin || me.roles.includes('hr_admin'))
  // Mirrors services/acknowledgement._require_can_record: whoever sat with the
  // employee (evaluator / dept manager) plus HR. Deliberately not GM/MD — they
  // approve the very next step.
  const canRecordAck = isHr || isEvaluator || isDeptApprover
  // The employee signs between the dept manager's approval and GM/MD's, so the
  // section appears from dept_approved onward (and stays visible afterwards).
  const showAckSection = ['dept_approved', 'md_approved', 'finalized'].includes(ev?.status ?? '')
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
    }), 'บันทึกคะแนนแล้ว')

  const saveAttendance = () =>
    act(() => apiSend('PUT', `/api/evaluations/${id}/attendance`, {
      ...att,
      attendance_score: attOverride === '' ? null : Number(attOverride),
      clear_override: attOverride === '',
    }), 'บันทึกข้อมูลการมา-ลาแล้ว')

  const transition = (path: string, okMsg: string) =>
    act(() => apiSend('POST', `/api/evaluations/${id}/${path}`, {}), okMsg)

  const saveAcknowledgement = () =>
    act(async () => {
      await apiSendForm(`/api/evaluations/${id}/acknowledge-paper`, {
        decision: ackForm.decision,
        comment: ackForm.comment || undefined,
        witness_name: ackForm.witness_name || undefined,
        signed_at: ackForm.signed_at || undefined,
      }, ackFile)
      setAckFile(null)
    }, 'บันทึกการรับทราบแล้ว')

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
          <CurrentUserBadge />
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
            <div className="space-y-3">
              {cat.items.map((it) => {
                const anchors = [it.desc_5, it.desc_4, it.desc_3, it.desc_2, it.desc_1] // level 5..1
                const hasAnchors = anchors.some((a) => a)
                const sel = scores[it.id]
                return (
                  <div key={it.id} className="text-sm">
                    <div className="flex items-center justify-between gap-3">
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
                    {hasAnchors && (
                      <details className="mt-1 group">
                        <summary className="text-xs text-blue-600 cursor-pointer select-none list-none">
                          เกณฑ์การให้คะแนน (BARS) ▾
                        </summary>
                        <ul className="mt-1 space-y-0.5 pl-1">
                          {anchors.map((a, i) => {
                            const level = 5 - i
                            const active = sel != null && (Math.floor(sel) === level || Math.ceil(sel) === level)
                            return (
                              <li key={level} className={`flex gap-2 text-xs rounded px-1 py-0.5 ${active ? 'bg-blue-50 text-blue-800' : 'text-slate-500'}`}>
                                <span className="font-medium tabular-nums">{level}</span>
                                <span>{a ?? '—'}</span>
                              </li>
                            )
                          })}
                        </ul>
                      </details>
                    )}
                  </div>
                )
              })}
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
          <p className="text-slate-600">
            คะแนน: <b>{ev.attendance?.attendance_score ?? '—'}</b> / 40
            {ev.attendance?.attendance_score_overridden && (
              <span className="ml-2 text-xs text-amber-600">(ปรับโดย HR)</span>
            )}
          </p>
          {ev.attendance && (
            <p className="text-xs text-slate-400 mt-1">
              ลาป่วย {ev.attendance.sick_days} วัน · ลากิจ {ev.attendance.personal_days} วัน ·
              {' '}สาย {ev.attendance.late_count} ครั้ง ({ev.attendance.late_minutes} นาที) ·
              {' '}ขาดงาน {ev.attendance.absent_days} วัน
            </p>
          )}
          <p className="text-xs text-slate-400 mt-1">ข้อมูลนี้กรอกโดยฝ่ายบุคคล หัวหน้างานดูได้อย่างเดียว</p>

          {isHr && ev.status !== 'finalized' && (
            <div className="mt-4 border-t pt-3 space-y-2">
              <p className="text-xs font-medium text-slate-500">แก้ไขข้อมูลการมา-ลา (ฝ่ายบุคคล)</p>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                <label className="text-xs text-slate-500">ลาป่วย (วัน)
                  <input type="number" min={0} className="border rounded px-2 py-1 w-full mt-0.5"
                    value={att.sick_days} onChange={(e) => setAtt((a) => ({ ...a, sick_days: Number(e.target.value) }))} />
                </label>
                <label className="text-xs text-slate-500">ลากิจ (วัน)
                  <input type="number" min={0} className="border rounded px-2 py-1 w-full mt-0.5"
                    value={att.personal_days} onChange={(e) => setAtt((a) => ({ ...a, personal_days: Number(e.target.value) }))} />
                </label>
                <label className="text-xs text-slate-500">สาย (ครั้ง)
                  <input type="number" min={0} className="border rounded px-2 py-1 w-full mt-0.5"
                    value={att.late_count} onChange={(e) => setAtt((a) => ({ ...a, late_count: Number(e.target.value) }))} />
                </label>
                <label className="text-xs text-slate-500">สาย (นาทีรวม)
                  <input type="number" min={0} className="border rounded px-2 py-1 w-full mt-0.5"
                    value={att.late_minutes} onChange={(e) => setAtt((a) => ({ ...a, late_minutes: Number(e.target.value) }))} />
                </label>
                <label className="text-xs text-slate-500">ขาดงาน (วัน)
                  <input type="number" min={0} className="border rounded px-2 py-1 w-full mt-0.5"
                    value={att.absent_days} onChange={(e) => setAtt((a) => ({ ...a, absent_days: Number(e.target.value) }))} />
                </label>
              </div>
              <label className="text-xs text-slate-500 block">
                ปรับคะแนนเอง (เว้นว่าง = คำนวณอัตโนมัติจากข้อมูลด้านบน)
                <input type="number" min={0} max={40} className="border rounded px-2 py-1 w-28 ml-2"
                  value={attOverride} onChange={(e) => setAttOverride(e.target.value === '' ? '' : Number(e.target.value))} />
              </label>
              <button onClick={saveAttendance} disabled={busy}
                className="bg-slate-700 text-white rounded px-4 py-2 text-sm disabled:opacity-50">บันทึกข้อมูลการมา-ลา</button>
            </div>
          )}
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
              {/* Backend blocks this until the employee has signed; disable rather
                  than let GM/MD click into a 409. */}
              <button onClick={() => transition('approve', 'อนุมัติแล้ว')} disabled={busy || !ev.acknowledgement}
                title={!ev.acknowledgement ? 'ต้องบันทึกการรับทราบของพนักงานก่อน' : undefined}
                className="bg-green-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50">อนุมัติ</button>
              <button onClick={() => transition('return', 'ตีกลับแล้ว')} disabled={busy} className="bg-amber-600 text-white rounded px-4 py-2 text-sm disabled:opacity-50">ตีกลับ</button>
              {!ev.acknowledgement && (
                <p className="text-sm text-amber-600 self-center">ต้องบันทึกการรับทราบของพนักงานก่อนจึงจะอนุมัติได้</p>
              )}
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
            <p className="text-sm text-slate-400 self-center">
              {ev.acknowledgement ? 'รอ GM/MD อนุมัติ' : 'รอพนักงานลงนามรับทราบ ก่อนส่งให้ GM/MD อนุมัติ'}
            </p>
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

        {showAckSection && (
          <section className="bg-white rounded-xl shadow p-5 text-sm">
            <h3 className="font-medium text-slate-700 mb-2">การรับทราบของพนักงาน</h3>

            {ev.acknowledgement ? (
              <div className="space-y-1 text-slate-600">
                <p>
                  <b>{ACK_DECISION_LABEL[ev.acknowledgement.decision] ?? ev.acknowledgement.decision}</b>
                  {' '}· {ev.acknowledgement.method === 'paper' ? 'ลงนามในเอกสาร' : 'ลงนามทางระบบ'}
                  {' '}เมื่อ {new Date(ev.acknowledgement.signed_at).toLocaleDateString('th-TH')}
                </p>
                {ev.acknowledgement.witness_name && (
                  <p className="text-xs text-slate-400">พยาน: {ev.acknowledgement.witness_name}</p>
                )}
                {ev.acknowledgement.comment && (
                  <p className="text-xs text-slate-500">ความเห็นของผู้ถูกประเมิน: {ev.acknowledgement.comment}</p>
                )}
                {ev.acknowledgement.attachment_path && (
                  <button
                    onClick={() => apiDownload(`/api/evaluations/${id}/acknowledgement-attachment`, `acknowledgement-${id}`).catch((e) => setError(String(e)))}
                    className="text-xs text-blue-600 hover:text-blue-800">ดาวน์โหลดไฟล์แนบ</button>
                )}
              </div>
            ) : ev.status === 'dept_approved' && canRecordAck ? (
              <div className="space-y-2">
                <p className="text-xs text-slate-500">
                  กด "ดาวน์โหลด PDF" ด้านบนเพื่อพิมพ์ให้พนักงานลงนาม แล้วบันทึกผลกลับเข้าระบบที่นี่ —
                  <b> GM/MD จะอนุมัติขั้นถัดไปได้ก็ต่อเมื่อบันทึกการรับทราบแล้ว</b>
                  {' '}(ระบบรับทราบทางอีเมลจะเปิดใช้ในเฟสถัดไป)
                </p>
                <div className="flex flex-wrap gap-2 items-end">
                  <label className="text-xs text-slate-500">ผลการลงนาม
                    <select className="border rounded px-2 py-1 block mt-0.5"
                      value={ackForm.decision}
                      onChange={(e) => setAckForm((f) => ({ ...f, decision: e.target.value }))}>
                      <option value="acknowledged">รับทราบ</option>
                      <option value="acknowledged_disagreed">รับทราบ (มีความเห็นแย้ง)</option>
                      <option value="refused">ปฏิเสธการลงนาม</option>
                    </select>
                  </label>
                  <label className="text-xs text-slate-500">วันที่ลงนาม
                    <input type="date" className="border rounded px-2 py-1 block mt-0.5"
                      value={ackForm.signed_at}
                      onChange={(e) => setAckForm((f) => ({ ...f, signed_at: e.target.value }))} />
                  </label>
                  {ackForm.decision === 'refused' && (
                    <label className="text-xs text-slate-500">ชื่อพยาน
                      <input className="border rounded px-2 py-1 block mt-0.5"
                        value={ackForm.witness_name}
                        onChange={(e) => setAckForm((f) => ({ ...f, witness_name: e.target.value }))} />
                    </label>
                  )}
                  <label className="text-xs text-slate-500">ไฟล์แนบ (สแกน)
                    <input type="file" className="block mt-0.5 text-xs"
                      onChange={(e) => setAckFile(e.target.files?.[0] ?? null)} />
                  </label>
                </div>
                <textarea
                  className="w-full border rounded px-2 py-1 text-sm"
                  placeholder="ความเห็นของผู้ถูกประเมิน (ถ้ามี)"
                  rows={2}
                  value={ackForm.comment}
                  onChange={(e) => setAckForm((f) => ({ ...f, comment: e.target.value }))}
                />
                <button onClick={saveAcknowledgement} disabled={busy}
                  className="bg-slate-700 text-white rounded px-4 py-2 text-sm disabled:opacity-50">บันทึกการรับทราบ</button>
              </div>
            ) : ev.status === 'dept_approved' ? (
              <p className="text-slate-400">
                รอหัวหน้างาน/ผจก.แผนก/ฝ่ายบุคคล พิมพ์เอกสารให้พนักงานลงนามและบันทึกผล
              </p>
            ) : (
              <p className="text-slate-400">ยังไม่มีบันทึกการรับทราบ</p>
            )}
          </section>
        )}
      </main>
    </div>
  )
}
