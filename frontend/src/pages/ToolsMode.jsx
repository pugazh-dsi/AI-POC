import { useCallback, useEffect, useMemo, useState } from 'react'
import ChatShell from '../components/ChatShell'
import ChatHistory from '../components/ChatHistory'
import ToolsModal from '../components/ToolsModal'
import ConnectionsModal from '../components/ConnectionsModal'
import { getTools, setToolEnabled } from '../api'
import { useDocumentChat } from '../hooks/useDocumentChat'

/**
 * Tool Calling tile: the model picks a function, the backend runs it, and the
 * result comes back as prose — with every invocation visible in the transcript.
 *
 * The tool catalog comes from GET /api/tools, which is derived from the same
 * registry the model is given, so the UI can never drift from what the model
 * can actually call. Tools are grouped by integration (built-in, AWS,
 * Snowflake, Google Workspace, Salesforce) and each one can be switched off —
 * the backend then drops it from the schemas, so the switch removes the
 * capability, not just the row.
 *
 * Everything about the catalog — the stats, the full list, parameters, the
 * example prompts, the switches — lives in ToolsModal behind the pinned
 * sidebar button, leaving that column for the conversation itself. The sidebar
 * names no tool and no integration: the popup is the one place the catalog is
 * shown, so the two can never disagree.
 *
 * ConnectionsModal sits beside it and decides what that catalog contains:
 * connecting an AWS account swings the S3 / CloudWatch tools from demo data to
 * live read-only calls, and connecting an MCP server adds its tools outright.
 * Both re-fetch the catalog when they change something, so the popup, the
 * button's count and the model always describe the same set of tools.
 */
export default function ToolsMode({ mode, onOpenSettings, activeProvider }) {
  const [tools, setTools] = useState([])
  const [integrations, setIntegrations] = useState([])
  const [pendingTools, setPendingTools] = useState([])
  const [loadError, setLoadError] = useState(false)
  const [toolsOpen, setToolsOpen] = useState(false)
  const [connectionsOpen, setConnectionsOpen] = useState(false)

  const {
    messages, isLoading,
    send, chats, chatId, newChat, openChat, removeChat, renameChat,
  } = useDocumentChat({ api: mode.endpoint, mode: mode.id })

  // Re-read after a connection changes: an MCP server adds or removes whole
  // tools, and connecting AWS clears their "Demo data" badge.
  const loadTools = useCallback(() => {
    getTools()
      .then((data) => {
        setTools(data.tools || [])
        setIntegrations(data.integrations || [])
        setLoadError(false)
      })
      .catch(() => setLoadError(true))
  }, [])

  useEffect(() => {
    loadTools()
  }, [loadTools])

  const handleSend = (question) => {
    send(question)
  }

  // Optimistic: the switch moves immediately and only rolls back if the write
  // failed, so toggling a row never feels laggy.
  const applyEnabled = (names, enabled) => {
    const wanted = new Set(names)
    setTools((prev) =>
      prev.map((t) => (wanted.has(t.name) ? { ...t, enabled } : t))
    )
  }

  const toggleTools = async (names, enabled) => {
    if (names.length === 0) return

    const before = tools
    applyEnabled(names, enabled)
    setPendingTools((prev) => [...prev, ...names])

    try {
      const results = await Promise.all(
        names.map((name) => setToolEnabled(name, enabled))
      )
      // The last response carries the current integration counts.
      const last = results[results.length - 1]
      if (last?.integrations) setIntegrations(last.integrations)
    } catch {
      setTools(before)
    } finally {
      setPendingTools((prev) => prev.filter((n) => !names.includes(n)))
    }
  }

  const handleToggle = (name, enabled) => toggleTools([name], enabled)
  const handleToggleGroup = (names, enabled) => toggleTools(names, enabled)

  const enabledTools = useMemo(
    () => tools.filter((t) => t.enabled !== false),
    [tools]
  )

  const lastMeta = [...messages].reverse().find((m) => m.annotations?.[0])?.annotations?.[0]
  const callCount = messages.reduce((n, m) => n + (m.toolInvocations?.length || 0), 0)

  const history = (
    <ChatHistory
      chats={chats}
      chatId={chatId}
      accent={mode.accent}
      onNew={newChat}
      onOpen={openChat}
      onRename={renameChat}
      onDelete={removeChat}
    />
  )

  const connectedCount = integrations.length

  // Pinned to the bottom of the sidebar so both stay reachable however long the
  // chat history grows: the full catalog, and what feeds it.
  const sidebarFooter = (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setToolsOpen(true)}
        className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition-all hover:border-gray-300 hover:bg-gray-50"
      >
        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75 3.75 2.25 7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
        </svg>
        {tools.length === 0
          ? 'View available tools'
          : `View all tools (${enabledTools.length}/${tools.length})`}
      </button>

      <button
        type="button"
        onClick={() => setConnectionsOpen(true)}
        className="w-full inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm transition-all hover:border-gray-300 hover:bg-gray-50"
      >
        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
        </svg>
        {connectedCount === 0
          ? 'Connect AWS or MCP'
          : `Connections (${connectedCount})`}
      </button>
    </div>
  )

  const sidebar = (
    <>
      <div className="px-4 py-4">
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
    <>
      <ChatShell
        mode={mode}
        onOpenSettings={onOpenSettings}
        activeProvider={activeProvider}
        history={history}
        sidebar={sidebar}
        sidebarFooter={sidebarFooter}
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
            : `${enabledTools.length} tools available across ${integrations.length} integrations • provider configured under Settings`
        }
      />

      <ConnectionsModal
        open={connectionsOpen}
        onClose={() => setConnectionsOpen(false)}
        onChange={loadTools}
      />

      <ToolsModal
        open={toolsOpen}
        tools={tools}
        integrations={integrations}
        callCount={callCount}
        messageCount={messages.filter((m) => m.role === 'user').length}
        loadError={loadError}
        pendingTools={pendingTools}
        onClose={() => setToolsOpen(false)}
        onTry={handleSend}
        onToggle={handleToggle}
        onToggleGroup={handleToggleGroup}
      />
    </>
  )
}
