import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export default function HoleCard({ holeNumber, existingScore, playingHandicap, onSubmit }) {
  const { t } = useTranslation()
  const [strokes, setStrokes] = useState(existingScore?.strokes || existingScore?.hole_par || 4)

  useEffect(() => {
    setStrokes(existingScore?.strokes || existingScore?.hole_par || 4)
  }, [holeNumber, existingScore])

  const par = existingScore?.hole_par
  const si = existingScore?.hole_stroke_index

  return (
    <div className="bg-white border rounded-xl p-4 shadow-sm">
      <div className="flex justify-between items-center mb-3">
        <span className="text-2xl font-bold text-green-700">{t('holeCard.hole')} {holeNumber}</span>
        {par && <span className="text-sm text-gray-500">{t('holeCard.par')} {par} · {t('holeCard.si')} {si}</span>}
      </div>
      <div className="flex items-center justify-center gap-6">
        <button onClick={() => setStrokes(s => Math.max(1, s - 1))}
          className="w-12 h-12 rounded-full bg-gray-200 text-2xl font-bold hover:bg-gray-300">−</button>
        <span className="text-4xl font-bold w-12 text-center">{strokes}</span>
        <button onClick={() => setStrokes(s => s + 1)}
          className="w-12 h-12 rounded-full bg-gray-200 text-2xl font-bold hover:bg-gray-300">+</button>
      </div>
      <button onClick={() => onSubmit(strokes, par, si)}
        className="mt-4 w-full bg-green-700 text-white py-2 rounded font-semibold">
        {t('holeCard.saveHole', { hole: holeNumber })}
      </button>
    </div>
  )
}
