import { supabase } from './supabase'

const base = import.meta.env.VITE_API_BASE_URL as string

// Attaches the current access token so the backend can verify + scope by tenant.
export async function apiGet<T>(path: string): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  const res = await fetch(`${base}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`Request failed: ${res.status}`)
  return (await res.json()) as T
}
