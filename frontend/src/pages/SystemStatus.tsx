const components = [
  {
    name: 'Backend API',
    detail: 'No live API health data',
    status: 'Not connected',
  },
  {
    name: 'Camera input',
    detail: 'No camera session is active',
    status: 'Not connected',
  },
  {
    name: 'AI processing',
    detail: 'AI engine is not connected',
    status: 'Not connected',
  },
  {
    name: 'Local database',
    detail: 'Database health is not available',
    status: 'Not connected',
  },
  {
    name: 'Synchronization',
    detail: 'Sync service is not connected',
    status: 'Not connected',
  },
]

export default function SystemStatus() {
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-gray-400">System health</p>
          <h2 className="mt-1 text-2xl font-semibold">System Status</h2>
          <p className="mt-1 text-sm text-gray-400">
            Health checks will appear here after service integration
          </p>
        </div>
        <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-200">
          Preview · no live checks
        </span>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {components.map((component) => (
          <article
            key={component.name}
            className="rounded-xl border border-white/10 bg-[#18181b] p-5"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold">{component.name}</h3>
                <p className="mt-2 text-sm text-gray-400">{component.detail}</p>
              </div>
              <span className="shrink-0 rounded-full bg-white/10 px-3 py-1 text-xs text-gray-300">
                {component.status}
              </span>
            </div>
          </article>
        ))}
      </section>

      <section className="rounded-xl border border-white/10 bg-[#18181b] p-5">
        <h3 className="font-semibold">Status information</h3>
        <p className="mt-2 text-sm leading-6 text-gray-400">
          This screen does not contact or monitor live services yet. Statuses
          will be supplied by the backend after its health-check contract is
          agreed.
        </p>
      </section>
    </div>
  )
}