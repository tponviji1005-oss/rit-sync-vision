import { useState } from 'react'

const pages = [
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
]

const todayClasses = [
  { name: 'CSE - A', subject: 'AI (CS301)', time: '10:00 AM' },
  { name: 'CSE - B', subject: 'DBMS (CS302)', time: '11:30 AM' },
  { name: 'CSE - F', subject: 'OS (CS403)', time: '02:00 PM' },
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
        <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="mb-1 text-sm text-gray-400">Teacher workspace</p>
            <h1 className="text-2xl font-semibold">{activePage}</h1>
          </div>
          <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
            Preview data
          </span>
        </header>

        {activePage === 'Dashboard' ? (
          <>
            <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {[
                ['Students enrolled', '246'],
                ['Sessions today', '3'],
                ['Present candidates', '94.3%'],
              ].map(([label, value]) => (
                <article
                  key={label}
                  className="rounded-xl border border-white/10 bg-[#18181b] p-5"
                >
                  <p className="text-sm text-gray-400">{label}</p>
                  <p className="mt-3 text-3xl font-semibold">{value}</p>
                </article>
              ))}
            </section>

            <section className="rounded-xl border border-white/10 bg-[#18181b]">
              <div className="border-b border-white/10 p-5">
                <h2 className="font-semibold">Today’s classes</h2>
                <p className="mt-1 text-sm text-gray-400">
                  Example schedule for the interface preview
                </p>
              </div>

              <div className="divide-y divide-white/10">
                {todayClasses.map((classItem) => (
                  <div
                    key={classItem.name}
                    className="flex flex-wrap items-center justify-between gap-3 p-5"
                  >
                    <div>
                      <p className="font-medium">{classItem.name}</p>
                      <p className="text-sm text-gray-400">
                        {classItem.subject}
                      </p>
                    </div>
                    <span className="text-sm text-gray-300">
                      {classItem.time}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <p className="mt-5 text-sm text-gray-400">
              Attendance suggestions require teacher review before records are
              finalized.
            </p>
          </>
        ) : (
          <section className="rounded-xl border border-white/10 bg-[#18181b] p-6">
            <h2 className="font-semibold">{activePage}</h2>
            <p className="mt-2 text-sm text-gray-400">
              This screen is planned for the frontend. It is not connected to
              live data yet.
            </p>
          </section>
        )}
      </main>
    </div>
  )
}

export default App