import { useState } from 'react'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const [message, setMessage] = useState('')

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!email.trim() || !password.trim()) {
      setMessage('Enter your email and password to continue.')
      return
    }

    setMessage('Demo sign-in only. Backend authentication is not connected yet.')
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#0d0d0f] px-4 py-10 text-white">
      <section className="w-full max-w-md rounded-2xl border border-white/10 bg-[#18181b] p-8 shadow-xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 grid size-14 place-items-center rounded-2xl bg-[#cd202c] text-2xl font-bold">
            R
          </div>
          <h1 className="text-3xl font-semibold">RIT-Sync Vision</h1>
          <p className="mt-2 text-sm text-gray-400">
            Classroom Edge AI Attendance System
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <label className="block space-y-2">
            <span className="text-sm text-gray-300">Email address</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="teacher@rit.ac.in"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-4 py-3 text-white placeholder:text-gray-600"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm text-gray-300">Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-4 py-3 text-white placeholder:text-gray-600"
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={(event) => setRememberMe(event.target.checked)}
              className="size-4 accent-[#cd202c]"
            />
            Remember me
          </label>

          <button
            type="submit"
            className="w-full rounded-lg bg-[#cd202c] px-4 py-3 font-medium text-white hover:bg-red-700"
          >
            Sign in
          </button>

          {message && (
            <p className="rounded-lg border border-white/10 bg-black/20 p-3 text-sm text-gray-300" role="status">
              {message}
            </p>
          )}
        </form>

        <p className="mt-6 text-center text-xs text-gray-500">
          Preview only. Authentication is not connected to the backend.
        </p>
      </section>
    </main>
  )
}