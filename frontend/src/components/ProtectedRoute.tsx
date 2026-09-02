import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'
import { Spinner } from '../shared/ui'

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth()
  if (loading) return <Spinner />
  if (!session) return <Navigate to="/login" replace />
  return <>{children}</>
}
