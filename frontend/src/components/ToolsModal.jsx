import { useEffect, useMemo, useState } from 'react'
import IntegrationIcon from './IntegrationIcon'

/**
 * The Tool Calling tile's tool workspace, in a popup: every tool the model can
 * actually call, grouped by the system it belongs to, with its parameters, a
 * one-click example prompt and an on/off switch.
 *
 * Mirrors DocumentsModal on the RAG tile — the sidebar keeps the conversation
 * and one button into here. It renders from the catalog the tile already
 * fetched (GET /api/tools, derived from the same registry the model is given),
 * so the popup, the sidebar count and the model can never disagree.
 *
 * Switching a tool off is not a display filter: the backend drops it from the
 * schemas handed to the model and refuses to run it, so the row and the
 * capability disappear together.
 */

// One badge per registry `kind`, so a new tool categorises itself.
export const KIND_BADGES = {
  local: { label: 'Local', className: 'bg-gray-100 text-gray-600 border-gray-200' },
  api: { label: 'Live API', className: 'bg-blue-50 text-blue-700 border-blue-200' },
  rag: { label: 'Documents', className: 'bg-violet-50 text-violet-700 border-violet-200' },
  integration: { label: 'Integration', className: 'bg-amber-50 text-amber-700 border-amber-200' },
  mcp: { label: 'MCP', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
}

export function Switch({ checked, disabled, onChange, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={(e) => {
        // The row itself expands on click; the switch must not do both.
        e.stopPropagation()
        onChange(!checked)
      }}
      className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
        checked ? 'bg-violet-600' : 'bg-gray-300'
      }`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-[1.15rem]' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

export function ToolEntry({ tool, onTry, onToggle, pending = false, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const badge = KIND_BADGES[tool.kind] || KIND_BADGES.local
  const params = Object.entries(tool.parameters?.properties || {})
  const required = tool.parameters?.required || []
  const enabled = tool.enabled !== false

  return (
    <li
      className={`rounded-lg bg-white border transition-all ${
        enabled ? 'border-gray-200 hover:border-gray-300' : 'border-dashed border-gray-200 opacity-60'
      }`}
    >
      <div className="flex items-start gap-2.5 p-3">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="min-w-0 flex-1 text-left"
        >
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-xs font-medium text-gray-900">{tool.name}</span>
            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${badge.className}`}>
              {badge.label}
            </span>
            {tool.demo && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded border bg-orange-50 text-orange-700 border-orange-200">
                Demo data
              </span>
            )}
            {!enabled && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded border bg-gray-100 text-gray-500 border-gray-200">
                Off
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-1 line-clamp-2">{tool.description}</p>
        </button>

        {onToggle && (
          <Switch
            checked={enabled}
            disabled={pending}
            onChange={(next) => onToggle(tool.name, next)}
            label={`${enabled ? 'Disable' : 'Enable'} ${tool.name}`}
          />
        )}

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="shrink-0 mt-0.5 text-gray-400"
          aria-label={open ? 'Collapse' : 'Expand'}
        >
          <svg
            className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>
      </div>

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

          {tool.example && onTry && (
            <button
              type="button"
              onClick={() => onTry(tool.example)}
              disabled={!enabled}
              title={enabled ? undefined : 'Switch this tool on to try it'}
              className="w-full text-left text-xs rounded-md border border-violet-200 bg-violet-50 px-2.5 py-2 text-violet-700 transition-colors hover:bg-violet-100 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-violet-50"
            >
              Try: “{tool.example}”
            </button>
          )}
        </div>
      )}
    </li>
  )
}

