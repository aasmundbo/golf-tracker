import { useTranslation } from 'react-i18next'
import { Chart } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  LineElement,
  LineController,
  PointElement,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  LineElement,
  LineController,
  PointElement,
  Tooltip,
  Legend,
)

export default function HandicapHistoryChart({ rounds, locale }) {
  const { t } = useTranslation()

  const chartRounds = [...rounds]
    .filter(r => r.projected_hcp != null)
    .sort((a, b) => new Date(a.started_at) - new Date(b.started_at))

  if (chartRounds.length < 1) return null

  const langTag = locale === 'nb' ? 'nb-NO' : 'en-GB'
  const labels = chartRounds.map(r =>
    new Date(r.started_at).toLocaleDateString(langTag, { day: 'numeric', month: 'short' })
  )

  const barColors = chartRounds.map(r =>
    r.projected_hcp < r.hcp_index ? '#5DCAA5' : '#F09595'
  )

  const data = {
    labels,
    datasets: [
      {
        type: 'bar',
        label: t('history.chartPlayedTo'),
        data: chartRounds.map(r => r.projected_hcp),
        backgroundColor: barColors,
        borderRadius: 3,
        order: 2,
      },
      {
        type: 'line',
        label: t('history.chartRegistered'),
        data: chartRounds.map(r => r.hcp_index),
        borderColor: '#ef4444',
        borderDash: [5, 5],
        borderWidth: 2,
        pointRadius: 0,
        fill: false,
        tension: 0,
        order: 1,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      x: {
        ticks: { maxRotation: 45, font: { size: 11 } },
      },
      y: {
        title: { display: true, text: t('history.chartHandicap'), font: { size: 12 } },
        ticks: { font: { size: 11 } },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y}`,
        },
      },
    },
  }

  return (
    <div className="bg-white border rounded-xl p-4 shadow-sm mb-4">
      <Chart type="bar" data={data} options={options} />
    </div>
  )
}
