import { useState } from 'react'

type ReviewRow = {
  id: string
  name: string
  className: string
  confidence: string
  systemStatus: 'Present candidate' | 'Needs review' | 'Not observed' | 'Finalized present'
  teacherDecision: 'No decision' | 'Present' | 'Needs review' | 'Not observed'
}

const startingRows: ReviewRow[] = [
  {
    id: 'STU-021',
    name: 'Demo Student 021',
    className: 'CSE - A',
    confidence: '98%',
    systemStatus: 'Present candidate',
    teacherDecision: 'No decision',
  },
  {
    id: 'STU-022',
    name: 'Demo Student 022',
    className: 'CSE - B',
    confidence: '72%',
    systemStatus: 'Needs review',
    teacherDecision: 'No decision',
  },
  {
    id: 'STU-023',
    name: 'Demo Student 023',
    className: 'CSE - F',
    confidence: '—',
    systemStatus: 'Not observed',
    teacherDecision: 'No decision',
  },
]

export default function AttendanceReview() {
  const [rows, setRows] = useState(startingRows)
  const [notice, setNotice] = useState('')

  function updateDecision(id: string, decision: ReviewRow['teacherDecision']) {
    setRows((currentRows) =>
      currentRows.map((row) =>
        row.id === id ? { ...row, teacherDecision: decision } : row,
      ),
    )
    setNotice('')
  }

  function finalizePresentDecisions() {
    const hasPresentDecision = rows.some(
      (row) =>
        row.teacherDecision === 'Present' &&
        row.systemStatus !== 'Finalized present',
    )

    if (!hasPresentDecision) {
      setNotice('Choose Present for at least one student first.')
      return
    }

    setRows((currentRows) =>
      currentRows.map((row) =>
        row.teacherDecision === 'Present'
          ? { ...row, systemStatus: 'Finalized present' }
          : row,
      ),
    )
    setNotice('Teacher decisions updated in this preview only; nothing was saved.')
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">Teacher decision required</p>
          <h2 className="mt-1 text-2xl font-semibold">Attendance Review</h2>
          <p className="mt-1 text-sm text-gray-400">
            Review candidate records before finalizing attendance
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          Demo only · not saved
        </span>
      </header>

      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-100">
        “Not observed” means the system did not get enough evidence. It does not
        mean “Absent.”
      </div>

      <section className="overflow-hidden rounded-xl border border-white/10 bg-[#18181b]">
        <div className="border-b border-white/10 p-5">
          <h3 className="font-semibold">CSE - A · Example session</h3>
          <p className="mt-1 text-sm text-gray-400">
            Review each system suggestion and choose a teacher decision.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-white/5 text-gray-400">
              <tr>
                <th className="px-5 py-3 font-medium">Student</th>
                <th className="px-5 py-3 font-medium">Class</th>
                <th className="px-5 py-3 font-medium">Confidence</th>
                <th className="px-5 py-3 font-medium">System suggestion</th>
                <th className="px-5 py-3 font-medium">Teacher decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {rows.map((row) => (
                <tr key={row.id} className="text-gray-200">
                  <td className="px-5 py-4">
                    <span className="font-medium">{row.name}</span>
                    <span className="mt-1 block text-xs text-gray-500">{row.id}</span>
                  </td>
                  <td className="px-5 py-4">{row.className}</td>
                  <td className="px-5 py-4">{row.confidence}</td>
                  <td className="px-5 py-4">{row.systemStatus}</td>
                  <td className="px-5 py-4">
                    <select
                      aria-label={`Teacher decision for ${row.id}`}
                      value={row.teacherDecision}
                      onChange={(event) =>
                        updateDecision(
                          row.id,
                          event.target.value as ReviewRow['teacherDecision'],
                        )
                      }
                      disabled={row.systemStatus === 'Finalized present'}
                      className="rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-2 text-sm text-white outline-none focus:border-[#cd202c]"
                    >
                      <option>No decision</option>
                      <option>Present</option>
                      <option>Needs review</option>
                      <option>Not observed</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/10 p-5">
          <p className="text-xs text-gray-500">
            Only an explicit teacher decision can finalize a present record.
          </p>
          <button
            type="button"
            onClick={finalizePresentDecisions}
            className="rounded-lg bg-[#cd202c] px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
          >
            Finalize teacher-selected Present records
          </button>
        </div>

        {notice && (
          <p role="status" className="border-t border-white/10 px-5 py-3 text-sm text-gray-300">
            {notice}
          </p>
        )}
      </section>
    </div>
  )
}