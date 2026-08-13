import { supabase } from './supabase'

const base = import.meta.env.VITE_API_BASE_URL as string

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

// Render free tier sleeps the backend after 15min idle; the first request(s)
// after waking can fail to connect at all (browser throws "Failed to fetch",
// not an HTTP error) before the container is warm. Same root cause already
// fixed backend-side for outbound GoTrue calls (auth_admin.py) -- mirror it
// here so a cold start doesn't surface as a misleading "no permission"/empty
// page. Only retries on network-level failures, never on HTTP error responses
// (those are real answers from a live server, not connection problems).
async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  const delays = [3000, 6000]
  for (let attempt = 0; ; attempt++) {
    try {
      return await fetch(url, init)
    } catch (e) {
      if (attempt >= delays.length) throw e
      await sleep(delays[attempt])
    }
  }
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
  const res = await fetchWithRetry(`${base}${path}`, { headers: await authHeaders() })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as T
}

export async function apiDownload(path: string, filename: string): Promise<void> {
  const res = await fetchWithRetry(`${base}${path}`, { headers: await authHeaders() })
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

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)
  // No Content-Type header: the browser sets multipart/form-data with the
  // correct boundary itself when the body is a FormData instance.
  const res = await fetchWithRetry(`${base}${path}`, { method: 'POST', headers: await authHeaders(), body: form })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as T
}

export async function apiSendForm<T>(
  path: string,
  fields: Record<string, string | undefined>,
  file?: File | null,
): Promise<T> {
  const form = new FormData()
  Object.entries(fields).forEach(([k, v]) => { if (v !== undefined) form.append(k, v) })
  if (file) form.append('file', file)
  const res = await fetchWithRetry(`${base}${path}`, { method: 'POST', headers: await authHeaders(), body: form })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as T
}

export async function apiSend<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetchWithRetry(`${base}${path}`, {
    method,
    headers: { ...(await authHeaders()), 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as T
}
