import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../api/client'

export default function Admin() {
  const { t } = useTranslation()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchUsers = useCallback(() => {
    setLoading(true)
    setError(null)
    api.get('/users')
      .then(res => setUsers(res.data))
      .catch(() => setError(t('admin.error')))
      .finally(() => setLoading(false))
  }, [t])

  useEffect(() => { fetchUsers() }, [fetchUsers])

  const handleDelete = async (user) => {
    if (!window.confirm(t('admin.confirmDelete'))) return
    try {
      await api.delete(`/users/${user.id}`)
      fetchUsers()
    } catch {
      alert(t('admin.deleteError'))
    }
  }

  return (
    <div className="py-4">
      <h1 className="text-xl font-bold text-gray-900 mb-4">{t('admin.title')}</h1>

      {loading && (
        <p className="text-gray-500 text-sm">{t('activeRound.loading')}</p>
      )}

      {error && (
        <p className="text-red-600 text-sm">{error}</p>
      )}

      {!loading && !error && users.length === 0 && (
        <p className="text-gray-500 text-sm">{t('admin.noUsers')}</p>
      )}

      {!loading && !error && users.length > 0 && (
        <ul className="space-y-2">
          {users.map(user => (
            <li
              key={user.id}
              className="flex items-center justify-between bg-white rounded-lg border border-gray-200 px-4 py-3"
            >
              <div>
                <p className="font-medium text-gray-900">{user.name || '—'}</p>
                <p className="text-sm text-gray-500">{user.email}</p>
                <p className="text-xs text-gray-400 capitalize">{user.role}</p>
              </div>
              {user.role !== 'admin' && (
                <button
                  onClick={() => handleDelete(user)}
                  className="text-sm text-red-600 hover:text-red-800 font-medium"
                >
                  {t('admin.delete')}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
