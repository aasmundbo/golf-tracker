import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'
import HoleCard from '../components/HoleCard'
import LiveStats from '../components/LiveStats'
import HoleDataPrompt from '../components/HoleDataPrompt'
import Scorecard from '../components/Scorecard'

export default function ActiveRound() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [round, setRound] = useState(null)
  const [stats, setStats] = useState(null)
  const [scores, setScores] = useState({})
  const [holeData, setHoleData] = useState({}) // hole_number → {par, stroke_index} from local_holes
  const [currentHole, setCurrentHole] = useState(1)
  const [holeDataNeeded, setHoleDataNeeded] = useState(null)
  const [showScorecard, setShowScorecard] = useState(false)
  const totalHoles = 18

  useEffect(() => { loadRound() }, [id])

  // Fetch stored tee hole data once we know the tee_id
  useEffect(() => {
    if (!round?.tee_id) return
    api.get(`/courses/local/tees/${round.tee_id}/holes`)
      .then(res => {
        const map = {}
        res.data.forEach(h => { map[h.hole_number] = h })
        setHoleData(map)
      })
      .catch(() => {})
  }, [round?.tee_id])

  const loadRound = async () => {
    const [roundRes, liveRes] = await Promise.all([
      api.get(`/rounds/${id}`),
      api.get(`/rounds/${id}/live`)
    ])
    setRound(roundRes.data)
    setStats(liveRes.data)
    const scoreMap = {}
    ;(roundRes.data.scores || []).forEach(s => { scoreMap[s.hole_number] = s })
    setScores(scoreMap)
    for (let h = 1; h <= totalHoles; h++) {
      if (!scoreMap[h]) { setCurrentHole(h); break }
    }
  }

  const submitScore = async (holeNumber, strokes, holePar, holeStrokeIndex) => {
    const existing = scores[holeNumber]
    if (existing) {
      await api.put(`/rounds/${id}/scores/${holeNumber}`, { strokes, hole_par: holePar, hole_stroke_index: holeStrokeIndex })
    } else {
      await api.post(`/rounds/${id}/scores`, { hole_number: holeNumber, strokes, hole_par: holePar, hole_stroke_index: holeStrokeIndex })
    }
    await loadRound()
    if (holeNumber < totalHoles) setCurrentHole(holeNumber + 1)
  }

  const finishRound = async () => {
    await api.put(`/rounds/${id}/finish`)
    navigate('/history')
  }

  // Build the score object passed to HoleCard: existing score takes priority,
  // then fall back to par/SI from the stored local hole so HoleDataPrompt is skipped.
  const resolveHoleScore = (holeNumber) => {
    const score = scores[holeNumber]
    if (score) return score
    const stored = holeData[holeNumber]
    if (stored?.par && stored?.stroke_index) {
      return { hole_par: stored.par, hole_stroke_index: stored.stroke_index }
    }
    return undefined
  }

  if (!round) return <div className="mt-8 text-center">Loading…</div>

  const resolvedScore = resolveHoleScore(currentHole)

  return (
    <div className="space-y-4 mt-4">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-bold text-lg">{round.course_name}</h2>
          <p className="text-sm text-gray-500">{round.tee_name} · Eksakt handicap {round.hcp_index} → Spillehandicap {round.playing_handicap}</p>
        </div>
        <button onClick={() => setShowScorecard(!showScorecard)} className="text-sm text-green-700 underline">
          {showScorecard ? 'Hide' : 'Scorecard'}
        </button>
      </div>

      {stats && <LiveStats stats={stats} />}

      {showScorecard && <Scorecard scores={scores} totalHoles={totalHoles} />}

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
          <button key={h} onClick={() => setCurrentHole(h)}
            className={`w-8 h-8 rounded text-sm font-medium ${scores[h] ? 'bg-green-600 text-white' : h === currentHole ? 'bg-green-100 border-2 border-green-600' : 'bg-gray-100'}`}>
            {h}
          </button>
        ))}
      </div>

      {Object.keys(scores).length > 0 && round.status === 'active' && (
        <button onClick={finishRound} className="w-full bg-gray-800 text-white py-2 rounded font-semibold">
          Finish Round
        </button>
      )}
    </div>
  )
}
