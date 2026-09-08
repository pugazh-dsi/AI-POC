import { useState } from 'react'

/**
 * The conversation list in every tile's sidebar: start a new chat, re-open a
 * stored one, rename or delete it.
 *
 * Conversations are scoped per tile by the `mode` the hook was given, so the
 * RAG tile lists RAG chats and the Tools tile lists tool chats — the same
 * shared component either way.
 */

function relativeTime(iso) {
  if (!iso) return ''
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const seconds = Math.max(0, Math.round((Date.now() - then) / 1000))
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

function ChatRow({ chat, isActive, accent, onOpen, onRename, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(chat.title)

  const commit = () => {
    const title = draft.trim()
    setEditing(false)
    if (title && title !== chat.title) onRename(chat.id, title)
    else setDraft(chat.title)
  }

  if (editing) {
    return (
      <li className="rounded-lg border border-gray-300 bg-white px-2.5 py-2">
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit()
            if (e.key === 'Escape') {
              setDraft(chat.title)
              setEditing(false)
            }
          }}
          className="w-full text-sm text-gray-900 outline-none"
        />
      </li>
    )
  }

  return (
    <li>
      <div
        role="button"
        tabIndex={0}
        onClick={() => onOpen(chat.id)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onOpen(chat.id)
          }
        }}
        className={`group w-full flex items-start gap-2 rounded-lg border px-2.5 py-2 text-left cursor-pointer transition-all ${
          isActive
            ? `bg-white border-gray-300 shadow-sm ${accent.text}`
            : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-sm'
        }`}
      >
        <span
          className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${
            isActive ? accent.dot : 'bg-gray-300'
          }`}
        />
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium text-gray-900 truncate">
            {chat.title}
          </span>
          <span className="block text-[11px] text-gray-400 truncate">
            {relativeTime(chat.updated_at)}
            {chat.message_count ? ` · ${chat.message_count} messages` : ''}
          </span>
        </span>

        <span className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button
            type="button"
            title="Rename chat"
            onClick={(e) => {
              e.stopPropagation()
              setDraft(chat.title)
              setEditing(true)
            }}
            className="p-1 rounded-md text-gray-400 hover:bg-gray-100 hover:text-gray-700"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
            </svg>
          </button>
          <button
            type="button"
            title="Delete chat"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(chat.id)
            }}
            className="p-1 rounded-md text-gray-400 hover:bg-red-50 hover:text-red-600"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </span>
      </div>
    </li>
  )
}

export default function ChatHistory({
  chats = [],
  chatId = null,
  accent,
  onNew,
  onOpen,
  onRename,
  onDelete,
}) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="px-4 py-4 border-b border-gray-200">
      <button
        type="button"
        onClick={onNew}
        className={`w-full inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white shadow-sm transition-opacity hover:opacity-90 ${accent.icon}`}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        New chat
      </button>

      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        className="w-full flex items-center justify-between mt-4 mb-2 text-xs font-medium text-gray-500 hover:text-gray-700"
      >
        <span>Chat history ({chats.length})</span>
        <svg
          className={`w-3.5 h-3.5 transition-transform ${collapsed ? '-rotate-90' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {!collapsed && (
        chats.length === 0 ? (
          <p className="text-sm text-gray-400">
            No saved chats yet. Ask something and it is stored here.
          </p>
        ) : (
          <ul className="space-y-1.5 max-h-64 overflow-y-auto pr-0.5">
            {chats.map((chat) => (
              <ChatRow
                key={chat.id}
                chat={chat}
                isActive={chat.id === chatId}
                accent={accent}
                onOpen={onOpen}
                onRename={onRename}
                onDelete={onDelete}
              />
            ))}
          </ul>
        )
      )}
    </div>
  )
}
