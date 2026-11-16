import { useState } from 'react'

type ReviewStatus = 'Needs review' | 'Present' | 'Not observed'

const startingRows = [
  { id: 'STU-001', name: 'Demo Student 001', confidence: '98%', status: 'Needs review' as ReviewStatus },
  { id: 'STU-002', name: 'Demo Student 002', confidence: '91%', status: 'Needs review' as ReviewStatus },
  { id: 'STU-003', name: 'Demo Student 003', confidence: '—', status: 'Not observed' as ReviewStatus },
]

export default function AttendanceReview() {
  const [rows, setRows] = useState(startingRows)
  const [finalized, setFinalized] = useState(false)

  function setStatus(id: string, status: ReviewStatus) {
    setRows((current) =>
      current.map((row) => (row.id === id ? { ...row, status } : row)),
    )
    setFinalized(false)
  }

  const needsReview = rows.filter((row) => row.status === 'Needs review').length

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-gray-400">Teacher confirmation</p>
        <h1 className="mt-1 text-3xl font-semibold">Attendance Review</h1>
        <p className="mt-2 text-gray-400">
          Review the sample results before finalizing this session.
        </p>
      </header>

      <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-white/10 bg-[#18181b] p-5">
        <div>
          <p className="font-medium">CSE - A · Sample session</p>
          <p className="mt-1 text-sm text-gray-400">
            {needsReview} record{needsReview === 1 ? '' : 's'} need review
          </p>
        </div>
        <span className="rounded-full bg-amber-400/10 px-3 py-1 text-sm text-amber-300">
          Teacher review required
        </span>
      </section>

      <section className="overflow-hidden rounded-xl border border-white/10 bg-[#18181b]">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-white/5 text-gray-300">
              <tr>
                <th className="px-5 py-4">Student ID</th>
                <th className="px-5 py-4">Student</th>
                <th className="px-5 py-4">Sample confidence</th>
                <th className="px-5 py-4">Status</th>
                <th className="px-5 py-4">Teacher action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-t border-white/10">
                  <td className="px-5 py-4">{row.id}</td>
                  <td className="px-5 py-4 font-medium">{row.name}</td>
                  <td className="px-5 py-4">{row.confidence}</td>
                  <td className="px-5 py-4">
                    <span className="rounded-full bg-white/10 px-3 py-1 text-xs">
                      {row.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setStatus(row.id, 'Present')}
                        className="rounded-md bg-green-500/15 px-3 py-2 text-xs text-green-300 hover:bg-green-500/25"
                      >
                        Mark present
                      </button>
                      <button
                        type="button"
                        onClick={() => setStatus(row.id, 'Not observed')}
                        className="rounded-md bg-white/10 px-3 py-2 text-xs text-gray-300 hover:bg-white/20"
                      >
                        Not observed
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/10 p-5">
          <p className="text-sm text-gray-500">
            Sample preview only. “Not observed” does not mean absent.
          </p>
          <button
            type="button"
            onClick={() => setFinalized(true)}
            disabled={needsReview > 0}
            className="rounded-lg bg-[#cd202c] px-5 py-3 font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Finalize attendance
          </button>
        </div>

        {finalized && (
          <p className="border-t border-green-500/20 bg-green-500/10 px-5 py-4 text-sm text-green-300" role="status">
            Preview finalized. No attendance data was sent or saved.
          </p>
        )}
      </section>
    </div>
  )
}