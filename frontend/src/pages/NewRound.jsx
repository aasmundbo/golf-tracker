import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api/client'
import TeeSelector from '../components/TeeSelector'
import FieldHint from '../components/FieldHint'
import { parseDecimal, formatDecimal } from '../utils/formatters'

export default function NewRound() {
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage === 'nb' ? 'nb' : 'en'
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [courseDetail, setCourseDetail] = useState(null)
  const [selectedTee, setSelectedTee] = useState(null)
  const [hcp, setHcp] = useState('')
  const [defaultHcp, setDefaultHcp] = useState(null)
  const [preferredTeeGender, setPreferredTeeGender] = useState(null)
  const [playingHcp, setPlayingHcp] = useState(null)
  const [manualMode, setManualMode] = useState(false)
  const [manualData, setManualData] = useState({
    club_name: '', city: '', country: '', course_name: 'Hovedbane', tee_name: '', tee_gender: '', par_total: '', slope: '', course_rating: '', hcp_index: ''
  })
  const [loading, setLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [recentCourses, setRecentCourses] = useState([])
  const [activeRounds, setActiveRounds] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/rounds/recent-courses').then(r => setRecentCourses(r.data)).catch(() => {})
    api.get('/rounds').then(r => setActiveRounds((r.data || []).filter(x => x.status === 'active'))).catch(() => {})
  }, [])

  useEffect(() => {
    api.get('/users/me').then(r => {
      const val = r.data.default_hcp_index
      if (val != null) {
        setDefaultHcp(val)
        setHcp(prev => prev === '' ? formatDecimal(val, locale) : prev)
        setManualData(prev => ({ ...prev, hcp_index: prev.hcp_index === '' ? formatDecimal(val, locale) : prev.hcp_index }))
      }
      setPreferredTeeGender(r.data.preferred_tee_gender ?? null)
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
    const slope = tee.slope_rating || tee.slope
    if (!slope) return
    const ph = Math.round(
      parseDecimal(hcpVal) * (slope / 113) + (tee.course_rating - (tee.par_total || 72))
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
          tee_name: manualData.tee_name || undefined,
          tee_gender: manualData.tee_gender || undefined,
          par_total: manualData.par_total ? parseInt(manualData.par_total) : undefined,
          city: manualData.city || undefined,
          country: manualData.country || undefined,
          slope: parseDecimal(manualData.slope),
          course_rating: parseDecimal(manualData.course_rating),
          hcp_index: parseDecimal(manualData.hcp_index),
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
          hcp_index: parseDecimal(hcp),
        }
      }
      const res = await api.post('/rounds', payload)
      const usedHcp = parseDecimal(manualMode ? manualData.hcp_index : hcp)
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

  const field = (key, inputProps = {}) => (
    <div key={key}>
      <label className="block text-sm font-medium">
        {t(`newRound.manualLabels.${key}`)}
        <FieldHint text={t(`newRound.manualHints.${key}`)} />
      </label>
      <input
        className="border rounded px-3 py-2 w-full"
        value={manualData[key]}
        onChange={e => setManualData(d => ({ ...d, [key]: e.target.value }))}
        {...inputProps}
      />
    </div>
  )

  if (manualMode) {
    return (
      <div className="space-y-4 mt-6">
        <h2 className="text-xl font-bold">{t('newRound.startWithoutDataTitle')}</h2>

        {field('club_name')}

        <div className="grid grid-cols-2 gap-3">
          {field('city')}
          {field('country')}
        </div>

        {field('course_name')}

        <div className="grid grid-cols-2 gap-3">
          {field('tee_name')}
          <div>
            <label className="block text-sm font-medium">{t('newRound.manualLabels.tee_gender')}</label>
            <select
              className="border rounded px-3 py-2 w-full bg-white"
              value={manualData.tee_gender}
              onChange={e => setManualData(d => ({ ...d, tee_gender: e.target.value }))}
            >
              <option value="">—</option>
              <option value="herre">{t('common.genderMale')}</option>
              <option value="dame">{t('common.genderFemale')}</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 items-end">
          {field('slope', { type: 'text', inputMode: 'decimal' })}
          {field('course_rating', { type: 'text', inputMode: 'decimal' })}
          {field('par_total', { type: 'number', inputMode: 'numeric', min: '1' })}
        </div>

        {field('hcp_index', { type: 'text', inputMode: 'decimal' })}

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
      {activeRounds.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            {t('newRound.activeRounds')}
          </h3>
          {activeRounds.map(round => (
            <button
              key={round.id}
              onClick={() => navigate(`/round/${round.id}`)}
              className="w-full text-left bg-green-50 border border-green-200 rounded-xl px-4 py-3 hover:bg-green-100 active:bg-green-200 transition-colors flex justify-between items-center"
            >
              <div>
                <div className="font-medium text-sm">
                  {round.club_name ? `${round.club_name} · ${round.course_name}` : round.course_name}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {round.tee_name && <span>{round.tee_name} · </span>}
                  {t('activeRound.exactHandicap')} {formatDecimal(round.hcp_index, locale)}
                </div>
              </div>
              <span className="text-xs text-green-700 font-medium">{t('newRound.resumeRound')} →</span>
            </button>
          ))}
        </div>
      )}
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
          preferredGender={preferredTeeGender}
          onSelect={tee => { setSelectedTee(tee); calcPlayingHcp(tee, hcp) }}
        />
      )}
      {selectedTee && (
        <div>
          <label className="block text-sm font-medium">{t('newRound.yourHandicap')}</label>
          <input
            type="text"
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
              <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                {course.tee_name && (
                  <span className="text-xs text-gray-400">{course.tee_name}</span>
                )}
                {course.tee_gender === 'herre' && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full border border-blue-300 bg-blue-50 text-blue-700 font-medium">{t('common.genderMale')}</span>
                )}
                {course.tee_gender === 'dame' && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full border border-pink-300 bg-pink-50 text-pink-700 font-medium">{t('common.genderFemale')}</span>
                )}
                {(course.slope || course.course_rating || course.par_total) && (
                  <span className="text-xs text-gray-400">
                    {course.tee_name ? '· ' : ''}
                    {course.slope && `SR ${formatDecimal(course.slope, locale)}`}
                    {course.course_rating && ` / CR ${formatDecimal(course.course_rating, locale)}`}
                    {course.par_total && ` / Par ${course.par_total}`}
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
