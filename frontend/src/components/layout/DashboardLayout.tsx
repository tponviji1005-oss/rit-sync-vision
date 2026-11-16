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
        <div className="mb-5 flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-xl bg-[#cd202c] font-bold">
            R
          </div>
          <div>
            <p className="font-semibold">RIT-Sync Vision</p>
            <p className="text-xs text-gray-400">Classroom attendance</p>
          </div>
        </div>

        <label htmlFor="mobile-navigation" className="sr-only">
          Choose a page
        </label>
        <select
          id="mobile-navigation"
          value={activePage}
          onChange={(event) => onPageChange(event.target.value)}
          className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-white outline-none focus:border-[#cd202c] md:hidden"
        >
          {pages.map((page) => (
            <option key={page} value={page}>
              {page}
            </option>
          ))}
        </select>

        <nav aria-label="Main navigation" className="hidden gap-2 md:flex md:flex-col">
          {pages.map((page) => (
            <button
              key={page}
              type="button"
              aria-current={activePage === page ? 'page' : undefined}
              onClick={() => onPageChange(page)}
              className={`rounded-lg px-3 py-2 text-left text-sm transition ${
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

      <main className="min-w-0 flex-1 p-4 sm:p-5 md:p-8">{children}</main>
    </div>
  )
}