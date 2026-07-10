import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from './components/ProtectedRoute'
import Dashboard from './pages/Dashboard'
import EvaluationDetail from './pages/EvaluationDetail'
import Evaluations from './pages/Evaluations'
import Inbox from './pages/Inbox'
import Login from './pages/Login'
import People from './pages/People'
import TenantDetail from './pages/TenantDetail'
import Tenants from './pages/Tenants'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/inbox" element={<ProtectedRoute><Inbox /></ProtectedRoute>} />
      <Route path="/people" element={<ProtectedRoute><People /></ProtectedRoute>} />
      <Route path="/tenants" element={<ProtectedRoute><Tenants /></ProtectedRoute>} />
      <Route path="/tenants/:id" element={<ProtectedRoute><TenantDetail /></ProtectedRoute>} />
      <Route path="/evaluations" element={<ProtectedRoute><Evaluations /></ProtectedRoute>} />
      <Route path="/evaluations/:id" element={<ProtectedRoute><EvaluationDetail /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
