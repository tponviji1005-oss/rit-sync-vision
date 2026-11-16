import { useState } from 'react'

export default function FaceRegistration() {
  const [consentConfirmed, setConsentConfirmed] = useState(false)

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">Student enrollment</p>
          <h2 className="mt-1 text-2xl font-semibold">Face Registration</h2>
          <p className="mt-1 text-sm text-gray-400">
            Register an authorized student template
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          UI preview only
        </span>
      </header>

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-5 rounded-xl border border-white/10 bg-[#18181b] p-5">
          <div>
            <label htmlFor="student" className="mb-2 block text-sm text-gray-300">
              Select student
            </label>
            <select
              id="student"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-white outline-none focus:border-[#cd202c]"
              defaultValue=""
            >
              <option value="" disabled>
                Choose a demo student
              </option>
              <option value="STU-001">STU-001 · Demo Student 001 · CSE - A</option>
              <option value="STU-002">STU-002 · Demo Student 002 · CSE - B</option>
              <option value="STU-003">STU-003 · Demo Student 003 · CSE - F</option>
            </select>
          </div>

          <div className="rounded-lg border border-white/10 bg-[#0d0d0f] p-4">
            <h3 className="font-medium">Before registration</h3>
            <ul className="mt-3 space-y-2 text-sm text-gray-400">
              <li>• Confirm the student is authorized for registration.</li>
              <li>• Ask the student to face the camera in good lighting.</li>
              <li>• Check the capture result before submitting.</li>
            </ul>
          </div>

          <label className="flex items-start gap-3 rounded-lg border border-white/10 p-4 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={consentConfirmed}
              onChange={(event) => setConsentConfirmed(event.target.checked)}
              className="mt-1 accent-[#cd202c]"
            />
            <span>
              I confirm the required authorization and consent have been
              obtained.
            </span>
          </label>
        </div>

        <div className="rounded-xl border border-white/10 bg-[#18181b] p-5">
          <div className="mb-4">
            <h3 className="font-semibold">Capture preview</h3>
            <p className="mt-1 text-sm text-gray-400">
              Camera connection will be added after the approved integration is ready.
            </p>
          </div>

          <div className="grid min-h-72 place-items-center rounded-xl border border-dashed border-white/20 bg-[#0d0d0f] p-6 text-center">
            <div>
              <div className="mx-auto mb-4 grid size-16 place-items-center rounded-full border border-white/20 text-2xl text-gray-400">
                ○
              </div>
              <p className="font-medium">Camera not connected</p>
              <p className="mt-2 max-w-sm text-sm text-gray-500">
                This preview does not request camera permission or capture an image.
              </p>
            </div>
          </div>

          <button
            type="button"
            disabled={!consentConfirmed}
            className="mt-4 w-full rounded-lg bg-[#cd202c] px-4 py-3 text-sm font-semibold text-white opacity-50"
          >
            Capture &amp; Register — integration pending
          </button>

          <p className="mt-3 text-xs leading-5 text-gray-500">
            Face images and templates are not stored by this preview. Registration
            requires the agreed backend and AI integration.
          </p>
        </div>
      </section>
    </div>
  )
}