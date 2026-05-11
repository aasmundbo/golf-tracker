import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { parseDecimal, formatDecimal } from '../utils/formatters'

export default function Settings() {
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage === 'nb' ? 'nb' : 'en'
  const navigate = useNavigate()

  const [original, setOriginal] = useState(null)
  const [name, setName] = useState('')
  const [lang, setLang] = useState('nb')
  const [hcp, setHcp] = useState('')
  const [scoreDisplay, setScoreDisplay] = useState('netto')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    api.get('/users/me')
      .then(res => {
        const user = res.data
        setOriginal(user)
        setName(user.name ?? '')
        setLang(user.preferred_language ?? 'nb')
        setHcp(user.default_hcp_index != null ? formatDecimal(user.default_hcp_index, locale) : '')
        setScoreDisplay(user.score_display ?? 'netto')
      })
      .catch(() => setError(t('settings.error')))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async e => {
    e.preventDefault()
    if (!original) return

    const patch = {}
    if (name !== original.name) patch.name = name
    if (lang !== original.preferred_language) patch.preferred_language = lang
    if (scoreDisplay !== original.score_display) patch.score_display = scoreDisplay
    const hcpVal = hcp === '' ? null : parseDecimal(hcp)
    if (hcpVal !== original.default_hcp_index) patch.default_hcp_index = hcpVal
    if (Object.keys(patch).length === 0) return

    setSaving(true)
    setError('')
    setSaved(false)

    try {
      const res = await api.patch('/users/me', patch)
      const updated = res.data
      setOriginal(updated)
      setName(updated.name ?? '')
      setLang(updated.preferred_language ?? 'nb')
      setHcp(updated.default_hcp_index != null ? formatDecimal(updated.default_hcp_index, locale) : '')
      setScoreDisplay(updated.score_display ?? 'netto')

      if (patch.preferred_language) {
        i18n.changeLanguage(patch.preferred_language)
      }

      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch {
      setError(t('settings.error'))
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (!window.confirm(t('settings.confirmDeleteAccount'))) return
    setDeleteError('')
    try {
      await api.delete('/users/me')
      localStorage.removeItem('token')
      navigate('/login')
    } catch {
      setDeleteError(t('settings.deleteAccountError'))
    }
  }

  if (loading) {
    return (
      <div className="mt-6 text-gray-500 text-sm">{t('activeRound.loading')}</div>
    )
  }

  return (
    <div className="mt-6 space-y-6 max-w-md">
      <h2 className="text-xl font-bold">{t('settings.title')}</h2>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('settings.name')}
          </label>
          <input
            type="text"
            required
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('settings.language')}
          </label>
          <select
            value={lang}
            onChange={e => setLang(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 bg-white"
          >
            <option value="nb">Norsk</option>
            <option value="en">English</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('settings.scoreDisplay')}
          </label>
          <select
            value={scoreDisplay}
            onChange={e => setScoreDisplay(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 bg-white"
          >
            <option value="netto">{t('settings.scoreDisplayNetto')}</option>
            <option value="brutto">{t('settings.scoreDisplayBrutto')}</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('settings.defaultHcp')}
          </label>
          <input
            type="text"
            inputMode="decimal"
            value={hcp}
            onChange={e => setHcp(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            placeholder="—"
          />
        </div>

        {error && (
          <p className="text-sm text-red-600">{error}</p>
        )}

        {saved && (
          <p className="text-sm text-green-600 font-medium">{t('settings.saved')}</p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-green-700 text-white font-semibold rounded-xl py-2.5 text-sm hover:bg-green-800 disabled:opacity-50 transition-colors"
        >
          {saving ? t('settings.saving') : t('settings.save')}
        </button>
      </form>

      <div className="border border-red-200 rounded-xl p-4 space-y-3">
        <h3 className="text-sm font-semibold text-red-700">{t('settings.deleteAccount')}</h3>
        {deleteError && (
          <p className="text-sm text-red-600">{deleteError}</p>
        )}
        <button
          type="button"
          onClick={handleDeleteAccount}
          className="w-full border border-red-500 text-red-600 font-semibold rounded-xl py-2.5 text-sm hover:bg-red-50 transition-colors"
        >
          {t('settings.deleteAccount')}
        </button>
      </div>
    </div>
  )
}
