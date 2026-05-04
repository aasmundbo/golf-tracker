import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import api from '../api/client'

const EMPTY_COURSE_FORM = { name: '', city: '', country: '', layout_name: 'Hovedbane', tee_name: 'Gul', slope: '', course_rating: '', par_total: '' }
const EMPTY_LAYOUT_FORM = { name: '', slope: '', course_rating: '', par_total: '', tee_name: '' }
const EMPTY_TEE_FORM = { name: '', slope: '', course_rating: '', par_total: '' }

const emptyHoleRow = (n) => ({ hole_number: n, par: '', stroke_index: '' })
const emptyHoles = () => Array.from({ length: 18 }, (_, i) => emptyHoleRow(i + 1))

export default function MyCourses() {
  const { t } = useTranslation()
  const [currentUser, setCurrentUser] = useState(null)
  const [courses, setCourses] = useState([])
  const [expandedCourse, setExpandedCourse] = useState(null)
  const [layouts, setLayouts] = useState({})
  const [expandedLayout, setExpandedLayout] = useState(null)
  const [layoutTees, setLayoutTees] = useState({})

  const [addingCourse, setAddingCourse] = useState(false)
  const [courseForm, setCourseForm] = useState(EMPTY_COURSE_FORM)
  const [courseError, setCourseError] = useState(null)

  const [addingLayoutTo, setAddingLayoutTo] = useState(null)
  const [layoutForm, setLayoutForm] = useState(EMPTY_LAYOUT_FORM)

  const [addingTeeTo, setAddingTeeTo] = useState(null)
  const [teeForm, setTeeForm] = useState(EMPTY_TEE_FORM)

  // Unified tee editor
  const [editingTee, setEditingTee] = useState(null)
  const [teeEditForm, setTeeEditForm] = useState(null)
  const [savingTee, setSavingTee] = useState(false)
  const [teeEditError, setTeeEditError] = useState(null)
  const [duplicatingTee, setDuplicatingTee] = useState(null)
  const [openTeeMenu, setOpenTeeMenu] = useState(null)

  // Hole data cache for "18 hull lagret" badge
  const [holeData, setHoleData] = useState({})

  const holeInputRefs = useRef({})
  const teeMenuRef = useRef(null)

  useEffect(() => {
    if (!openTeeMenu) return
    const handleClick = (e) => {
      if (teeMenuRef.current && !teeMenuRef.current.contains(e.target)) setOpenTeeMenu(null)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [openTeeMenu])

  useEffect(() => {
    api.get('/users/me').then(r => setCurrentUser(r.data)).catch(() => {})
  }, [])

  const canDelete = (createdBy) =>
    currentUser?.role === 'admin' || createdBy === currentUser?.id

  const loadCourses = () =>
    api.get('/courses').then(r => setCourses(r.data)).catch(() => {})

  useEffect(() => { loadCourses() }, [])

  const loadLayouts = async (courseId) => {
    const res = await api.get(`/courses/${courseId}/layouts`)
    setLayouts(prev => ({ ...prev, [courseId]: res.data }))
  }

  const loadTees = async (layoutId) => {
    const res = await api.get(`/courses/local/${layoutId}/tees`)
    setLayoutTees(prev => ({ ...prev, [layoutId]: res.data }))
  }

  const loadHoles = async (teeId) => {
    const res = await api.get(`/courses/local/tees/${teeId}/holes`)
    const rows = emptyHoles()
    for (const h of res.data) {
      const idx = h.hole_number - 1
      if (idx >= 0 && idx < 18) {
        rows[idx] = { hole_number: h.hole_number, par: h.par ?? '', stroke_index: h.stroke_index ?? '' }
      }
    }
    setHoleData(prev => ({ ...prev, [teeId]: rows }))
    return rows
  }

  const toggleCourse = async (courseId) => {
    if (expandedCourse === courseId) { setExpandedCourse(null); return }
    setExpandedCourse(courseId)
    if (!layouts[courseId]) await loadLayouts(courseId)
  }

  const toggleLayout = async (layoutId) => {
    if (expandedLayout === layoutId) { setExpandedLayout(null); return }
    setExpandedLayout(layoutId)
    if (!layoutTees[layoutId]) await loadTees(layoutId)
  }

  const openEditPanel = async (tee) => {
    const rows = holeData[tee.id] ?? await loadHoles(tee.id)
    setTeeEditForm({
      name: tee.name,
      slope: tee.slope ?? '',
      course_rating: tee.course_rating ?? '',
      par_total: tee.par_total ?? '',
      holes: rows.map(r => ({ ...r })),
    })
    setTeeEditError(null)
    setEditingTee(tee.id)
  }

  const closeTeeEdit = () => {
    setEditingTee(null)
    setTeeEditForm(null)
    setTeeEditError(null)
  }

  const updateTeeEditMeta = (field, value) => {
    setTeeEditForm(f => ({ ...f, [field]: value }))
  }

  const updateTeeEditHole = (teeId, holeIndex, field, value, flatIndex) => {
    setTeeEditForm(f => {
      const holes = [...f.holes]
      holes[holeIndex] = { ...holes[holeIndex], [field]: value }
      return { ...f, holes }
    })
    const len = value.length
    if (len >= 2 || (len === 1 && value !== '1')) {
      const refs = holeInputRefs.current[teeId] || []
      const next = refs[flatIndex + 1]
      if (next) { next.focus(); next.select() }
    }
  }

  const saveTeeEdit = async (layoutId) => {
    setSavingTee(true)
    setTeeEditError(null)
    try {
      await api.put(`/courses/local/tees/${editingTee}`, {
        name: teeEditForm.name,
        slope: teeEditForm.slope !== '' ? parseFloat(teeEditForm.slope) : null,
        course_rating: teeEditForm.course_rating !== '' ? parseFloat(teeEditForm.course_rating) : null,
        par_total: teeEditForm.par_total !== '' ? parseInt(teeEditForm.par_total) : null,
      })
      const holes = teeEditForm.holes.map(r => ({
        hole_number: r.hole_number,
        par: r.par !== '' ? parseInt(r.par) : null,
        stroke_index: r.stroke_index !== '' ? parseInt(r.stroke_index) : null,
      }))
      await api.put(`/courses/local/tees/${editingTee}/holes`, { holes })
      await loadHoles(editingTee)
      await loadTees(layoutId)
      closeTeeEdit()
    } catch (err) {
      setTeeEditError(err.response?.data?.detail ?? err.message ?? t('myCourses.saveFailed'))
    } finally {
      setSavingTee(false)
    }
  }

  const duplicateTee = async (layoutId, teeId) => {
    setDuplicatingTee(teeId)
    try {
      const res = await api.post(`/courses/local/tees/${teeId}/duplicate`)
      await loadTees(layoutId)
      await openEditPanel(res.data)
    } catch (err) {
      alert(err.response?.data?.detail ?? err.message ?? t('myCourses.somethingWentWrong'))
    } finally {
      setDuplicatingTee(null)
    }
  }

  const deleteTee = async (layoutId, teeId) => {
    if (!confirm(t('myCourses.confirmDeleteTee'))) return
    try {
      await api.delete(`/courses/local/tees/${teeId}`)
      await loadTees(layoutId)
    } catch (err) {
      alert(err.response?.data?.detail ?? err.message ?? t('myCourses.deletionFailed'))
    }
  }

  const teeHasSavedHoles = (teeId) => {
    const rows = holeData[teeId]
    return rows && rows.some(r => r.par !== '' && r.par !== null)
  }

  const addCourse = async () => {
    if (!courseForm.name.trim()) return
    setCourseError(null)
    try {
      const club = await api.post('/courses', {
        name: courseForm.name,
        city: courseForm.city,
        country: courseForm.country,
      })
      if (courseForm.layout_name.trim()) {
        await api.post(`/courses/${club.data.id}/layouts`, {
          name: courseForm.layout_name,
          tee_name: courseForm.tee_name.trim() || undefined,
          slope: courseForm.slope ? parseFloat(courseForm.slope) : undefined,
          course_rating: courseForm.course_rating ? parseFloat(courseForm.course_rating) : undefined,
          par_total: courseForm.par_total ? parseInt(courseForm.par_total) : undefined,
        })
      }
      setAddingCourse(false)
      setCourseForm(EMPTY_COURSE_FORM)
      loadCourses()
    } catch (err) {
      setCourseError(err.response?.data?.detail ?? err.message ?? t('myCourses.somethingWentWrong'))
    }
  }

  const deleteCourse = async (id) => {
    if (!confirm(t('myCourses.confirmDeleteCourse'))) return
    try {
      await api.delete(`/courses/${id}`)
      setExpandedCourse(prev => (prev === id ? null : prev))
      setLayouts(prev => { const n = { ...prev }; delete n[id]; return n })
      loadCourses()
    } catch (err) {
      alert(err.response?.data?.detail ?? err.message ?? t('myCourses.deletionFailed'))
    }
  }

  const addLayout = async (courseId) => {
    if (!layoutForm.name.trim()) return
    await api.post(`/courses/${courseId}/layouts`, {
      name: layoutForm.name,
      tee_name: layoutForm.tee_name || undefined,
      slope: layoutForm.slope ? parseFloat(layoutForm.slope) : undefined,
      course_rating: layoutForm.course_rating ? parseFloat(layoutForm.course_rating) : undefined,
      par_total: layoutForm.par_total ? parseInt(layoutForm.par_total) : undefined,
    })
    setAddingLayoutTo(null)
    setLayoutForm(EMPTY_LAYOUT_FORM)
    await loadLayouts(courseId)
  }

  const deleteLayout = async (courseId, layoutId) => {
    if (!confirm(t('myCourses.confirmDeleteLayout'))) return
    await api.delete(`/courses/local/${layoutId}`)
    setLayouts(prev => ({
      ...prev,
      [courseId]: (prev[courseId] || []).filter(l => l.id !== layoutId),
    }))
    if (expandedLayout === layoutId) setExpandedLayout(null)
  }

  const addTee = async (layoutId) => {
    if (!teeForm.name.trim()) return
    await api.post(`/courses/local/${layoutId}/tees`, {
      name: teeForm.name,
      slope: teeForm.slope ? parseFloat(teeForm.slope) : undefined,
      course_rating: teeForm.course_rating ? parseFloat(teeForm.course_rating) : undefined,
      par_total: teeForm.par_total ? parseInt(teeForm.par_total) : undefined,
    })
    setAddingTeeTo(null)
    setTeeForm(EMPTY_TEE_FORM)
    await loadTees(layoutId)
  }

  return (
    <div className="space-y-4 mt-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">{t('myCourses.title')}</h2>
        <button
          onClick={() => { setAddingCourse(!addingCourse); setCourseForm(EMPTY_COURSE_FORM); setCourseError(null) }}
          className="bg-green-700 text-white px-3 py-1 rounded text-sm"
        >
          {t('myCourses.addCourse')}
        </button>
      </div>

      {/* New top-level course form */}
      {addingCourse && (
        <div className="bg-white border rounded-xl p-4 space-y-3">
          <h3 className="font-semibold text-sm">{t('myCourses.newCourse')}</h3>
          <div>
            <label className="block text-sm font-medium">{t('myCourses.courseName')}</label>
            <input
              className="border rounded px-3 py-2 w-full"
              placeholder={t('myCourses.courseNamePlaceholder')}
              value={courseForm.name}
              onChange={e => setCourseForm(d => ({ ...d, name: e.target.value }))}
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm font-medium">{t('myCourses.city')}</label>
              <input className="border rounded px-3 py-2 w-full" value={courseForm.city}
                onChange={e => setCourseForm(d => ({ ...d, city: e.target.value }))} />
            </div>
            <div>
              <label className="block text-sm font-medium">{t('myCourses.country')}</label>
              <input className="border rounded px-3 py-2 w-full" value={courseForm.country}
                onChange={e => setCourseForm(d => ({ ...d, country: e.target.value }))} />
            </div>
          </div>
          <div className="border-t pt-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              {t('myCourses.firstLayout')}
            </p>
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-sm font-medium">{t('myCourses.layout')}</label>
                  <input
                    className="border rounded px-3 py-2 w-full"
                    placeholder={t('myCourses.layoutPlaceholder')}
                    value={courseForm.layout_name}
                    onChange={e => setCourseForm(d => ({ ...d, layout_name: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium">{t('myCourses.teeSpot')}</label>
                  <input
                    className="border rounded px-3 py-2 w-full"
                    placeholder={t('myCourses.teeSpotPlaceholder')}
                    value={courseForm.tee_name}
                    onChange={e => setCourseForm(d => ({ ...d, tee_name: e.target.value }))}
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[['slope', 'Slope'], ['course_rating', 'CR'], ['par_total', 'Par']].map(([field, label]) => (
                  <div key={field}>
                    <label className="block text-sm font-medium">{label}</label>
                    <input
                      type="number"
                      inputMode={field === 'par_total' ? 'numeric' : 'decimal'}
                      className="border rounded px-3 py-2 w-full"
                      value={courseForm[field]}
                      onChange={e => setCourseForm(d => ({ ...d, [field]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
          {courseError && <p className="text-red-600 text-sm">{courseError}</p>}
          <div className="flex gap-2">
            <button type="button" onClick={addCourse} className="bg-green-700 text-white px-4 py-2 rounded flex-1 text-sm">
              {t('myCourses.save')}
            </button>
            <button type="button" onClick={() => { setAddingCourse(false); setCourseForm(EMPTY_COURSE_FORM); setCourseError(null) }} className="border px-4 py-2 rounded flex-1 text-sm">
              {t('myCourses.cancel')}
            </button>
          </div>
        </div>
      )}

      {/* Course list */}
      {courses.map(course => (
        <div key={course.id} className="bg-white border rounded-xl">
          <div
            className="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50"
            onClick={() => toggleCourse(course.id)}
          >
            <div>
              <span className="font-semibold">{course.name}</span>
              {course.city && <span className="text-sm text-gray-500 ml-2">{course.city}</span>}
            </div>
            <div className="flex items-center gap-3">
              {canDelete(course.created_by) && (
                <button
                  onClick={e => { e.stopPropagation(); deleteCourse(course.id) }}
                  className="text-red-500 text-sm"
                >
                  {t('myCourses.delete')}
                </button>
              )}
              <span className="text-gray-400 text-sm select-none">
                {expandedCourse === course.id ? '▲' : '▼'}
              </span>
            </div>
          </div>

          {expandedCourse === course.id && (
            <div className="border-t bg-gray-50 px-4 py-3 space-y-2">
              {(layouts[course.id] || []).map(layout => (
                <div key={layout.id} className="bg-white border rounded-lg">
                  <div
                    className="px-3 py-2 flex justify-between items-center cursor-pointer hover:bg-green-50"
                    onClick={() => toggleLayout(layout.id)}
                  >
                    <span className="font-medium text-sm">{layout.name}</span>
                    <div className="flex items-center gap-2">
                      {canDelete(layout.created_by) && (
                        <button
                          onClick={e => { e.stopPropagation(); deleteLayout(course.id, layout.id) }}
                          className="text-red-500 text-xs"
                        >
                          {t('myCourses.delete')}
                        </button>
                      )}
                      <span className="text-gray-400 text-xs select-none">
                        {expandedLayout === layout.id ? '▲' : '▼'}
                      </span>
                    </div>
                  </div>

                  {expandedLayout === layout.id && (
                    <div className="border-t px-3 py-2 space-y-1">
                      {(layoutTees[layout.id] || []).map(tee => (
                        <div key={tee.id} className="border-b last:border-0 py-2">
                          {/* Tee summary row */}
                          <div className="flex justify-between items-center text-sm text-gray-700">
                            <div className="flex flex-col gap-0.5">
                              <span className="font-medium">{tee.name}</span>
                              <span className="text-gray-400 text-xs">
                                Slope {tee.slope ?? '–'} · CR {tee.course_rating ?? '–'} · Par {tee.par_total ?? '–'}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              {teeHasSavedHoles(tee.id) && editingTee !== tee.id && (
                                <span className="text-xs text-green-700">{t('myCourses.holesSaved')}</span>
                              )}
                              <button
                                onClick={() => editingTee === tee.id ? closeTeeEdit() : openEditPanel(tee)}
                                className="text-xs bg-green-700 text-white rounded px-2 py-0.5 hover:bg-green-800"
                              >
                                {editingTee === tee.id ? t('myCourses.cancel') : t('myCourses.editTee')}
                              </button>
                              <div className="relative" ref={openTeeMenu === tee.id ? teeMenuRef : null}>
                                <button
                                  onClick={() => setOpenTeeMenu(v => v === tee.id ? null : tee.id)}
                                  className="text-xs border border-gray-300 rounded px-2 py-0.5 hover:bg-gray-50"
                                >
                                  ⋯
                                </button>
                                {openTeeMenu === tee.id && (
                                  <div className="absolute right-0 top-full mt-1 bg-white border rounded shadow-lg min-w-[120px] z-10">
                                    <button
                                      onClick={() => { setOpenTeeMenu(null); duplicateTee(layout.id, tee.id) }}
                                      disabled={duplicatingTee === tee.id}
                                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-gray-50 disabled:opacity-50"
                                    >
                                      {t('myCourses.duplicateTee')}
                                    </button>
                                    {canDelete(layout.created_by) && (
                                      <button
                                        onClick={() => { setOpenTeeMenu(null); deleteTee(layout.id, tee.id) }}
                                        className="w-full text-left px-3 py-1.5 text-xs text-red-500 hover:bg-red-50"
                                      >
                                        {t('myCourses.delete')}
                                      </button>
                                    )}
                                    <a
                                      href={`https://github.com/aasmundbo/golf-tracker/issues/new?title=${encodeURIComponent(`Problem med tee: ${tee.name} (${course.name})`)}&body=${encodeURIComponent(`**Bane:** ${course.name}\n**Tee:** ${tee.name}\n\n**Beskriv problemet:**\n\n`)}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      onClick={() => setOpenTeeMenu(null)}
                                      className="block w-full text-left px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50"
                                    >
                                      🐛 {t('myCourses.reportIssue')}
                                    </a>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Unified edit panel */}
                          {editingTee === tee.id && teeEditForm && (
                            <div className="mt-3 space-y-3 border-t pt-3">
                              {/* Tee name */}
                              <div>
                                <label className="block text-xs font-medium text-gray-600">{t('myCourses.teeName')}</label>
                                <input
                                  className="border rounded px-2 py-1 w-full text-sm"
                                  value={teeEditForm.name}
                                  onChange={e => updateTeeEditMeta('name', e.target.value)}
                                />
                              </div>

                              {/* Slope / CR / Par grid */}
                              <div className="grid grid-cols-3 gap-2">
                                {[['slope', 'Slope'], ['course_rating', 'CR'], ['par_total', 'Par']].map(([field, label]) => (
                                  <div key={field}>
                                    <label className="block text-xs font-medium text-gray-600">{label}</label>
                                    <input
                                      type="number"
                                      inputMode={field === 'par_total' ? 'numeric' : 'decimal'}
                                      className="border rounded px-2 py-1 w-full text-sm"
                                      value={teeEditForm[field]}
                                      onChange={e => updateTeeEditMeta(field, e.target.value)}
                                    />
                                  </div>
                                ))}
                              </div>
                              <p className="text-xs text-gray-400">{t('myCourses.parAutoNote')}</p>

                              {/* Hole table */}
                              <table className="w-full text-xs border-collapse">
                                <thead>
                                  <tr className="text-gray-500 border-b">
                                    <th className="text-left py-1 pr-2 font-medium">{t('myCourses.hole')}</th>
                                    <th className="text-left py-1 pr-2 font-medium">{t('myCourses.par')}</th>
                                    <th className="text-left py-1 font-medium">{t('myCourses.strokeIndex')}</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {teeEditForm.holes.map((row, idx) => (
                                    <tr key={row.hole_number} className="border-b last:border-0">
                                      <td className="py-0.5 pr-2 text-gray-500">{row.hole_number}</td>
                                      <td className="py-0.5 pr-2">
                                        <input
                                          type="number"
                                          min={3}
                                          max={6}
                                          inputMode="numeric"
                                          className="border rounded px-1 py-0.5 w-14 text-xs"
                                          value={row.par}
                                          ref={el => { (holeInputRefs.current[tee.id] ??= [])[idx * 2] = el }}
                                          onChange={e => updateTeeEditHole(tee.id, idx, 'par', e.target.value, idx * 2)}
                                        />
                                      </td>
                                      <td className="py-0.5">
                                        <input
                                          type="number"
                                          min={1}
                                          max={18}
                                          inputMode="numeric"
                                          className="border rounded px-1 py-0.5 w-14 text-xs"
                                          value={row.stroke_index}
                                          ref={el => { (holeInputRefs.current[tee.id] ??= [])[idx * 2 + 1] = el }}
                                          onChange={e => updateTeeEditHole(tee.id, idx, 'stroke_index', e.target.value, idx * 2 + 1)}
                                        />
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>

                              {teeEditError && <p className="text-red-600 text-xs">{teeEditError}</p>}

                              <div className="flex gap-2">
                                <button
                                  onClick={() => saveTeeEdit(layout.id)}
                                  disabled={savingTee}
                                  className="bg-green-700 text-white px-3 py-1 rounded text-xs disabled:opacity-50 flex-1"
                                >
                                  {savingTee ? t('myCourses.saving') : t('myCourses.saveHoleInfo')}
                                </button>
                                <button
                                  onClick={closeTeeEdit}
                                  className="border px-3 py-1 rounded text-xs flex-1"
                                >
                                  {t('myCourses.cancel')}
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}

                      {(layoutTees[layout.id] || []).length === 0 && addingTeeTo !== layout.id && (
                        <p className="text-gray-400 italic text-xs py-1">{t('myCourses.noTeesAdded')}</p>
                      )}

                      {/* Add tee inline form */}
                      {addingTeeTo === layout.id ? (
                        <div className="pt-2 space-y-2">
                          <div>
                            <label className="block text-xs font-medium text-gray-600">{t('myCourses.teeName')}</label>
                            <input
                              className="border rounded px-2 py-1 w-full text-sm"
                              placeholder={t('myCourses.teeNamePlaceholder')}
                              value={teeForm.name}
                              onChange={e => setTeeForm(d => ({ ...d, name: e.target.value }))}
                            />
                          </div>
                          <div className="grid grid-cols-3 gap-2">
                            {[['slope', 'Slope'], ['course_rating', 'CR'], ['par_total', 'Par']].map(([field, label]) => (
                              <div key={field}>
                                <label className="block text-xs font-medium text-gray-600">{label}</label>
                                <input
                                  type="number"
                                  inputMode={field === 'par_total' ? 'numeric' : 'decimal'}
                                  className="border rounded px-2 py-1 w-full text-sm"
                                  value={teeForm[field]}
                                  onChange={e => setTeeForm(d => ({ ...d, [field]: e.target.value }))}
                                />
                              </div>
                            ))}
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={() => addTee(layout.id)}
                              className="bg-green-700 text-white px-3 py-1 rounded text-xs flex-1"
                            >
                              {t('myCourses.save')}
                            </button>
                            <button
                              onClick={() => { setAddingTeeTo(null); setTeeForm(EMPTY_TEE_FORM) }}
                              className="border px-3 py-1 rounded text-xs flex-1"
                            >
                              {t('myCourses.cancel')}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => { setAddingTeeTo(layout.id); setTeeForm(EMPTY_TEE_FORM) }}
                          className="text-xs text-green-700 underline pt-1 block"
                        >
                          {t('myCourses.addTee')}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {/* Add layout inline form */}
              {addingLayoutTo === course.id ? (
                <div className="bg-white border rounded-lg p-3 space-y-2">
                  <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">{t('myCourses.newLayout')}</p>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">{t('myCourses.layout')}</label>
                    <input
                      className="border rounded px-2 py-1 w-full text-sm"
                      placeholder={t('myCourses.layoutPlaceholder')}
                      value={layoutForm.name}
                      onChange={e => setLayoutForm(d => ({ ...d, name: e.target.value }))}
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {[['slope', 'Slope'], ['course_rating', 'CR'], ['par_total', 'Par']].map(([field, label]) => (
                      <div key={field}>
                        <label className="block text-xs font-medium text-gray-600">{label}</label>
                        <input
                          type="number"
                          inputMode={field === 'par_total' ? 'numeric' : 'decimal'}
                          className="border rounded px-2 py-1 w-full text-sm"
                          value={layoutForm[field]}
                          onChange={e => setLayoutForm(d => ({ ...d, [field]: e.target.value }))}
                        />
                      </div>
                    ))}
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">
                      {t('myCourses.teeNameOptional')} <span className="text-gray-400 font-normal">{t('myCourses.teeNameOptionalNote')}</span>
                    </label>
                    <input
                      className="border rounded px-2 py-1 w-full text-sm"
                      placeholder={t('myCourses.teeNameOptionalPlaceholder')}
                      value={layoutForm.tee_name}
                      onChange={e => setLayoutForm(d => ({ ...d, tee_name: e.target.value }))}
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => addLayout(course.id)}
                      className="bg-green-700 text-white px-3 py-1 rounded text-sm flex-1"
                    >
                      {t('myCourses.save')}
                    </button>
                    <button
                      onClick={() => { setAddingLayoutTo(null); setLayoutForm(EMPTY_LAYOUT_FORM) }}
                      className="border px-3 py-1 rounded text-sm flex-1"
                    >
                      {t('myCourses.cancel')}
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => { setAddingLayoutTo(course.id); setLayoutForm(EMPTY_LAYOUT_FORM) }}
                  className="text-sm text-green-700 underline"
                >
                  {t('myCourses.addLayout')}
                </button>
              )}
            </div>
          )}
        </div>
      ))}

      {courses.length === 0 && !addingCourse && (
        <p className="text-gray-500 text-center py-8">{t('myCourses.noCourses')}</p>
      )}
    </div>
  )
}
