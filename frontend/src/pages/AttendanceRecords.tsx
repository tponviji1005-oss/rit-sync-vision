import { useState } from 'react'

type SyncStatus = 'Pending' | 'Syncing' | 'Synced' | 'Failed'

type Session = {
  date: string
  className: string
  subject: string
  total: number
  present: number
  teacherAbsent: number
  notObserved: number
  syncStatus: SyncStatus
}

const sampleSessions: Session[] = [
  {
    date: 'Nov 16, 2026',
    className: 'CSE - A',
    subject: 'AI (CS301)',
    total: 62,
    present: 58,
    teacherAbsent: 2,
    notObserved: 2,
    syncStatus: 'Synced',
  },
  {
    date: 'Nov 13, 2026',
    className: 'CSE - B',
    subject: 'DBMS (CS302)',
    total: 61,
    present: 57,
    teacherAbsent: 1,
    notObserved: 3,
    syncStatus: 'Pending',
  },
  {
    date: 'Nov 12, 2026',
    className: 'CSE - F',
    subject: 'OS (CS403)',
    total: 62,
    present: 58,
    teacherAbsent: 2,
    notObserved: 2,
    syncStatus: 'Syncing',
  },
  {
    date: 'Nov 11, 2026',
    className: 'CSE - A',
    subject: 'AI (CS301)',
    total: 62,
    present: 56,
    teacherAbsent: 3,
    notObserved: 3,
    syncStatus: 'Failed',
  },
]

const statusStyles: Record<SyncStatus, string> = {
  Pending: 'bg-amber-500/10 text-amber-200',
  Syncing: 'bg-sky-500/10 text-sky-200',
  Synced: 'bg-emerald-500/10 text-emerald-200',
  Failed: 'bg-red-500/10 text-red-200',
}

export default function AttendanceRecords() {
  const [search, setSearch] = useState('')

  const filteredSessions = sampleSessions.filter((session) =>
    `${session.date} ${session.className} ${session.subject}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  )

  const syncCounts = {
    Pending: sampleSessions.filter((session) => session.syncStatus === 'Pending').length,
    Syncing: sampleSessions.filter((session) => session.syncStatus === 'Syncing').length,
    Synced: sampleSessions.filter((session) => session.syncStatus === 'Synced').length,
    Failed: sampleSessions.filter((session) => session.syncStatus === 'Failed').length,
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">History</p>
          <h2 className="mt-1 text-2xl font-semibold">Attendance Records</h2>
          <p className="mt-1 text-sm text-gray-400">
            Example teacher-reviewed session summaries
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          Sample preview data
        </span>
      </header>

      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-100">
        “Not observed” is reported separately and is never counted as absent.
      </div>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {(['Pending', 'Syncing', 'Synced', 'Failed'] as const).map((status) => (
          <article
            key={status}
            className="rounded-xl border border-white/10 bg-[#18181b] p-4"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm text-gray-400">{status}</span>
              <span className={`rounded-full px-3 py-1 text-xs ${statusStyles[status]}`}>
                {status}
              </span>
            </div>
            <p className="mt-3 text-2xl font-semibold">{syncCounts[status]}</p>
            <p className="mt-1 text-xs text-gray-500">Example sessions</p>
          </article>
        ))}
      </section>

      <section className="overflow-hidden rounded-xl border border-white/10 bg-[#18181b]">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 p-5">
          <div>
            <h3 className="font-semibold">Session history</h3>
            <p className="mt-1 text-sm text-gray-400">
              Example finalized summaries
            </p>
          </div>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search date, class, or subject..."
            aria-label="Search attendance records"
            className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-2 text-sm outline-none placeholder:text-gray-500 focus:border-[#cd202c] sm:w-72"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1050px] text-left text-sm">
            <thead className="bg-white/5 text-gray-400">
              <tr>
                <th className="px-5 py-3 font-medium">Date</th>
                <th className="px-5 py-3 font-medium">Class</th>
                <th className="px-5 py-3 font-medium">Subject</th>
                <th className="px-5 py-3 font-medium">Students</th>
                <th className="px-5 py-3 font-medium">Present</th>
                <th className="px-5 py-3 font-medium">Teacher-confirmed absent</th>
                <th className="px-5 py-3 font-medium">Not observed</th>
                <th className="px-5 py-3 font-medium">Sync status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {filteredSessions.map((session) => (
                <tr
                  key={`${session.date}-${session.className}`}
                  className="text-gray-200"
                >
                  <td className="px-5 py-4">{session.date}</td>
                  <td className="px-5 py-4 font-medium">{session.className}</td>
                  <td className="px-5 py-4">{session.subject}</td>
                  <td className="px-5 py-4">{session.total}</td>
                  <td className="px-5 py-4 text-emerald-200">{session.present}</td>
                  <td className="px-5 py-4">{session.teacherAbsent}</td>
                  <td className="px-5 py-4 text-gray-400">{session.notObserved}</td>
                  <td className="px-5 py-4">
                    <span className={`rounded-full px-3 py-1 text-xs ${statusStyles[session.syncStatus]}`}>
                      {session.syncStatus}
                    </span>
                  </td>
                </tr>
              ))}
              {filteredSessions.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-5 py-8 text-center text-gray-400">
                    No matching attendance records.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <p className="border-t border-white/10 px-5 py-3 text-xs text-gray-500">
          Preview only. Sync statuses and records are examples, not live backend data.
        </p>
      </section>
    </div>
  )
}