import { useState } from 'react'

export default function Settings() {
  const [autoSync, setAutoSync] = useState(true)

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">Preferences</p>
          <h2 className="mt-1 text-2xl font-semibold">Settings</h2>
          <p className="mt-1 text-sm text-gray-400">
            General system configuration preview
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          Preview · not saved
        </span>
      </header>

      <section className="max-w-3xl rounded-xl border border-white/10 bg-[#18181b]">
        <div className="border-b border-white/10 p-5">
          <h3 className="font-semibold">General</h3>
          <p className="mt-1 text-sm text-gray-400">
            Basic preferences for the attendance application
          </p>
        </div>

        <div className="space-y-5 p-5">
          <div>
            <label htmlFor="institution" className="mb-2 block text-sm text-gray-300">
              Institution name
            </label>
            <input
              id="institution"
              defaultValue="RIT"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-white outline-none focus:border-[#cd202c]"
            />
          </div>

          <div>
            <label htmlFor="system-name" className="mb-2 block text-sm text-gray-300">
              System name
            </label>
            <input
              id="system-name"
              defaultValue="RIT-Sync Vision"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-white outline-none focus:border-[#cd202c]"
            />
          </div>

          <div>
            <label htmlFor="capture-duration" className="mb-2 block text-sm text-gray-300">
              Capture duration
            </label>
            <select
              id="capture-duration"
              defaultValue="120"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-white outline-none focus:border-[#cd202c]"
            >
              <option value="60">60 seconds</option>
              <option value="120">120 seconds</option>
              <option value="180">180 seconds</option>
            </select>
          </div>

          <label className="flex items-center justify-between gap-4 rounded-lg border border-white/10 bg-[#0d0d0f] p-4">
            <span>
              <span className="block text-sm font-medium">Automatic sync</span>
              <span className="mt-1 block text-xs text-gray-400">
                Sync attendance when a connection is available
              </span>
            </span>
            <input
              type="checkbox"
              checked={autoSync}
              onChange={(event) => setAutoSync(event.target.checked)}
              className="size-5 accent-[#cd202c]"
            />
          </label>

          <div>
            <label htmlFor="theme" className="mb-2 block text-sm text-gray-300">
              Theme
            </label>
            <select
              id="theme"
              defaultValue="dark"
              className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-3 py-3 text-sm text-white outline-none focus:border-[#cd202c]"
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </select>
          </div>

          <button
            type="button"
            disabled
            className="cursor-not-allowed rounded-lg bg-[#cd202c] px-4 py-3 text-sm font-semibold text-white opacity-50"
          >
            Save changes · integration pending
          </button>

          <p className="text-xs leading-5 text-gray-500">
            Preview only. These values are not saved or applied to the camera,
            synchronization, account, or security settings.
          </p>
        </div>
      </section>
    </div>
  )
}