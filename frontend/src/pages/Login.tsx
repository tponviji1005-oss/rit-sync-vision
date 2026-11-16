export default function Login() {
  return (
    <main className="grid min-h-[70vh] place-items-center">
      <section className="w-full max-w-md rounded-2xl border border-white/10 bg-[#18181b] p-6 shadow-2xl sm:p-8">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid size-12 place-items-center rounded-xl bg-[#cd202c] text-lg font-bold">
            R
          </div>
          <div>
            <p className="text-lg font-semibold">RIT-Sync Vision</p>
            <p className="text-sm text-gray-400">
              Classroom attendance system
            </p>
          </div>
        </div>

        <p className="text-sm text-gray-400">Teacher access</p>
        <h2 className="mt-1 text-2xl font-semibold">Sign in</h2>
        <p className="mt-2 text-sm text-gray-400">
          Sign-in will be enabled after authentication is connected.
        </p>

        <form className="mt-6 space-y-4">
          <div>
            <label htmlFor="email" className="mb-2 block text-sm text-gray-300">
              Email
            </label>
            <input
              id="email"
              type="email"
              disabled
              placeholder="teacher@example.edu"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-gray-400"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-2 block text-sm text-gray-300">
              Password
            </label>
            <input
              id="password"
              type="password"
              disabled
              placeholder="Password"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-gray-400"
            />
          </div>

          <button
            type="button"
            disabled
            className="w-full cursor-not-allowed rounded-lg bg-[#cd202c] px-4 py-3 text-sm font-semibold text-white opacity-50"
          >
            Sign in · integration pending
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-gray-500">
          Preview only. No credentials are collected, sent, or saved.
        </p>
      </section>
    </main>
  )
}