import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import AppHeader from '../components/AppHeader'
import { apiGet } from '../lib/api'
import type { InboxAction, InboxItem } from '../types'
import { ACTION_LABEL } from '../types'

const ACTION_STYLE: Record<InboxAction, string> = {
  score: 'bg-primary-soft text-primary',
  dept_approve: 'bg-amber-50 text-amber-700',
  md_approve: 'bg-purple-50 text-purple-700',
  finalize: 'bg-green-50 text-green-700',
}

export default function Inbox() {
  const navigate = useNavigate()
  const [items, setItems] = useState<InboxItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiGet<InboxItem[]>('/api/evaluations/inbox')
      .then(setItems)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-canvas">
      <AppHeader title="งานที่รอฉัน" />

      <main className="p-6 space-y-4 max-w-3xl mx-auto">
        {error && <p className="text-danger text-sm">{error}</p>}

        <section className="bg-surface rounded-card shadow p-5">
          {loading ? (
            <p className="text-faint text-sm">กำลังโหลด…</p>
          ) : items.length === 0 ? (
            <p className="text-faint text-sm py-2">ไม่มีงานค้างในขณะนี้ 🎉</p>
          ) : (
            <ul className="divide-y">
              {items.map((it) => (
                <li
                  key={it.id}
                  onClick={() => navigate(`/evaluations/${it.id}`)}
                  className="flex items-center justify-between gap-3 py-3 cursor-pointer hover:bg-canvas -mx-2 px-2 rounded"
                >
                  <div>
                    <div className="text-sm font-medium text-ink">{it.emp_code} · {it.full_name}</div>
                    <div className="text-xs text-muted">{it.kind === 'annual' ? 'ประจำปี' : 'ทดลองงาน'}</div>
                  </div>
                  <span className={`text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${ACTION_STYLE[it.action]}`}>
                    {ACTION_LABEL[it.action]}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
