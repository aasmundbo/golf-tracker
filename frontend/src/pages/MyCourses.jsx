import { useEffect, useState } from 'react'
import api from '../api/client'

export default function MyCourses() {
  const [courses, setCourses] = useState([])
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ name: '', city: '', country: '' })

  const load = () => api.get('/courses/local').then(r => setCourses(r.data)).catch(() => {})
  useEffect(() => { load() }, [])

  const addCourse = async () => {
    await api.post('/courses/local', form)
    setAdding(false)
    setForm({ name: '', city: '', country: '' })
    load()
  }

  const deleteCourse = async (id) => {
    if (!confirm('Delete this course?')) return
    await api.delete(`/courses/local/${id}`)
    load()
  }

  return (
    <div className="space-y-4 mt-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">My Courses</h2>
        <button onClick={() => setAdding(!adding)} className="bg-green-700 text-white px-3 py-1 rounded text-sm">+ Add</button>
      </div>
      {adding && (
        <div className="bg-white border rounded-xl p-4 space-y-3">
          {['name', 'city', 'country'].map(f => (
            <div key={f}>
              <label className="block text-sm font-medium capitalize">{f}</label>
              <input className="border rounded px-3 py-2 w-full" value={form[f]}
                onChange={e => setForm(d => ({ ...d, [f]: e.target.value }))} />
            </div>
          ))}
          <button onClick={addCourse} className="bg-green-700 text-white px-4 py-2 rounded w-full">Save Course</button>
        </div>
      )}
      {courses.map(c => (
        <div key={c.id} className="bg-white border rounded-xl p-4 flex justify-between items-center">
          <div>
            <span className="font-semibold">{c.name}</span>
            {c.city && <span className="text-sm text-gray-500 ml-2">{c.city}</span>}
            {c.is_verified && <span className="ml-2 text-xs bg-green-100 text-green-700 px-1 rounded">✓ verified</span>}
          </div>
          <button onClick={() => deleteCourse(c.id)} className="text-red-500 text-sm">Delete</button>
        </div>
      ))}
    </div>
  )
}
