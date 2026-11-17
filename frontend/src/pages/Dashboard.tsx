const metrics = [
  { label: 'Students enrolled', value: '246' },
  { label: 'Sessions today', value: '3' },
  { label: 'Present candidates', value: '58' },
  { label: 'Needs review', value: '4' },
]

const classes = [
  { name: 'CSE - A', subject: 'AI (CS301)', time: '10:00 AM', status: 'Ready' },
  { name: 'CSE - B', subject: 'DBMS (CS302)', time: '11:30 AM', status: 'Ready' },
  { name: 'CSE - F', subject: 'OS (CS403)', time: '02:00 PM', status: 'Ready' },
]

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">Teacher workspace</p>
          <h2 className="mt-1 text-2xl font-semibold">Dashboard</h2>
          <p className="mt-1 text-sm text-gray-400">
            Classroom attendance overview
          </p>
        </div>

        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          Sample preview data
        </span>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <article
            key={metric.label}
            className="rounded-xl border border-white/10 bg-[#18181b] p-5"
          >
            <p className="text-sm text-gray-400">{metric.label}</p>
            <p className="mt-3 text-3xl font-semibold">{metric.value}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <article className="overflow-hidden rounded-xl border border-white/10 bg-[#18181b]">
          <div className="border-b border-white/10 p-5">
            <h3 className="font-semibold">Today’s classes</h3>
            <p className="mt-1 text-sm text-gray-400">
              Example schedule for the interface preview
            </p>
          </div>

          <div className="divide-y divide-white/10">
            {classes.map((classItem) => (
              <div
                key={classItem.name}
                className="grid gap-2 p-5 sm:grid-cols-[1fr_1fr_auto] sm:items-center"
              >
                <div>
                  <p className="font-medium">{classItem.name}</p>
                  <p className="text-sm text-gray-400">{classItem.subject}</p>
                </div>
                <p className="text-sm text-gray-300">{classItem.time}</p>
                <span className="w-fit rounded-full bg-white/10 px-3 py-1 text-xs text-gray-300">
                  {classItem.status}
                </span>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-xl border border-white/10 bg-[#18181b] p-5">
          <h3 className="font-semibold">Attendance review</h3>
          <p className="mt-1 text-sm text-gray-400">
            Example candidate summary
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-emerald-500/10 p-4">
              <p className="text-sm text-emerald-200">Present candidates</p>
              <p className="mt-2 text-2xl font-semibold text-emerald-100">58</p>
            </div>
            <div className="rounded-lg bg-amber-500/10 p-4">
              <p className="text-sm text-amber-200">Needs review</p>
              <p className="mt-2 text-2xl font-semibold text-amber-100">4</p>
            </div>
          </div>

          <p className="mt-5 text-sm leading-6 text-gray-400">
            A teacher reviews and finalizes attendance. “Not observed” does not
            automatically mean “absent.”
          </p>
        </article>
      </section>
    </div>
  )
}