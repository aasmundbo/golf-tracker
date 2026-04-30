import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api/client'

export default function History() {
  const { t, i18n } = useTranslation()
  const [rounds, setRounds] = useState([])

  const loadRounds = () =>
    api.get('/rounds').then(r => setRounds(r.data)).catch(() => {})

  useEffect(() => { loadRounds() }, [])

  const deleteRound = async (e, id) => {
    e.preventDefault()
    if (!confirm(t('history.confirmDelete'))) return
    await api.delete(`/rounds/${id}`)
    loadRounds()
  }

  return (
    <div className="space-y-3 mt-6">
      <h2 className="text-xl font-bold">{t('history.title')}</h2>
      {rounds.length === 0 && <p className="text-gray-500">{t('history.empty')}</p>}
      {rounds.map(r => (
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
            <div className="text-sm text-gray-500 mt-1">
              {t('history.exactHandicap')} {r.hcp_index} · {t('history.playingHandicap')} {r.playing_handicap} · {new Date(r.started_at).toLocaleDateString(i18n.resolvedLanguage === 'nb' ? 'nb-NO' : 'en-GB')}
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
