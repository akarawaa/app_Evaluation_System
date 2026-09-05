import { Link, useLocation } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import CompanySwitcher from './CompanySwitcher'
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
  {
    // A cross-evaluation analysis tool -- meaningful for people who oversee
    // many evaluations at once (HR/GM/MD/super_admin), not for a supervisor
    // who only ever scores their own reports' single forms.
    to: '/evaluations/compare', label: 'เปรียบเทียบผล',
    show: (me) => !!me && (me.is_super_admin || ['hr_admin', 'gm', 'md'].some((r) => me.roles.includes(r))),
    isActive: (p) => p === '/evaluations/compare',
  },
  {
    // hr_admin only -- their own company_id scopes this page unambiguously
    // via RLS. super_admin has no single "own company" for this page to mean
    // anything (their company_id is the reserved platform tenant), so they
    // reach it per-company instead, from a company's own page in "จัดการบริษัท".
    to: '/people', label: 'พนักงาน & สาขา',
    show: (me) => !!me && me.roles.includes('hr_admin'),
    isActive: (p) => p === '/people',
  },
  {
    to: '/tenants', label: 'จัดการบริษัท',
    show: (me) => !!me?.is_super_admin,
    isActive: (p) => p === '/tenants' || p.startsWith('/tenants/'),
  },
]

// hr-portal launcher URL -- a small "← HR Suite" link above the brand.
// Leave VITE_PORTAL_URL unset to hide it.
const PORTAL_URL = (import.meta.env.VITE_PORTAL_URL as string | undefined)?.trim()

export default function AppHeader({ title }: { title?: string }) {
  const { me, signOut } = useAuth()
  const { pathname } = useLocation()

  return (
    <header className="border-b border-line bg-surface px-4 py-3 font-sans sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex min-w-0 items-center gap-3">
          <div>
            {PORTAL_URL && (
              <a href={PORTAL_URL} className="flex items-center gap-1 text-xs text-faint hover:text-primary">
                <span aria-hidden="true">←</span> HR Suite
              </a>
            )}
            <Link to="/" className="shrink-0 font-semibold text-ink hover:text-ink">E-Appraisal</Link>
          </div>
          {title && <span className="shrink-0 text-faint">/</span>}
          {title && <span className="break-words text-sm text-muted">{title}</span>}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <CompanySwitcher />
          <CurrentUserBadge />
          <button onClick={signOut} className="shrink-0 text-sm text-muted hover:text-ink">
            ออกจากระบบ
          </button>
        </div>
      </div>
      <nav className="mt-2 flex flex-wrap items-center gap-4">
        {NAV_ITEMS.filter((item) => item.show(me)).map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={
              item.isActive(pathname)
                ? 'border-b-2 border-primary pb-0.5 text-sm font-medium text-primary-hover'
                : 'text-sm text-primary hover:text-primary-hover'
            }
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </header>
  )
}
