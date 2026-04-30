import { useState } from 'react'
import { useTranslation } from 'react-i18next'

export default function HoleDataPrompt({ holeNumber, onSubmit, onCancel }) {
  const { t } = useTranslation()
  const [par, setPar] = useState('4')
  const [si, setSi] = useState('')

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-80 shadow-xl space-y-4">
        <h3 className="font-bold text-lg">{t('holeDataPrompt.title', { hole: holeNumber })}</h3>
        <div>
          <label className="block text-sm font-medium">{t('holeDataPrompt.par')}</label>
          <div className="flex gap-2 mt-1">
            {[3, 4, 5].map(p => (
              <button key={p} onClick={() => setPar(String(p))}
                className={`flex-1 py-2 rounded border font-bold ${par === String(p) ? 'bg-green-700 text-white' : 'bg-gray-50'}`}>{p}</button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium">{t('holeDataPrompt.strokeIndex')}</label>
          <input type="number" min="1" max="18" className="border rounded px-3 py-2 w-full mt-1"
            value={si} onChange={e => setSi(e.target.value)} />
        </div>
        <div className="flex gap-2">
          <button onClick={onCancel} className="flex-1 py-2 border rounded">{t('holeDataPrompt.cancel')}</button>
          <button onClick={() => onSubmit(parseInt(par), parseInt(si))} disabled={!si}
            className="flex-1 py-2 bg-green-700 text-white rounded font-semibold">{t('holeDataPrompt.save')}</button>
        </div>
      </div>
    </div>
  )
}
