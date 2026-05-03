import { useTranslation } from 'react-i18next'

export function getHandicapStrokes(playingHcp, si) {
  if (playingHcp == null || si == null || playingHcp <= 0) return 0
  const base = Math.floor(playingHcp / 18)
  const remainder = playingHcp % 18
  return base + (si <= remainder ? 1 : 0)
}

export function ScoreIndicator({ gross, par, si, playingHcp, scoreDisplay = 'netto' }) {
  if (gross == null || par == null) {
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28 }}>
        {gross ?? '-'}
      </span>
    )
  }

  const netToPar = scoreDisplay === 'brutto'
    ? gross - par
    : (gross - getHandicapStrokes(playingHcp, si)) - par

  const base = { display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 28, height: 28, boxSizing: 'border-box' }

  if (netToPar <= -2) {
    return (
      <span style={{ ...base, borderRadius: '50%', border: '2px solid #22c55e', outline: '2px solid #22c55e', outlineOffset: '2px', color: '#15803d' }}>
        {gross}
      </span>
    )
  }
  if (netToPar === -1) {
    return (
      <span style={{ ...base, borderRadius: '50%', border: '2px solid #22c55e', color: '#15803d' }}>
        {gross}
      </span>
    )
  }
  if (netToPar === 0) {
    return <span style={base}>{gross}</span>
  }
  if (netToPar === 1) {
    return (
      <span style={{ ...base, borderRadius: '2px', border: '2px solid var(--color-text-primary, #111827)' }}>
        {gross}
      </span>
    )
  }
  if (netToPar === 2) {
    return (
      <span style={{ ...base, borderRadius: '2px', border: '2px solid var(--color-text-primary, #111827)', outline: '2px solid var(--color-text-primary, #111827)', outlineOffset: '2px' }}>
        {gross}
      </span>
    )
  }
  return (
    <span style={{ ...base, borderRadius: '2px', border: '2px solid #ef4444', outline: '2px solid #ef4444', outlineOffset: '2px', color: '#b91c1c' }}>
      {gross}
    </span>
  )
}

function Sparkline({ holeByHole, hcpIndex }) {
  const values = holeByHole.map(h => h.projected_differential_after_hole)
  const allValues = [...values, hcpIndex].filter(v => v != null)
  const minVal = Math.min(...allValues)
  const maxVal = Math.max(...allValues)
  const range = maxVal - minVal || 1

  const W = 180, H = 50, PX = 5, PY = 5
  const mapX = h => PX + ((h - 1) / 17) * (W - 2 * PX)
  const mapY = v => PY + ((maxVal - v) / range) * (H - 2 * PY)

  const coords = values.map((v, i) => ({ x: mapX(i + 1), y: mapY(v), v }))
  const hcpY = mapY(hcpIndex)
  const color = v => v > hcpIndex ? '#ef4444' : '#22c55e'

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 56 }}>
      <line
        x1={PX} y1={hcpY} x2={W - PX} y2={hcpY}
        stroke="#9ca3af" strokeWidth="1" strokeDasharray="4 2"
      />
      {coords.slice(1).map((pt, i) => (
        <line
          key={i}
          x1={coords[i].x} y1={coords[i].y}
          x2={pt.x} y2={pt.y}
          stroke={color(pt.v)} strokeWidth="1.5"
        />
      ))}
      {coords.map((pt, i) => (
        <circle key={i} cx={pt.x} cy={pt.y} r="2" fill={color(pt.v)} />
      ))}
    </svg>
  )
}

export default function Scorecard({ scores, totalHoles, projection, hcpIndex, playingHandicap, scoreDisplay = 'netto' }) {
  const { t } = useTranslation()

  return (
    <div className="space-y-2">
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
                  <td className="border px-2 py-1 text-center font-medium">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <ScoreIndicator gross={s?.strokes} par={s?.hole_par} si={s?.hole_stroke_index} playingHcp={playingHandicap} scoreDisplay={scoreDisplay} />
                    </div>
                  </td>
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
