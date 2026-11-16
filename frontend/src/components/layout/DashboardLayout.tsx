import type { ReactNode } from 'react'

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

type DashboardLayoutProps = {
  activePage: string
  onPageChange: (page: string) => void
  children: ReactNode
}

export default function DashboardLayout({
  activePage,
  onPageChange,
  children,
}: DashboardLayoutProps) {
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

        <nav aria-label="Main navigation" className="flex gap-2 overflow-x-auto md:flex-col">
          {pages.map((page) => (
            <button
              key={page}
              type="button"
              aria-current={activePage === page ? 'page' : undefined}
              onClick={() => onPageChange(page)}
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

      <main className="min-w-0 flex-1 p-5 md:p-8">{children}</main>
    </div>
  )
}