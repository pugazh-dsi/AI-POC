import { Link } from 'react-router-dom'
import ChatWindow from './ChatWindow'
import MessageInput from './MessageInput'

/**
 * Shared layout for every mode: branded sidebar on the left, chat on the
 * right. Modes supply their own sidebar content and message handling; the
 * frame, header and back navigation stay identical across all three tiles.
 */
export default function ChatShell({
  mode,
  onOpenSettings,
  sidebar,
  messages,
  isStreaming,
  onSend,
  placeholder,
  inputDisabled = false,
  footer,
  emptyTitle,
  emptyText,
}) {
  return (
    <div className="h-screen flex bg-gray-50">
      <aside className="w-80 bg-white border-r border-gray-200 flex flex-col shadow-sm">
        <div className="p-4 border-b border-gray-200">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-900 mb-4 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            All capabilities
          </Link>

          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white shadow-sm shrink-0 ${mode.accent.icon}`}>
              <mode.Icon className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold text-gray-900 truncate">{mode.title}</h1>
              <p className="text-xs text-gray-500 truncate">{mode.tagline}</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">{sidebar}</div>

        <div className="p-3 border-t border-gray-200">
          <button
            type="button"
            onClick={onOpenSettings}
            className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:text-gray-900 hover:bg-gray-50"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12a7.5 7.5 0 0015 0m-15 0a7.5 7.5 0 1115 0m-15 0H3m16.5 0H21m-1.5 0H12m-8.457 3.077l1.41-.513m14.095-5.13l1.41-.513M5.106 17.785l1.15-.964m11.49-9.642l1.149-.964M7.501 19.795l.75-1.3m7.5-12.99l.75-1.3m-6.063 16.658l.26-1.477m2.605-14.772l.26-1.477m0 17.726l-.26-1.477M10.698 4.614l-.26-1.477M16.5 19.794l-.75-1.299M7.5 4.205L12 12m6.894 5.785l-1.149-.964M20.905 7.5l-1.3.75" />
            </svg>
            Provider settings
          </button>
        </div>
      </aside>

      <main className="flex-1 flex flex-col bg-white">
        <ChatWindow
          messages={messages}
          isStreaming={isStreaming}
          emptyTitle={emptyTitle}
          emptyText={emptyText}
        />

        {footer && (
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center">{footer}</p>
          </div>
        )}

        <MessageInput
          onSend={onSend}
          disabled={isStreaming || inputDisabled}
          placeholder={placeholder}
        />
      </main>
    </div>
  )
}
