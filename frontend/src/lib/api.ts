import { supabase } from './supabase'

const base = import.meta.env.VITE_API_BASE_URL as string

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function errText(res: Response): Promise<string> {
  try {
    const j = await res.json()
    return j?.detail ? `${res.status}: ${j.detail}` : `HTTP ${res.status}`
  } catch {
    return `HTTP ${res.status}`
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${base}${path}`, { headers: await authHeaders() })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as T
}

export async function apiDownload(path: string, filename: string): Promise<void> {
  const res = await fetch(`${base}${path}`, { headers: await authHeaders() })
  if (!res.ok) throw new Error(await errText(res))
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export async function apiSend<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as T
}
