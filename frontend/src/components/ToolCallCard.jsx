import { useState } from 'react'

/**
 * One tool invocation, as streamed by the "9:" (call) and "a:" (result) parts
 * and surfaced by useChat as `message.toolInvocations`.
 *
 * The point of the Tool Calling tile is that the machinery is visible, so the
 * arguments and the raw JSON result are both inspectable — the card shows the
 * signature line by default and expands to the payloads.
 */

function formatArgs(args) {
  if (!args || Object.keys(args).length === 0) return ''
  return Object.entries(args)
    .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
    .join(', ')
}

export default function ToolCallCard({ invocation }) {
  const [open, setOpen] = useState(false)

  const { toolName, args, state, result } = invocation
  // state is 'partial-call' | 'call' | 'result'
  const isDone = state === 'result'
  const failed = isDone && result && typeof result === 'object' && result.error

  const status = failed ? 'failed' : isDone ? 'done' : 'running'
  const statusStyles = {
    running: 'bg-amber-50 text-amber-700 border-amber-200',
    done: 'bg-violet-50 text-violet-700 border-violet-200',
    failed: 'bg-red-50 text-red-700 border-red-200',
  }[status]

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-100 transition-colors"
      >
        <span className={`w-6 h-6 rounded-md border flex items-center justify-center shrink-0 ${statusStyles}`}>
          {status === 'running' ? (
            <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
          ) : failed ? (
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          )}
        </span>

        <span className="min-w-0 flex-1">
          <span className="font-mono text-xs text-gray-900">
            {toolName}
            <span className="text-gray-500">({formatArgs(args)})</span>
          </span>
        </span>

        <span className="text-[11px] font-medium text-gray-400 shrink-0">
          {status === 'running' ? 'running' : failed ? 'error' : 'result'}
        </span>

        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <div className="border-t border-gray-200 bg-white px-3 py-2 space-y-2">
          <div>
            <p className="text-[11px] font-medium text-gray-500 mb-1">Arguments</p>
            <pre className="text-[11px] font-mono text-gray-700 bg-gray-50 border border-gray-200 rounded p-2 overflow-x-auto">
              {JSON.stringify(args ?? {}, null, 2)}
            </pre>
          </div>
          {isDone && (
            <div>
              <p className="text-[11px] font-medium text-gray-500 mb-1">Result</p>
              <pre className="text-[11px] font-mono text-gray-700 bg-gray-50 border border-gray-200 rounded p-2 overflow-x-auto max-h-64 overflow-y-auto">
                {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
