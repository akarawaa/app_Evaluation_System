import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'

import { apiGet, apiSend } from '../lib/api'
import { supabase } from '../lib/supabase'
import type { Me } from '../types'

type AuthValue = {
  session: Session | null
  me: Me | null
  loading: boolean
  meLoading: boolean
  signIn: (email: string, password: string) => Promise<{ error?: string }>
  signOut: () => Promise<void>
  refreshMe: () => Promise<void>
  switchCompany: (companyId: string) => Promise<{ error?: string }>
}

const AuthContext = createContext<AuthValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)
  const [meLoading, setMeLoading] = useState(true)

  const loadMe = async () => {
    setMeLoading(true)
    try {
      setMe(await apiGet<Me>('/api/me'))
    } catch {
      setMe(null)
    } finally {
      setMeLoading(false)
    }
  }

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data }) => {
      setSession(data.session)
      if (data.session) await loadMe()
      else setMeLoading(false)
      setLoading(false)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next)
      if (next) void loadMe()
      else { setMe(null); setMeLoading(false) }
    })
    return () => sub.subscription.unsubscribe()
  }, [])

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return { error: error?.message }
  }

  const signOut = async () => {
    await supabase.auth.signOut()
  }

  const switchCompany = async (companyId: string) => {
    try {
      await apiSend('POST', '/api/me/active-company', { company_id: companyId })
    } catch (e) {
      return { error: String(e) }
    }
    // profiles.company_id changed server-side -- the current JWT still
    // carries the old claim until we mint a new one, so the auth hook must
    // re-run via a refresh (not just re-fetch /api/me) or RLS would keep
    // scoping every query to the company we just switched away from.
    const { data, error } = await supabase.auth.refreshSession()
    if (error || !data.session) return { error: error?.message ?? 'refresh failed' }
    setSession(data.session)
    await loadMe()
    return {}
  }

  return (
    <AuthContext.Provider value={{ session, me, loading, meLoading, signIn, signOut, refreshMe: loadMe, switchCompany }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
