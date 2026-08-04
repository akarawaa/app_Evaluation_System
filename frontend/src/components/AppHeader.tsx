import { Link, useLocation } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import CurrentUserBadge from './CurrentUserBadge'

type NavItem = {
  to: string
  label: string
  show: (me: ReturnType<typeof useAuth>['me']) => boolean
  isActive: (pathname: string) => boolean
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'แดชบอร์ด', show: () => true, isActive: (p) => p === '/' },
  { to: '/inbox', label: 'งานที่รอฉัน', show: () => true, isActive: (p) => p === '/inbox' },
  {
    to: '/evaluations', label: 'ใบประเมินผล', show: () => true,
    isActive: (p) => p === '/evaluations' || (p.startsWith('/evaluations/') && p !== '/evaluations/compare'),
  },
  { to: '/evaluations/compare', label: 'เปรียบเทียบผล', show: () => true, isActive: (p) => p === '/evaluations/compare' },
  {
    to: '/people', label: 'พนักงาน & สาขา',
    show: (me) => !!me && (me.is_super_admin || me.roles.includes('hr_admin')),
    isActive: (p) => p === '/people',
  },
  {
    to: '/tenants', label: 'จัดการบริษัท',
    show: (me) => !!me?.is_super_admin,
    isActive: (p) => p === '/tenants' || p.startsWith('/tenants/'),
  },
]

export default function AppHeader({ title }: { title?: string }) {
  const { me, signOut } = useAuth()
  const { pathname } = useLocation()

  return (
    <header className="bg-white border-b px-6 py-3">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <Link to="/" className="font-semibold text-slate-800 hover:text-slate-900">E-Appraisal</Link>
          {title && <span className="text-slate-300">/</span>}
          {title && <span className="text-sm text-slate-600">{title}</span>}
        </div>
        <div className="flex items-center gap-4">
          <CurrentUserBadge />
          <button onClick={signOut} className="text-sm text-slate-600 hover:text-slate-900">
            ออกจากระบบ
          </button>
        </div>
      </div>
      <nav className="flex items-center gap-4 mt-2 flex-wrap">
        {NAV_ITEMS.filter((item) => item.show(me)).map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={
              item.isActive(pathname)
                ? 'text-sm font-medium text-blue-700 border-b-2 border-blue-700 pb-0.5'
                : 'text-sm text-blue-600 hover:text-blue-800'
            }
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </header>
  )
}
