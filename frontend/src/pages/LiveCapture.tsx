const processingSteps = [
  'Face detection',
  'Face tracking',
  'Identity matching',
  'Candidate review',
]

const summaryItems = [
  { label: 'Present candidates', value: '—', color: 'text-emerald-200' },
  { label: 'Needs review', value: '—', color: 'text-amber-200' },
  { label: 'Not observed', value: '—', color: 'text-gray-300' },
]

export default function LiveCapture() {
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">Attendance session</p>
          <h2 className="mt-1 text-2xl font-semibold">Live Capture</h2>
          <p className="mt-1 text-sm text-gray-400">
            Monitor the session and processing status
          </p>
        </div>
        <span className="rounded-full border border-gray-500/40 bg-white/5 px-3 py-1 text-xs text-gray-300">
          Idle · preview only
        </span>
      </header>

      <section className="grid gap-6 xl:grid-cols-[1.5fr_0.8fr]">
        <div className="rounded-xl border border-white/10 bg-[#18181b] p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-semibold">Camera preview</h3>
              <p className="mt-1 text-sm text-gray-400">
                No camera is connected in this preview
              </p>
            </div>
            <select
              aria-label="Select class"
              defaultValue="CSE - A"
              className="rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-2 text-sm text-white"
            >
              <option>CSE - A</option>
              <option>CSE - B</option>
              <option>CSE - F</option>
            </select>
          </div>

          <div className="grid min-h-72 place-items-center rounded-xl border border-dashed border-white/20 bg-[#0d0d0f] p-6 text-center">
            <div>
              <div className="mx-auto mb-4 grid size-16 place-items-center rounded-full border border-white/20 text-2xl text-gray-500">
                ○
              </div>
              <p className="font-medium">Capture session is idle</p>
              <p className="mt-2 max-w-sm text-sm text-gray-500">
                The camera feed will appear here after an authorized camera
                integration is connected.
              </p>
            </div>
          </div>

          <button
            type="button"
            disabled
            className="mt-4 w-full cursor-not-allowed rounded-lg bg-[#cd202c] px-4 py-3 text-sm font-semibold text-white opacity-50"
          >
            Start capture · integration pending
          </button>
        </div>

        <div className="space-y-6">
          <section className="rounded-xl border border-white/10 bg-[#18181b] p-5">
            <h3 className="font-semibold">AI processing status</h3>
            <p className="mt-1 text-sm text-gray-400">Waiting for a session</p>

            <div className="mt-4 space-y-3">
              {processingSteps.map((step) => (
                <div
                  key={step}
                  className="flex items-center justify-between rounded-lg bg-[#0d0d0f] px-4 py-3"
                >
                  <span className="text-sm text-gray-300">{step}</span>
                  <span className="text-xs text-gray-500">Waiting</span>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-white/10 bg-[#18181b] p-5">
            <h3 className="font-semibold">Attendance candidates</h3>
            <div className="mt-4 space-y-3">
              {summaryItems.map((item) => (
                <div key={item.label} className="flex justify-between text-sm">
                  <span className="text-gray-400">{item.label}</span>
                  <span className={`font-medium ${item.color}`}>{item.value}</span>
                </div>
              ))}
            </div>
            <p className="mt-4 border-t border-white/10 pt-4 text-xs leading-5 text-gray-500">
              AI can suggest candidates. A teacher must review and finalize
              attendance.
            </p>
          </section>
        </div>
      </section>
    </div>
  )
}