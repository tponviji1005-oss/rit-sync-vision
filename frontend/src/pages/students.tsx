import { useState } from 'react'

const sampleStudents = [
  { id: 'STU-001', name: 'Demo Student 001', className: 'CSE - A', faceStatus: 'Registered' },
  { id: 'STU-002', name: 'Demo Student 002', className: 'CSE - B', faceStatus: 'Pending' },
  { id: 'STU-003', name: 'Demo Student 003', className: 'CSE - F', faceStatus: 'Registered' },
  { id: 'STU-004', name: 'Demo Student 004', className: 'CSE - A', faceStatus: 'Pending' },
]

const filters = ['All students', 'Registered', 'Pending']

export default function Students() {
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('All students')

  const filteredStudents = sampleStudents.filter((student) => {
    const matchesSearch = `${student.id} ${student.name} ${student.className}`
      .toLowerCase()
      .includes(search.toLowerCase())

    const matchesFilter =
      activeFilter === 'All students' || student.faceStatus === activeFilter

    return matchesSearch && matchesFilter
  })

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">People</p>
          <h2 className="mt-1 text-2xl font-semibold">Students</h2>
          <p className="mt-1 text-sm text-gray-400">
            Preview of student records and enrollment status
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          Sample preview data
        </span>
      </header>

      <section className="rounded-xl border border-white/10 bg-[#18181b]">
        <div className="space-y-4 border-b border-white/10 p-5">
          <div className="flex flex-wrap gap-2">
            {filters.map((filter) => (
              <button
                key={filter}
                onClick={() => setActiveFilter(filter)}
                className={`rounded-lg px-3 py-2 text-sm ${
                  activeFilter === filter
                    ? 'bg-[#cd202c] text-white'
                    : 'bg-white/5 text-gray-300 hover:bg-white/10'
                }`}
              >
                {filter}
              </button>
            ))}
          </div>

          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by student or class..."
            aria-label="Search students"
            className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-2 text-sm outline-none placeholder:text-gray-500 focus:border-[#cd202c]"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead className="bg-white/5 text-gray-400">
              <tr>
                <th className="px-5 py-3 font-medium">Student ID</th>
                <th className="px-5 py-3 font-medium">Student name</th>
                <th className="px-5 py-3 font-medium">Class</th>
                <th className="px-5 py-3 font-medium">Face registration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {filteredStudents.map((student) => (
                <tr key={student.id} className="text-gray-200">
                  <td className="px-5 py-4">{student.id}</td>
                  <td className="px-5 py-4 font-medium">{student.name}</td>
                  <td className="px-5 py-4">{student.className}</td>
                  <td className="px-5 py-4">
                    <span
                      className={`rounded-full px-3 py-1 text-xs ${
                        student.faceStatus === 'Registered'
                          ? 'bg-emerald-500/10 text-emerald-200'
                          : 'bg-amber-500/10 text-amber-200'
                      }`}
                    >
                      {student.faceStatus}
                    </span>
                  </td>
                </tr>
              ))}
              {filteredStudents.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-gray-400">
                    No matching students.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <p className="border-t border-white/10 px-5 py-3 text-xs text-gray-500">
          Preview only. No real student or face data is used; records are not connected to the backend.
        </p>
      </section>
    </div>
  )
}