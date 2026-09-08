import { Link } from 'react-router-dom'
import { MODES } from '../modes'
import { ProviderBadge } from '../components/ProviderIcon'

/**
 * Entry screen: one tile per capability. Picking a tile swaps the whole view
 * for that mode's chat (App.jsx owns the `mode` state).
 */
export default function LandingPage({ onOpenSettings, activeProvider = null }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="flex justify-end px-6 pt-6">
        <button
          type="button"
          onClick={onOpenSettings}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 shadow-sm transition-colors hover:text-gray-900 hover:border-gray-300"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a6.759 6.759 0 010 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 010-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Settings
          {activeProvider && (
            <>
              <span className="w-px h-4 bg-gray-200" />
              <ProviderBadge icon={activeProvider.icon} size="sm" />
              <span className="text-gray-500 font-normal">{activeProvider.label}</span>
            </>
          )}
        </button>
      </div>

      <header className="px-6 pt-6 pb-10 text-center">
        <div className="w-14 h-14 mx-auto mb-5 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <h1 className="text-3xl font-semibold text-gray-900 mb-3">DocuChat AI</h1>
        <p className="text-gray-500 max-w-xl mx-auto">
          Three ways to work with an LLM, sharing one chat interface. Pick a capability to start.
        </p>
      </header>

      <main className="flex-1 px-6 pb-16">
        <div className="grid gap-6 md:grid-cols-3 max-w-5xl mx-auto">
          {MODES.map((mode) => {
            const live = mode.status === 'live'
            return (
              <Link
                key={mode.id}
                to={mode.path}
                className={`group block text-left bg-white rounded-2xl border border-gray-200 p-6 shadow-sm transition-all hover:shadow-lg hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 ${mode.accent.border}`}
              >
                <div className="flex items-start justify-between mb-5">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white shadow-sm ${mode.accent.icon}`}>
                    <mode.Icon className="w-6 h-6" />
                  </div>
                  <span
                    className={`text-xs font-medium px-2.5 py-1 rounded-full border ${
                      live
                        ? 'bg-green-50 text-green-700 border-green-200'
                        : 'bg-gray-50 text-gray-500 border-gray-200'
                    }`}
                  >
                    {live ? 'Available' : 'Coming soon'}
                  </span>
                </div>

                <h2 className="text-lg font-semibold text-gray-900 mb-1">{mode.title}</h2>
                <p className={`text-sm font-medium mb-3 ${mode.accent.text}`}>{mode.tagline}</p>
                <p className="text-sm text-gray-500 leading-relaxed mb-5">{mode.description}</p>

                <ul className="space-y-2 mb-5">
                  {mode.steps.map((step) => (
                    <li key={step} className="flex items-center gap-2.5 text-xs text-gray-600">
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${mode.accent.dot}`} />
                      {step}
                    </li>
                  ))}
                </ul>

                <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${mode.accent.text}`}>
                  {live ? 'Open' : 'Preview'}
                  <svg
                    className="w-4 h-4 transition-transform group-hover:translate-x-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                  </svg>
                </span>
              </Link>
            )
          })}
        </div>
      </main>

      <footer className="px-6 py-4 border-t border-gray-200 bg-white">
        <p className="text-xs text-gray-500 text-center">
          FastAPI + FAISS backend • React & AI SDK frontend • provider configured under Settings
        </p>
      </footer>
    </div>
  )
}
