import { useState } from 'react'
import type { FormEvent } from 'react'

type ClassRow = {
  name: string
  department: string
  year: string
  subjects: string[]
  students: number
}

const startingClasses: ClassRow[] = [
  {
    name: 'CSE - A',
    department: 'CSE',
    year: 'II / III',
    subjects: ['AI', 'DBMS', 'OS', 'Maths', 'Networks'],
    students: 62,
  },
  {
    name: 'CSE - B',
    department: 'CSE',
    year: 'II / III',
    subjects: ['AI', 'DBMS', 'OS', 'Maths', 'Networks'],
    students: 61,
  },
  {
    name: 'CSE - F',
    department: 'CSE',
    year: 'II / III',
    subjects: ['AI', 'DBMS', 'OS', 'Maths', 'Networks'],
    students: 62,
  },
]

const emptyForm = {
  name: '',
  department: '',
  year: '',
  subjects: '',
  students: '',
}

const inputClass =
  'w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-2 text-sm text-white outline-none focus:border-[#cd202c]'

export default function Classes() {
  const [classes, setClasses] = useState(startingClasses)
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingName, setEditingName] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [form, setForm] = useState(emptyForm)

  const filteredClasses = classes.filter((classItem) =>
    `${classItem.name} ${classItem.department} ${classItem.year} ${classItem.subjects.join(' ')}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  )

  function openAddForm() {
    setEditingName(null)
    setForm(emptyForm)
    setNotice('')
    setShowForm(true)
  }

  function openEditForm(classItem: ClassRow) {
    setEditingName(classItem.name)
    setForm({
      name: classItem.name,
      department: classItem.department,
      year: classItem.year,
      subjects: classItem.subjects.join(', '),
      students: String(classItem.students),
    })
    setNotice('')
    setShowForm(true)
  }

  function saveClass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const newClass: ClassRow = {
      name: form.name.trim(),
      department: form.department.trim(),
      year: form.year.trim(),
      subjects: form.subjects
        .split(',')
        .map((subject) => subject.trim())
        .filter(Boolean),
      students: Number(form.students) || 0,
    }

    const duplicate = classes.some(
      (classItem) =>
        classItem.name.toLowerCase() === newClass.name.toLowerCase() &&
        classItem.name !== editingName,
    )

    if (duplicate) {
      setNotice('A class with that name already exists in this preview.')
      return
    }

    if (editingName) {
      setClasses((current) =>
        current.map((classItem) =>
          classItem.name === editingName ? newClass : classItem,
        ),
      )
      setNotice('Class updated in this preview only. It has not been saved.')
    } else {
      setClasses((current) => [newClass, ...current])
      setNotice('Class added in this preview only. It has not been saved.')
    }

    setForm(emptyForm)
    setEditingName(null)
    setShowForm(false)
  }

  function deleteClass(name: string) {
    if (!window.confirm(`Remove ${name} from this preview?`)) return

    setClasses((current) =>
      current.filter((classItem) => classItem.name !== name),
    )
    setNotice('Class removed from this preview only. It has not been saved.')
  }

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
          Preview only · not saved
        </span>
      </header>

      <section className="overflow-hidden rounded-xl border border-white/10 bg-[#18181b]">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 p-5">
          <h3 className="font-semibold">Class list</h3>
          <div className="flex w-full flex-wrap gap-3 sm:w-auto">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search classes..."
              aria-label="Search classes"
              className={`${inputClass} sm:w-64`}
            />
            <button
              type="button"
              onClick={openAddForm}
              className="rounded-lg bg-[#cd202c] px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
            >
              + Add Class
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="bg-white/5 text-gray-400">
              <tr>
                <th className="px-5 py-3 font-medium">Class</th>
                <th className="px-5 py-3 font-medium">Department</th>
                <th className="px-5 py-3 font-medium">Year / Semester</th>
                <th className="px-5 py-3 font-medium">Subjects</th>
                <th className="px-5 py-3 font-medium">Students</th>
                <th className="px-5 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {filteredClasses.map((classItem) => (
                <tr key={classItem.name} className="text-gray-200">
                  <td className="px-5 py-4 font-medium">{classItem.name}</td>
                  <td className="px-5 py-4">{classItem.department}</td>
                  <td className="px-5 py-4">{classItem.year}</td>
                  <td
                    className="px-5 py-4"
                    title={classItem.subjects.join(', ') || 'No subjects'}
                  >
                    {classItem.subjects.length}
                  </td>
                  <td className="px-5 py-4">{classItem.students}</td>
                  <td className="px-5 py-4">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => openEditForm(classItem)}
                        className="rounded-md border border-white/10 px-3 py-1 text-xs hover:bg-white/10"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteClass(classItem.name)}
                        className="rounded-md border border-red-500/30 px-3 py-1 text-xs text-red-200 hover:bg-red-500/10"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredClasses.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-gray-400">
                    No matching classes.
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
          Changes here are examples held in this page preview only.
        </p>
      </section>

      {showForm && (
        <div className="fixed inset-0 z-10 grid place-items-center bg-black/70 p-4">
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="class-form-title"
            className="w-full max-w-lg rounded-xl border border-white/10 bg-[#18181b] p-6"
          >
            <h3 id="class-form-title" className="text-lg font-semibold">
              {editingName ? 'Edit class' : 'Add a class'}
            </h3>
            <p className="mt-1 text-sm text-gray-400">
              Preview form · information is not saved
            </p>

            <form onSubmit={saveClass} className="mt-5 space-y-4">
              <div>
                <label htmlFor="class-name" className="mb-1 block text-sm text-gray-300">
                  Class name
                </label>
                <input
                  id="class-name"
                  required
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  placeholder="e.g. CSE - D"
                  className={inputClass}
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="department" className="mb-1 block text-sm text-gray-300">
                    Department
                  </label>
                  <input
                    id="department"
                    required
                    value={form.department}
                    onChange={(event) => setForm({ ...form, department: event.target.value })}
                    placeholder="e.g. CSE"
                    className={inputClass}
                  />
                </div>
                <div>
                  <label htmlFor="year" className="mb-1 block text-sm text-gray-300">
                    Year / semester
                  </label>
                  <input
                    id="year"
                    required
                    value={form.year}
                    onChange={(event) => setForm({ ...form, year: event.target.value })}
                    placeholder="e.g. II / III"
                    className={inputClass}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="subjects" className="mb-1 block text-sm text-gray-300">
                  Subjects, separated by commas
                </label>
                <input
                  id="subjects"
                  value={form.subjects}
                  onChange={(event) => setForm({ ...form, subjects: event.target.value })}
                  placeholder="e.g. AI, DBMS, OS"
                  className={inputClass}
                />
              </div>

              <div>
                <label htmlFor="students" className="mb-1 block text-sm text-gray-300">
                  Student count
                </label>
                <input
                  id="students"
                  type="number"
                  min="0"
                  value={form.students}
                  onChange={(event) => setForm({ ...form, students: event.target.value })}
                  placeholder="e.g. 60"
                  className={inputClass}
                />
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
                  {editingName ? 'Save preview changes' : 'Add to preview'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}