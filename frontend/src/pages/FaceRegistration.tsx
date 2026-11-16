import { useState } from 'react'

export default function FaceRegistration() {
  const [studentId, setStudentId] = useState('')
  const [className, setClassName] = useState('CSE - A')
  const [message, setMessage] = useState('')

  function handleRegister() {
    if (!studentId.trim()) {
      setMessage('Enter a demo student ID to continue.')
      return
    }

    setMessage(
      `Preview only: registration flow shown for ${studentId}. No camera or face data was used.`,
    )
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-gray-400">Student enrollment</p>
        <h1 className="mt-1 text-3xl font-semibold">Face Registration</h1>
        <p className="mt-2 text-gray-400">
          Preview the registration steps for a student.
        </p>
      </header>

      <section className="grid max-w-5xl gap-6 rounded-xl border border-white/10 bg-[#18181b] p-6 md:grid-cols-2">
        <div className="space-y-5">
          <label className="block space-y-2">
            <span className="text-sm text-gray-300">Student ID</span>
            <input
              value={studentId}
              onChange={(event) => {
                setStudentId(event.target.value)
                setMessage('')
              }}
              placeholder="Example: STU-001"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-4 py-3 text-white placeholder:text-gray-600"
            />
          </label>

          <label className="block space-y-2">
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

          <div className="rounded-lg border border-white/10 bg-black/20 p-4">
            <h2 className="font-medium">Registration steps</h2>
            <ol className="mt-3 space-y-2 text-sm text-gray-300">
              <li>1. Confirm the student and class.</li>
              <li>2. The authorized system captures a face template.</li>
              <li>3. Review the result before saving.</li>
            </ol>
          </div>

          <button
            type="button"
            onClick={handleRegister}
            className="w-full rounded-lg bg-[#cd202c] px-4 py-3 font-medium text-white hover:bg-red-700"
          >
            Preview registration
          </button>
        </div>

        <div className="flex min-h-72 flex-col items-center justify-center rounded-xl border border-dashed border-white/20 bg-[#0d0d0f] p-6 text-center">
          <div className="grid size-16 place-items-center rounded-full bg-white/10 text-2xl">
            ◉
          </div>
          <h2 className="mt-4 text-lg font-semibold">Camera preview unavailable</h2>
          <p className="mt-2 max-w-sm text-sm text-gray-400">
            Camera capture will be connected during system integration. This
            screen does not access a camera or collect biometric data.
          </p>
        </div>

        {message && (
          <p
            className="rounded-lg border border-white/10 bg-black/20 p-3 text-sm text-gray-300 md:col-span-2"
            role="status"
          >
            {message}
          </p>
        )}
      </section>

      <p className="text-sm text-gray-500">
        Preview only. Registration is not connected to the backend.
      </p>
    </div>
  )
}