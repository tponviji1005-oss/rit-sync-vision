type FeedbackKind =
  | 'loading'
  | 'empty'
  | 'error'
  | 'offline'
  | 'permission-denied'

type FeedbackStateProps = {
  kind: FeedbackKind
  title?: string
  message?: string
  onRetry?: () => void
}

const defaults: Record<FeedbackKind, { title: string; message: string }> = {
  loading: {
    title: 'Loading',
    message: 'Please wait while this information loads.',
  },
  empty: {
    title: 'Nothing to show yet',
    message: 'There are no records to display.',
  },
  error: {
    title: 'Something went wrong',
    message: 'We could not load this information.',
  },
  offline: {
    title: 'You are offline',
    message: 'Reconnect to continue syncing information.',
  },
  'permission-denied': {
    title: 'Permission needed',
    message: 'The required permission was not granted.',
  },
}

const symbols: Record<FeedbackKind, string> = {
  loading: '…',
  empty: '—',
  error: '!',
  offline: '↻',
  'permission-denied': '!',
}

export default function FeedbackState({
  kind,
  title,
  message,
  onRetry,
}: FeedbackStateProps) {
  const content = defaults[kind]
  const isAlert = kind === 'error' || kind === 'permission-denied'

  return (
    <section
      role={isAlert ? 'alert' : 'status'}
      aria-busy={kind === 'loading'}
      className="rounded-xl border border-white/10 bg-[#18181b] p-6 text-center"
    >
      <div
        aria-hidden="true"
        className="mx-auto grid size-10 place-items-center rounded-full bg-white/10 text-lg text-gray-200"
      >
        {symbols[kind]}
      </div>

      <h3 className="mt-3 font-semibold text-white">{title ?? content.title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-gray-400">
        {message ?? content.message}
      </p>

      {kind === 'error' && onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-lg bg-[#cd202c] px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
        >
          Try again
        </button>
      )}
    </section>
  )
}