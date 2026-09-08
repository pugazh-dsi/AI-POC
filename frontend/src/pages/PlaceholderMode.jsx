import ChatShell from '../components/ChatShell'

/**
 * Preview for a tile whose backend pipeline is not built yet. It uses the same
 * shell as a live mode so the layout is already proven, but the composer stays
 * disabled — there is no endpoint behind it to call.
 */
export default function PlaceholderMode({ mode, onOpenSettings, activeProvider }) {
  const sidebar = (
    <div className="p-4 space-y-4">
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
        <p className="text-xs font-medium text-gray-500 mb-1">Status</p>
        <p className="text-sm text-gray-700">Not built yet</p>
      </div>

      <div>
        <h3 className="text-xs font-medium text-gray-500 mb-3">Planned pipeline</h3>
        <ol className="space-y-2">
          {mode.steps.map((step, i) => (
            <li
              key={step}
              className="flex items-center gap-3 p-3 rounded-lg bg-white border border-gray-200 text-sm text-gray-700"
            >
              <span className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-medium shrink-0 ${mode.accent.iconSoft}`}>
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </div>

      <div>
        <h3 className="text-xs font-medium text-gray-500 mb-2">Endpoint</h3>
        <p className="text-sm font-mono text-gray-700 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2">
          POST {mode.endpoint}
        </p>
      </div>

      <p className="text-xs text-gray-500 leading-relaxed">{mode.description}</p>
    </div>
  )

  return (
    <ChatShell
      mode={mode}
      onOpenSettings={onOpenSettings}
      activeProvider={activeProvider}
      sidebar={sidebar}
      messages={[]}
      isStreaming={false}
      onSend={() => {}}
      inputDisabled
      placeholder="Not available yet"
      emptyTitle={`${mode.title} is coming soon`}
      emptyText={mode.description}
      footer={`This tile shares the chat shell — only the pipeline behind ${mode.endpoint} is missing`}
    />
  )
}
