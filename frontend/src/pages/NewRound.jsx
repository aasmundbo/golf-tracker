import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api/client'
import TeeSelector from '../components/TeeSelector'

export default function NewRound() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [courseDetail, setCourseDetail] = useState(null)
  const [selectedTee, setSelectedTee] = useState(null)
  const [hcp, setHcp] = useState('')
  const [defaultHcp, setDefaultHcp] = useState(null)
  const [playingHcp, setPlayingHcp] = useState(null)
  const [manualMode, setManualMode] = useState(false)
  const [manualData, setManualData] = useState({
    club_name: '', course_name: 'Hovedbane', slope: '', course_rating: '', hcp_index: ''
  })
  const [loading, setLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [recentCourses, setRecentCourses] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/rounds/recent-courses').then(r => setRecentCourses(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    api.get('/users/me').then(r => {
      const val = r.data.default_hcp_index
      if (val != null) {
        setDefaultHcp(val)
        setHcp(prev => prev === '' ? String(val) : prev)
      }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!query || query.length < 2) { setResults([]); setHasSearched(false); setSearchLoading(false); return }
    const timer = setTimeout(async () => {
      setSearchLoading(true)
      try {
        const res = await api.get(`/courses/search?q=${encodeURIComponent(query)}`)
        setResults(res.data)
        setHasSearched(true)
      } catch {}
      setSearchLoading(false)
    }, 400)
    return () => clearTimeout(timer)
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

  const selectRecentCourse = (course) => {
    const label = course.club_name
      ? `${course.club_name} — ${course.course_name}`
      : (course.course_name || '')
    setQuery(label)
    setResults([])
    setCourseDetail(null)
    const tee = {
      id: course.tee_id,
      name: course.tee_name,
      slope: course.slope,
      course_rating: course.course_rating,
      par_total: course.par_total,
    }
    setSelectedTee(tee)
    setSelected({ source: 'local', club_name: course.club_name, name: course.course_name })
    calcPlayingHcp(tee, hcp)
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
          tee_id: selectedTee?.id ?? null,
          slope: selectedTee?.slope_rating || selectedTee?.slope,
          course_rating: selectedTee?.course_rating,
          par_total: selectedTee?.par_total,
          hcp_index: parseFloat(hcp),
        }
      }
      const res = await api.post('/rounds', payload)
      const usedHcp = parseFloat(manualMode ? manualData.hcp_index : hcp)
      if (!isNaN(usedHcp) && usedHcp !== defaultHcp) {
        api.patch('/users/me', { default_hcp_index: usedHcp }).catch(() => {})
      }
      navigate(`/round/${res.data.id}`)
    } catch {
      alert(t('newRound.failedToStart'))
    } finally {
      setLoading(false)
    }
  }

  const MANUAL_FIELDS = ['club_name', 'course_name', 'slope', 'course_rating', 'hcp_index']

  if (manualMode) {
    return (
      <div className="space-y-4 mt-6">
        <h2 className="text-xl font-bold">{t('newRound.startWithoutDataTitle')}</h2>
        {MANUAL_FIELDS.map(f => {
          const isDecimal = ['slope', 'course_rating', 'hcp_index'].includes(f)
          const isNumeric = isDecimal || f === 'hcp_index'
          return (
            <div key={f}>
              <label className="block text-sm font-medium">{t(`newRound.manualLabels.${f}`)}</label>
              <input
                className="border rounded px-3 py-2 w-full"
                value={manualData[f]}
                onChange={e => setManualData(d => ({ ...d, [f]: e.target.value }))}
                {...(isNumeric ? { inputMode: isDecimal ? 'decimal' : 'numeric', pattern: '[0-9]*' } : {})}
              />
            </div>
          )
        })}
        <button
          onClick={startRound}
          disabled={loading}
          className="bg-green-700 text-white px-6 py-2 rounded w-full font-semibold"
        >
          {loading ? t('newRound.starting') : t('newRound.startRound')}
        </button>
        <button onClick={() => setManualMode(false)} className="text-sm text-gray-500 underline">
          {t('newRound.backToSearch')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4 mt-6">
      <h2 className="text-xl font-bold">{t('newRound.title')}</h2>
      <input
        className="border rounded px-3 py-2 w-full"
        placeholder={t('newRound.searchPlaceholder')}
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
      {hasSearched && !searchLoading && results.length === 0 && !selected && (
        <div className="text-sm text-gray-500 space-y-1 px-1">
          <p>{t('search.noResults')}</p>
          <button
            onClick={() => navigate('/courses')}
            className="text-green-700 underline"
          >
            {t('search.addManually')}
          </button>
        </div>
      )}
      {courseDetail && (
        <TeeSelector
          courseDetail={courseDetail}
          onSelect={tee => { setSelectedTee(tee); calcPlayingHcp(tee, hcp) }}
        />
      )}
      {selectedTee && (
        <div>
          <label className="block text-sm font-medium">{t('newRound.yourHandicap')}</label>
          <input
            type="number"
            step="0.1"
            inputMode="decimal"
            className="border rounded px-3 py-2 w-full"
            value={hcp}
            onChange={e => { setHcp(e.target.value); calcPlayingHcp(selectedTee, e.target.value) }}
          />
          {playingHcp !== null && (
            <p className="text-sm text-green-700 mt-1">
              {t('newRound.playingHandicap')}: <strong>{playingHcp}</strong>
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
          {loading ? t('newRound.starting') : t('newRound.startRound')}
        </button>
      )}
      <button onClick={() => setManualMode(true)} className="text-sm text-gray-500 underline">
        {t('newRound.startWithoutData')}
      </button>
      {recentCourses.length > 0 && (
        <div className="space-y-2 pt-2">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            {t('newRound.recentlyPlayed')}
          </h3>
          {recentCourses.map((course, i) => (
            <button
              key={i}
              onClick={() => selectRecentCourse(course)}
              className="w-full text-left bg-white border rounded-xl px-4 py-3 hover:bg-green-50 active:bg-green-100 transition-colors"
            >
              <div className="font-medium text-sm">
                {course.club_name || course.course_name}
              </div>
              {course.club_name && course.course_name !== course.club_name && (
                <div className="text-xs text-gray-500">{course.course_name}</div>
              )}
              <div className="text-xs text-gray-400 mt-0.5">
                {course.tee_name && <span>{course.tee_name} · </span>}
                {course.slope && <span>SR {course.slope}</span>}
                {course.course_rating && <span> / CR {course.course_rating}</span>}
                {course.par_total && <span> / Par {course.par_total}</span>}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
