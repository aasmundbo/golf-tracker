export default function Scorecard({ scores, totalHoles }) {
  return (
    <div className="overflow-x-auto">
      <table className="text-sm w-full border-collapse">
        <thead>
          <tr className="bg-green-50">
            <th className="border px-2 py-1">Hole</th>
            <th className="border px-2 py-1">Par</th>
            <th className="border px-2 py-1">SI</th>
            <th className="border px-2 py-1">Gross</th>
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: totalHoles }, (_, i) => i + 1).map(h => {
            const s = scores[h]
            return (
              <tr key={h} className={s ? '' : 'text-gray-300'}>
                <td className="border px-2 py-1 text-center">{h}</td>
                <td className="border px-2 py-1 text-center">{s?.hole_par ?? '-'}</td>
                <td className="border px-2 py-1 text-center">{s?.hole_stroke_index ?? '-'}</td>
                <td className="border px-2 py-1 text-center font-medium">{s?.strokes ?? '-'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
