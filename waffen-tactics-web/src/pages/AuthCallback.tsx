import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../services/api'

export default function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { setUser, setToken } = useAuthStore()
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const code = searchParams.get('code')

    if (!code) {
      navigate('/login')
      return
    }

    let cancelled = false

    console.log('Exchanging Discord code...')
    authAPI.exchangeCode(code)
      .then((response) => {
        if (cancelled) return
        const { user, token } = response.data
        console.log('Auth successful, user:', user.username)
        setUser(user)
        setToken(token)
        navigate('/game')
      })
      .catch((err) => {
        if (cancelled) return
        console.error('Auth error:', err)
        setError(err.response?.data?.message || err.message || 'Błąd logowania')
      })

    return () => {
      cancelled = true
    }
  }, [searchParams, navigate, setUser, setToken, attempt])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="card text-center space-y-4">
        {error ? (
          <>
            <div className="text-red-500 text-xl">Błąd</div>
            <p className="text-text">{error}</p>
            <div className="flex items-center justify-center gap-3 pt-2">
              <button className="btn btn-primary" onClick={() => { setError(null); setAttempt(v => v + 1) }}>
                Spróbuj ponownie
              </button>
              <button className="btn btn-secondary" onClick={() => navigate('/login')}>
                Wróć do logowania
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="animate-spin text-4xl">Ładowanie</div>
            <p className="text-text">Logowanie...</p>
          </>
        )}
      </div>
    </div>
  )
}
