import { useAuth } from '../context/AuthContext'

const ROLE_LABEL: Record<string, string> = {
  hr_admin: 'HR admin',
  manager: 'หัวหน้างาน',
  dept_manager: 'ผจก.แผนก',
  md: 'MD',
  gm: 'GM',
  employee: 'พนักงาน',
}

export default function CurrentUserBadge() {
  const { me } = useAuth()
  if (!me) return null

  const roleLabels = me.is_super_admin
    ? ['super_admin']
    : me.roles.map((r) => ROLE_LABEL[r] ?? r)

  return (
    <span className="text-xs text-slate-500">
      {me.email ?? '—'}
      {roleLabels.length > 0 && <span className="text-slate-400"> · {roleLabels.join(', ')}</span>}
      {me.company_name && <span className="text-slate-400"> · {me.company_name}</span>}
      {me.branch_name && <span className="text-slate-400"> ({me.branch_name})</span>}
    </span>
  )
}
