import { useState } from 'react'

const classRows = [
  { name: 'CSE - A', department: 'CSE', year: 'II / III', subjects: 5, students: 62 },
  { name: 'CSE - B', department: 'CSE', year: 'II / III', subjects: 5, students: 61 },
  { name: 'CSE - F', department: 'CSE', year: 'II / III', subjects: 5, students: 62 },
]

export default function Classes() {
  const [search, setSearch] = useState('')

  const filteredClasses = classRows.filter((classItem) =>
    `${classItem.name} ${classItem.department}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  )

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">Academic setup</p>
          <h2 className="mt-1 text-2xl font-semibold">Classes &amp; Subjects</h2>
          <p className="mt-1 text-sm text-gray-400">
            Preview of class and subject mappings
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          Sample preview data
        </span>
      </header>

      <section className="rounded-xl border border-white/10 bg-[#18181b]">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 p-5">
          <h3 className="font-semibold">Class list</h3>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search classes..."
            aria-label="Search classes"
            className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-2 text-sm outline-none placeholder:text-gray-500 focus:border-[#cd202c] sm:w-64"
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead className="bg-white/5 text-gray-400">
              <tr>
                <th className="px-5 py-3 font-medium">Class</th>
                <th className="px-5 py-3 font-medium">Department</th>
                <th className="px-5 py-3 font-medium">Year / Semester</th>
                <th className="px-5 py-3 font-medium">Subjects</th>
                <th className="px-5 py-3 font-medium">Students</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {filteredClasses.map((classItem) => (
                <tr key={classItem.name} className="text-gray-200">
                  <td className="px-5 py-4 font-medium">{classItem.name}</td>
                  <td className="px-5 py-4">{classItem.department}</td>
                  <td className="px-5 py-4">{classItem.year}</td>
                  <td className="px-5 py-4">{classItem.subjects}</td>
                  <td className="px-5 py-4">{classItem.students}</td>
                </tr>
              ))}
              {filteredClasses.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-gray-400">
                    No matching classes.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <p className="border-t border-white/10 px-5 py-3 text-xs text-gray-500">
          Preview only. Class data and management actions are not connected to the backend yet.
        </p>
      </section>
    </div>
  )
}