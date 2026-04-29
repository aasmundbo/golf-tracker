import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'

export default function History() {
  const [rounds, setRounds] = useState([])

  const loadRounds = () =>
    api.get('/rounds').then(r => setRounds(r.data)).catch(() => {})

  useEffect(() => { loadRounds() }, [])

  const deleteRound = async (e, id) => {
    e.preventDefault()
    if (!confirm('Slett denne runden?')) return
    await api.delete(`/rounds/${id}`)
    loadRounds()
  }

  return (
    <div className="space-y-3 mt-6">
      <h2 className="text-xl font-bold">Rundehistorikk</h2>
      {rounds.length === 0 && <p className="text-gray-500">Ingen runder ennå.</p>}
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
                {r.status === 'active' ? 'Aktiv' : 'Ferdig'}
              </span>
            </div>
            <div className="text-sm text-gray-500 mt-1">
              Eksakt handicap {r.hcp_index} · Spillehandicap {r.playing_handicap} · {new Date(r.started_at).toLocaleDateString('nb-NO')}
            </div>
          </Link>
          <button
            onClick={e => deleteRound(e, r.id)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-red-400 hover:text-red-600 text-xs px-2 py-1"
            title="Slett runde"
          >
            Slett
          </button>
        </div>
      ))}
    </div>
  )
}
