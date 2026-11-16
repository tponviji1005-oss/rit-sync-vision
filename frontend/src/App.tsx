import { useState } from 'react'
import AttendanceRecords from './pages/AttendanceRecords'
import AttendanceReview from './pages/AttendanceReview'
import Classes from './pages/Classes'
import Dashboard from './pages/Dashboard'
import FaceRegistration from './pages/FaceRegistration'
import LiveCapture from './pages/LiveCapture'
import Login from './pages/Login'
import Profile from './pages/Profile'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import Students from './pages/Students'
import SystemStatus from './pages/SystemStatus'

const pages = [
  'Login / Authentication',
  'Dashboard',
  'Classes',
  'Students',
  'Face Registration',
  'Live Capture',
  'Attendance Review',
  'Attendance Records',
  'Reports',
  'System Status',
  'Settings',
  'Profile / Account',
]

function App() {
  const [activePage, setActivePage] = useState('Dashboard')

  return (
    <div className="min-h-screen bg-[#0d0d0f] text-white md:flex">
      <aside className="border-b border-white/10 bg-[#141416] p-4 md:min-h-screen md:w-64 md:border-b-0 md:border-r">
        <div className="mb-6 flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-[#cd202c] font-bold">
            R
          </div>
          <div>
            <p className="font-semibold">RIT-Sync Vision</p>
            <p className="text-xs text-gray-400">Classroom attendance</p>
          </div>
        </div>

        <nav className="flex gap-2 overflow-x-auto md:flex-col">
          {pages.map((page) => (
            <button
              key={page}
              onClick={() => setActivePage(page)}
              className={`shrink-0 rounded-lg px-3 py-2 text-left text-sm transition ${
                activePage === page
                  ? 'bg-[#cd202c] text-white'
                  : 'text-gray-300 hover:bg-white/10'
              }`}
            >
              {page}
            </button>
          ))}
        </nav>
      </aside>

      <main className="min-w-0 flex-1 p-5 md:p-8">
        {activePage === 'Login / Authentication' ? (
          <Login />
        ) : activePage === 'Dashboard' ? (
          <Dashboard />
        ) : activePage === 'Classes' ? (
          <Classes />
        ) : activePage === 'Students' ? (
          <Students />
        ) : activePage === 'Face Registration' ? (
          <FaceRegistration />
        ) : activePage === 'Live Capture' ? (
          <LiveCapture />
        ) : activePage === 'Attendance Review' ? (
          <AttendanceReview />
        ) : activePage === 'Attendance Records' ? (
          <AttendanceRecords />
        ) : activePage === 'Reports' ? (
          <Reports />
        ) : activePage === 'System Status' ? (
          <SystemStatus />
        ) : activePage === 'Settings' ? (
          <Settings />
        ) : (
          <Profile />
        )}
      </main>
    </div>
  )
}

export default App