export default function ToolsModal({
  open,
  tools = [],
  integrations = [],
  callCount = 0,
  messageCount = 0,
  loadError = false,
  onClose,
  onTry,
  onToggle,
  onToggleGroup,
  pendingTools = [],
}) {
  const [filter, setFilter] = useState('')

  // Reset the search each time it opens, so it never comes back filtered.
  useEffect(() => {
    if (open) setFilter('')
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const query = filter.trim().toLowerCase()

  // Group the (filtered) tools under their integration, in the backend's
  // order. A tool whose integration the backend didn't describe still shows,
  // under an "Other" heading, rather than vanishing.
  const groups = useMemo(() => {
    const visible = query
      ? tools.filter(
          (t) =>
            t.name.toLowerCase().includes(query) ||
            (t.label || '').toLowerCase().includes(query) ||
            (t.description || '').toLowerCase().includes(query) ||
            (t.integration || '').toLowerCase().includes(query)
        )
      : tools

    const known = integrations.map((g) => ({ ...g, tools: [] }))
    const byId = new Map(known.map((g) => [g.id, g]))
    const extras = { id: '_other', label: 'Other', icon: 'unknown', description: '', tools: [] }

    for (const tool of visible) {
      const group = byId.get(tool.integration) || extras
      group.tools.push(tool)
    }

    const all = [...known, ...(extras.tools.length ? [extras] : [])]
    return all.filter((g) => g.tools.length > 0)
  }, [tools, integrations, query])

  if (!open) return null

  const enabledCount = tools.filter((t) => t.enabled !== false).length
  const matchCount = groups.reduce((n, g) => n + g.tools.length, 0)
  const pending = new Set(pendingTools)

  // Running an example closes the popup so the answer is visible straight away.
  const handleTry = (example) => {
    onTry?.(example)
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Available tools</h2>
            <p className="text-xs text-gray-500">
              Every function the model can call, grouped by integration. Switch one off
              and the model stops seeing it.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-all"
            title="Close"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Stats and the filter stay put; only the catalog itself scrolls, so a
            long tool list never pushes the search box off the screen. */}
        <div className="px-6 pt-6 pb-4 space-y-4 shrink-0">
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500 mb-1">Tools enabled</p>
              <p className="text-2xl font-semibold text-gray-900">
                {enabledCount}
                <span className="text-sm font-normal text-gray-400"> / {tools.length}</span>
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500 mb-1">Calls made</p>
              <p className="text-2xl font-semibold text-gray-900">{callCount}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-xs text-gray-500 mb-1">Questions asked</p>
              <p className="text-2xl font-semibold text-gray-900">{messageCount}</p>
            </div>
          </div>

          {tools.length > 5 && (
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter tools or integrations…"
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 outline-none focus:border-violet-400"
            />
          )}
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto px-6 pb-6">
          {loadError ? (
            <p className="text-sm text-gray-400 text-center py-6">
              Could not load the tool list. Is the backend running?
            </p>
          ) : tools.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">Loading tools…</p>
          ) : matchCount === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">
              No tool matches “{filter.trim()}”.
            </p>
          ) : (
            <div className="space-y-5">
              {groups.map((group) => {
                const on = group.tools.filter((t) => t.enabled !== false).length
                const allOn = on === group.tools.length

                return (
                  <section key={group.id}>
                    <div className="flex items-start gap-2.5 mb-2">
                      <IntegrationIcon slug={group.icon} tile />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="text-sm font-semibold text-gray-900">{group.label}</h3>
                          <span className="text-[11px] text-gray-400">
                            {on} of {group.tools.length} on
                          </span>
                        </div>
                        {group.description && (
                          <p className="text-[11px] text-gray-500 leading-snug">{group.description}</p>
                        )}
                      </div>
                      {onToggleGroup && (
                        <button
                          type="button"
                          onClick={() =>
                            onToggleGroup(group.tools.map((t) => t.name), !allOn)
                          }
                          className="shrink-0 text-[11px] font-medium text-gray-500 hover:text-violet-700 transition-colors"
                        >
                          {allOn ? 'Turn all off' : 'Turn all on'}
                        </button>
                      )}
                    </div>

                    <ul className="space-y-2">
                      {group.tools.map((tool) => (
                        <ToolEntry
                          key={tool.name}
                          tool={tool}
                          onTry={handleTry}
                          onToggle={onToggle}
                          pending={pending.has(tool.name)}
                        />
                      ))}
                    </ul>
                  </section>
                )
              })}
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 rounded-b-xl">
          <p className="text-xs text-gray-500">
            This list comes from the same registry the model is given, so it can never
            claim a tool the model cannot call. Integrations marked{' '}
            <span className="font-medium text-orange-700">Demo data</span> return
            simulated records, not a live account.
          </p>
        </div>
      </div>
    </div>
  )
}
