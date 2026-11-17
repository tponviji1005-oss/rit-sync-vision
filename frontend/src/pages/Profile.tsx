export default function Profile() {
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">Account</p>
          <h2 className="mt-1 text-2xl font-semibold">My Profile</h2>
          <p className="mt-1 text-sm text-gray-400">
            Profile and account settings preview
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          Sample profile
        </span>
      </header>

      <section className="grid gap-6 xl:grid-cols-[0.7fr_1.3fr]">
        <div className="rounded-xl border border-white/10 bg-[#18181b] p-6 text-center">
          <div className="mx-auto grid size-20 place-items-center rounded-full bg-[#cd202c] text-3xl font-semibold">
            T
          </div>
          <h3 className="mt-4 text-lg font-semibold">Demo Teacher</h3>
          <p className="mt-1 text-sm text-gray-400">teacher@example.edu</p>
          <p className="mt-4 inline-flex rounded-full bg-white/10 px-3 py-1 text-xs text-gray-300">
            Faculty
          </p>
        </div>

        <div className="rounded-xl border border-white/10 bg-[#18181b]">
          <div className="border-b border-white/10 p-5">
            <h3 className="font-semibold">Profile information</h3>
            <p className="mt-1 text-sm text-gray-400">
              Example details for the account screen
            </p>
          </div>

          <div className="space-y-4 p-5">
            <div>
              <label htmlFor="profile-name" className="mb-2 block text-sm text-gray-300">
                Name
              </label>
              <input
                id="profile-name"
                value="Demo Teacher"
                readOnly
                className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-gray-400"
              />
            </div>

            <div>
              <label htmlFor="profile-email" className="mb-2 block text-sm text-gray-300">
                Email
              </label>
              <input
                id="profile-email"
                value="teacher@example.edu"
                readOnly
                className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-gray-400"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="profile-role" className="mb-2 block text-sm text-gray-300">
                  Role
                </label>
                <input
                  id="profile-role"
                  value="Faculty"
                  readOnly
                  className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-gray-400"
                />
              </div>
              <div>
                <label htmlFor="profile-department" className="mb-2 block text-sm text-gray-300">
                  Department
                </label>
                <input
                  id="profile-department"
                  value="CSE"
                  readOnly
                  className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-gray-400"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                type="button"
                disabled
                className="cursor-not-allowed rounded-lg bg-[#cd202c] px-4 py-3 text-sm font-semibold text-white opacity-50"
              >
                Edit profile · integration pending
              </button>
              <button
                type="button"
                disabled
                className="cursor-not-allowed rounded-lg border border-white/10 px-4 py-3 text-sm text-gray-400 opacity-50"
              >
                Change password · integration pending
              </button>
            </div>
          </div>
        </div>
      </section>

      <p className="text-xs text-gray-500">
        Preview only. This screen does not display or change a real user account.
      </p>
    </div>
  )
}