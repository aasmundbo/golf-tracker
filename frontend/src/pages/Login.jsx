import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import axios from 'axios'

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ''

export default function Login() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const googleBtnRef = useRef(null)

  useEffect(() => {
    if (!googleClientId) return
    let cancelled = false

    function initGoogle() {
      if (!window.google || cancelled) return
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: async (response) => {
          if (cancelled) return
          setLoading(true)
          setError('')
          try {
            const { data } = await axios.post('/api/auth/google', { id_token: response.credential })
            if (!cancelled) {
              localStorage.setItem('token', data.access_token)
              navigate('/')
            }
          } catch {
            if (!cancelled) setError(t('login.googleError'))
          } finally {
            if (!cancelled) setLoading(false)
          }
        },
      })
      if (googleBtnRef.current) {
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: 'outline',
          size: 'large',
          width: googleBtnRef.current.offsetWidth || 300,
        })
      }
    }

    if (window.google) {
      initGoogle()
    } else {
      const script = document.querySelector('script[src*="accounts.google.com/gsi/client"]')
      if (script) {
        script.addEventListener('load', initGoogle)
        return () => {
          cancelled = true
          script.removeEventListener('load', initGoogle)
        }
      }
    }

    return () => { cancelled = true }
  }, [t, navigate])

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { data } = await axios.post('/api/auth/login', { username: email, password })
      localStorage.setItem('token', data.access_token)
      navigate('/')
    } catch {
      setError(t('login.error'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-green-700 text-center mb-6">{t('brand')}</h1>
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow p-6 space-y-4">
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('login.email')}
            </label>
            <input
              type="text"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-600"
              autoComplete="email"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('login.password')}
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-600"
              autoComplete="current-password"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-green-700 text-white rounded-lg py-2 font-medium hover:bg-green-800 disabled:opacity-50"
          >
            {loading ? '…' : t('login.submit')}
          </button>
          {googleClientId && (
            <>
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-400">{t('login.or')}</span>
                </div>
              </div>
              <div ref={googleBtnRef} className="w-full" />
            </>
          )}
        </form>
      </div>
    </div>
  )
}
