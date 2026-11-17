import { useState } from 'react'

const initialSettings = {
  institution: 'Rajalakshmi Institute of Technology',
  systemName: 'RIT-Sync Vision',
  captureDuration: '120 seconds',
  autoSync: true,
  theme: 'Dark (Default)',
}

export default function Settings() {
  const [settings, setSettings] = useState(initialSettings)
  const [saved, setSaved] = useState(false)

  function updateSetting(name: string, value: string | boolean) {
    setSettings((current) => ({ ...current, [name]: value }))
    setSaved(false)
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm text-gray-400">System configuration</p>
        <h1 className="mt-1 text-3xl font-semibold">Settings</h1>
        <p className="mt-2 text-gray-400">
          Manage your system preferences.
        </p>
      </header>

      <section className="max-w-3xl space-y-5 rounded-xl border border-white/10 bg-[#18181b] p-6">
        <label className="block space-y-2">
          <span className="text-sm text-gray-300">Institution name</span>
          <input
            value={settings.institution}
            onChange={(event) => updateSetting('institution', event.target.value)}
            className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-4 py-3 text-white"
          />
        </label>

        <label className="block space-y-2">
          <span className="text-sm text-gray-300">System name</span>
          <input
            value={settings.systemName}
            onChange={(event) => updateSetting('systemName', event.target.value)}
            className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-4 py-3 text-white"
          />
        </label>

        <label className="block space-y-2">
          <span className="text-sm text-gray-300">Capture duration</span>
          <select
            value={settings.captureDuration}
            onChange={(event) => updateSetting('captureDuration', event.target.value)}
            className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-4 py-3 text-white"
          >
            <option>60 seconds</option>
            <option>120 seconds</option>
            <option>180 seconds</option>
          </select>
        </label>

        <label className="flex items-center justify-between gap-4 rounded-lg border border-white/10 p-4">
          <span>
            <span className="block font-medium">Automatic sync</span>
            <span className="text-sm text-gray-400">
              Sync attendance when a connection is available
            </span>
          </span>
          <input
            type="checkbox"
            checked={settings.autoSync}
            onChange={(event) => updateSetting('autoSync', event.target.checked)}
            className="size-5 accent-[#cd202c]"
          />
        </label>

        <label className="block space-y-2">
          <span className="text-sm text-gray-300">Theme</span>
          <select
            value={settings.theme}
            onChange={(event) => updateSetting('theme', event.target.value)}
            className="w-full rounded-lg border border-white/10 bg-[#0d0d0f] px-4 py-3 text-white"
          >
            <option>Dark (Default)</option>
            <option>Light</option>
          </select>
        </label>

        <div className="flex items-center gap-4 pt-2">
          <button
            type="button"
            onClick={() => setSaved(true)}
            className="rounded-lg bg-[#cd202c] px-5 py-3 font-medium text-white hover:bg-red-700"
          >
            Save changes
          </button>
          {saved && <span className="text-sm text-green-400">Preview settings saved</span>}
        </div>

        <p className="border-t border-white/10 pt-4 text-sm text-gray-500">
          Preview only. Settings are not saved to the backend.
        </p>
      </section>
    </div>
  )
}