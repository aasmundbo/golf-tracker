import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../api/client'

// ── Users tab ──────────────────────────────────────────────────────────────

function daysSince(isoStr) {
  if (!isoStr) return null
  const ms = Date.now() - new Date(isoStr).getTime()
  return Math.floor(ms / 86400000)
}

function UsersTab() {
  const { t } = useTranslation()
  const [users, setUsers] = useState([])
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [filteredIds, setFilteredIds] = useState(null)
  const [sortAsc, setSortAsc] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const dropdownRef = useRef(null)

  const fetchUsers = useCallback(() => {
    setLoading(true)
    setError(null)
    api.get('/users')
      .then(res => setUsers(res.data))
      .catch(() => setError(t('admin.error')))
      .finally(() => setLoading(false))
  }, [t])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  useEffect(() => {
    if (!query || query.length < 1) { setSuggestions([]); return }
    const timer = setTimeout(async () => {
      try {
        const res = await api.get(`/users?search=${encodeURIComponent(query)}`)
        setSuggestions(res.data)
      } catch { setSuggestions([]) }
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (!suggestions.length) return
    const handler = e => {
      if (!dropdownRef.current?.contains(e.target) && !inputRef.current?.contains(e.target)) {
        setSuggestions([])
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [suggestions.length])

  const selectSuggestion = (s) => {
    setQuery(s.display_name || s.name || s.email)
    setSuggestions([])
    setFilteredIds([s.id])
  }

  const clearSearch = () => {
    setQuery('')
    setSuggestions([])
    setFilteredIds(null)
  }

  const handleDelete = async (user) => {
    if (!window.confirm(t('admin.confirmDelete'))) return
    try {
      await api.delete(`/users/${user.id}`)
      fetchUsers()
      if (filteredIds) clearSearch()
    } catch {
      alert(t('admin.deleteError'))
    }
  }

  const sorted = [...users].sort((a, b) => {
    const da = a.last_login_at ? new Date(a.last_login_at).getTime() : 0
    const db_ = b.last_login_at ? new Date(b.last_login_at).getTime() : 0
    return sortAsc ? da - db_ : db_ - da
  })

  const visibleUsers = filteredIds
    ? sorted.filter(u => filteredIds.includes(u.id))
    : sorted

  return (
    <div className="space-y-3">
      <div className="relative">
        <input
          ref={inputRef}
          className="border rounded px-3 py-2 w-full"
          placeholder={t('admin.searchUsers')}
          value={query}
          onChange={e => { setQuery(e.target.value); setFilteredIds(null) }}
        />
        {query && (
          <button
            onClick={clearSearch}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg leading-none"
          >x</button>
        )}
        {suggestions.length > 0 && (
          <ul ref={dropdownRef} className="absolute z-10 left-0 right-0 top-full mt-1 border rounded divide-y bg-white shadow">
            {suggestions.map(s => (
              <li
                key={s.id}
                className="px-3 py-2 cursor-pointer hover:bg-green-50"
                onMouseDown={() => selectSuggestion(s)}
              >
                <span className="font-medium">{s.display_name || s.name}</span>
                <span className="text-sm text-gray-500 ml-2">{s.email}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {!loading && !error && users.length > 0 && (
        <div className="flex justify-end">
          <button
            onClick={() => setSortAsc(v => !v)}
            className="text-xs text-gray-500 hover:text-gray-800 underline"
          >
            {sortAsc ? t('admin.sortMostRecent') : t('admin.sortLeastRecent')}
          </button>
        </div>
      )}

      {loading && <p className="text-gray-500 text-sm">{t('activeRound.loading')}</p>}
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {!loading && !error && visibleUsers.length === 0 && (
        <p className="text-gray-500 text-sm">{t('admin.noUsers')}</p>
      )}
      {!loading && !error && visibleUsers.length > 0 && (
        <ul className="space-y-2">
          {visibleUsers.map(user => (
            <UserCard
              key={user.id}
              user={user}
              onDelete={handleDelete}
              onSave={u => { setUsers(prev => prev.map(x => x.id === u.id ? { ...x, ...u } : x)) }}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

function UserCard({ user, onDelete, onSave }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    name: user.name || '',
    preferred_language: user.preferred_language || 'nb',
    score_display: user.score_display || 'netto',
    default_hcp_index: user.default_hcp_index != null ? String(user.default_hcp_index) : '',
    preferred_tee_gender: user.preferred_tee_gender || '',
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const days = daysSince(user.last_login_at)

  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = {
        name: form.name || undefined,
        preferred_language: form.preferred_language || undefined,
        score_display: form.score_display || undefined,
        default_hcp_index: form.default_hcp_index !== '' ? parseFloat(form.default_hcp_index.replace(',', '.')) : undefined,
        preferred_tee_gender: form.preferred_tee_gender || null,
      }
      const res = await api.patch(`/users/${user.id}`, payload)
      onSave(res.data)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch { /* ignore */ }
    setSaving(false)
  }

  return (
    <li className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 active:bg-gray-100 transition-colors"
        onClick={() => setOpen(v => !v)}
      >
        <div>
          <p className="font-medium text-gray-900">{user.name || '—'}</p>
          <p className="text-sm text-gray-500">{user.email}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            <span className="capitalize">{user.role}</span>
            {days !== null
              ? <span className="ml-2">· {t('admin.daysAgo', { count: days })}</span>
              : <span className="ml-2">· {t('admin.neverActive')}</span>}
          </p>
        </div>
        <span className="text-gray-400 text-lg ml-2">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="border-t border-gray-100 px-4 py-3 space-y-3 bg-gray-50">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">{t('settings.name')}</label>
            <input className="border rounded px-3 py-1.5 w-full text-sm" value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">{t('settings.language')}</label>
              <select className="border rounded px-2 py-1.5 w-full text-sm bg-white"
                value={form.preferred_language}
                onChange={e => setForm(f => ({ ...f, preferred_language: e.target.value }))}>
                <option value="nb">Norsk</option>
                <option value="en">English</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">{t('settings.scoreDisplay')}</label>
              <select className="border rounded px-2 py-1.5 w-full text-sm bg-white"
                value={form.score_display}
                onChange={e => setForm(f => ({ ...f, score_display: e.target.value }))}>
                <option value="netto">Netto</option>
                <option value="brutto">Brutto</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">{t('settings.defaultHcp')}</label>
              <input className="border rounded px-3 py-1.5 w-full text-sm" type="text" inputMode="decimal"
                value={form.default_hcp_index}
                onChange={e => setForm(f => ({ ...f, default_hcp_index: e.target.value }))} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">{t('settings.teeGender')}</label>
              <select className="border rounded px-2 py-1.5 w-full text-sm bg-white"
                value={form.preferred_tee_gender}
                onChange={e => setForm(f => ({ ...f, preferred_tee_gender: e.target.value }))}>
                <option value="">{t('settings.teeGenderNone')}</option>
                <option value="herre">Herre</option>
                <option value="dame">Dame</option>
              </select>
            </div>
          </div>
          <div className="flex items-center justify-between pt-1">
            {user.role !== 'admin' && (
              <button onClick={() => onDelete(user)}
                className="text-sm text-red-600 hover:text-red-800 font-medium">
                {t('admin.delete')}
              </button>
            )}
            <button
              onClick={handleSave}
              disabled={saving}
              className="ml-auto bg-green-700 text-white px-4 py-1.5 rounded text-sm font-medium disabled:opacity-50"
            >
              {saved ? t('settings.saved') : saving ? t('settings.saving') : t('settings.save')}
            </button>
          </div>
        </div>
      )}
    </li>
  )
}
// ── Stats tab ──────────────────────────────────────────────────────────────

const SOURCE_LABELS = {
  local: 'admin.sourceLocal',
  api: 'admin.sourceApi',
  on_the_fly: 'admin.sourceOnTheFly',
}

function RankedList({ items, nameKey, subKey, countKey }) {
  const max = items[0]?.[countKey] || 1
  return (
    <ul className="bg-white border rounded-xl divide-y">
      {items.map((item, i) => (
        <li key={i} className="flex items-center gap-3 px-4 py-2.5">
          <span className="text-xs text-gray-400 w-4 text-right shrink-0">{i + 1}</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{item[nameKey]}</p>
            {subKey && item[subKey] && <p className="text-xs text-gray-500">{item[subKey]}</p>}
          </div>
          <div className="w-12 shrink-0">
            <div className="bg-gray-100 rounded-full h-1">
              <div
                className="bg-green-700 h-1 rounded-full"
                style={{ width: `${Math.round(item[countKey] / max * 100)}%` }}
              />
            </div>
          </div>
          <span className="text-sm text-gray-600 shrink-0 w-8 text-right">{item[countKey]}</span>
        </li>
      ))}
    </ul>
  )
}

function StatsTab() {
  const { t } = useTranslation()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/admin/stats')
      .then(r => setStats(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-gray-500 text-sm">{t('activeRound.loading')}</p>
  if (!stats) return <p className="text-red-600 text-sm">{t('admin.error')}</p>

  const topCourses = stats.top_courses.map(c => ({
    name: [c.club_name, c.tee_name].filter(Boolean).join(' — '),
    sub: c.course_name || '',
    count: c.count,
  }))

  const topUsers = stats.top_users.map(u => ({
    name: u.name || u.email,
    sub: u.hcp_index != null ? `Hcp ${u.hcp_index}` : '',
    count: u.count,
  }))

  const sourceEntries = Object.entries(stats.rounds_by_source).sort((a, b) => b[1] - a[1])
  const sourceMax = sourceEntries[0]?.[1] || 1

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: t('admin.totalRounds'), value: stats.total_rounds },
          { label: t('admin.totalUsers'), value: stats.total_users },
          { label: t('admin.avgRoundsPerUser'), value: stats.avg_rounds_per_user },
          { label: t('admin.completionRate'), value: `${stats.completion_rate} %` },
        ].map(m => (
          <div key={m.label} className="bg-gray-50 rounded-xl px-4 py-3">
            <p className="text-xs text-gray-500 mb-1">{m.label}</p>
            <p className="text-2xl font-medium text-gray-900">{m.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-50 rounded-xl px-4 py-3 flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500">{t('admin.inactiveUsers')}</p>
          <p className="text-sm text-gray-400 mt-0.5">{t('admin.inactiveUsersDesc')}</p>
        </div>
        <p className="text-2xl font-medium text-gray-900">{stats.inactive_users}</p>
      </div>

      {topCourses.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            {t('admin.topCourses')}
          </h3>
          <RankedList items={topCourses} nameKey="name" subKey="sub" countKey="count" />
        </div>
      )}

      {topUsers.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            {t('admin.topUsers')}
          </h3>
          <RankedList items={topUsers} nameKey="name" subKey="sub" countKey="count" />
        </div>
      )}

      {sourceEntries.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            {t('admin.roundsBySource')}
          </h3>
          <ul className="bg-white border rounded-xl divide-y">
            {sourceEntries.map(([src, count]) => (
              <li key={src} className="flex items-center gap-3 px-4 py-2.5">
                <p className="flex-1 text-sm font-medium">{t(SOURCE_LABELS[src] || src)}</p>
                <div className="w-12 shrink-0">
                  <div className="bg-gray-100 rounded-full h-1">
                    <div
                      className="bg-green-700 h-1 rounded-full"
                      style={{ width: `${Math.round(count / sourceMax * 100)}%` }}
                    />
                  </div>
                </div>
                <span className="text-sm text-gray-600 shrink-0 w-8 text-right">{count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────

export default function Admin() {
  const { t } = useTranslation()
  const [tab, setTab] = useState('stats')

  return (
    <div className="py-4">
      <h1 className="text-xl font-bold text-gray-900 mb-4">{t('admin.title')}</h1>
      <div className="flex gap-2 mb-5">
        {['stats', 'users'].map(key => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-1.5 rounded-full text-sm border transition-colors ${
              tab === key
                ? 'bg-green-700 text-white border-green-700'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {t(`admin.tab_${key}`)}
          </button>
        ))}
      </div>
      {tab === 'stats' ? <StatsTab /> : <UsersTab />}
    </div>
  )
}
