import { useEffect, useState } from 'react'
import ChatShell from '../components/ChatShell'
import { getTools } from '../api'
import { useDocumentChat } from '../hooks/useDocumentChat'

/**
 * Tool Calling tile: the model picks a function, the backend runs it, and the
 * result comes back as prose — with every invocation visible in the transcript.
 *
 * The sidebar lists the tools from GET /api/tools, which is derived from the
 * same registry the model is given, so the UI can never drift from what the
 * model can actually call.
 */

// One badge per registry `kind`, so a new tool categorises itself.
const KIND_BADGES = {
  local: { label: 'Local', className: 'bg-gray-100 text-gray-600 border-gray-200' },
  api: { label: 'Live API', className: 'bg-blue-50 text-blue-700 border-blue-200' },
  rag: { label: 'Documents', className: 'bg-violet-50 text-violet-700 border-violet-200' },
}

function ToolEntry({ tool, onTry }) {
  const [open, setOpen] = useState(false)
  const badge = KIND_BADGES[tool.kind] || KIND_BADGES.local
  const params = Object.entries(tool.parameters?.properties || {})
  const required = tool.parameters?.required || []

  return (
    <li className="rounded-lg bg-white border border-gray-200 hover:border-gray-300 transition-all">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-start gap-2.5 p-3 text-left"
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-medium text-gray-900">{tool.name}</span>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${badge.className}`}>
              {badge.label}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1 line-clamp-2">{tool.description}</p>
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 mt-0.5 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-gray-200 px-3 py-2.5 space-y-2.5">
          <p className="text-xs text-gray-600 leading-relaxed">{tool.description}</p>

          <div>
            <p className="text-[11px] font-medium text-gray-500 mb-1.5">Parameters</p>
            {params.length === 0 ? (
              <p className="text-xs text-gray-400">None</p>
            ) : (
              <ul className="space-y-1.5">
                {params.map(([name, spec]) => (
                  <li key={name} className="text-xs">
                    <span className="font-mono text-gray-900">{name}</span>
                    <span className="text-gray-400"> : {spec.type}</span>
                    {required.includes(name) && (
                      <span className="text-[10px] text-red-500 ml-1">required</span>
                    )}
                    {spec.description && (
                      <p className="text-gray-500 mt-0.5 leading-snug">{spec.description}</p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {tool.example && (
            <button
              type="button"
              onClick={() => onTry(tool.example)}
              className="w-full text-left text-xs rounded-md border border-violet-200 bg-violet-50 px-2.5 py-2 text-violet-700 hover:bg-violet-100 transition-colors"
            >
              Try: “{tool.example}”
            </button>
          )}
        </div>
      )}
    </li>
  )
}

export default function ToolsMode({ mode, onOpenSettings, activeProvider }) {
  const [tools, setTools] = useState([])
  const [loadError, setLoadError] = useState(false)

  const { messages, append, isLoading } = useDocumentChat({ api: mode.endpoint })

  useEffect(() => {
    getTools()
      .then((data) => setTools(data.tools || []))
      .catch(() => setLoadError(true))
  }, [])

  const handleSend = (question) => {
    append({ role: 'user', content: question })
  }

  const lastMeta = [...messages].reverse().find((m) => m.annotations?.[0])?.annotations?.[0]
  const callCount = messages.reduce((n, m) => n + (m.toolInvocations?.length || 0), 0)

  const sidebar = (
    <>
      <div className="px-4 py-4 bg-gray-50 border-b border-gray-200">
        <h3 className="text-xs font-medium text-gray-500 mb-3">Session Overview</h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">Tools</p>
            <p className="text-2xl font-semibold text-gray-900">{tools.length}</p>
          </div>
          <div className="bg-white rounded-lg p-3 border border-gray-200 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">Calls made</p>
            <p className="text-2xl font-semibold text-gray-900">{callCount}</p>
          </div>
        </div>
      </div>

      <div className="px-4 py-4">
        <h2 className="text-xs font-medium text-gray-500 mb-3">
          Available tools ({tools.length})
        </h2>

        {loadError ? (
          <p className="text-sm text-gray-400">
            Could not load the tool list. Is the backend running?
          </p>
        ) : tools.length === 0 ? (
          <p className="text-sm text-gray-400">Loading tools…</p>
        ) : (
          <ul className="space-y-2">
            {tools.map((tool) => (
              <ToolEntry key={tool.name} tool={tool} onTry={handleSend} />
            ))}
          </ul>
        )}
      </div>

      <div className="px-4 pb-4">
        <h3 className="text-xs font-medium text-gray-500 mb-2">How a turn runs</h3>
        <ol className="space-y-2">
          {mode.steps.map((step, i) => (
            <li
              key={step}
              className="flex items-center gap-3 p-2.5 rounded-lg bg-white border border-gray-200 text-xs text-gray-700"
            >
              <span className={`w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-medium shrink-0 ${mode.accent.iconSoft}`}>
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
        <p className="text-[11px] text-gray-400 mt-2 leading-relaxed">
          Tool calling uses the provider's function-calling API — configure OpenAI
          under Settings.
        </p>
      </div>
    </>
  )

  return (
    <ChatShell
      mode={mode}
      onOpenSettings={onOpenSettings}
      activeProvider={activeProvider}
      sidebar={sidebar}
      messages={messages}
      isStreaming={isLoading}
      onSend={handleSend}
      placeholder="Ask something that needs a tool…"
      emptyTitle="Ask a question that needs a tool"
      emptyText="The model decides which function to call, the backend runs it, and you see the call, its arguments and the raw result before the written answer."
      footer={
        lastMeta?.provider
          ? `Answered by ${lastMeta.provider} • ${lastMeta.model}${
              lastMeta.tools_used?.length ? ` • called ${lastMeta.tools_used.join(', ')}` : ' • no tool needed'
            }`
          : `${tools.length} tools available • provider configured under Settings`
      }
    />
  )
}
