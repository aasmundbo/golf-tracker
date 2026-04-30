import { useTranslation } from 'react-i18next'

export default function LiveStats({ stats, projection, hcpIndex }) {
  const { t } = useTranslation()
  const sign = n => n > 0 ? `+${n}` : String(n)
  const diff = projection?.projected_differential ?? null
  const hcpColor = diff == null
    ? 'text-gray-400'
    : diff < hcpIndex ? 'text-green-600' : 'text-red-600'
  const hcpValue = diff == null ? '—' : `~${diff.toFixed(1)}`
  return (
    <div className="grid grid-cols-4 gap-2 bg-white border rounded-xl p-3">
      <div className="text-center">
        <div className={`text-xl font-bold ${stats.gross_to_par > 0 ? 'text-red-600' : stats.gross_to_par < 0 ? 'text-green-600' : ''}`}>
          {sign(stats.gross_to_par)}
        </div>
        <div className="text-xs text-gray-500">{t('liveStats.gross')}</div>
      </div>
      <div className="text-center">
        <div className={`text-xl font-bold ${stats.net_to_par > 0 ? 'text-red-600' : stats.net_to_par < 0 ? 'text-green-600' : ''}`}>
          {sign(stats.net_to_par)}
        </div>
        <div className="text-xs text-gray-500">{t('liveStats.net')}</div>
      </div>
      <div className="text-center">
        <div className="text-xl font-bold text-blue-600">{stats.stableford_total}</div>
        <div className="text-xs text-gray-500">{t('liveStats.stableford')}</div>
      </div>
      <div className="text-center">
        <div className={`text-xl font-bold ${hcpColor}`}>{hcpValue}</div>
        <div className="text-xs text-gray-500">{t('liveStats.projectedHcp')}</div>
      </div>
    </div>
  )
}
