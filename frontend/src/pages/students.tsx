import { useState } from 'react'
import type { FormEvent } from 'react'

type StudentRow = {
  id: string
  name: string
  className: string
  faceStatus: 'Registered' | 'Pending'
}

const startingStudents: StudentRow[] = [
  { id: 'STU-001', name: 'Demo Student 001', className: 'CSE - A', faceStatus: 'Registered' },
  { id: 'STU-002', name: 'Demo Student 002', className: 'CSE - B', faceStatus: 'Pending' },
  { id: 'STU-003', name: 'Demo Student 003', className: 'CSE - F', faceStatus: 'Registered' },
  { id: 'STU-004', name: 'Demo Student 004', className: 'CSE - A', faceStatus: 'Pending' },
]

const emptyForm = { id: '', name: '', className: 'CSE - A' }
const inputClass =
  'w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-2 text-sm text-white outline-none focus:border-[#cd202c]'

export default function Students() {
  const [students, setStudents] = useState(startingStudents)
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('All students')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [form, setForm] = useState(emptyForm)

  const filteredStudents = students.filter((student) => {
    const matchesSearch = `${student.id} ${student.name} ${student.className}`
      .toLowerCase()
      .includes(search.toLowerCase())
    const matchesFilter =
      activeFilter === 'All students' || student.faceStatus === activeFilter
    return matchesSearch && matchesFilter
  })

  function openAddForm() {
    setEditingId(null)
    setForm(emptyForm)
    setNotice('')
    setShowForm(true)
  }

  function openEditForm(student: StudentRow) {
    setEditingId(student.id)
    setForm({
      id: student.id,
      name: student.name,
      className: student.className,
    })
    setNotice('')
    setShowForm(true)
  }

  function saveStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const duplicateId = students.some(
      (student) =>
        student.id.toLowerCase() === form.id.trim().toLowerCase() &&
        student.id !== editingId,
    )

    if (duplicateId) {
      setNotice('That student ID already exists in this preview.')
      return
    }

    if (editingId) {
      setStudents((current) =>
        current.map((student) =>
          student.id === editingId
            ? { ...student, name: form.name.trim(), className: form.className }
            : student,
        ),
      )
      setNotice('Student updated in this preview only. It has not been saved.')
    } else {
      setStudents((current) => [
        {
          id: form.id.trim(),
          name: form.name.trim(),
          className: form.className,
          faceStatus: 'Pending',
        },
        ...current,
      ])
      setNotice('Demo student added to this preview only. It has not been saved.')
    }

    setForm(emptyForm)
    setEditingId(null)
    setShowForm(false)
  }

  function deleteStudent(id: string) {
    if (!window.confirm(`Remove ${id} from this preview?`)) return

    setStudents((current) => current.filter((student) => student.id !== id))
    setNotice('Student removed from this preview only. It has not been saved.')
  }

  const filters = ['All students', 'Registered', 'Pending']

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
          Preview only · not saved
        </span>
      </header>

      <section className="overflow-hidden rounded-xl border border-white/10 bg-[#18181b]">
        <div className="space-y-4 border-b border-white/10 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
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

            <button
              type="button"
              onClick={openAddForm}
              className="rounded-lg bg-[#cd202c] px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
            >
              + Add Student
            </button>
          </div>

          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by student or class..."
            aria-label="Search students"
            className={`${inputClass} sm:max-w-sm`}
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-white/5 text-gray-400">
              <tr>
                <th className="px-5 py-3 font-medium">Student ID</th>
                <th className="px-5 py-3 font-medium">Student name</th>
                <th className="px-5 py-3 font-medium">Class</th>
                <th className="px-5 py-3 font-medium">Face registration</th>
                <th className="px-5 py-3 font-medium">Actions</th>
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
                  <td className="px-5 py-4">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => openEditForm(student)}
                        className="rounded-md border border-white/10 px-3 py-1 text-xs hover:bg-white/10"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteStudent(student.id)}
                        className="rounded-md border border-red-500/30 px-3 py-1 text-xs text-red-200 hover:bg-red-500/10"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredStudents.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-gray-400">
                    No matching students.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {notice && (
          <p role="status" className="border-t border-white/10 px-5 py-3 text-sm text-amber-200">
            {notice}
          </p>
        )}

        <p className="border-t border-white/10 px-5 py-3 text-xs text-gray-500">
          Use fake examples only. Preview changes are not saved and contain no real student or face data.
        </p>
      </section>

      {showForm && (
        <div className="fixed inset-0 z-10 grid place-items-center bg-black/70 p-4">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="student-form-title"
            className="w-full max-w-lg rounded-xl border border-white/10 bg-[#18181b] p-6"
          >
            <h3 id="student-form-title" className="text-lg font-semibold">
              {editingId ? 'Edit student' : 'Add a student'}
            </h3>
            <p className="mt-1 text-sm text-gray-400">
              Preview form · information is not saved
            </p>

            <form onSubmit={saveStudent} className="mt-5 space-y-4">
              <div>
                <label htmlFor="student-id" className="mb-1 block text-sm text-gray-300">
                  Student ID
                </label>
                <input
                  id="student-id"
                  required
                  disabled={Boolean(editingId)}
                  value={form.id}
                  onChange={(event) => setForm({ ...form, id: event.target.value })}
                  placeholder="e.g. STU-005"
                  className={`${inputClass} disabled:opacity-50`}
                />
              </div>

              <div>
                <label htmlFor="student-name" className="mb-1 block text-sm text-gray-300">
                  Student name
                </label>
                <input
                  id="student-name"
                  required
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  placeholder="Use a demo name only"
                  className={inputClass}
                />
              </div>

              <div>
                <label htmlFor="student-class" className="mb-1 block text-sm text-gray-300">
                  Class
                </label>
                <select
                  id="student-class"
                  value={form.className}
                  onChange={(event) => setForm({ ...form, className: event.target.value })}
                  className={inputClass}
                >
                  <option>CSE - A</option>
                  <option>CSE - B</option>
                  <option>CSE - F</option>
                </select>
              </div>

              {notice && <p role="alert" className="text-sm text-amber-200">{notice}</p>}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false)
                    setNotice('')
                  }}
                  className="rounded-lg border border-white/10 px-4 py-2 text-sm text-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded-lg bg-[#cd202c] px-4 py-2 text-sm font-semibold text-white"
                >
                  {editingId ? 'Save preview changes' : 'Add to preview'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}