import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from './components/ProtectedRoute'
import RequireRole from './components/RequireRole'
import Compare from './pages/Compare'
import Dashboard from './pages/Dashboard'
import EvaluationDetail from './pages/EvaluationDetail'
import Evaluations from './pages/Evaluations'
import ForgotPassword from './pages/ForgotPassword'
import Inbox from './pages/Inbox'
import Login from './pages/Login'
import People from './pages/People'
import ResetPassword from './pages/ResetPassword'
import TenantDetail from './pages/TenantDetail'
import Tenants from './pages/Tenants'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/inbox" element={<ProtectedRoute><Inbox /></ProtectedRoute>} />
      <Route path="/people" element={<ProtectedRoute><RequireRole anyOf={['hr_admin']}><People /></RequireRole></ProtectedRoute>} />
      <Route path="/tenants" element={<ProtectedRoute><RequireRole anyOf={['super_admin']}><Tenants /></RequireRole></ProtectedRoute>} />
      <Route path="/tenants/:id" element={<ProtectedRoute><RequireRole anyOf={['super_admin']}><TenantDetail /></RequireRole></ProtectedRoute>} />
      <Route path="/evaluations" element={<ProtectedRoute><Evaluations /></ProtectedRoute>} />
      <Route path="/evaluations/compare" element={<ProtectedRoute><Compare /></ProtectedRoute>} />
      <Route path="/evaluations/:id" element={<ProtectedRoute><EvaluationDetail /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
