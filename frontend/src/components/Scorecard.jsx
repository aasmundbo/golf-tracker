import { useTranslation } from 'react-i18next'

function Sparkline({ holeByHole, hcpIndex }) {
  const values = holeByHole.map(h => h.projected_differential_after_hole)
  const allValues = [...values, hcpIndex].filter(v => v != null)
  const minVal = Math.min(...allValues)
  const maxVal = Math.max(...allValues)
  const range = maxVal - minVal || 1

  const W = 180, H = 50, PX = 5, PY = 5
  const mapX = h => PX + ((h - 1) / 17) * (W - 2 * PX)
  const mapY = v => PY + ((maxVal - v) / range) * (H - 2 * PY)

  const points = values.map((v, i) => `${mapX(i + 1)},${mapY(v)}`).join(' ')
  const hcpY = mapY(hcpIndex)

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 56 }}>
      <line
        x1={PX} y1={hcpY} x2={W - PX} y2={hcpY}
        stroke="#9ca3af" strokeWidth="1" strokeDasharray="4 2"
      />
      <polyline points={points} fill="none" stroke="#16a34a" strokeWidth="1.5" />
      {values.map((v, i) => (
        <circle key={i} cx={mapX(i + 1)} cy={mapY(v)} r="2" fill="#16a34a" />
      ))}
    </svg>
  )
}

export default function Scorecard({ scores, totalHoles, projection, hcpIndex }) {
  const { t } = useTranslation()
  const diff = projection?.projected_differential ?? null
  const labelColor = diff == null
    ? 'text-gray-400'
    : diff < hcpIndex ? 'text-green-600' : 'text-red-500'
  const labelText = diff == null
    ? t('scorecard.playingToHcpUnknown')
    : t('scorecard.playingToHcp', { diff: diff.toFixed(1) })

  return (
    <div className="space-y-2">
      <p className={`text-sm font-medium ${labelColor}`}>{labelText}</p>

      <div className="overflow-x-auto">
        <table className="text-sm w-full border-collapse">
          <thead>
            <tr className="bg-green-50">
              <th className="border px-2 py-1">{t('scorecard.hole')}</th>
              <th className="border px-2 py-1">{t('scorecard.par')}</th>
              <th className="border px-2 py-1">{t('scorecard.si')}</th>
              <th className="border px-2 py-1">{t('scorecard.gross')}</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: totalHoles }, (_, i) => i + 1).map(h => {
              const s = scores[h]
              return (
                <tr key={h} className={s ? '' : 'text-gray-300'}>
                  <td className="border px-2 py-1 text-center">{h}</td>
                  <td className="border px-2 py-1 text-center">{s?.hole_par ?? '-'}</td>
                  <td className="border px-2 py-1 text-center">{s?.hole_stroke_index ?? '-'}</td>
                  <td className="border px-2 py-1 text-center font-medium">{s?.strokes ?? '-'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {projection?.hole_by_hole?.length === 18 && hcpIndex != null && (
        <Sparkline holeByHole={projection.hole_by_hole} hcpIndex={hcpIndex} />
      )}
    </div>
  )
}
