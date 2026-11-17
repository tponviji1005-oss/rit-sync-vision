import { useState } from 'react'

const steps = ['Face detection', 'Face tracking', 'Identity matching', 'Attendance review']

export default function LiveCapture() {
  const [previewActive, setPreviewActive] = useState(false)
  const [className, setClassName] = useState('CSE - A')

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-gray-400">Classroom monitoring</p>
        <h1 className="mt-1 text-3xl font-semibold">Live Capture & AI Processing</h1>
        <p className="mt-2 text-gray-400">
          Preview the capture session and processing status.
        </p>
      </header>

      <section className="flex flex-wrap items-end gap-4 rounded-xl border border-white/10 bg-[#18181b] p-5">
        <label className="block min-w-48 space-y-2">
          <span className="text-sm text-gray-300">Class</span>
          <select
            value={className}
            onChange={(event) => setClassName(event.target.value)}
            className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-4 py-3 text-white"
          >
            <option>CSE - A</option>
            <option>CSE - B</option>
            <option>CSE - F</option>
          </select>
        </label>

        <button
          type="button"
          onClick={() => setPreviewActive((active) => !active)}
          className={`rounded-lg px-5 py-3 font-medium text-white ${
            previewActive
              ? 'border border-white/20 bg-white/10 hover:bg-white/20'
              : 'bg-[#cd202c] hover:bg-red-700'
          }`}
        >
          {previewActive ? 'Stop preview' : 'Start preview'}
        </button>

        <span className="text-sm text-gray-400">
          {previewActive ? 'Preview session active' : 'Session not started'}
        </span>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]">
        <div className="flex min-h-80 flex-col items-center justify-center rounded-xl border border-dashed border-white/20 bg-[#18181b] p-8 text-center">
          <div className="grid size-16 place-items-center rounded-full bg-white/10 text-3xl">
            ◉
          </div>
          <h2 className="mt-4 text-xl font-semibold">Camera preview unavailable</h2>
          <p className="mt-2 max-w-lg text-sm text-gray-400">
            Camera access and AI processing will be connected during system
            integration. This preview does not use a camera or identify anyone.
          </p>
        </div>

        <aside className="rounded-xl border border-white/10 bg-[#18181b] p-5">
          <h2 className="text-lg font-semibold">Processing status</h2>
          <p className="mt-1 text-sm text-gray-400">
            {previewActive ? 'Preview state' : 'Waiting to start'}
          </p>

          <ul className="mt-5 space-y-4">
            {steps.map((step, index) => (
              <li key={step} className="flex items-center justify-between gap-3">
                <span className="text-sm text-gray-300">{step}</span>
                <span
                  className={`rounded-full px-3 py-1 text-xs ${
                    previewActive && index === 0
                      ? 'bg-amber-400/10 text-amber-300'
                      : 'bg-white/5 text-gray-400'
                  }`}
                >
                  {previewActive && index === 0 ? 'Preview only' : 'Waiting'}
                </span>
              </li>
            ))}
          </ul>
        </aside>
      </section>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          ['Faces detected', '—'],
          ['Needs review', '—'],
          ['Not observed', '—'],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-xl border border-white/10 bg-[#18181b] p-5"
          >
            <p className="text-sm text-gray-400">{label}</p>
            <p className="mt-2 text-2xl font-semibold">{value}</p>
          </div>
        ))}
      </div>

      <p className="text-sm text-gray-500">
        Preview only. No camera, face data, attendance decisions, or backend
        processing are used here.
      </p>
    </div>
  )
}