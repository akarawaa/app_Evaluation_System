import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import AppHeader from '../components/AppHeader'
import { apiDownload, apiGet, apiSend, apiUpload } from '../lib/api'
import type { AttendanceFormula, AttendanceImportResult, Branch, Employee, EvalListItem, ImportResult, TenantUser } from '../types'
import { INVITE_ROLES, LEVEL_LABEL, ROLE_LABEL, STATUS_LABEL } from '../types'

const emptyForm = {
  emp_code: '', full_name: '', position: '', level: 'operational',
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

  const [formula, setFormula] = useState<AttendanceFormula | null>(null)
  const [savingFormula, setSavingFormula] = useState(false)

  const load = () => Promise.all([
    apiGet<Employee[]>(`/api/employees${qs}`).then(setEmployees),
    apiGet<Branch[]>(`/api/branches${qs}`).then(setBranches),
    apiGet<TenantUser[]>(`/api/users${qs}`).then(setUsers),
    // attendance formula/import/evaluations aren't scoped to a specific
    // company yet -- out of scope for cross-company browsing for now,
    // hidden below instead (GET /api/evaluations has no company_id param;
    // calling it while browsing another tenant would leak that tenant's
    // evaluations into a super_admin's own RLS-bypassed view).
    companyId ? Promise.resolve() : apiGet<AttendanceFormula>('/api/settings/attendance-formula').then(setFormula),
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

  const saveFormula = () => {
    if (!formula) return
    setSavingFormula(true); setError(null); setMsg(null)
    apiSend<AttendanceFormula>('PUT', '/api/settings/attendance-formula', formula)
      .then((f) => { setFormula(f); setMsg('บันทึกสูตรคะแนนการมา-ลาแล้ว') })
      .catch((e) => setError(String(e)))
      .finally(() => setSavingFormula(false))
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
    <div className="min-h-screen bg-slate-50">
      <AppHeader title={companyName ? `จัดการพนักงาน & สาขา — ${companyName}` : 'จัดการพนักงาน & สาขา'} />

      <main className="p-6 space-y-6 max-w-6xl mx-auto">
        {error && <p className="text-red-600 text-sm">{error}</p>}
        {msg && <p className="text-green-700 text-sm">{msg}</p>}
        {companyId && (
          <p className="text-xs bg-blue-50 text-blue-700 rounded px-3 py-2">
            กำลังจัดการข้อมูลของบริษัท <strong>{companyName ?? companyId}</strong> ในฐานะ super_admin —
            การนำเข้าไฟล์ CSV และตั้งสูตรคะแนนการมา-ลา ยังต้องให้ hr_admin ของบริษัทนี้ทำเองในหน้านี้โดยตรง (login เป็น hr_admin)
          </p>
        )}

        <nav className="flex items-center gap-4 border-b">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={
                tab === t.id
                  ? 'text-sm font-medium text-blue-700 border-b-2 border-blue-700 pb-2 -mb-px'
                  : 'text-sm text-slate-500 hover:text-slate-800 pb-2'
              }
            >
              {t.label}
            </button>
          ))}
        </nav>

        {tab === 'import' && !companyId && (
        <>
        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-1 text-slate-700">นำเข้าพนักงานจากไฟล์</h2>
          <p className="text-xs text-slate-500 mb-3">
            สำหรับตอนขึ้นระบบครั้งแรก หรือเพิ่ม/แก้ไขพนักงานจำนวนมากพร้อมกัน — ดาวน์โหลดเทมเพลต กรอกข้อมูลใน Excel
            แล้วอัปโหลดกลับ ระบุ "รหัสหัวหน้างาน"/"รหัสผจก.แผนก" เป็นรหัสพนักงานของอีกแถวในไฟล์เดียวกันได้เลย
            (นำเข้าซ้ำด้วยรหัสพนักงานเดิมจะเป็นการแก้ไข ไม่ใช่สร้างซ้ำ)
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={downloadTemplate} className="text-sm text-blue-600 hover:text-blue-800 font-medium">
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
            {importing && <span className="text-sm text-slate-400">กำลังนำเข้า…</span>}
          </div>

          {importResult && (
            <div className="mt-4 border-t pt-4">
              <div className="flex flex-wrap gap-4 text-sm mb-2">
                <span className="text-green-700">สร้างใหม่ {importResult.created} คน</span>
                <span className="text-blue-700">แก้ไข {importResult.updated} คน</span>
                <span className="text-slate-600">ผูกสายบังคับบัญชา {importResult.linked} รายการ</span>
                {importResult.branches_created > 0 && (
                  <span className="text-slate-600">สร้างสาขาใหม่ {importResult.branches_created} สาขา</span>
                )}
                {importResult.errors.length > 0 && (
                  <span className="text-red-600 font-medium">ผิดพลาด {importResult.errors.length} แถว</span>
                )}
              </div>
              {importResult.errors.length > 0 && (
                <table className="w-full text-xs mt-2">
                  <thead>
                    <tr className="text-left text-slate-500 border-b">
                      <th className="py-1 pr-2 w-16">แถว</th><th className="pr-2 w-32">รหัสพนักงาน</th><th>ข้อผิดพลาด</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importResult.errors.map((err, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1 pr-2">{err.row}</td>
                        <td className="pr-2">{err.emp_code ?? '—'}</td>
                        <td className="text-red-600">{err.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </section>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-1 text-slate-700">นำเข้าข้อมูลการมา-ลาจากไฟล์</h2>
          <p className="text-xs text-slate-500 mb-3">
            สำหรับ HR กรอกข้อมูลลาป่วย/ลากิจ/มาสาย/ขาดงานให้พนักงานหลายคนพร้อมกัน — ระบบคำนวณคะแนนการมา-ลา (เต็ม 40) ให้อัตโนมัติ
            แต่ละแถวจะจับคู่กับใบประเมินที่ยังไม่ปิดของพนักงานคนนั้น (ต้องมีใบประเมินอยู่แล้ว 1 ใบ) ถ้าใบไหนถูก HR ปรับคะแนนเองไว้แล้วจะไม่ถูกเขียนทับ
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <button onClick={downloadAttTemplate} className="text-sm text-blue-600 hover:text-blue-800 font-medium">
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
            {attImporting && <span className="text-sm text-slate-400">กำลังนำเข้า…</span>}
          </div>

          {attImportResult && (
            <div className="mt-4 border-t pt-4">
              <div className="flex flex-wrap gap-4 text-sm mb-2">
                <span className="text-blue-700">อัปเดตแล้ว {attImportResult.updated} ใบ</span>
                {attImportResult.skipped_overridden > 0 && (
                  <span className="text-slate-600">ข้าม (HR ปรับเองไว้แล้ว) {attImportResult.skipped_overridden} ใบ</span>
                )}
                {attImportResult.errors.length > 0 && (
                  <span className="text-red-600 font-medium">ผิดพลาด {attImportResult.errors.length} แถว</span>
                )}
              </div>
              {attImportResult.errors.length > 0 && (
                <table className="w-full text-xs mt-2">
                  <thead>
                    <tr className="text-left text-slate-500 border-b">
                      <th className="py-1 pr-2 w-16">แถว</th><th className="pr-2 w-32">รหัสพนักงาน</th><th>ข้อผิดพลาด</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attImportResult.errors.map((err, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1 pr-2">{err.row}</td>
                        <td className="pr-2">{err.emp_code ?? '—'}</td>
                        <td className="text-red-600">{err.message}</td>
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
        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-1 text-slate-700">สูตรคำนวณคะแนนการมา-ลา</h2>
          <p className="text-xs text-slate-500 mb-3">
            ระบบคำนวณคะแนนการมา-ลา (เต็ม) จากข้อมูลดิบด้วยสูตร: คะแนนเต็ม − (ค่าลด×วันขาด) − (ค่าลด×วันลากิจ) − (ค่าลด×วันลาป่วย) − (ค่าลด×ครั้งมาสาย)
            ปรับตัวเลขได้ตามนโยบายบริษัท การเปลี่ยนสูตรมีผลกับข้อมูลที่กรอก/นำเข้าใหม่หลังจากนี้ ไม่กระทบคะแนนที่บันทึกไว้แล้ว
          </p>
          {formula && (
            <div className="flex flex-wrap gap-3 items-end">
              <label className="text-sm">
                <span className="block text-slate-500">คะแนนเต็ม</span>
                <input type="number" min={0} step="0.5" className="border rounded px-2 py-1 w-24"
                  value={formula.full_score}
                  onChange={(e) => setFormula({ ...formula, full_score: Number(e.target.value) })} />
              </label>
              <label className="text-sm">
                <span className="block text-slate-500">ลด/วันขาดงาน</span>
                <input type="number" min={0} step="0.5" className="border rounded px-2 py-1 w-24"
                  value={formula.coef_absent}
                  onChange={(e) => setFormula({ ...formula, coef_absent: Number(e.target.value) })} />
              </label>
              <label className="text-sm">
                <span className="block text-slate-500">ลด/วันลากิจ</span>
                <input type="number" min={0} step="0.5" className="border rounded px-2 py-1 w-24"
                  value={formula.coef_personal}
                  onChange={(e) => setFormula({ ...formula, coef_personal: Number(e.target.value) })} />
              </label>
              <label className="text-sm">
                <span className="block text-slate-500">ลด/วันลาป่วย</span>
                <input type="number" min={0} step="0.5" className="border rounded px-2 py-1 w-24"
                  value={formula.coef_sick}
                  onChange={(e) => setFormula({ ...formula, coef_sick: Number(e.target.value) })} />
              </label>
              <label className="text-sm">
                <span className="block text-slate-500">ลด/ครั้งมาสาย</span>
                <input type="number" min={0} step="0.5" className="border rounded px-2 py-1 w-24"
                  value={formula.coef_late}
                  onChange={(e) => setFormula({ ...formula, coef_late: Number(e.target.value) })} />
              </label>
              <button onClick={saveFormula} disabled={savingFormula}
                className="bg-slate-700 text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
                {savingFormula ? 'กำลังบันทึก…' : 'บันทึกสูตร'}
              </button>
            </div>
          )}
        </section>
        )}

        {tab === 'branches' && (
        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-3 text-slate-700">สาขา</h2>
          <ul className="divide-y mb-3">
            {branches.map((b) => (
              <li key={b.id} className="flex items-center justify-between py-2 text-sm gap-2">
                {renaming?.id === b.id ? (
                  <>
                    <input className="border rounded px-2 py-1 flex-1" value={renaming.name}
                      onChange={(e) => setRenaming({ id: b.id, name: e.target.value })} />
                    <button onClick={saveBranchRename} disabled={busy} className="text-blue-600 text-xs font-medium disabled:opacity-50">บันทึก</button>
                    <button onClick={() => setRenaming(null)} className="text-slate-400 text-xs">ยกเลิก</button>
                  </>
                ) : (
                  <>
                    <span>{b.name}</span>
                    <button onClick={() => setRenaming({ id: b.id, name: b.name })} className="text-blue-600 text-xs font-medium">แก้ไข</button>
                  </>
                )}
              </li>
            ))}
            {branches.length === 0 && <li className="py-2 text-slate-400 text-sm">ยังไม่มีสาขา</li>}
          </ul>
          <div className="flex gap-2">
            <input className="border rounded px-2 py-1 text-sm flex-1" placeholder="ชื่อสาขาใหม่"
              value={newBranch} onChange={(e) => setNewBranch(e.target.value)} />
            <button onClick={addBranch} disabled={busy || !newBranch.trim()}
              className="bg-slate-800 text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">เพิ่มสาขา</button>
          </div>
        </section>
        )}

        {tab === 'employees' && (
        <>
        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-3 text-slate-700">{editingId ? 'แก้ไขพนักงาน' : 'เพิ่มพนักงาน'}</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <label>
              <span className="block text-slate-500 mb-0.5">รหัสพนักงาน</span>
              <input className="border rounded px-2 py-1 w-full" value={form.emp_code}
                onChange={(e) => setForm((f) => ({ ...f, emp_code: e.target.value }))} />
            </label>
            <label>
              <span className="block text-slate-500 mb-0.5">ชื่อ-นามสกุล</span>
              <input className="border rounded px-2 py-1 w-full" value={form.full_name}
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} />
            </label>
            <label>
              <span className="block text-slate-500 mb-0.5">ตำแหน่ง</span>
              <input className="border rounded px-2 py-1 w-full" value={form.position}
                onChange={(e) => setForm((f) => ({ ...f, position: e.target.value }))} />
            </label>
            <label>
              <span className="block text-slate-500 mb-0.5">ประเภทแบบประเมิน</span>
              <select className="border rounded px-2 py-1 w-full" value={form.level}
                onChange={(e) => setForm((f) => ({ ...f, level: e.target.value }))}>
                <option value="operational">{LEVEL_LABEL.operational}</option>
                <option value="supervisor">{LEVEL_LABEL.supervisor}</option>
              </select>
            </label>
            <label>
              <span className="block text-slate-500 mb-0.5">สาขา</span>
              <select className="border rounded px-2 py-1 w-full" value={form.branch_id}
                onChange={(e) => setForm((f) => ({ ...f, branch_id: e.target.value }))}>
                <option value="">— ไม่ระบุ —</option>
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </label>
            <label>
              <span className="block text-slate-500 mb-0.5">หัวหน้างาน (ผู้ให้คะแนน)</span>
              <select className="border rounded px-2 py-1 w-full" value={form.supervisor_id}
                onChange={(e) => setForm((f) => ({ ...f, supervisor_id: e.target.value }))}>
                <option value="">— ไม่ระบุ —</option>
                {supervisorCandidates.map((e) => <option key={e.id} value={e.id}>{e.emp_code} · {e.full_name}</option>)}
              </select>
            </label>
            <label>
              <span className="block text-slate-500 mb-0.5">ผจก.แผนก (ผู้อนุมัติชั้นที่ 1)</span>
              <select className="border rounded px-2 py-1 w-full" value={form.manager_id}
                onChange={(e) => setForm((f) => ({ ...f, manager_id: e.target.value }))}>
                <option value="">— ไม่ระบุ —</option>
                {supervisorCandidates.map((e) => <option key={e.id} value={e.id}>{e.emp_code} · {e.full_name}</option>)}
              </select>
            </label>
          </div>
          <div className="flex gap-2 mt-4">
            <button onClick={submitForm} disabled={busy || !form.emp_code.trim() || !form.full_name.trim()}
              className="bg-slate-800 text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
              {editingId ? 'บันทึกการแก้ไข' : 'เพิ่มพนักงาน'}
            </button>
            {editingId && (
              <button onClick={cancelEdit} className="text-sm text-slate-500 hover:text-slate-700">ยกเลิก</button>
            )}
          </div>
        </section>

        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-3 text-slate-700">รายชื่อพนักงาน</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b">
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
                    <td className="pr-2 text-slate-500 whitespace-nowrap">{emp.branch_name ?? '—'}</td>
                    <td className="pr-2 text-slate-500 whitespace-nowrap">{emp.supervisor_name ?? '—'}</td>
                    <td className="pr-2 text-slate-500 whitespace-nowrap">{emp.manager_name ?? '—'}</td>
                    <td className="pr-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${emp.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                        {emp.status === 'active' ? 'ทำงานอยู่' : 'ปิดใช้งาน'}
                      </span>
                    </td>
                    <td className="pr-2 whitespace-nowrap">
                      {(() => {
                        const latest = latestEvalByEmployee.get(emp.id)
                        return latest ? (
                          <Link to={`/evaluations/${latest.id}`} className="text-blue-600 hover:text-blue-800 text-xs">
                            {STATUS_LABEL[latest.status] ?? latest.status}
                            {latest.percentage != null ? ` · ${latest.percentage}%` : ''} →
                          </Link>
                        ) : (
                          <span className="text-slate-300 text-xs">— ไม่มี —</span>
                        )
                      })()}
                    </td>
                    <td className="whitespace-nowrap">
                      <button onClick={() => startEdit(emp)} className="text-blue-600 text-xs font-medium mr-2">แก้ไข</button>
                      <button onClick={() => toggleStatus(emp)} className="text-slate-500 text-xs font-medium">
                        {emp.status === 'active' ? 'ปิดใช้งาน' : 'เปิดใช้งาน'}
                      </button>
                    </td>
                  </tr>
                ))}
                {employees.length === 0 && (
                  <tr><td colSpan={9} className="py-3 text-slate-400">ยังไม่มีพนักงาน</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
        </>
        )}

        {tab === 'users' && (
        <section className="bg-white rounded-xl shadow p-5">
          <h2 className="font-medium mb-1 text-slate-700">ผู้ใช้ระบบ (บัญชีเข้าสู่ระบบ)</h2>
          <p className="text-xs text-slate-500 mb-3">
            แยกจาก "พนักงาน" ด้านบน — เฉพาะคนที่ต้องล็อกอินเข้าระบบ (เช่น หัวหน้างานที่ต้องให้คะแนน
            หรือผู้อนุมัติ) เท่านั้นที่ต้องเชิญที่นี่ พนักงานทั่วไปไม่จำเป็นต้องมีบัญชี
          </p>
          <div className="grid grid-cols-3 gap-3 text-sm mb-3">
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
                onChange={(e) => setInvite((f) => ({
                  ...f, role: e.target.value,
                  employee_id: ROLES_NEEDING_EMPLOYEE.includes(e.target.value) ? f.employee_id : '',
                }))}>
                {INVITE_ROLES.map((r) => <option key={r} value={r}>{ROLE_LABEL[r]}</option>)}
              </select>
            </label>
            {ROLES_NEEDING_EMPLOYEE.includes(invite.role) && (
              <label>
                <span className="block text-slate-500 mb-0.5">ผูกกับพนักงาน (จำเป็น — ไม่งั้นให้คะแนน/อนุมัติไม่ได้)</span>
                <select className="border rounded px-2 py-1 w-full" value={invite.employee_id}
                  onChange={(e) => setInvite((f) => ({ ...f, employee_id: e.target.value }))}>
                  <option value="">— เลือกพนักงาน —</option>
                  {employees.map((e) => <option key={e.id} value={e.id}>{e.emp_code} · {e.full_name}</option>)}
                </select>
              </label>
            )}
          </div>
          <button onClick={sendInvite} disabled={busy || !invite.email.trim() || invite.password.length < 8}
            className="bg-slate-800 text-white rounded px-4 py-1.5 text-sm disabled:opacity-50">
            เชิญเข้าระบบ
          </button>

          <table className="w-full text-sm mt-4">
            <thead>
              <tr className="text-left text-slate-500 border-b">
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
                          className="text-slate-400 hover:text-red-600 disabled:opacity-50 leading-none"
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
                    <span className={`text-xs px-2 py-0.5 rounded-full ${u.active ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                      {u.active ? 'ใช้งานอยู่' : 'ปิดใช้งาน'}
                    </span>
                  </td>
                  <td className="whitespace-nowrap">
                    <button onClick={() => toggleUserStatus(u)} disabled={busy} className="text-slate-500 text-xs font-medium disabled:opacity-50">
                      {u.active ? 'ปิดใช้งาน' : 'เปิดใช้งาน'}
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan={5} className="py-3 text-slate-400">ยังไม่มีผู้ใช้</td></tr>
              )}
            </tbody>
          </table>
        </section>
        )}
      </main>
    </div>
  )
}
