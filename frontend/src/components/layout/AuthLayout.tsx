import type { ReactNode } from 'react'

type AuthLayoutProps = {
  children: ReactNode
  onBack: () => void
}

export default function AuthLayout({ children, onBack }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-[#0d0d0f] px-4 py-8 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="mb-4 flex justify-end">
          <button
            type="button"
            onClick={onBack}
            className="rounded-lg border border-white/10 px-4 py-2 text-sm text-gray-300 hover:bg-white/10"
          >
            Back to dashboard
          </button>
        </div>

        <div className="grid min-h-[calc(100vh-8rem)] place-items-center">
          {children}
        </div>
      </div>
    </div>
  )
}