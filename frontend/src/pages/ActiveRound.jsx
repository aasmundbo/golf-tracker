import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api/client'
import HoleCard from '../components/HoleCard'
import LiveStats from '../components/LiveStats'
import HoleDataPrompt from '../components/HoleDataPrompt'
import Scorecard, { ScoreIndicator } from '../components/Scorecard'
import { formatDecimal } from '../utils/formatters'

export default function ActiveRound() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage === 'nb' ? 'nb' : 'en'
  const [round, setRound] = useState(null)
  const [stats, setStats] = useState(null)
  const [scores, setScores] = useState({})
  const [holeData, setHoleData] = useState({})
  const [currentHole, setCurrentHole] = useState(1)
  const [holeDataNeeded, setHoleDataNeeded] = useState(null)
  const [showScorecard, setShowScorecard] = useState(false)
  const [projection, setProjection] = useState(null)
  const [showMenu, setShowMenu] = useState(false)
  const [showHcpEdit, setShowHcpEdit] = useState(false)
  const [newHcp, setNewHcp] = useState('')
  const [hcpSaving, setHcpSaving] = useState(false)
  const [error, setError] = useState(null)
  const [scoreDisplay, setScoreDisplay] = useState('netto')
  const menuRef = useRef(null)
  const totalHoles = 18

  useEffect(() => {
    loadRound()
    api.get('/users/me').then(res => setScoreDisplay(res.data.score_display ?? 'netto')).catch(() => {})
  }, [id])

  useEffect(() => {
    if (!showMenu) return
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [showMenu])

  const loadRound = async () => {
    try {
      setError(null)
      const [roundRes, liveRes, projRes] = await Promise.all([
        api.get(`/rounds/${id}`),
        api.get(`/rounds/${id}/live`),
        api.get(`/rounds/${id}/projected_handicap`),
      ])
      const roundData = roundRes.data

      let newHoleData = {}
      if (roundData.tee_id) {
        try {
          const holesRes = await api.get(`/courses/local/tees/${roundData.tee_id}/holes`)
          holesRes.data.forEach(h => { newHoleData[h.hole_number] = h })
        } catch {}
      }

      setRound(roundData)
      setStats(liveRes.data)
      setProjection(projRes.data)
      setHoleData(newHoleData)
      const scoreMap = {}
      ;(roundData.scores || []).forEach(s => { scoreMap[s.hole_number] = s })
      setScores(scoreMap)
      for (let h = 1; h <= totalHoles; h++) {
        if (!scoreMap[h]) { setCurrentHole(h); break }
      }
    } catch (err) {
      setError(t('activeRound.somethingWentWrong'))
    }
  }

  const submitScore = async (holeNumber, strokes, holePar, holeStrokeIndex) => {
    try {
      setError(null)
      const existing = scores[holeNumber]
      if (existing) {
        await api.put(`/rounds/${id}/scores/${holeNumber}`, {
          strokes, hole_par: holePar, hole_stroke_index: holeStrokeIndex,
        })
      } else {
        await api.post(`/rounds/${id}/scores`, {
          hole_number: holeNumber, strokes, hole_par: holePar, hole_stroke_index: holeStrokeIndex,
        })
      }
      await loadRound()
      if (holeNumber < totalHoles) setCurrentHole(holeNumber + 1)
    } catch (err) {
      setError(t('activeRound.somethingWentWrong'))
    }
  }

  const finishRound = async () => {
    await api.put(`/rounds/${id}/finish`)
    navigate('/history')
  }

  const saveHcp = async () => {
    const val = parseFloat(newHcp)
    if (isNaN(val)) return
    setHcpSaving(true)
    try {
      await Promise.all([
        api.patch(`/rounds/${id}/hcp`, { hcp_index: val }),
        api.patch('/users/me', { default_hcp_index: val }),
      ])
      setShowHcpEdit(false)
      setNewHcp('')
      await loadRound()
    } catch {
      setError(t('activeRound.somethingWentWrong'))
    } finally {
      setHcpSaving(false)
    }
  }

  const deleteRound = async () => {
    if (!confirm(t('activeRound.confirmDelete'))) return
    await api.delete(`/rounds/${id}`)
    navigate('/')
  }

  const resolveHoleScore = (holeNumber) => {
    const score = scores[holeNumber]
    if (score) return score
    const stored = holeData[holeNumber]
    if (stored?.par && stored?.stroke_index) {
      return { hole_par: stored.par, hole_stroke_index: stored.stroke_index }
    }
    return undefined
  }

  if (!round) return <div className="mt-8 text-center">{t('activeRound.loading')}</div>

  const courseLine = round.club_name
    ? `${round.club_name} · ${round.course_name}`
    : round.course_name

  const resolvedScore = resolveHoleScore(currentHole)

  return (
    <div className="space-y-4 mt-4">
      {error && (
        <div className="bg-red-50 border border-red-300 text-red-700 rounded px-4 py-2 text-sm">
          {error}
        </div>
      )}

      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-bold text-lg">{courseLine}</h2>
          <p className="text-sm text-gray-500">
            {round.tee_name} · {t('activeRound.exactHandicap')} {formatDecimal(round.hcp_index, locale)} → {t('activeRound.playingHandicap')} {round.playing_handicap}
          </p>
        </div>
        <button
          onClick={() => setShowScorecard(!showScorecard)}
          className="text-sm text-green-700 underline"
        >
          {showScorecard ? t('activeRound.hideScorecard') : t('activeRound.showScorecard')}
        </button>
      </div>

      {stats && <LiveStats stats={stats} projection={projection} hcpIndex={round.hcp_index} />}

      {showScorecard && (
        <Scorecard
          scores={scores}
          totalHoles={totalHoles}
          projection={projection}
          hcpIndex={round.hcp_index}
          playingHandicap={round.playing_handicap}
          scoreDisplay={scoreDisplay}
        />
      )}

      <HoleCard
        holeNumber={currentHole}
        existingScore={resolvedScore}
        playingHandicap={round.playing_handicap}
        onSubmit={(strokes, par, si) => {
          if (!par || !si) {
            setHoleDataNeeded({ holeNumber: currentHole, strokes })
          } else {
            submitScore(currentHole, strokes, par, si)
          }
        }}
      />

      {holeDataNeeded && (
        <HoleDataPrompt
          holeNumber={holeDataNeeded.holeNumber}
          onSubmit={(par, si) => {
            submitScore(holeDataNeeded.holeNumber, holeDataNeeded.strokes, par, si)
            setHoleDataNeeded(null)
          }}
          onCancel={() => setHoleDataNeeded(null)}
        />
      )}

      <div className="flex gap-2 flex-wrap">
        {Array.from({ length: totalHoles }, (_, i) => i + 1).map(h => {
          const s = scores[h]
          return (
            <button
              key={h}
              onClick={() => setCurrentHole(h)}
              className={`w-8 h-8 flex items-center justify-center rounded text-sm font-medium ${
                s && h === currentHole ? 'bg-green-600 text-white ring-2 ring-green-600'
                : s ? 'bg-green-600 text-white'
                : h === currentHole ? 'bg-gray-100 border-2 border-green-600'
                : 'bg-gray-100'
              }`}
            >
              {s ? (
                <ScoreIndicator
                  gross={s.strokes}
                  par={s.hole_par}
                  si={s.hole_stroke_index}
                  playingHcp={round.playing_handicap}
                  scoreDisplay={scoreDisplay}
                />
              ) : h}
            </button>
          )
        })}
      </div>

      {showHcpEdit && (
        <div className="bg-gray-50 border rounded p-3 flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700">{t('newRound.yourHandicap')}</label>
          <input
            type="number"
            step="0.1"
            value={newHcp}
            onChange={e => setNewHcp(e.target.value)}
            className="border rounded px-3 py-1.5 text-sm w-full"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              onClick={saveHcp}
              disabled={hcpSaving}
              className="flex-1 bg-gray-800 text-white py-1.5 rounded text-sm disabled:opacity-50"
            >
              {hcpSaving ? '…' : t('activeRound.saveHandicap')}
            </button>
            <button
              onClick={() => { setShowHcpEdit(false); setNewHcp('') }}
              className="px-3 py-1.5 rounded border text-sm text-gray-600"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {round.status === 'active' && (
        <div className="flex items-center gap-2">
          <button
            onClick={finishRound}
            disabled={Object.keys(scores).length === 0}
            className="flex-1 bg-gray-800 text-white py-2 rounded font-semibold disabled:opacity-40"
          >
            {t('activeRound.finishRound')}
          </button>
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowMenu(v => !v)}
              className="w-10 h-10 flex items-center justify-center rounded border border-gray-300 text-gray-600 text-lg"
            >
              ⋯
            </button>
            {showMenu && (
              <div className="absolute right-0 bottom-full mb-1 bg-white border rounded shadow-lg min-w-[160px]">
                <button
                  onClick={() => { setShowMenu(false); setNewHcp(round.hcp_index != null ? String(round.hcp_index) : ''); setShowHcpEdit(true) }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  {t('activeRound.changeHandicap')}
                </button>
                <button
                  onClick={() => { setShowMenu(false); deleteRound() }}
                  className="w-full text-left px-4 py-2 text-sm text-red-500 hover:bg-red-50"
                >
                  {t('activeRound.deleteRound')}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
