import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import api from '../api/client'
import HoleCard from '../components/HoleCard'
import LiveStats from '../components/LiveStats'
import HoleDataPrompt from '../components/HoleDataPrompt'
import Scorecard from '../components/Scorecard'

export default function ActiveRound() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [round, setRound] = useState(null)
  const [stats, setStats] = useState(null)
  const [scores, setScores] = useState({})
  const [holeData, setHoleData] = useState({})
  const [currentHole, setCurrentHole] = useState(1)
  const [holeDataNeeded, setHoleDataNeeded] = useState(null)
  const [showScorecard, setShowScorecard] = useState(false)
  const [projection, setProjection] = useState(null)
  const [showMenu, setShowMenu] = useState(false)
  const menuRef = useRef(null)
  const totalHoles = 18

  useEffect(() => { loadRound() }, [id])

  useEffect(() => {
    if (!showMenu) return
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [showMenu])

  const loadRound = async () => {
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
  }

  const submitScore = async (holeNumber, strokes, holePar, holeStrokeIndex) => {
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
  }

  const finishRound = async () => {
    await api.put(`/rounds/${id}/finish`)
    navigate('/history')
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
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-bold text-lg">{courseLine}</h2>
          <p className="text-sm text-gray-500">
            {round.tee_name} · {t('activeRound.exactHandicap')} {round.hcp_index} → {t('activeRound.playingHandicap')} {round.playing_handicap}
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
        {Array.from({ length: totalHoles }, (_, i) => i + 1).map(h => (
          <button
            key={h}
            onClick={() => setCurrentHole(h)}
            className={`w-8 h-8 rounded text-sm font-medium ${
              scores[h]
                ? 'bg-green-600 text-white'
                : h === currentHole
                ? 'bg-green-100 border-2 border-green-600'
                : 'bg-gray-100'
            }`}
          >
            {h}
          </button>
        ))}
      </div>

      {round.status === 'active' && (
        <div className="flex items-center gap-2">
          {Object.keys(scores).length > 0 && (
            <button
              onClick={finishRound}
              className="flex-1 bg-gray-800 text-white py-2 rounded font-semibold"
            >
              {t('activeRound.finishRound')}
            </button>
          )}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowMenu(v => !v)}
              className="w-10 h-10 flex items-center justify-center rounded border border-gray-300 text-gray-600 text-lg"
            >
              ⋯
            </button>
            {showMenu && (
              <div className="absolute right-0 bottom-full mb-1 bg-white border rounded shadow-lg min-w-[130px]">
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
