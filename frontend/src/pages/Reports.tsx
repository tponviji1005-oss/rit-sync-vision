import { useState } from 'react'

type ReportRow = {
  week: string
  className: string
  period: 'This month' | 'Last month'
  sessions: number
  students: number
  candidateRate: number
}

const sampleReports: ReportRow[] = [
  { week: 'Week 1', className: 'CSE - A', period: 'This month', sessions: 2, students: 62, candidateRate: 78 },
  { week: 'Week 2', className: 'CSE - A', period: 'This month', sessions: 2, students: 62, candidateRate: 84 },
  { week: 'Week 3', className: 'CSE - B', period: 'This month', sessions: 2, students: 61, candidateRate: 91 },
  { week: 'Week 4', className: 'CSE - F', period: 'This month', sessions: 2, students: 62, candidateRate: 94 },
  { week: 'Week 1', className: 'CSE - A', period: 'Last month', sessions: 2, students: 62, candidateRate: 89 },
  { week: 'Week 2', className: 'CSE - B', period: 'Last month', sessions: 2, students: 61, candidateRate: 87 },
]

export default function Reports() {
  const [classFilter, setClassFilter] = useState('All classes')
  const [periodFilter, setPeriodFilter] = useState<'This month' | 'Last month'>(
    'This month',
  )

  const filteredReports = sampleReports.filter((row) => {
    const matchesClass =
      classFilter === 'All classes' || row.className === classFilter
    return matchesClass && row.period === periodFilter
  })

  const totalSessions = filteredReports.reduce(
    (total, row) => total + row.sessions,
    0,
  )
  const averageCandidateRate =
    filteredReports.length === 0
      ? 0
      : Math.round(
          filteredReports.reduce((total, row) => total + row.candidateRate, 0) /
            filteredReports.length,
        )

  function exportPreviewCsv() {
    const header = 'Week,Class,Period,Sessions,Students,Candidate rate'
    const rows = filteredReports.map((row) =>
      [
        row.week,
        row.className,
        row.period,
        row.sessions,
        row.students,
        `${row.candidateRate}%`,
      ].join(','),
    )
    const csv = [header, ...rows].join('\n')
    const file = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(file)
    const link = document.createElement('a')

    link.href = url
    link.download = 'rit-sync-report-preview.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">Insights</p>
          <h2 className="mt-1 text-2xl font-semibold">Reports &amp; Analytics</h2>
          <p className="mt-1 text-sm text-gray-400">
            Example attendance candidate trends
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          Sample preview data
        </span>
      </header>

      <section className="flex flex-wrap items-end gap-3 rounded-xl border border-white/10 bg-[#18181b] p-5">
        <div>
          <label htmlFor="report-class" className="mb-2 block text-sm text-gray-300">
            Class
          </label>
          <select
            id="report-class"
            value={classFilter}
            onChange={(event) => setClassFilter(event.target.value)}
            className="rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-2 text-sm text-white"
          >
            <option>All classes</option>
            <option>CSE - A</option>
            <option>CSE - B</option>
            <option>CSE - F</option>
          </select>
        </div>

        <div>
          <label htmlFor="report-period" className="mb-2 block text-sm text-gray-300">
            Period
          </label>
          <select
            id="report-period"
            value={periodFilter}
            onChange={(event) =>
              setPeriodFilter(event.target.value as 'This month' | 'Last month')
            }
            className="rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-2 text-sm text-white"
          >
            <option>This month</option>
            <option>Last month</option>
          </select>
        </div>

        <button
          type="button"
          onClick={exportPreviewCsv}
          disabled={filteredReports.length === 0}
          className="rounded-lg bg-[#cd202c] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Export preview CSV
        </button>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Sessions in preview', value: String(totalSessions) },
          {
            label: 'Students represented',
            value: String(
              Math.max(0, ...filteredReports.map((row) => row.students)),
            ),
          },
          { label: 'Average candidate rate', value: `${averageCandidateRate}%` },
        ].map((summary) => (
          <article
            key={summary.label}
            className="rounded-xl border border-white/10 bg-[#18181b] p-5"
          >
            <p className="text-sm text-gray-400">{summary.label}</p>
            <p className="mt-3 text-3xl font-semibold">{summary.value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <article className="rounded-xl border border-white/10 bg-[#18181b] p-5">
          <div>
            <h3 className="font-semibold">Candidate trend</h3>
            <p className="mt-1 text-sm text-gray-400">
              Example weekly candidate rate · {periodFilter}
            </p>
          </div>

          {filteredReports.length === 0 ? (
            <p className="mt-6 rounded-lg bg-[#0d0d0f] p-5 text-sm text-gray-400">
              No preview data for these filters.
            </p>
          ) : (
            <div
              role="img"
              aria-label="Sample weekly candidate rate chart"
              className="mt-6 flex h-56 items-end gap-3 border-b border-l border-white/10 px-3"
            >
              {filteredReports.map((row) => (
                <div
                  key={`${row.period}-${row.className}-${row.week}`}
                  className="flex h-full flex-1 flex-col items-center justify-end gap-2"
                >
                  <span className="text-xs text-gray-400">
                    {row.candidateRate}%
                  </span>
                  <div
                    className="w-full max-w-14 rounded-t-md bg-[#cd202c]"
                    style={{ height: `${row.candidateRate}%` }}
                  />
                  <span className="mb-2 text-[10px] text-gray-500">
                    {row.week}
                  </span>
                </div>
              ))}
            </div>
          )}

          <p className="mt-4 text-xs leading-5 text-gray-500">
            Candidate rates are not final attendance decisions. Teachers review
            and finalize attendance records.
          </p>
        </article>

        <article className="rounded-xl border border-white/10 bg-[#18181b] p-5">
          <h3 className="font-semibold">Review guide</h3>
          <p className="mt-1 text-sm text-gray-400">
            Keep system observations distinct
          </p>

          <div className="mt-5 space-y-3">
            <div className="rounded-lg bg-emerald-500/10 p-4">
              <p className="font-medium text-emerald-200">Present candidate</p>
              <p className="mt-1 text-sm text-gray-400">
                A suggestion for teacher review.
              </p>
            </div>
            <div className="rounded-lg bg-amber-500/10 p-4">
              <p className="font-medium text-amber-200">Needs review</p>
              <p className="mt-1 text-sm text-gray-400">
                Evidence or identity needs a teacher decision.
              </p>
            </div>
            <div className="rounded-lg bg-white/5 p-4">
              <p className="font-medium text-gray-200">Not observed</p>
              <p className="mt-1 text-sm text-gray-400">
                Does not mean absent.
              </p>
            </div>
          </div>
        </article>
      </section>

      <p className="text-xs text-gray-500">
        Preview only. This page and its CSV export use example data, not live
        attendance records.
      </p>
    </div>
  )
}