import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import { apiDownload, apiGet, apiSend, apiUpload } from '../lib/api'
import type {
  AttendanceBracket, AttendanceBracketCategory, AttendanceBrackets,
  AttendanceImportResult, Branch, Employee, EvalListItem, ImportResult, TenantUser,
} from '../types'
import { ATTENDANCE_CATEGORY_LABEL, ATTENDANCE_CATEGORY_UNIT, INVITE_ROLES, LEVEL_LABEL, ROLE_LABEL, STATUS_LABEL } from '../types'

const BRACKET_CATEGORIES: AttendanceBracketCategory[] = ['personal', 'absent', 'sick', 'late']

function AttendanceBracketEditor({ category, rows, saving, onChange, onSave }: {
  category: AttendanceBracketCategory
  rows: AttendanceBracket[]
  saving: boolean
  onChange: (rows: AttendanceBracket[]) => void
  onSave: () => void
}) {
  const unit = ATTENDANCE_CATEGORY_UNIT[category]
  const update = (i: number, field: keyof AttendanceBracket, value: number | null) => {
    const next = rows.map((r, idx) => (idx === i ? { ...r, [field]: value } : r))
    onChange(next)
  }
  const addRow = () => {
    const last = rows[rows.length - 1]
    const min = last ? (last.max_value ?? last.min_value) + 1 : 0
    onChange([...rows, { min_value: min, max_value: null, score: 0 }])
  }
  const removeRow = (i: number) => onChange(rows.filter((_, idx) => idx !== i))

  return (
    <div className="border rounded-lg p-3">
      <h3 className="text-sm font-medium text-ink mb-2">{ATTENDANCE_CATEGORY_LABEL[category]}</h3>
      <table className="w-full text-xs mb-2">
        <thead>
          <tr className="text-left text-muted">
            <th className="pb-1 pr-2">ตั้งแต่ ({unit})</th>
            <th className="pb-1 pr-2">ถึง ({unit}) — เว้นว่าง = ไม่จำกัด</th>
            <th className="pb-1 pr-2">คะแนน</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td className="pr-2 py-0.5">
                <input type="number" min={0} className="border rounded px-1.5 py-0.5 w-16"
                  value={r.min_value} onChange={(e) => update(i, 'min_value', Number(e.target.value))} />
              </td>
              <td className="pr-2 py-0.5">
                <input type="number" min={0} className="border rounded px-1.5 py-0.5 w-16" placeholder="ไม่จำกัด"
                  value={r.max_value ?? ''}
                  onChange={(e) => update(i, 'max_value', e.target.value === '' ? null : Number(e.target.value))} />
              </td>
              <td className="pr-2 py-0.5">
                <input type="number" min={0} step="0.5" className="border rounded px-1.5 py-0.5 w-16"
                  value={r.score} onChange={(e) => update(i, 'score', Number(e.target.value))} />
              </td>
              <td>
                <button onClick={() => removeRow(i)} className="text-faint hover:text-danger text-xs">ลบ</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex gap-2">
        <button onClick={addRow} className="text-xs text-primary hover:text-primary-hover">+ เพิ่มช่วง</button>
        <button onClick={onSave} disabled={saving}
          className="ml-auto bg-primary text-white rounded px-3 py-1 text-xs disabled:opacity-50">
          {saving ? 'กำลังบันทึก…' : 'บันทึกหมวดนี้'}
        </button>
      </div>
    </div>
  )
}

const emptyForm = {
  emp_code: '', full_name: '', position: '', email: '', level: 'operational',
  branch_id: '', supervisor_id: '', manager_id: '',
}

const emptyInvite = { email: '', password: '', role: 'manager', employee_id: '' }

// These two roles are authorized by the real org chain (employee.supervisor_id
// / manager_id), not by role alone -- see services/evaluations.py. A login
// invited with one of these roles but no employee linked can sign in but can
// never actually score or approve anything.
const ROLES_NEEDING_EMPLOYEE = ['manager', 'dept_manager']

