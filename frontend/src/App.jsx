import { Routes, Route, Link } from 'react-router-dom'
import NewRound from './pages/NewRound'
import ActiveRound from './pages/ActiveRound'
import History from './pages/History'
import MyCourses from './pages/MyCourses'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-green-700 text-white p-4 flex gap-6 items-center">
        <span className="font-bold text-lg">⛳ Golf Tracker</span>
        <Link to="/" className="hover:underline">Ny runde</Link>
        <Link to="/history" className="hover:underline">Historikk</Link>
        <Link to="/courses" className="hover:underline">Mine baner</Link>
      </nav>
      <main className="max-w-2xl mx-auto p-4">
        <Routes>
          <Route path="/" element={<NewRound />} />
          <Route path="/round/:id" element={<ActiveRound />} />
          <Route path="/history" element={<History />} />
          <Route path="/courses" element={<MyCourses />} />
        </Routes>
      </main>
    </div>
  )
}
