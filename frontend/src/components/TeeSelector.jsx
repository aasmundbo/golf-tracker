import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { formatDecimal } from '../utils/formatters'

export default function TeeSelector({ courseDetail, preferredGender, onSelect }) {
  const { t, i18n } = useTranslation()
  const locale = i18n.resolvedLanguage === 'nb' ? 'nb' : 'en'
  const [showAll, setShowAll] = useState(false)
  const course = courseDetail?.course
  if (!course) return null

  let tees = []
  if (course.tees) {
    if (Array.isArray(course.tees)) {
      tees = course.tees
    } else {
      tees = [...(course.tees.male || []), ...(course.tees.female || [])]
    }
  }

  const preferredTees = preferredGender ? tees.filter(t => t.gender === preferredGender) : []
  const otherTees = preferredGender ? tees.filter(t => t.gender !== preferredGender) : tees
  const usePreference = preferredTees.length > 0

  const genderLabel = gender => gender === 'herre' ? 'Herre' : gender === 'dame' ? 'Dame' : 'Øvrige'

  const renderTeeButton = (tee, i) => (
    <button key={i} onClick={() => onSelect(tee)}
      className="text-left border rounded px-3 py-2 hover:bg-green-50 flex justify-between">
      <span className="font-medium">{tee.tee_name || tee.name}</span>
      <span className="text-sm text-gray-500">
        SR {formatDecimal(tee.slope_rating || tee.slope, locale)} / CR {formatDecimal(tee.course_rating, locale)}
      </span>
    </button>
  )

  if (!usePreference) {
    const herreTees = tees.filter(t => t.gender === 'herre')
    const dameTees = tees.filter(t => t.gender === 'dame')
    const ungroupedTees = tees.filter(t => t.gender !== 'herre' && t.gender !== 'dame')
    const useGroups = herreTees.length > 0 || dameTees.length > 0

    return (
      <div>
        <label className="block text-sm font-medium mb-1">{t('teeSelector.label')}</label>
        {useGroups ? (
          <div className="space-y-3">
            {herreTees.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Herre</p>
                <div className="grid gap-2">{herreTees.map(renderTeeButton)}</div>
              </div>
            )}
            {dameTees.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Dame</p>
                <div className="grid gap-2">{dameTees.map(renderTeeButton)}</div>
              </div>
            )}
            {ungroupedTees.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Øvrige</p>
                <div className="grid gap-2">{ungroupedTees.map(renderTeeButton)}</div>
              </div>
            )}
          </div>
        ) : (
          <div className="grid gap-2">{tees.map(renderTeeButton)}</div>
        )}
      </div>
    )
  }

  return (
    <div>
      <label className="block text-sm font-medium mb-1">{t('teeSelector.label')}</label>
      <div className="space-y-3">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
            {genderLabel(preferredGender)}
          </p>
          <div className="grid gap-2">{preferredTees.map(renderTeeButton)}</div>
        </div>
        {otherTees.length > 0 && (
          showAll ? (
            <div className="space-y-3">
              {['herre', 'dame'].map(g => {
                const gTees = otherTees.filter(t => t.gender === g)
                if (!gTees.length) return null
                return (
                  <div key={g}>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{genderLabel(g)}</p>
                    <div className="grid gap-2">{gTees.map(renderTeeButton)}</div>
                  </div>
                )
              })}
              {(() => {
                const ungrouped = otherTees.filter(t => t.gender !== 'herre' && t.gender !== 'dame')
                return ungrouped.length > 0 ? (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Øvrige</p>
                    <div className="grid gap-2">{ungrouped.map(renderTeeButton)}</div>
                  </div>
                ) : null
              })()}
              <button
                onClick={() => setShowAll(false)}
                className="text-sm text-green-700 underline mt-1"
              >
                {t('teeSelector.showFewer')}
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAll(true)}
              className="text-sm text-green-700 underline"
            >
              {t('teeSelector.showMore')}
            </button>
          )
        )}
      </div>
    </div>
  )
}
