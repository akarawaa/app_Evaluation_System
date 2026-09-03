import { useEffect, useState } from 'react'

import { useAuth } from '../context/AuthContext'
import { apiGet } from '../lib/api'
import type { MyCompany } from '../types'

export default function CompanySwitcher() {
  const { me, switchCompany } = useAuth()
  const [companies, setCompanies] = useState<MyCompany[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!me) return
    apiGet<MyCompany[]>('/api/me/companies').then(setCompanies).catch(() => undefined)
  }, [me])

  // Renders nothing for the common case of exactly one company -- most
  // accounts never need this at all.
  if (companies.length <= 1) return null

  const onChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const companyId = e.target.value
    if (!companyId || companyId === me?.company_id) return
    setBusy(true)
    setError(null)
    const { error: err } = await switchCompany(companyId)
    if (err) {
      setError(err)
      setBusy(false)
      return
    }
    window.location.reload()
  }

  return (
    <span className="text-xs">
      <select
        value={me?.company_id ?? ''}
        onChange={onChange}
        disabled={busy}
        className="rounded border border-line bg-surface px-1 py-0.5 text-xs text-muted"
        title="สลับบริษัท"
      >
        {companies.map((c) => (
          <option key={c.company_id} value={c.company_id}>{c.company_name}</option>
        ))}
      </select>
      {error && <span className="ml-1 text-danger">{error}</span>}
    </span>
  )
}
