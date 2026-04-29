import { useEffect, useState } from 'react'
import api from '../api/client'

const EMPTY_COURSE_FORM = { name: '', city: '', country: '', layout_name: 'Hovedbane', tee_name: 'gul', slope: '', course_rating: '', par_total: '' }
const EMPTY_LAYOUT_FORM = { name: '', slope: '', course_rating: '', par_total: '', tee_name: '' }
const EMPTY_TEE_FORM = { name: '', slope: '', course_rating: '', par_total: '' }

export default function MyCourses() {
  const [courses, setCourses] = useState([])
  const [expandedCourse, setExpandedCourse] = useState(null)
  const [layouts, setLayouts] = useState({})         // course_id → layout[]
  const [expandedLayout, setExpandedLayout] = useState(null)
  const [layoutTees, setLayoutTees] = useState({})   // layout_id → tee[]

  const [addingCourse, setAddingCourse] = useState(false)
  const [courseForm, setCourseForm] = useState(EMPTY_COURSE_FORM)
  const [courseError, setCourseError] = useState(null)

  const [addingLayoutTo, setAddingLayoutTo] = useState(null)  // course_id
  const [layoutForm, setLayoutForm] = useState(EMPTY_LAYOUT_FORM)

  const [addingTeeTo, setAddingTeeTo] = useState(null)        // layout_id
  const [teeForm, setTeeForm] = useState(EMPTY_TEE_FORM)

  // ── Load ────────────────────────────────────────────────────────────────────

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

  // ── Toggle expand ────────────────────────────────────────────────────────────

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

  // ── Top-level course ─────────────────────────────────────────────────────────

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
      setCourseError(err.response?.data?.detail ?? err.message ?? 'Noe gikk galt')
    }
  }

  const deleteCourse = async (id) => {
    if (!confirm('Slett banen? Dette sletter alle varianter og teer.')) return
    try {
      await api.delete(`/courses/${id}`)
      setExpandedCourse(prev => (prev === id ? null : prev))
      setLayouts(prev => { const n = { ...prev }; delete n[id]; return n })
      loadCourses()
    } catch (err) {
      alert(err.response?.data?.detail ?? err.message ?? 'Sletting feilet')
    }
  }

  // ── Layout (variant) ─────────────────────────────────────────────────────────

  const addLayout = async (courseId) => {
    if (!layoutForm.name.trim()) return
    const payload = {
      name: layoutForm.name,
      tee_name: layoutForm.tee_name || undefined,
      slope: layoutForm.slope ? parseFloat(layoutForm.slope) : undefined,
      course_rating: layoutForm.course_rating ? parseFloat(layoutForm.course_rating) : undefined,
      par_total: layoutForm.par_total ? parseInt(layoutForm.par_total) : undefined,
    }
    await api.post(`/courses/${courseId}/layouts`, payload)
    setAddingLayoutTo(null)
    setLayoutForm(EMPTY_LAYOUT_FORM)
    await loadLayouts(courseId)
  }

  const deleteLayout = async (courseId, layoutId) => {
    if (!confirm('Slett banevariant?')) return
    await api.delete(`/courses/local/${layoutId}`)
    setLayouts(prev => ({
      ...prev,
      [courseId]: (prev[courseId] || []).filter(l => l.id !== layoutId),
    }))
    if (expandedLayout === layoutId) setExpandedLayout(null)
  }

  // ── Tee ──────────────────────────────────────────────────────────────────────

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

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4 mt-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Mine baner</h2>
        <button
          onClick={() => { setAddingCourse(!addingCourse); setCourseForm(EMPTY_COURSE_FORM); setCourseError(null) }}
          className="bg-green-700 text-white px-3 py-1 rounded text-sm"
        >
          + Legg til bane
        </button>
      </div>

      {/* New top-level course form */}
      {addingCourse && (
        <div className="bg-white border rounded-xl p-4 space-y-3">
          <h3 className="font-semibold text-sm">Ny bane</h3>
          <div>
            <label className="block text-sm font-medium">Banenavn</label>
            <input
              className="border rounded px-3 py-2 w-full"
              placeholder="f.eks. Bærum Golfklubb"
              value={courseForm.name}
              onChange={e => setCourseForm(d => ({ ...d, name: e.target.value }))}
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm font-medium">By</label>
              <input className="border rounded px-3 py-2 w-full" value={courseForm.city}
                onChange={e => setCourseForm(d => ({ ...d, city: e.target.value }))} />
            </div>
            <div>
              <label className="block text-sm font-medium">Land</label>
              <input className="border rounded px-3 py-2 w-full" value={courseForm.country}
                onChange={e => setCourseForm(d => ({ ...d, country: e.target.value }))} />
            </div>
          </div>
          <div className="border-t pt-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Første banevariant</p>
            <div className="space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-sm font-medium">Variant</label>
                  <input
                    className="border rounded px-3 py-2 w-full"
                    placeholder="f.eks. Hovedbane"
                    value={courseForm.layout_name}
                    onChange={e => setCourseForm(d => ({ ...d, layout_name: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium">Utslagssted</label>
                  <input
                    className="border rounded px-3 py-2 w-full"
                    placeholder="f.eks. gul"
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
                      className="border rounded px-3 py-2 w-full"
                      value={courseForm[field]}
                      onChange={e => setCourseForm(d => ({ ...d, [field]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
          {courseError && (
            <p className="text-red-600 text-sm">{courseError}</p>
          )}
          <div className="flex gap-2">
            <button type="button" onClick={addCourse} className="bg-green-700 text-white px-4 py-2 rounded flex-1 text-sm">Lagre</button>
            <button type="button" onClick={() => { setAddingCourse(false); setCourseForm(EMPTY_COURSE_FORM); setCourseError(null) }} className="border px-4 py-2 rounded flex-1 text-sm">Avbryt</button>
          </div>
        </div>
      )}

      {/* Course list */}
      {courses.map(course => (
        <div key={course.id} className="bg-white border rounded-xl overflow-hidden">

          {/* Course header row */}
          <div
            className="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50"
            onClick={() => toggleCourse(course.id)}
          >
            <div>
              <span className="font-semibold">{course.name}</span>
              {course.city && <span className="text-sm text-gray-500 ml-2">{course.city}</span>}
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={e => { e.stopPropagation(); deleteCourse(course.id) }}
                className="text-red-500 text-sm"
              >
                Slett
              </button>
              <span className="text-gray-400 text-sm select-none">
                {expandedCourse === course.id ? '▲' : '▼'}
              </span>
            </div>
          </div>

          {/* Expanded: layouts */}
          {expandedCourse === course.id && (
            <div className="border-t bg-gray-50 px-4 py-3 space-y-2">

              {(layouts[course.id] || []).map(layout => (
                <div key={layout.id} className="bg-white border rounded-lg overflow-hidden">

                  {/* Layout header row */}
                  <div
                    className="px-3 py-2 flex justify-between items-center cursor-pointer hover:bg-green-50"
                    onClick={() => toggleLayout(layout.id)}
                  >
                    <span className="font-medium text-sm">{layout.name}</span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={e => { e.stopPropagation(); deleteLayout(course.id, layout.id) }}
                        className="text-red-500 text-xs"
                      >
                        Slett
                      </button>
                      <span className="text-gray-400 text-xs select-none">
                        {expandedLayout === layout.id ? '▲' : '▼'}
                      </span>
                    </div>
                  </div>

                  {/* Expanded: tees */}
                  {expandedLayout === layout.id && (
                    <div className="border-t px-3 py-2 space-y-1">
                      {(layoutTees[layout.id] || []).map(t => (
                        <div key={t.id} className="flex justify-between py-1 border-b last:border-0 text-sm text-gray-700">
                          <span>{t.name}</span>
                          <span className="text-gray-400 text-xs">
                            SR {t.slope ?? '–'} / CR {t.course_rating ?? '–'} / Par {t.par_total ?? '–'}
                          </span>
                        </div>
                      ))}
                      {(layoutTees[layout.id] || []).length === 0 && addingTeeTo !== layout.id && (
                        <p className="text-gray-400 italic text-xs py-1">Ingen teer lagt til</p>
                      )}

                      {/* Add tee inline form */}
                      {addingTeeTo === layout.id ? (
                        <div className="pt-2 space-y-2">
                          <div>
                            <label className="block text-xs font-medium text-gray-600">Tee-navn</label>
                            <input
                              className="border rounded px-2 py-1 w-full text-sm"
                              placeholder="f.eks. Gul"
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
                              Lagre
                            </button>
                            <button
                              onClick={() => { setAddingTeeTo(null); setTeeForm(EMPTY_TEE_FORM) }}
                              className="border px-3 py-1 rounded text-xs flex-1"
                            >
                              Avbryt
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => { setAddingTeeTo(layout.id); setTeeForm(EMPTY_TEE_FORM) }}
                          className="text-xs text-green-700 underline pt-1 block"
                        >
                          + Legg til tee
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {/* Add layout inline form */}
              {addingLayoutTo === course.id ? (
                <div className="bg-white border rounded-lg p-3 space-y-2">
                  <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Ny banevariant</p>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">Variant</label>
                    <input
                      className="border rounded px-2 py-1 w-full text-sm"
                      placeholder="f.eks. Hovedbane"
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
                          className="border rounded px-2 py-1 w-full text-sm"
                          value={layoutForm[field]}
                          onChange={e => setLayoutForm(d => ({ ...d, [field]: e.target.value }))}
                        />
                      </div>
                    ))}
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600">
                      Tee-navn <span className="text-gray-400 font-normal">(valgfritt, brukes hvis slope/CR er satt)</span>
                    </label>
                    <input
                      className="border rounded px-2 py-1 w-full text-sm"
                      placeholder="f.eks. Hvit"
                      value={layoutForm.tee_name}
                      onChange={e => setLayoutForm(d => ({ ...d, tee_name: e.target.value }))}
                    />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => addLayout(course.id)}
                      className="bg-green-700 text-white px-3 py-1 rounded text-sm flex-1"
                    >
                      Lagre
                    </button>
                    <button
                      onClick={() => { setAddingLayoutTo(null); setLayoutForm(EMPTY_LAYOUT_FORM) }}
                      className="border px-3 py-1 rounded text-sm flex-1"
                    >
                      Avbryt
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => { setAddingLayoutTo(course.id); setLayoutForm(EMPTY_LAYOUT_FORM) }}
                  className="text-sm text-green-700 underline"
                >
                  + Legg til variant
                </button>
              )}
            </div>
          )}
        </div>
      ))}

      {courses.length === 0 && !addingCourse && (
        <p className="text-gray-500 text-center py-8">Ingen baner lagt til ennå.</p>
      )}
    </div>
  )
}
