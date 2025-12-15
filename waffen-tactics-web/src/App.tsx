import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import AuthCallback from './pages/AuthCallback'
import Game from './pages/Game'
import TermsOfService from './pages/TermsOfService'
import { useAuthStore } from './store/authStore'
import './App.css'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, token, hydrated } = useAuthStore()
  
  if (!hydrated) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>
  }
  
  return user && token ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <div className="min-h-screen bg-background">
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/tos" element={<TermsOfService />} />
        <Route
          path="/game"
          element={
            <PrivateRoute>
              <Game />
            </PrivateRoute>
          }
        />
        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </div>
  )
}

export default App
