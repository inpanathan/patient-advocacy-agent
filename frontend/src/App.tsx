import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import Login from './pages/Login'
import Dashboard from './pages/patient/Dashboard'
import RegisterPatient from './pages/patient/RegisterPatient'
import StartSession from './pages/patient/StartSession'
import VoiceSession from './pages/patient/VoiceSession'
import ImageCapture from './pages/patient/ImageCapture'
import CaseResult from './pages/patient/CaseResult'
import CaseQueue from './pages/doctor/CaseQueue'
import CaseReview from './pages/doctor/CaseReview'

function ProtectedRoute({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>
  if (!user) return <Navigate to="/login" />
  if (roles && !roles.includes(user.role)) return <Navigate to="/login" />
  return <>{children}</>
}

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="flex items-center justify-center h-screen text-lg">Loading...</div>
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={user.role === 'doctor' ? '/doctor/cases' : '/patient/dashboard'} /> : <Login />} />

      {/* Patient mode (admin role) */}
      <Route path="/patient/dashboard" element={<ProtectedRoute roles={['admin']}><Dashboard /></ProtectedRoute>} />
      <Route path="/patient/register" element={<ProtectedRoute roles={['admin']}><RegisterPatient /></ProtectedRoute>} />
      <Route path="/patient/start" element={<ProtectedRoute roles={['admin']}><StartSession /></ProtectedRoute>} />
      <Route path="/patient/session/:caseId" element={<ProtectedRoute roles={['admin']}><VoiceSession /></ProtectedRoute>} />
      <Route path="/patient/session/:caseId/image" element={<ProtectedRoute roles={['admin']}><ImageCapture /></ProtectedRoute>} />
      <Route path="/patient/session/:caseId/result" element={<ProtectedRoute roles={['admin']}><CaseResult /></ProtectedRoute>} />

      {/* Doctor mode */}
      <Route path="/doctor/cases" element={<ProtectedRoute roles={['doctor']}><CaseQueue /></ProtectedRoute>} />
      <Route path="/doctor/cases/:caseId" element={<ProtectedRoute roles={['doctor']}><CaseReview /></ProtectedRoute>} />

      {/* Default redirect */}
      <Route path="*" element={<Navigate to="/login" />} />
    </Routes>
  )
}
