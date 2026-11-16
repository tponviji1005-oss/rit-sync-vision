const weeklyTrend = [
  { label: 'Week 1', value: 78 },
  { label: 'Week 2', value: 82 },
  { label: 'Week 3', value: 88 },
  { label: 'Week 4', value: 84 },
  { label: 'Week 5', value: 94 },
]

const summaries = [
  { label: 'Sessions in preview', value: '18' },
  { label: 'Students in preview', value: '62' },
  { label: 'Needs review', value: '4' },
]

export default function Reports() {
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

      <section className="grid gap-4 sm:grid-cols-3">
        {summaries.map((summary) => (
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
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold">Candidate trend</h3>
              <p className="mt-1 text-sm text-gray-400">
                Example weekly candidate rate
              </p>
            </div>
            <span className="text-xs text-gray-500">Preview · percent</span>
          </div>

          <div
            role="img"
            aria-label="Sample weekly candidate rates: 78, 82, 88, 84, and 94 percent"
            className="mt-6 flex h-56 items-end gap-3 border-b border-l border-white/10 px-3"
          >
            {weeklyTrend.map((item) => (
              <div
                key={item.label}
                className="flex h-full flex-1 flex-col items-center justify-end gap-2"
              >
                <span className="text-xs text-gray-400">{item.value}%</span>
                <div
                  className="w-full max-w-14 rounded-t-md bg-[#cd202c]"
                  style={{ height: `${item.value}%` }}
                />
                <span className="mb-2 text-[10px] text-gray-500">
                  {item.label}
                </span>
              </div>
            ))}
          </div>

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
    </div>
  )
}