import { createContext, useContext, useEffect, useRef, useState } from 'react'
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
  meError: string | null
  signIn: (email: string, password: string) => Promise<{ error?: string }>
  signOut: () => Promise<void>
  refreshMe: () => Promise<void>
  switchCompany: (companyId: string) => Promise<{ error?: string }>
}

const INACTIVITY_LIMIT_MS = 30 * 60 * 1000

const AuthContext = createContext<AuthValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)
  const [meLoading, setMeLoading] = useState(true)
  // Distinct from "me is null because you're logged out" -- RequireRole must
  // not render "ไม่มีสิทธิ์เข้าถึงหน้านี้" when /api/me merely failed to load
  // (e.g. backend cold start), or a connection blip looks like a permissions
  // problem to the user.
  const [meError, setMeError] = useState<string | null>(null)

  const loadMe = async () => {
    setMeLoading(true)
    try {
      setMe(await apiGet<Me>('/api/me'))
      setMeError(null)
    } catch (e) {
      setMe(null)
      setMeError(String(e))
    } finally {
      setMeLoading(false)
    }
  }

  // supabase-js fires onAuthStateChange for TOKEN_REFRESHED too -- roughly
  // hourly AND every time the tab regains focus. That keeps the SAME user,
  // so re-fetching /api/me there only flashes a "loading user" state and,
  // when the backend is cold (Render), hangs the whole app for tens of
  // seconds on nothing more than an alt-tab. Reload me only when the
  // identity actually changes.
  const lastUid = useRef<string | undefined>(undefined)

  useEffect(() => {
    const apply = async (next: Session | null, initial = false) => {
      setSession(next)
      const uid = next?.user?.id
      if (!initial && uid === lastUid.current) return
      lastUid.current = uid
      if (next) {
        await loadMe()
      } else {
        setMe(null)
        setMeError(null)
        setMeLoading(false)
      }
    }

    supabase.auth.getSession().then(async ({ data }) => {
      await apply(data.session, true)
      setLoading(false)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      void apply(next)
    })
    return () => sub.subscription.unsubscribe()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto sign-out after 30 min with no mouse/keyboard/touch activity
  // (security review 2026-09-05): supabase-js otherwise keeps a session
  // valid indefinitely via silent refresh, which is fine on a personal
  // phone/laptop but leaves data exposed on a shared office computer
  // someone forgot to sign out of. Wall-clock check on an interval, not a
  // single setTimeout, so a laptop that was asleep/closed for over 30 min
  // signs out immediately on wake rather than waiting out a timer that
  // never ran. Kept in lockstep across all 4 HR Suite frontends -- one
  // shared Supabase project, same policy everywhere (see memory
  // auto-logout-inactivity).
  const hasSession = !!session
  const lastActivity = useRef(Date.now())
  useEffect(() => {
    if (!hasSession) return
    lastActivity.current = Date.now()
    const markActive = () => {
      lastActivity.current = Date.now()
    }
    const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'wheel'] as const
    events.forEach((e) => window.addEventListener(e, markActive, { passive: true }))
    const interval = setInterval(() => {
      if (Date.now() - lastActivity.current >= INACTIVITY_LIMIT_MS) {
        try {
          sessionStorage.setItem('auto_logged_out', '1')
        } catch {
          /* private mode -- the sign-out itself still happens */
        }
        void supabase.auth.signOut()
      }
    }, 30_000)
    return () => {
      events.forEach((e) => window.removeEventListener(e, markActive))
      clearInterval(interval)
    }
  }, [hasSession])

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
    <AuthContext.Provider value={{ session, me, loading, meLoading, meError, signIn, signOut, refreshMe: loadMe, switchCompany }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
