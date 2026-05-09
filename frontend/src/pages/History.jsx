import { useEffect, useState, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api/client'
import HandicapHistoryChart from '../components/HandicapHistoryChart'

export default function History() {
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage === 'nb' ? 'nb' : 'en'

  const [currentUser, setCurrentUser] = useState(null)
  const [rounds, setRounds] = useState([])

  // Filters
  const [period, setPeriod] = useState('all') // 'all' | '30' | '90'
  const [filterClub, setFilterClub] = useState('')
  const [filterTee, setFilterTee] = useState('')

  // Admin: selected user
  const [selectedUserId, setSelectedUserId] = useState(null)
  const [userSearch, setUserSearch] = useState('')
  const [userResults, setUserResults] = useState([])
  const [showUserDropdown, setShowUserDropdown] = useState(false)
  const searchDebounceRef = useRef(null)
  const searchContainerRef = useRef(null)

  useEffect(() => {
    api.get('/users/me').then(r => setCurrentUser(r.data)).catch(() => {})
  }, [])

  const loadRounds = useCallback(() => {
    const params = selectedUserId ? `?user_id=${selectedUserId}` : ''
    api.get(`/rounds${params}`).then(r => setRounds(r.data)).catch(() => {})
  }, [selectedUserId])

  useEffect(() => { loadRounds() }, [loadRounds])

  // Close user dropdown on outside click
  useEffect(() => {
    const handler = e => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target)) {
        setShowUserDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleUserSearchChange = e => {
    const q = e.target.value
    setUserSearch(q)
    clearTimeout(searchDebounceRef.current)
    if (q.length < 2) {
      setUserResults([])
      setShowUserDropdown(false)
      return
    }
    searchDebounceRef.current = setTimeout(async () => {
      try {
        const res = await api.get(`/users?search=${encodeURIComponent(q)}`)
        setUserResults(res.data)
        setShowUserDropdown(true)
      } catch {
        setUserResults([])
      }
    }, 300)
  }

  const selectUser = user => {
    setSelectedUserId(user.id)
    setUserSearch(user.display_name)
    setUserResults([])
    setShowUserDropdown(false)
  }

  const clearUserFilter = () => {
    setSelectedUserId(null)
    setUserSearch('')
    setUserResults([])
    setShowUserDropdown(false)
  }

  const deleteRound = async (e, id) => {
    e.preventDefault()
    if (!confirm(t('history.confirmDelete'))) return
    await api.delete(`/rounds/${id}`)
    loadRounds()
  }

  // Client-side filtering
  const filteredRounds = rounds.filter(r => {
    if (period !== 'all') {
      const days = parseInt(period, 10)
      const cutoff = Date.now() - days * 24 * 60 * 60 * 1000
      if (new Date(r.started_at).getTime() < cutoff) return false
    }
    if (filterClub && r.club_name !== filterClub) return false
    if (filterTee && r.tee_name !== filterTee) return false
    return true
  })

  // Unique clubs and tees from all loaded rounds (for dropdown options)
  const clubs = [...new Set(rounds.map(r => r.club_name).filter(Boolean))].sort()
  const tees = [...new Set(rounds.map(r => r.tee_name).filter(Boolean))].sort()

  const isAdmin = currentUser?.role === 'admin'
  const langTag = locale === 'nb' ? 'nb-NO' : 'en-GB'

  return (
    <div className="space-y-3 mt-6">
      <h2 className="text-xl font-bold">{t('history.title')}</h2>

      {/* Admin: user search */}
      {isAdmin && (
        <div className="relative" ref={searchContainerRef}>
          <input
            type="text"
            value={userSearch}
            onChange={handleUserSearchChange}
            onFocus={() => userResults.length > 0 && setShowUserDropdown(true)}
            placeholder={t('history.searchUser')}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
          />
          {showUserDropdown && userResults.length > 0 && (
            <div className="absolute z-10 left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg max-h-48 overflow-y-auto">
              {selectedUserId && (
                <button
                  className="w-full text-left px-3 py-2 text-sm text-green-700 hover:bg-gray-50 border-b"
                  onClick={clearUserFilter}
                >
                  {t('history.showAll')}
                </button>
              )}
              {userResults.map(u => (
                <button
                  key={u.id}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50"
                  onClick={() => selectUser(u)}
                >
                  <span className="font-medium">{u.display_name}</span>
                  <span className="text-gray-400 ml-2 text-xs">{u.email}</span>
                </button>
              ))}
            </div>
          )}
          {selectedUserId && (
            <button
              onClick={clearUserFilter}
              className="mt-1 text-xs text-gray-500 underline"
            >
              {t('history.showAll')}
            </button>
          )}
        </div>
      )}

      {/* Filter bar */}
      <div className="space-y-2">
        {/* Period pills */}
        <div className="flex gap-2 flex-wrap">
          {[
            { key: 'all', label: t('history.filterAll') },
            { key: '30', label: t('history.filter30days') },
            { key: '90', label: t('history.filter90days') },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setPeriod(key)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                period === key
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Club + Tee dropdowns */}
        {(clubs.length > 0 || tees.length > 0) && (
          <div className="flex gap-2 flex-wrap">
            {clubs.length > 0 && (
              <select
                value={filterClub}
                onChange={e => setFilterClub(e.target.value)}
                className="border rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
              >
                <option value="">{t('history.allClubs')}</option>
                {clubs.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            )}
            {tees.length > 0 && (
              <select
                value={filterTee}
                onChange={e => setFilterTee(e.target.value)}
                className="border rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
              >
                <option value="">{t('history.allTees')}</option>
                {tees.map(te => (
                  <option key={te} value={te}>{te}</option>
                ))}
              </select>
            )}
          </div>
        )}
      </div>

      {/* Chart */}
      <HandicapHistoryChart rounds={filteredRounds} locale={locale} />

      {/* Round cards */}
      {filteredRounds.length === 0 && (
        <p className="text-gray-500">{t('history.empty')}</p>
      )}
      {filteredRounds.map(r => (
        <div key={r.id} className="relative">
          <Link
            to={`/round/${r.id}`}
            className="block bg-white border rounded-xl p-4 shadow-sm hover:border-green-400 pr-12"
          >
            <div className="flex justify-between">
              <span className="font-semibold">
                {r.club_name ? `${r.club_name} · ${r.course_name}` : r.course_name}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded ${r.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                {r.status === 'active' ? t('history.active') : t('history.finished')}
              </span>
            </div>
            {isAdmin && r.player_name && (
              <div className="text-xs text-green-700 mt-0.5 font-medium">{r.player_name}</div>
            )}
            <div className="text-sm text-gray-500 mt-1">
              {t('history.handicap')} {r.hcp_index}{r.projected_hcp != null
                ? <>
                    {' · '}{t('history.playedTo')} {r.projected_hcp}
                    {r.projected_hcp < r.hcp_index
                      ? <span className="text-green-500">↓</span>
                      : r.projected_hcp > r.hcp_index
                      ? <span className="text-red-500">↑</span>
                      : null}
                  </>
                : null}{' · '}{new Date(r.started_at).toLocaleDateString(langTag)}
            </div>
          </Link>
          <button
            onClick={e => deleteRound(e, r.id)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-red-400 hover:text-red-600 text-xs px-2 py-1"
            title={t('history.delete')}
          >
            {t('history.delete')}
          </button>
        </div>
      ))}
    </div>
  )
}
