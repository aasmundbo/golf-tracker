import { useState, useEffect } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import NewRound from './pages/NewRound'
import ActiveRound from './pages/ActiveRound'
import History from './pages/History'
import MyCourses from './pages/MyCourses'
import Login from './pages/Login'
import LanguageSwitcher from './components/LanguageSwitcher'

const NAV_ITEMS = [
  { to: '/', icon: '🏌️', key: 'nav.newRound', end: true },
  { to: '/history', icon: '📋', key: 'nav.history' },
  { to: '/courses', icon: '🗺️', key: 'nav.myCourses' },
]

export default function App() {
  const { t } = useTranslation()
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'))

  useEffect(() => {
    const handleLogout = () => setIsAuthenticated(false)
    window.addEventListener('auth:logout', handleLogout)
    return () => window.removeEventListener('auth:logout', handleLogout)
  }, [])

  function handleLogout() {
    localStorage.removeItem('token')
    setIsAuthenticated(false)
  }

  if (!isAuthenticated) {
    return <Login onLogin={() => setIsAuthenticated(true)} />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="fixed top-0 left-0 right-0 z-40 bg-green-700 text-white flex items-center justify-between px-4 py-3">
        <span className="font-bold text-lg">{t('brand')}</span>
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          <button
            onClick={handleLogout}
            className="text-xs text-white/80 hover:text-white underline"
          >
            {t('logout')}
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 pt-14 pb-20">
        <Routes>
          <Route path="/" element={<NewRound />} />
          <Route path="/round/:id" element={<ActiveRound />} />
          <Route path="/history" element={<History />} />
          <Route path="/courses" element={<MyCourses />} />
        </Routes>
      </main>

      <nav
        className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-200"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="max-w-2xl mx-auto flex">
          {NAV_ITEMS.map(({ to, icon, key, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex-1 flex flex-col items-center gap-0.5 py-2 text-xs font-medium transition-colors ${
                  isActive ? 'text-green-700' : 'text-gray-400'
                }`
              }
            >
              <span className="text-xl leading-none">{icon}</span>
              <span>{t(key)}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
