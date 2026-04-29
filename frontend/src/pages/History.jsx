import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'

export default function History() {
  const [rounds, setRounds] = useState([])
  useEffect(() => {
    api.get('/rounds').then(r => setRounds(r.data)).catch(() => {})
  }, [])

  return (
    <div className="space-y-3 mt-6">
      <h2 className="text-xl font-bold">Round History</h2>
      {rounds.length === 0 && <p className="text-gray-500">No rounds yet.</p>}
      {rounds.map(r => (
        <Link key={r.id} to={`/round/${r.id}`}
          className="block bg-white border rounded-xl p-4 shadow-sm hover:border-green-400">
          <div className="flex justify-between">
            <span className="font-semibold">{r.course_name}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${r.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>{r.status}</span>
          </div>
          <div className="text-sm text-gray-500 mt-1">
            HCP {r.hcp_index} · Playing HCP {r.playing_handicap} · {new Date(r.started_at).toLocaleDateString()}
          </div>
        </Link>
      ))}
    </div>
  )
}
