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
import DashboardLayout from './components/layout/DashboardLayout'

function App() {
  const [activePage, setActivePage] = useState('Dashboard')

  const pageContent =
    activePage === 'Login / Authentication' ? (
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
    )

  return (
    <DashboardLayout activePage={activePage} onPageChange={setActivePage}>
      {pageContent}
    </DashboardLayout>
  )
}

export default App