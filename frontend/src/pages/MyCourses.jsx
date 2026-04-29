import { useEffect, useState } from 'react'
import api from '../api/client'

export default function MyCourses() {
  const [courses, setCourses] = useState([]) // top-level "baner" (LocalClub)
  const [expandedCourse, setExpandedCourse] = useState(null)
  const [layouts, setLayouts] = useState({}) // course_id → layout[]
  const [expandedLayout, setExpandedLayout] = useState(null)
  const [layoutTees, setLayoutTees] = useState({}) // layout_id → tee[]
  const [addingCourse, setAddingCourse] = useState(false)
  const [addingLayoutTo, setAddingLayoutTo] = useState(null) // course_id
  const [courseForm, setCourseForm] = useState({ name: '', city: '', country: '' })
  const [layoutForm, setLayoutForm] = useState({ name: '' })

  const loadCourses = () =>
    api.get('/courses').then(r => setCourses(r.data)).catch(() => {})

  useEffect(() => { loadCourses() }, [])

  const toggleCourse = async (courseId) => {
    if (expandedCourse === courseId) { setExpandedCourse(null); return }
    setExpandedCourse(courseId)
    if (!layouts[courseId]) {
      const res = await api.get(`/courses/${courseId}/layouts`)
      setLayouts(prev => ({ ...prev, [courseId]: res.data }))
    }
  }

  const toggleLayout = async (layoutId) => {
    if (expandedLayout === layoutId) { setExpandedLayout(null); return }
    setExpandedLayout(layoutId)
    if (!layoutTees[layoutId]) {
      const res = await api.get(`/courses/local/${layoutId}/tees`)
      setLayoutTees(prev => ({ ...prev, [layoutId]: res.data }))
    }
  }

  const addCourse = async () => {
    await api.post('/courses', courseForm)
    setAddingCourse(false)
    setCourseForm({ name: '', city: '', country: '' })
    loadCourses()
  }

  const deleteCourse = async (id) => {
    if (!confirm('Slett banen? Dette sletter alle banevaranter og teer.')) return
    await api.delete(`/courses/${id}`)
    setExpandedCourse(prev => (prev === id ? null : prev))
    setLayouts(prev => { const n = { ...prev }; delete n[id]; return n })
    loadCourses()
  }

  const addLayout = async (courseId) => {
    await api.post(`/courses/${courseId}/layouts`, layoutForm)
    setAddingLayoutTo(null)
    setLayoutForm({ name: '' })
    const res = await api.get(`/courses/${courseId}/layouts`)
    setLayouts(prev => ({ ...prev, [courseId]: res.data }))
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

  const FIELD_LABELS = { name: 'Banenavn', city: 'By', country: 'Land' }

  return (
    <div className="space-y-4 mt-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Mine baner</h2>
        <button
          onClick={() => setAddingCourse(!addingCourse)}
          className="bg-green-700 text-white px-3 py-1 rounded text-sm"
        >
          + Legg til bane
        </button>
      </div>

      {addingCourse && (
        <div className="bg-white border rounded-xl p-4 space-y-3">
          <h3 className="font-semibold">Ny bane</h3>
          {['name', 'city', 'country'].map(f => (
            <div key={f}>
              <label className="block text-sm font-medium">{FIELD_LABELS[f]}</label>
              <input
                className="border rounded px-3 py-2 w-full"
                value={courseForm[f]}
                onChange={e => setCourseForm(d => ({ ...d, [f]: e.target.value }))}
              />
            </div>
          ))}
          <div className="flex gap-2">
            <button onClick={addCourse} className="bg-green-700 text-white px-4 py-2 rounded flex-1">Lagre</button>
            <button onClick={() => setAddingCourse(false)} className="border px-4 py-2 rounded flex-1">Avbryt</button>
          </div>
        </div>
      )}

      {courses.map(course => (
        <div key={course.id} className="bg-white border rounded-xl overflow-hidden">
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
              <span className="text-gray-400 text-sm">{expandedCourse === course.id ? '▲' : '▼'}</span>
            </div>
          </div>

          {expandedCourse === course.id && (
            <div className="border-t px-4 py-3 space-y-2 bg-gray-50">
              {(layouts[course.id] || []).map(layout => (
                <div key={layout.id} className="bg-white border rounded-lg overflow-hidden">
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
                      <span className="text-gray-400 text-xs">{expandedLayout === layout.id ? '▲' : '▼'}</span>
                    </div>
                  </div>
                  {expandedLayout === layout.id && (
                    <div className="border-t px-3 py-2 text-sm">
                      {(layoutTees[layout.id] || []).length === 0 ? (
                        <p className="text-gray-400 italic text-xs">Ingen teer lagt til</p>
                      ) : (
                        (layoutTees[layout.id] || []).map(t => (
                          <div key={t.id} className="flex justify-between py-1 border-b last:border-0 text-gray-600">
                            <span>{t.name}</span>
                            <span className="text-gray-400 text-xs">
                              SR {t.slope ?? '–'} / CR {t.course_rating ?? '–'}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              ))}

              {addingLayoutTo === course.id ? (
                <div className="bg-white border rounded-lg p-3 space-y-2">
                  <label className="block text-sm font-medium">Navn på banevariant</label>
                  <input
                    className="border rounded px-3 py-2 w-full text-sm"
                    placeholder="f.eks. Hovedbane"
                    value={layoutForm.name}
                    onChange={e => setLayoutForm({ name: e.target.value })}
                  />
                  <div className="flex gap-2">
                    <button onClick={() => addLayout(course.id)} className="bg-green-700 text-white px-3 py-1 rounded text-sm flex-1">Lagre</button>
                    <button onClick={() => setAddingLayoutTo(null)} className="border px-3 py-1 rounded text-sm flex-1">Avbryt</button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setAddingLayoutTo(course.id)}
                  className="text-sm text-green-700 underline"
                >
                  + Legg til banevariant
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
