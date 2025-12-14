import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../services/api'

export default function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { setUser, setToken } = useAuthStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const code = searchParams.get('code')
    
    if (!code) {
      navigate('/login')
      return
    }

    authAPI.exchangeCode(code)
      .then((response) => {
        const { user, token } = response.data
        setUser(user)
        setToken(token)
        navigate('/game')
      })
      .catch((err) => {
        console.error('Auth error:', err)
        setError(err.response?.data?.message || err.message || 'Błąd logowania')
      })
  }, [searchParams, navigate, setUser, setToken])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="card text-center space-y-4">
        {error ? (
          <>
            <div className="text-red-500 text-xl">❌</div>
            <p className="text-text">{error}</p>
          </>
        ) : (
          <>
            <div className="animate-spin text-4xl">⚔️</div>
            <p className="text-text">Logowanie...</p>
          </>
        )}
      </div>
    </div>
  )
}