export default function People() {
  // Present only when a super_admin arrived here from a company's own page
  // ("จัดการพนักงาน & สาขาของบริษัทนี้" in TenantDetail.tsx) -- an hr_admin's
  // own company_id already scopes everything via RLS with no param needed.
  // company_name is display-only convenience carried in the URL; it is never
  // trusted for any filtering, only company_id is (and only server-side).
  const [params] = useSearchParams()
  const companyId = params.get('company_id')
  const companyName = params.get('company_name')
  const qs = companyId ? `?company_id=${companyId}` : ''

  const [tab, setTab] = useState<'employees' | 'branches' | 'users' | 'import' | 'settings'>('employees')

  const [employees, setEmployees] = useState<Employee[]>([])
  const [branches, setBranches] = useState<Branch[]>([])
  const [users, setUsers] = useState<TenantUser[]>([])
  const [evaluations, setEvaluations] = useState<EvalListItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [invite, setInvite] = useState(emptyInvite)

  const [newBranch, setNewBranch] = useState('')
  const [renaming, setRenaming] = useState<{ id: string; name: string } | null>(null)

  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)

  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [importing, setImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [attImportResult, setAttImportResult] = useState<AttendanceImportResult | null>(null)
  const [attImporting, setAttImporting] = useState(false)
  const attFileInputRef = useRef<HTMLInputElement>(null)

  const [brackets, setBrackets] = useState<AttendanceBrackets | null>(null)
  const [savingCategory, setSavingCategory] = useState<AttendanceBracketCategory | null>(null)

  const load = () => Promise.all([
    apiGet<Employee[]>(`/api/employees${qs}`).then(setEmployees),
    apiGet<Branch[]>(`/api/branches${qs}`).then(setBranches),
    apiGet<TenantUser[]>(`/api/users${qs}`).then(setUsers),
    // attendance brackets/import/evaluations aren't scoped to a specific
    // company yet -- out of scope for cross-company browsing for now,
    // hidden below instead (GET /api/evaluations has no company_id param;
    // calling it while browsing another tenant would leak that tenant's
    // evaluations into a super_admin's own RLS-bypassed view).
    companyId ? Promise.resolve() : apiGet<AttendanceBrackets>('/api/settings/attendance-brackets').then(setBrackets),
    companyId ? Promise.resolve() : apiGet<EvalListItem[]>('/api/evaluations').then(setEvaluations),
  ]).catch((e) => setError(String(e)))

  useEffect(() => { load() }, [companyId])

  const run = async (fn: () => Promise<unknown>, okMsg: string) => {
    setBusy(true); setError(null); setMsg(null)
    try { await fn(); await load(); setMsg(okMsg) }
    catch (e) { setError(String(e)) }
    finally { setBusy(false) }
  }

  const addBranch = () => {
    if (!newBranch.trim()) return
    run(async () => { await apiSend('POST', `/api/branches${qs}`, { name: newBranch.trim() }); setNewBranch('') }, 'เพิ่มสาขาแล้ว')
  }

  const saveBranchRename = () => {
    if (!renaming || !renaming.name.trim()) return
    run(async () => { await apiSend('PATCH', `/api/branches/${renaming.id}${qs}`, { name: renaming.name.trim() }); setRenaming(null) }, 'แก้ไขชื่อสาขาแล้ว')
  }

  const startEdit = (emp: Employee) => {
    setEditingId(emp.id)
    setForm({
      emp_code: emp.emp_code, full_name: emp.full_name, position: emp.position ?? '',
      email: emp.email ?? '',
      level: emp.level, branch_id: emp.branch_id ?? '', supervisor_id: emp.supervisor_id ?? '',
      manager_id: emp.manager_id ?? '',
    })
  }

  const cancelEdit = () => { setEditingId(null); setForm(emptyForm) }

  const submitForm = () => {
    if (!form.emp_code.trim() || !form.full_name.trim()) return
    const payload = {
      emp_code: form.emp_code.trim(),
      full_name: form.full_name.trim(),
      position: form.position.trim() || null,
      email: form.email.trim() || null,
      level: form.level,
      branch_id: form.branch_id || null,
      supervisor_id: form.supervisor_id || null,
      manager_id: form.manager_id || null,
    }
    if (editingId) {
      run(async () => { await apiSend('PATCH', `/api/employees/${editingId}${qs}`, payload); cancelEdit() }, 'แก้ไขพนักงานแล้ว')
    } else {
      run(async () => { await apiSend('POST', `/api/employees${qs}`, payload); setForm(emptyForm) }, 'เพิ่มพนักงานแล้ว')
    }
  }

  const toggleStatus = (emp: Employee) =>
    run(() => apiSend('PATCH', `/api/employees/${emp.id}${qs}`, { status: emp.status === 'active' ? 'inactive' : 'active' }),
      emp.status === 'active' ? 'ปิดใช้งานแล้ว' : 'เปิดใช้งานแล้ว')

  const supervisorCandidates = employees.filter((e) => e.level === 'supervisor' && e.id !== editingId)

  const downloadTemplate = () =>
    apiDownload('/api/employees/import-template', 'employee-import-template.csv').catch((e) => setError(String(e)))

  const runImport = async (file: File) => {
    setImporting(true); setError(null); setMsg(null); setImportResult(null)
    try {
      const result = await apiUpload<ImportResult>('/api/employees/import', file)
      setImportResult(result)
      await load()
    } catch (e) {
      setError(String(e))
    } finally {
      setImporting(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const downloadAttTemplate = () =>
    apiDownload('/api/evaluations/attendance-import-template', 'attendance-import-template.csv').catch((e) => setError(String(e)))

  const runAttImport = async (file: File) => {
    setAttImporting(true); setError(null); setMsg(null); setAttImportResult(null)
    try {
      const result = await apiUpload<AttendanceImportResult>('/api/evaluations/attendance-import', file)
      setAttImportResult(result)
    } catch (e) {
      setError(String(e))
    } finally {
      setAttImporting(false)
      if (attFileInputRef.current) attFileInputRef.current.value = ''
    }
  }

  const setBracketRows = (category: AttendanceBracketCategory, rows: AttendanceBracket[]) =>
    setBrackets((b) => (b ? { ...b, [category]: rows } : b))

  const saveBrackets = (category: AttendanceBracketCategory) => {
    if (!brackets) return
    setSavingCategory(category); setError(null); setMsg(null)
    apiSend<AttendanceBracket[]>('PUT', `/api/settings/attendance-brackets/${category}`, { items: brackets[category] })
      .then((rows) => { setBracketRows(category, rows); setMsg(`บันทึกเกณฑ์หมวด "${ATTENDANCE_CATEGORY_LABEL[category]}" แล้ว`) })
      .catch((e) => setError(String(e)))
      .finally(() => setSavingCategory(null))
  }

  const sendInvite = () => {
    if (!invite.email.trim() || invite.password.length < 8) return
    run(async () => {
      await apiSend('POST', `/api/users/invite${qs}`, {
        email: invite.email.trim(), password: invite.password, role: invite.role,
        employee_id: invite.employee_id || undefined,
      })
      setInvite(emptyInvite)
    }, 'เชิญผู้ใช้เข้าระบบแล้ว')
  }

  const toggleUserStatus = (u: TenantUser) =>
    run(() => apiSend('PATCH', `/api/users/${u.id}/status${qs}`, { active: !u.active }),
      u.active ? 'ปิดใช้งานบัญชีแล้ว' : 'เปิดใช้งานบัญชีแล้ว')

  const linkUserEmployee = (u: TenantUser, employeeId: string) =>
    run(() => apiSend('PATCH', `/api/users/${u.id}/employee${qs}`, { employee_id: employeeId || null }),
      employeeId ? 'ผูกกับพนักงานแล้ว' : 'ปลดการผูกแล้ว')

  // Revoke one role only -- login/profile/other roles untouched (contrast
  // with toggleUserStatus, which bans the whole login for a resignation).
  // For a department transfer: pull the old role off without kicking the
  // person out of the system entirely. No confirm() dialog -- matches
  // toggleUserStatus above, an equally one-click reversible action (just
  // re-grant the role if clicked by mistake).
  const revokeRole = (u: TenantUser, role: string) =>
    run(() => apiSend('DELETE', `/api/users/${u.id}/roles/${role}${qs}`), 'ถอดบทบาทแล้ว')

  // GET /api/evaluations is already ordered created_at desc (see
  // services/evaluations.list_all), so the first row per employee_id is
  // their most recent evaluation -- no extra sort needed here.
  const latestEvalByEmployee = new Map<string, EvalListItem>()
  for (const ev of evaluations) {
    if (!latestEvalByEmployee.has(ev.employee_id)) latestEvalByEmployee.set(ev.employee_id, ev)
  }

  // Cross-company browsing (super_admin via TenantDetail) doesn't support
  // file import / formula settings yet -- those tabs are hidden entirely
  // rather than shown-but-broken (see the notice above).
  const TABS: { id: typeof tab; label: string }[] = [
    { id: 'employees', label: 'พนักงาน' },
    { id: 'branches', label: 'สาขา' },
    { id: 'users', label: 'ผู้ใช้ระบบ' },
    ...(companyId ? [] : [
      { id: 'import' as const, label: 'นำเข้าข้อมูล' },
      { id: 'settings' as const, label: 'ตั้งค่า' },
    ]),
  ]

  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader title={companyName ? `จัดการพนักงาน & สาขา — ${companyName}` : 'จัดการพนักงาน & สาขา'} />

      <main className="p-6 space-y-6 max-w-6xl mx-auto">
        {error && <p className="text-danger text-sm">{error}</p>}
        {msg && <p className="text-green-700 text-sm">{msg}</p>}
        {companyId && (
          <p className="text-xs bg-primary-soft text-primary rounded px-3 py-2">
            กำลังจัดการข้อมูลของบริษัท <strong>{companyName ?? companyId}</strong> ในฐานะ super_admin —
            การนำเข้าไฟล์ CSV และตั้งเกณฑ์คะแนนการมา-ลา ยังต้องให้ hr_admin ของบริษัทนี้ทำเองในหน้านี้โดยตรง (login เป็น hr_admin)
          </p>
        )}

        <nav className="flex items-center gap-4 border-b">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={
                tab === t.id
                  ? 'text-sm font-medium text-primary border-b-2 border-primary pb-2 -mb-px'
                  : 'text-sm text-muted hover:text-ink pb-2'
              }
            >
              {t.label}
            </button>
          ))}
        </nav>

        {tab === 'import' && !companyId && (
        <>
        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-1 text-ink">นำเข้าพนักงานจากไฟล์</h2>
          <p className="text-xs text-muted mb-3">
            สำหรับตอนขึ้นระบบครั้งแรก หรือเพิ่ม/แก้ไขพนักงานจำนวนมากพร้อมกัน — ดาวน์โหลดเทมเพลต กรอกข้อมูลใน Excel
            แล้วอัปโหลดกลับ ระบุ "รหัสหัวหน้างาน"/"รหัสผจก.แผนก" เป็นรหัสพนักงานของอีกแถวในไฟล์เดียวกันได้เลย
            (นำเข้าซ้ำด้วยรหัสพนักงานเดิมจะเป็นการแก้ไข ไม่ใช่สร้างซ้ำ)
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={downloadTemplate} className="text-sm text-primary hover:text-primary-hover font-medium">
              ↓ ดาวน์โหลดเทมเพลต (CSV)
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              disabled={importing}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) runImport(f) }}
              className="text-sm"
            />
            {importing && <span className="text-sm text-faint">กำลังนำเข้า…</span>}
          </div>

          {importResult && (
            <div className="mt-4 border-t pt-4">
              <div className="flex flex-wrap gap-4 text-sm mb-2">
                <span className="text-green-700">สร้างใหม่ {importResult.created} คน</span>
                <span className="text-primary">แก้ไข {importResult.updated} คน</span>
                <span className="text-muted">ผูกสายบังคับบัญชา {importResult.linked} รายการ</span>
                {importResult.branches_created > 0 && (
                  <span className="text-muted">สร้างสาขาใหม่ {importResult.branches_created} สาขา</span>
                )}
                {importResult.errors.length > 0 && (
                  <span className="text-danger font-medium">ผิดพลาด {importResult.errors.length} แถว</span>
                )}
              </div>
              {importResult.errors.length > 0 && (
                <table className="w-full text-xs mt-2">
                  <thead>
                    <tr className="text-left text-muted border-b">
                      <th className="py-1 pr-2 w-16">แถว</th><th className="pr-2 w-32">รหัสพนักงาน</th><th>ข้อผิดพลาด</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importResult.errors.map((err, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1 pr-2">{err.row}</td>
                        <td className="pr-2">{err.emp_code ?? '—'}</td>
                        <td className="text-danger">{err.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </section>

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-1 text-ink">นำเข้าข้อมูลการมา-ลาจากไฟล์</h2>
          <p className="text-xs text-muted mb-3">
            สำหรับ HR กรอกข้อมูลลาป่วย/ลากิจ/มาสาย/ขาดงานให้พนักงานหลายคนพร้อมกัน — ระบบคำนวณคะแนนการมา-ลา (เต็ม 40) ให้อัตโนมัติ
            แต่ละแถวจะจับคู่กับใบประเมินที่ยังไม่ปิดของพนักงานคนนั้น (ต้องมีใบประเมินอยู่แล้ว 1 ใบ) ถ้าใบไหนถูก HR ปรับคะแนนเองไว้แล้วจะไม่ถูกเขียนทับ
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={downloadAttTemplate} className="text-sm text-primary hover:text-primary-hover font-medium">
              ↓ ดาวน์โหลดเทมเพลต (CSV)
            </button>
            <input
              ref={attFileInputRef}
              type="file"
              accept=".csv,text/csv"
              disabled={attImporting}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) runAttImport(f) }}
              className="text-sm"
            />
            {attImporting && <span className="text-sm text-faint">กำลังนำเข้า…</span>}
          </div>

          {attImportResult && (
            <div className="mt-4 border-t pt-4">
              <div className="flex flex-wrap gap-4 text-sm mb-2">
                <span className="text-primary">อัปเดตแล้ว {attImportResult.updated} ใบ</span>
                {attImportResult.skipped_overridden > 0 && (
                  <span className="text-muted">ข้าม (HR ปรับเองไว้แล้ว) {attImportResult.skipped_overridden} ใบ</span>
                )}
                {attImportResult.errors.length > 0 && (
                  <span className="text-danger font-medium">ผิดพลาด {attImportResult.errors.length} แถว</span>
                )}
              </div>
              {attImportResult.errors.length > 0 && (
                <table className="w-full text-xs mt-2">
                  <thead>
                    <tr className="text-left text-muted border-b">
                      <th className="py-1 pr-2 w-16">แถว</th><th className="pr-2 w-32">รหัสพนักงาน</th><th>ข้อผิดพลาด</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attImportResult.errors.map((err, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1 pr-2">{err.row}</td>
                        <td className="pr-2">{err.emp_code ?? '—'}</td>
                        <td className="text-danger">{err.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </section>
        </>
        )}

        {tab === 'settings' && !companyId && (
        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-1 text-ink">เกณฑ์คะแนนการมา-ลา</h2>
          <p className="text-xs text-muted mb-3">
            แต่ละหมวดคะแนนเต็ม 10 (รวม 4 หมวด = 40) ให้คะแนนตามช่วงที่จำนวนวัน/ครั้งจริงตกอยู่ — ไม่ใช่การหักคะแนนต่อหน่วย
            เช่น ลาป่วย 3 วันอาจยังได้เต็ม 10 ถ้าอยู่ในช่วงที่กำหนดไว้ ปรับช่วง/คะแนนได้ตามนโยบายบริษัทจริงทีละหมวด
            ต้องกรอกให้ครอบคลุมตั้งแต่ 0 ถึงไม่จำกัด (ช่วงสุดท้ายเว้นช่อง "ถึง" ว่างไว้) โดยไม่มีช่องว่างหรือช่วงทับซ้อนกัน
            การเปลี่ยนเกณฑ์มีผลกับข้อมูลที่กรอก/นำเข้าใหม่หลังจากนี้ ไม่กระทบคะแนนที่บันทึกไว้แล้ว
          </p>
          {brackets && (
            <div className="grid sm:grid-cols-2 gap-3">
              {BRACKET_CATEGORIES.map((cat) => (
                <AttendanceBracketEditor
                  key={cat}
                  category={cat}
                  rows={brackets[cat]}
                  saving={savingCategory === cat}
                  onChange={(rows) => setBracketRows(cat, rows)}
                  onSave={() => saveBrackets(cat)}
                />
              ))}
            </div>
          )}
        </section>
        )}

        {tab === 'branches' && (
        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-3 text-ink">สาขา</h2>
          <ul className="divide-y mb-3">
            {branches.map((b) => (
              <li key={b.id} className="flex items-center justify-between py-2 text-sm gap-2">
                {renaming?.id === b.id ? (
                  <>
                    <input className="border rounded px-2 py-1 flex-1" value={renaming.name}
                      onChange={(e) => setRenaming({ id: b.id, name: e.target.value })} />
                    <button onClick={saveBranchRename} disabled={busy} className="text-primary text-xs font-medium disabled:opacity-50">บันทึก</button>
                    <button onClick={() => setRenaming(null)} className="text-faint text-xs">ยกเลิก</button>
                  </>
                ) : (
                  <>
                    <span>{b.name}</span>
                    <button onClick={() => setRenaming({ id: b.id, name: b.name })} className="text-primary text-xs font-medium">แก้ไข</button>
                  </>
                )}
              </li>
            ))}
            {branches.length === 0 && <li className="py-2 text-faint text-sm">ยังไม่มีสาขา</li>}
          </ul>
          <div className="flex gap-2">
            <input className="border rounded px-2 py-1 text-sm flex-1" placeholder="ชื่อสาขาใหม่"
              value={newBranch} onChange={(e) => setNewBranch(e.target.value)} />
            <button onClick={addBranch} disabled={busy || !newBranch.trim()}
              className="bg-primary text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">เพิ่มสาขา</button>
          </div>
        </section>
        )}

        {tab === 'employees' && (
        <>
        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-3 text-ink">{editingId ? 'แก้ไขพนักงาน' : 'เพิ่มพนักงาน'}</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <label>
              <span className="block text-muted mb-0.5">รหัสพนักงาน</span>
              <input className="border rounded px-2 py-1 w-full" value={form.emp_code}
                onChange={(e) => setForm((f) => ({ ...f, emp_code: e.target.value }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">ชื่อ-นามสกุล</span>
              <input className="border rounded px-2 py-1 w-full" value={form.full_name}
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">ตำแหน่ง</span>
              <input className="border rounded px-2 py-1 w-full" value={form.position}
                onChange={(e) => setForm((f) => ({ ...f, position: e.target.value }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">
                อีเมล (รับสลิป/ยืนยันตัวตน)
              </span>
              <input type="email" className="border rounded px-2 py-1 w-full" value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
            </label>
            <label>
              <span className="block text-muted mb-0.5">ประเภทแบบประเมิน</span>
              <select className="border rounded px-2 py-1 w-full" value={form.level}
                onChange={(e) => setForm((f) => ({ ...f, level: e.target.value }))}>
                <option value="operational">{LEVEL_LABEL.operational}</option>
                <option value="supervisor">{LEVEL_LABEL.supervisor}</option>
              </select>
            </label>
            <label>
              <span className="block text-muted mb-0.5">สาขา</span>
              <select className="border rounded px-2 py-1 w-full" value={form.branch_id}
                onChange={(e) => setForm((f) => ({ ...f, branch_id: e.target.value }))}>
                <option value="">— ไม่ระบุ —</option>
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </label>
            <label>
              <span className="block text-muted mb-0.5">หัวหน้างาน (ผู้ให้คะแนน)</span>
              <select className="border rounded px-2 py-1 w-full" value={form.supervisor_id}
                onChange={(e) => setForm((f) => ({ ...f, supervisor_id: e.target.value }))}>
                <option value="">— ไม่ระบุ —</option>
                {supervisorCandidates.map((e) => <option key={e.id} value={e.id}>{e.emp_code} · {e.full_name}</option>)}
              </select>
            </label>
            <label>
              <span className="block text-muted mb-0.5">ผจก.แผนก (ผู้อนุมัติชั้นที่ 1)</span>
              <select className="border rounded px-2 py-1 w-full" value={form.manager_id}
                onChange={(e) => setForm((f) => ({ ...f, manager_id: e.target.value }))}>
                <option value="">— ไม่ระบุ —</option>
                {supervisorCandidates.map((e) => <option key={e.id} value={e.id}>{e.emp_code} · {e.full_name}</option>)}
              </select>
            </label>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={submitForm} disabled={busy || !form.emp_code.trim() || !form.full_name.trim()}
              className="bg-primary text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
              {editingId ? 'บันทึกการแก้ไข' : 'เพิ่มพนักงาน'}
            </button>
            {editingId && (
              <button onClick={cancelEdit} className="text-sm text-muted hover:text-ink">ยกเลิก</button>
            )}
          </div>
        </section>

        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-3 text-ink">รายชื่อพนักงาน</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted border-b">
                  <th className="py-1 pr-2 whitespace-nowrap">รหัส</th><th className="pr-2 whitespace-nowrap">ชื่อ</th><th className="pr-2 whitespace-nowrap">ประเภทแบบประเมิน</th>
                  <th className="pr-2 whitespace-nowrap">สาขา</th><th className="pr-2 whitespace-nowrap">หัวหน้า</th><th className="pr-2 whitespace-nowrap">ผจก.แผนก</th>
                  <th className="pr-2 whitespace-nowrap">สถานะ</th><th className="pr-2 whitespace-nowrap">ใบประเมินล่าสุด</th><th></th>
                </tr>
              </thead>
              <tbody>
                {employees.map((emp) => (
                  <tr key={emp.id} className="border-b last:border-0">
                    <td className="py-1.5 pr-2 whitespace-nowrap">{emp.emp_code}</td>
                    <td className="pr-2 whitespace-nowrap">{emp.full_name}</td>
                    <td className="pr-2 whitespace-nowrap">{LEVEL_LABEL[emp.level] ?? emp.level}</td>
                    <td className="pr-2 text-muted whitespace-nowrap">{emp.branch_name ?? '—'}</td>
                    <td className="pr-2 text-muted whitespace-nowrap">{emp.supervisor_name ?? '—'}</td>
                    <td className="pr-2 text-muted whitespace-nowrap">{emp.manager_name ?? '—'}</td>
                    <td className="pr-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${emp.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-muted'}`}>
                        {emp.status === 'active' ? 'ทำงานอยู่' : 'ปิดใช้งาน'}
                      </span>
                    </td>
                    <td className="pr-2 whitespace-nowrap">
                      {(() => {
                        const latest = latestEvalByEmployee.get(emp.id)
                        return latest ? (
                          <Link to={`/evaluations/${latest.id}`} className="text-primary hover:text-primary-hover text-xs">
                            {STATUS_LABEL[latest.status] ?? latest.status}
                            {latest.percentage != null ? ` · ${latest.percentage}%` : ''} →
                          </Link>
                        ) : (
                          <span className="text-faint text-xs">— ไม่มี —</span>
                        )
                      })()}
                    </td>
                    <td className="whitespace-nowrap">
                      <button onClick={() => startEdit(emp)} className="text-primary text-xs font-medium mr-2">แก้ไข</button>
                      <button onClick={() => toggleStatus(emp)} className="text-muted text-xs font-medium">
                        {emp.status === 'active' ? 'ปิดใช้งาน' : 'เปิดใช้งาน'}
                      </button>
                    </td>
                  </tr>
                ))}
                {employees.length === 0 && (
                  <tr><td colSpan={9} className="py-3 text-faint">ยังไม่มีพนักงาน</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
        </>
        )}

        {tab === 'users' && (
        <section className="bg-surface rounded-card shadow p-5">
          <h2 className="font-medium mb-1 text-ink">ผู้ใช้ระบบ (บัญชีเข้าสู่ระบบ)</h2>
          <p className="text-xs text-muted mb-3">
            แยกจาก "พนักงาน" ด้านบน — เฉพาะคนที่ต้องล็อกอินเข้าระบบ (เช่น หัวหน้างานที่ต้องให้คะแนน
            หรือผู้อนุมัติ) เท่านั้นที่ต้องเชิญที่นี่ พนักงานทั่วไปไม่จำเป็นต้องมีบัญชี
          </p>
          <div className="grid grid-cols-3 gap-3 text-sm mb-3">
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
                onChange={(e) => setInvite((f) => ({
                  ...f, role: e.target.value,
                  employee_id: ROLES_NEEDING_EMPLOYEE.includes(e.target.value) ? f.employee_id : '',
                }))}>
                {INVITE_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
              </select>
            </label>
            {ROLES_NEEDING_EMPLOYEE.includes(invite.role) && (
              <label>
                <span className="block text-muted mb-0.5">ผูกกับพนักงาน (จำเป็น — ไม่งั้นให้คะแนน/อนุมัติไม่ได้)</span>
                <select className="border rounded px-2 py-1 w-full" value={invite.employee_id}
                  onChange={(e) => setInvite((f) => ({ ...f, employee_id: e.target.value }))}>
                  <option value="">— เลือกพนักงาน —</option>
                  {employees.map((e) => <option key={e.id} value={e.id}>{e.emp_code} · {e.full_name}</option>)}
                </select>
              </label>
            )}
          </div>
          <button onClick={sendInvite} disabled={busy || !invite.email.trim() || invite.password.length < 8}
            className="bg-primary text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
            เชิญเข้าระบบ
          </button>

          <table className="w-full text-sm mt-4">
            <thead>
              <tr className="text-left text-muted border-b">
                <th className="py-1 pr-2">ชื่อที่แสดง</th><th>บทบาท</th><th>พนักงานที่ผูก</th><th>สถานะ</th><th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b last:border-0">
                  <td className="py-1.5 pr-2">{u.display_name ?? '—'}</td>
                  <td>
                    {u.roles.length === 0 && '—'}
                    {u.roles.map((r) => (
                      <span key={r} className="inline-flex items-center gap-1 bg-slate-100 rounded-full pl-2 pr-1 py-0.5 mr-1 mb-0.5 text-xs">
                        {ROLE_LABEL[r] ?? r}
                        <button
                          onClick={() => revokeRole(u, r)}
                          disabled={busy}
                          title={`ถอดบทบาท ${ROLE_LABEL[r] ?? r}`}
                          className="text-faint hover:text-danger disabled:opacity-50 leading-none"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </td>
                  <td>
                    <select className="border rounded px-1.5 py-0.5 text-xs" value={u.employee_id ?? ''} disabled={busy}
                      onChange={(e) => linkUserEmployee(u, e.target.value)}>
                      <option value="">— ไม่ผูก —</option>
                      {employees.map((e) => <option key={e.id} value={e.id}>{e.emp_code} · {e.full_name}</option>)}
                    </select>
                    {!u.employee_id && u.roles.some((r) => ROLES_NEEDING_EMPLOYEE.includes(r)) && (
                      <div className="text-[11px] text-amber-600 mt-0.5">ยังผูกไม่ได้ — ให้คะแนน/อนุมัติไม่ได้</div>
                    )}
                  </td>
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
              {users.length === 0 && (
                <tr><td colSpan={5} className="py-3 text-faint">ยังไม่มีผู้ใช้</td></tr>
              )}
            </tbody>
          </table>
        </section>
        )}
      </main>
    </div>
  )
}
