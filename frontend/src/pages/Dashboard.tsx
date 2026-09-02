import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import AppHeader from '../components/AppHeader'
import { useAuth } from '../context/AuthContext'
import { apiGet } from '../lib/api'
import { Section } from '../shared/ui'
import type { Employee, InboxItem } from '../types'
import { ACTION_LABEL, LEVEL_LABEL } from '../types'

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
  // A supervisor/dept manager cares about their own reports, not the whole
  // company roster -- narrow the table to just that when it applies (HR/
  // super_admin still get the full company view, same as before).
  const myReports = me?.employee_id
    ? employees.filter((e) => e.supervisor_id === me.employee_id || e.manager_id === me.employee_id)
    : []
  const rosterTitle = isHrAdmin ? 'พนักงาน (ทั้งบริษัท)' : `ทีมของคุณ (${myReports.length} คน)`
  const roster = isHrAdmin ? employees : myReports
  // Nothing to manage and nothing pending -- an account like this (GM/MD with
  // no direct reports, or a freshly invited profile) doesn't need an empty
  // roster table taking up the page.
  const showRoster = isHrAdmin || myReports.length > 0

  return (
    <div className="min-h-screen bg-canvas font-sans">
      <AppHeader />

      <main className="mx-auto max-w-3xl space-y-6 p-6">
        {error && <p className="text-danger">{error}</p>}

        {inbox.length > 0 && (
          <Link
            to="/inbox"
            className="block rounded-card border border-primary/30 bg-surface p-5 shadow-card transition-colors hover:border-primary"
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-medium text-ink">งานรอดำเนินการของคุณ</h2>
                  <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-fg">{inbox.length}</span>
                </div>
                <p className="mt-1 text-sm text-muted">
                  {inbox.slice(0, 2).map((it) => `${it.full_name} ${ACTION_LABEL[it.action]}`).join(' · ')}
                  {inbox.length > 2 ? ` และอีก ${inbox.length - 2} รายการ` : ''}
                </p>
              </div>
              <span className="whitespace-nowrap text-sm font-medium text-primary">ไปที่งานที่รอฉัน →</span>
            </div>
          </Link>
        )}

        {me && (
          <Section title="ผู้ใช้ปัจจุบัน">
            <dl className="space-y-1 text-sm text-muted">
              <div>อีเมล: {me.email}</div>
              <div>บริษัท: {me.company_name ?? (me.is_super_admin ? 'ทุกบริษัท (super_admin)' : '—')}</div>
              {me.branch_name && <div>สาขา: {me.branch_name}</div>}
              <div>
                roles: {me.roles.join(', ') || '—'}
                {me.is_super_admin ? ' (super_admin)' : ''}
              </div>
            </dl>
          </Section>
        )}

        {showRoster && (
          <Section
            title={rosterTitle}
            actions={
              isHrAdmin && (
                <Link to="/people" className="text-xs text-primary hover:text-primary-hover">
                  จัดการพนักงาน &amp; สาขา →
                </Link>
              )
            }
          >
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-muted">
                  <th className="py-1">รหัส</th>
                  <th>ชื่อ</th>
                  <th>ประเภทแบบประเมิน</th>
                  <th>สถานะ</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((e) => (
                  <tr key={e.id} className="border-b border-line last:border-0">
                    <td className="py-1">{e.emp_code}</td>
                    <td>{e.full_name}</td>
                    <td>{LEVEL_LABEL[e.level] ?? e.level}</td>
                    <td>{e.status}</td>
                  </tr>
                ))}
                {roster.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-3 text-faint">
                      ไม่มีข้อมูล
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </Section>
        )}
      </main>
    </div>
  )
}
