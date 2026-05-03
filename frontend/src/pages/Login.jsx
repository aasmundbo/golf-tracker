import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import axios from 'axios'

export default function Login() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

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
              type="email"
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
        </form>
      </div>
    </div>
  )
}
