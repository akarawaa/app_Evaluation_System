import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { apiGet, apiSend } from '../lib/api'
import type { Branch, Employee } from '../types'
import { LEVEL_LABEL } from '../types'

const emptyForm = {
  emp_code: '', full_name: '', position: '', level: 'operational',
  branch_id: '', supervisor_id: '', manager_id: '',
}

export default function People() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [branches, setBranches] = useState<Branch[]>([])
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [newBranch, setNewBranch] = useState('')
  const [renaming, setRenaming] = useState<{ id: string; name: string } | null>(null)

  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | null>(null)

  const load = () => Promise.all([
    apiGet<Employee[]>('/api/employees').then(setEmployees),
    apiGet<Branch[]>('/api/branches').then(setBranches),
  ]).catch((e) => setError(String(e)))

  useEffect(() => { load() }, [])

  const run = async (fn: () => Promise<unknown>, okMsg: string) => {
    setBusy(true); setError(null); setMsg(null)
    try { await fn(); await load(); setMsg(okMsg) }
    catch (e) { setError(String(e)) }
    finally { setBusy(false) }
  }

  const addBranch = () => {
    if (!newBranch.trim()) return
    run(async () => { await apiSend('POST', '/api/branches', { name: newBranch.trim() }); setNewBranch('') }, 'เพิ่มสาขาแล้ว')
  }

  const saveBranchRename = () => {
    if (!renaming || !renaming.name.trim()) return
    run(async () => { await apiSend('PATCH', `/api/branches/${renaming.id}`, { name: renaming.name.trim() }); setRenaming(null) }, 'แก้ไขชื่อสาขาแล้ว')
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
      run(async () => { await apiSend('PATCH', `/api/employees/${editingId}`, payload); cancelEdit() }, 'แก้ไขพนักงานแล้ว')
    } else {
      run(async () => { await apiSend('POST', '/api/employees', payload); setForm(emptyForm) }, 'เพิ่มพนักงานแล้ว')
    }
  }

  const toggleStatus = (emp: Employee) =>
    run(() => apiSend('PATCH', `/api/employees/${emp.id}`, { status: emp.status === 'active' ? 'inactive' : 'active' }),
      emp.status === 'active' ? 'ปิดใช้งานแล้ว' : 'เปิดใช้งานแล้ว')

  const supervisorCandidates = employees.filter((e) => e.level === 'supervisor' && e.id !== editingId)

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b px-6 py-3 flex justify-between items-center">
        <h1 className="font-semibold text-slate-800">จัดการพนักงาน &amp; สาขา</h1>
        <Link to="/" className="text-sm text-slate-600 hover:text-slate-900">← แดชบอร์ด</Link>
      </header>

      <main className="p-6 space-y-6 max-w-4xl mx-auto">
        {error && <p className="text-red-600 text-sm">{error}</p>}
        {msg && <p className="text-green-700 text-sm">{msg}</p>}

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
              <span className="block text-slate-500 mb-0.5">ระดับ</span>
              <select className="border rounded px-2 py-1 w-full" value={form.level}
                onChange={(e) => setForm((f) => ({ ...f, level: e.target.value }))}>
                <option value="operational">พนักงานปฏิบัติการ</option>
                <option value="supervisor">หัวหน้างาน</option>
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
                  <th className="py-1 pr-2">รหัส</th><th className="pr-2">ชื่อ</th><th className="pr-2">ระดับ</th>
                  <th className="pr-2">สาขา</th><th className="pr-2">หัวหน้า</th><th className="pr-2">ผจก.แผนก</th>
                  <th className="pr-2">สถานะ</th><th></th>
                </tr>
              </thead>
              <tbody>
                {employees.map((emp) => (
                  <tr key={emp.id} className="border-b last:border-0">
                    <td className="py-1.5 pr-2">{emp.emp_code}</td>
                    <td className="pr-2">{emp.full_name}</td>
                    <td className="pr-2">{LEVEL_LABEL[emp.level] ?? emp.level}</td>
                    <td className="pr-2 text-slate-500">{emp.branch_name ?? '—'}</td>
                    <td className="pr-2 text-slate-500">{emp.supervisor_name ?? '—'}</td>
                    <td className="pr-2 text-slate-500">{emp.manager_name ?? '—'}</td>
                    <td className="pr-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${emp.status === 'active' ? 'bg-green-50 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                        {emp.status === 'active' ? 'ทำงานอยู่' : 'ปิดใช้งาน'}
                      </span>
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
                  <tr><td colSpan={8} className="py-3 text-slate-400">ยังไม่มีพนักงาน</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  )
}
