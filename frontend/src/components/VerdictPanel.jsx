/**
 * The JSON verdict from POST /api/guardrails/validate, rendered.
 *
 * Every rule lands in exactly one of three buckets — Failed, Not Evaluable,
 * Passed — because that separation is the point of the demo: "not evaluable"
 * is not a pass, it is a document held because the extraction had a gap.
 */

const STATUS_STYLES = {
  compliant: {
    label: 'Compliant',
    banner: 'border-green-200 bg-green-50',
    dot: 'bg-green-500',
    text: 'text-green-800',
  },
  non_compliant: {
    label: 'Non-compliant',
    banner: 'border-red-200 bg-red-50',
    dot: 'bg-red-500',
    text: 'text-red-800',
  },
  incomplete: {
    label: 'Held — incomplete',
    banner: 'border-amber-200 bg-amber-50',
    dot: 'bg-amber-500',
    text: 'text-amber-800',
  },
}

const GROUPS = [
  {
    key: 'fail',
    title: 'Failed',
    hint: 'A rule was evaluated and the requisition violates it.',
    card: 'border-red-200 bg-red-50/60',
    badge: 'bg-red-100 text-red-700',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    ),
    iconColor: 'text-red-600',
  },
  {
    key: 'not_evaluable',
    title: 'Not evaluable',
    hint: 'A required field was missing, so the rule failed closed.',
    card: 'border-amber-200 bg-amber-50/60',
    badge: 'bg-amber-100 text-amber-800',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m0 3.75h.007M12 3l9 16.5H3L12 3z" />
    ),
    iconColor: 'text-amber-600',
  },
  {
    key: 'pass',
    title: 'Passed',
    hint: 'The rule was evaluated against real values and is satisfied.',
    card: 'border-green-200 bg-green-50/60',
    badge: 'bg-green-100 text-green-700',
    icon: <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />,
    iconColor: 'text-green-600',
  },
]

const SEVERITY_STYLES = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-gray-100 text-gray-600',
}

function Rule({ rule, group }) {
  const details = rule.details && Object.keys(rule.details).length > 0 ? rule.details : null

  return (
    <li className={`rounded-lg border p-4 ${group.card}`}>
      <div className="flex items-start gap-3">
        <svg
          className={`w-5 h-5 mt-0.5 shrink-0 ${group.iconColor}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          {group.icon}
        </svg>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-gray-500">{rule.id}</span>
            <h4 className="text-sm font-semibold text-gray-900">{rule.title || rule.name}</h4>
            <span
              className={`text-[10px] font-medium uppercase tracking-wide px-1.5 py-0.5 rounded ${
                SEVERITY_STYLES[rule.severity] || SEVERITY_STYLES.low
              }`}
            >
              {rule.severity}
            </span>
          </div>

          <p className="mt-1.5 text-sm text-gray-800">{rule.message}</p>

          {rule.remediation && (
            <p className="mt-2 text-xs text-gray-600">
              <span className="font-medium text-gray-700">Next step: </span>
              {rule.remediation}
            </p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
            <span className="font-mono">{rule.operator}()</span>
            {(rule.fields || []).map((field) => (
              <span key={field} className="font-mono px-1.5 py-0.5 rounded bg-white border border-gray-200">
                {field}
              </span>
            ))}
          </div>

          {details && (
            <details className="mt-2">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                Evidence
              </summary>
              <pre className="mt-1.5 text-[11px] leading-relaxed bg-white border border-gray-200 rounded p-2 overflow-x-auto text-gray-700">
                {JSON.stringify(details, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    </li>
  )
}

export default function VerdictPanel({ result, loading = false, error = null }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-500">
        <span className="inline-flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          Extracting fields and running the rule pack…
        </span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6">
        <h3 className="text-sm font-semibold text-red-800">Validation failed</h3>
        <p className="mt-1 text-sm text-red-700">{error}</p>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center">
        <p className="text-sm text-gray-600">No verdict yet.</p>
        <p className="mt-1 text-xs text-gray-500">
          Pick a requisition on the left and run validation to see every rule's outcome.
        </p>
      </div>
    )
  }

  const verdict = result.verdict || result
  const style = STATUS_STYLES[verdict.status] || STATUS_STYLES.incomplete
  const grouped = GROUPS.map((group) => ({
    group,
    rules: (verdict.results || []).filter((r) => r.status === group.key),
  }))

  return (
    <div className="space-y-4">
      <div className={`rounded-xl border p-5 ${style.banner}`}>
        <div className="flex flex-wrap items-center gap-3">
          <span className={`w-2.5 h-2.5 rounded-full ${style.dot}`} />
          <h3 className={`text-base font-semibold ${style.text}`}>{style.label}</h3>
          {verdict.blocked && (
            <span className="text-[10px] font-medium uppercase tracking-wide px-2 py-0.5 rounded-full bg-white/70 text-gray-700 border border-gray-200">
              Held from the LIS
            </span>
          )}
        </div>

        <p className={`mt-2 text-sm ${style.text}`}>{verdict.headline}</p>

        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
          {[
            ['Passed', verdict.summary?.passed, 'text-green-700'],
            ['Failed', verdict.summary?.failed, 'text-red-700'],
            ['Not evaluable', verdict.summary?.not_evaluable, 'text-amber-700'],
            ['Rules run', verdict.summary?.total, 'text-gray-700'],
          ].map(([label, value, color]) => (
            <div key={label} className="rounded-lg bg-white/80 border border-white px-3 py-2">
              <p className={`text-xl font-semibold ${color}`}>{value ?? 0}</p>
              <p className="text-[11px] text-gray-600">{label}</p>
            </div>
          ))}
        </div>

        <p className="mt-3 text-[11px] text-gray-600">
          {verdict.pack}
          {verdict.pack_version ? ` v${verdict.pack_version}` : ''} · {verdict.source} ·{' '}
          {result.extraction_source === 'llm'
            ? `extracted by ${result.provider?.label || 'the model'} (${result.provider?.model || ''})`
            : result.extraction_source === 'client'
              ? 'client-supplied extraction'
              : 'reference extraction'}{' '}
          · evaluated {verdict.evaluated_at}
        </p>
      </div>

      {grouped.map(({ group, rules }) =>
        rules.length === 0 ? null : (
          <section key={group.key}>
            <div className="flex items-baseline gap-2 mb-2">
              <h3 className="text-sm font-semibold text-gray-900">{group.title}</h3>
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${group.badge}`}>{rules.length}</span>
              <span className="text-xs text-gray-500">{group.hint}</span>
            </div>
            <ul className="space-y-2">
              {rules.map((rule) => (
                <Rule key={rule.id} rule={rule} group={group} />
              ))}
            </ul>
          </section>
        )
      )}

      <details className="rounded-xl border border-gray-200 bg-white p-4">
        <summary className="text-sm font-medium text-gray-700 cursor-pointer">
          Raw JSON response
        </summary>
        <pre className="mt-3 text-[11px] leading-relaxed bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-x-auto text-gray-700">
          {JSON.stringify(result, null, 2)}
        </pre>
      </details>
    </div>
  )
}
