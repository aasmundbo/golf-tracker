export default function TeeSelector({ courseDetail, onSelect }) {
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

  return (
    <div>
      <label className="block text-sm font-medium mb-1">Select Tee</label>
      <div className="grid gap-2">
        {tees.map((tee, i) => (
          <button key={i} onClick={() => onSelect(tee)}
            className="text-left border rounded px-3 py-2 hover:bg-green-50 flex justify-between">
            <span className="font-medium">{tee.tee_name || tee.name}</span>
            <span className="text-sm text-gray-500">
              SR {tee.slope_rating || tee.slope} / CR {tee.course_rating}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
