import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import TeeSelector from '../components/TeeSelector'

export default function NewRound() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [courseDetail, setCourseDetail] = useState(null)
  const [selectedTee, setSelectedTee] = useState(null)
  const [hcp, setHcp] = useState('')
  const [playingHcp, setPlayingHcp] = useState(null)
  const [manualMode, setManualMode] = useState(false)
  const [manualData, setManualData] = useState({
    club_name: '', course_name: '', slope: '', course_rating: '', hcp_index: ''
  })
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!query || query.length < 2) { setResults([]); return }
    const t = setTimeout(async () => {
      try {
        const res = await api.get(`/courses/search?q=${encodeURIComponent(query)}`)
        setResults(res.data)
      } catch {}
    }, 400)
    return () => clearTimeout(t)
  }, [query])

  const selectCourse = async (course) => {
    setSelected(course)
    setResults([])
    const label = course.club_name
      ? `${course.club_name} — ${course.name}`
      : (course.name || '')
    setQuery(label)
    try {
      const res = await api.get(`/courses/${encodeURIComponent(course.id)}`)
      setCourseDetail(res.data)
    } catch { setCourseDetail(null) }
  }

  const calcPlayingHcp = (tee, hcpVal) => {
    if (!tee || !hcpVal) return
    const ph = Math.round(
      parseFloat(hcpVal) * (tee.slope / 113) + (tee.course_rating - (tee.par_total || 72))
    )
    setPlayingHcp(ph)
  }

  const startRound = async () => {
    setLoading(true)
    try {
      let payload
      if (manualMode) {
        payload = {
          course_source: 'on_the_fly',
          club_name: manualData.club_name,
          course_name: manualData.course_name || manualData.club_name,
          slope: parseFloat(manualData.slope),
          course_rating: parseFloat(manualData.course_rating),
          hcp_index: parseFloat(manualData.hcp_index),
        }
      } else {
        payload = {
          course_source: selected?.source || 'on_the_fly',
          club_name: selected?.club_name || '',
          course_name: selected?.name || '',
          tee_name: selectedTee?.tee_name || selectedTee?.name || '',
          slope: selectedTee?.slope_rating || selectedTee?.slope,
          course_rating: selectedTee?.course_rating,
          par_total: selectedTee?.par_total,
          hcp_index: parseFloat(hcp),
        }
      }
      const res = await api.post('/rounds', payload)
      navigate(`/round/${res.data.id}`)
    } catch {
      alert('Failed to start round')
    } finally {
      setLoading(false)
    }
  }

  const MANUAL_LABELS = {
    club_name: 'Bane',
    course_name: 'Banevariant (valgfritt)',
    slope: 'Slope',
    course_rating: 'Course rating',
    hcp_index: 'Eksakt handicap',
  }

  if (manualMode) {
    return (
      <div className="space-y-4 mt-6">
        <h2 className="text-xl font-bold">Start uten banedata</h2>
        {['club_name', 'course_name', 'slope', 'course_rating', 'hcp_index'].map(f => (
          <div key={f}>
            <label className="block text-sm font-medium">{MANUAL_LABELS[f]}</label>
            <input
              className="border rounded px-3 py-2 w-full"
              value={manualData[f]}
              onChange={e => setManualData(d => ({ ...d, [f]: e.target.value }))}
            />
          </div>
        ))}
        <button
          onClick={startRound}
          disabled={loading}
          className="bg-green-700 text-white px-6 py-2 rounded w-full font-semibold"
        >
          {loading ? 'Starter…' : 'Start runde'}
        </button>
        <button onClick={() => setManualMode(false)} className="text-sm text-gray-500 underline">
          Tilbake til søk
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4 mt-6">
      <h2 className="text-xl font-bold">Ny runde</h2>
      <input
        className="border rounded px-3 py-2 w-full"
        placeholder="Søk etter bane…"
        value={query}
        onChange={e => setQuery(e.target.value)}
      />
      {results.length > 0 && (
        <ul className="border rounded divide-y bg-white shadow">
          {results.map((r, i) => (
            <li
              key={i}
              className="px-3 py-2 cursor-pointer hover:bg-green-50"
              onClick={() => selectCourse(r)}
            >
              <span className="font-medium">
                {r.club_name ? `${r.club_name} — ${r.name}` : r.name}
              </span>
              {r.city && (
                <span className="text-sm text-gray-500 ml-2">
                  {r.city}{r.country ? `, ${r.country}` : ''}
                </span>
              )}
              <span className={`text-xs ml-2 px-1 rounded ${r.source === 'local' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100'}`}>
                {r.source}
              </span>
            </li>
          ))}
        </ul>
      )}
      {courseDetail && (
        <TeeSelector
          courseDetail={courseDetail}
          onSelect={tee => { setSelectedTee(tee); calcPlayingHcp(tee, hcp) }}
        />
      )}
      {selectedTee && (
        <div>
          <label className="block text-sm font-medium">Eksakt handicap</label>
          <input
            type="number"
            step="0.1"
            className="border rounded px-3 py-2 w-full"
            value={hcp}
            onChange={e => { setHcp(e.target.value); calcPlayingHcp(selectedTee, e.target.value) }}
          />
          {playingHcp !== null && (
            <p className="text-sm text-green-700 mt-1">
              Spillehandicap: <strong>{playingHcp}</strong>
            </p>
          )}
        </div>
      )}
      {selectedTee && hcp && (
        <button
          onClick={startRound}
          disabled={loading}
          className="bg-green-700 text-white px-6 py-2 rounded w-full font-semibold"
        >
          {loading ? 'Starter…' : 'Start runde'}
        </button>
      )}
      <button onClick={() => setManualMode(true)} className="text-sm text-gray-500 underline">
        Start uten banedata
      </button>
    </div>
  )
}
