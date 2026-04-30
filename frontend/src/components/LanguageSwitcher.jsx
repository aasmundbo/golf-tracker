import { useTranslation } from 'react-i18next'

const FLAGS = { nb: '🇳🇴', en: '🇬🇧' }
const LANGS = ['nb', 'en']

export default function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const current = LANGS.includes(i18n.resolvedLanguage) ? i18n.resolvedLanguage : 'nb'
  const next = LANGS.find(l => l !== current)

  return (
    <button
      onClick={() => i18n.changeLanguage(next)}
      className="text-xl leading-none select-none"
      aria-label={`Switch to ${next}`}
    >
      {FLAGS[current]}
    </button>
  )
}
