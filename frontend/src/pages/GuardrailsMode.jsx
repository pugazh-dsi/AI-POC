import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import VerdictPanel from '../components/VerdictPanel'
import FileUpload from '../components/FileUpload'
import { ProviderBadge } from '../components/ProviderIcon'
import { getDocuments, getGuardrailRules, validateRequisition } from '../api'

/**
 * The Guardrails tile: a lab requisition goes in, a deterministic compliance
 * verdict comes out.
 *
 * The page is deliberately not the chat shell. Nothing here is a conversation:
 * the model's only job is filling the extraction schema, and the panel below the
 * guardrail list is the Python rule engine's output, rule by rule.
 *
 * The guardrail list is fetched from GET /api/guardrails/rules so it is the same
 * YAML the engine evaluates. FALLBACK_GUARDRAILS keeps the panel readable when
 * the backend is unreachable — it is a copy of the pack's display wording.
 */

const FALLBACK_GUARDRAILS = [
  {
    id: 'LR-001',
    title: 'Identity Verification',
    description:
      'Ensures critical identifiers (Patient ID, Name, Physician) are completely extracted before processing.',
  },
  {
    id: 'LR-002',
    title: 'Minor Consent Protocol',
    description:
      'Calculates exact patient age and halts processing if parental consent documentation is missing for minors.',
  },
  {
    id: 'LR-003',
    title: 'Chronological Validation',
    description:
      "Prevents processing of specimens where the collection date predates the physician's order date.",
  },
  {
    id: 'LR-004',
    title: 'Biological Compatibility',
    description:
      'Cross-references patient gender with requested test panels to prevent logically impossible lab orders (e.g., PSA tests for female patients).',
  },
  {
    id: 'LR-005',
    title: 'Pre-Test Protocol Check',
    description:
      'Verifies fasting status against the specific requirements of the requested test panels to prevent invalid lab results.',
  },
]

const REFERENCE_SOURCE = 'LR-2026-001_Lab_Requisition.docx'

function FieldValue({ value }) {
  if (value === null || value === undefined || value === '') {
    return <span className="text-amber-600 font-medium">null</span>
  }
  if (typeof value === 'boolean') {
    return <span className="text-gray-900">{value ? 'true' : 'false'}</span>
  }
  if (Array.isArray(value)) {
    return (
      <span className="text-gray-900">
        {value.length === 0 ? <span className="text-amber-600 font-medium">empty</span> : value.join(', ')}
      </span>
    )
  }
  return <span className="text-gray-900">{String(value)}</span>
}

export default function GuardrailsMode({ mode, onOpenSettings, activeProvider }) {
  const [pack, setPack] = useState(null)
  const [documents, setDocuments] = useState([])
  // '' means the reference extraction (no provider call); anything else is an
  // uploaded filename the model extracts first.
  const [source, setSource] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getGuardrailRules()
      .then(setPack)
      .catch(() => setPack(null))
    getDocuments()
      .then((data) => setDocuments(data.documents || []))
      .catch(() => setDocuments([]))
  }, [])

  const guardrails = pack?.guardrails?.length ? pack.guardrails : FALLBACK_GUARDRAILS
  const extracted = result?.verdict?.extracted || null
  const schemaFields = useMemo(
    () => (pack?.schema?.length ? pack.schema.map((f) => f.field) : Object.keys(extracted || {})),
    [pack, extracted]
  )

  const handleUploadSuccess = (result) => {
    setDocuments((prev) => {
      const next = prev.filter((d) => d.filename !== result.filename)
      next.push({ filename: result.filename, chunks: result.chunks })
      return next
    })
    setSource(result.filename)
  }

  async function runValidation() {
    setLoading(true)
    setError(null)
    try {
      const data = await validateRequisition(source ? { filename: source } : {})
      setResult(data)
    } catch (e) {
      setResult(null)
      setError(e.response?.data?.detail || e.message || 'Validation request failed')
    } finally {
      setLoading(false)
    }
  }

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
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center text-white shadow-sm shrink-0 ${mode.accent.icon}`}
            >
              <mode.Icon className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold text-gray-900 truncate">{mode.title}</h1>
              <p className="text-xs text-gray-500 truncate">{mode.tagline}</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          <div>
            <h3 className="text-xs font-medium text-gray-500 mb-3">How a validation runs</h3>
            <ol className="space-y-2">
              {mode.steps.map((step, i) => (
                <li
                  key={step}
                  className="flex items-center gap-3 p-3 rounded-lg bg-white border border-gray-200 text-sm text-gray-700"
                >
                  <span
                    className={`w-6 h-6 rounded-md flex items-center justify-center text-xs font-medium shrink-0 ${mode.accent.iconSoft}`}
                  >
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-1.5">
            <p className="text-xs font-medium text-gray-500">Rule pack</p>
            <p className="text-sm font-mono text-gray-800 break-all">
              {pack ? `${pack.pack}.yaml v${pack.version ?? 1}` : 'lab_requisition.yaml'}
            </p>
            <p className="text-xs text-gray-500 leading-relaxed">
              {guardrails.length} declarative rules, evaluated in Python. The model never sees them.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-3">
            <p className="text-xs font-medium text-gray-500 mb-2">Separation of concerns</p>
            <ul className="space-y-2 text-xs text-gray-600 leading-relaxed">
              <li>
                <span className="font-medium text-gray-800">LLM:</span> reads the document, fills the
                extraction schema, writes <span className="font-mono">null</span> for anything it cannot
                read.
              </li>
              <li>
                <span className="font-medium text-gray-800">Python:</span> evaluates the rule pack against
                those fields. Same payload, same verdict, every time.
              </li>
              <li>
                <span className="font-medium text-gray-800">Fail closed:</span> a missing field is
                <span className="font-mono"> not_evaluable</span>, never a pass.
              </li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-medium text-gray-500 mb-2">Endpoint</h3>
            <p className="text-sm font-mono text-gray-700 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 break-all">
              POST {mode.endpoint}
            </p>
          </div>
        </div>

        <div className="p-3 border-t border-gray-200">
          <button
            type="button"
            onClick={onOpenSettings}
            className="w-full inline-flex items-center gap-2.5 rounded-lg border border-gray-200 px-3 py-2 text-left transition-colors hover:border-gray-300 hover:bg-gray-50"
          >
            {activeProvider ? (
              <ProviderBadge icon={activeProvider.icon} size="sm" />
            ) : (
              <span className="w-6 h-6 rounded-md bg-gray-200 flex items-center justify-center text-gray-500 shrink-0">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m0 3.75h.007M4.5 19.5h15a1.5 1.5 0 001.3-2.25l-7.5-13a1.5 1.5 0 00-2.6 0l-7.5 13A1.5 1.5 0 004.5 19.5z"
                  />
                </svg>
              </span>
            )}
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium text-gray-800 truncate">
                {activeProvider ? activeProvider.label : 'No provider connected'}
              </span>
              <span className="block text-xs text-gray-500 truncate">
                {activeProvider ? `Extraction on ${activeProvider.model}` : 'Add an API key to extract'}
              </span>
            </span>
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 md:px-10 py-8 space-y-6">
          <header>
            <h2 className="text-2xl font-semibold text-gray-900">
              {pack?.title || 'Healthcare Lab Requisition Compliance'}
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              {pack?.description ||
                'Deterministic compliance checks applied to every extracted lab requisition before it is released to the laboratory information system.'}
            </p>
          </header>

          {/* The client-facing statement of what the engine enforces. */}
          <section className="rounded-xl border border-green-200 bg-white shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-green-100 bg-green-50 flex items-center gap-3">
              <span className="w-8 h-8 rounded-lg bg-green-600 text-white flex items-center justify-center shrink-0">
                <svg className="w-4.5 h-4.5" width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                  />
                </svg>
              </span>
              <div>
                <h3 className="text-base font-semibold text-green-900">Active Compliance Guardrails</h3>
                <p className="text-xs text-green-800/80">
                  Enforced in Python on every requisition — not by the language model.
                </p>
              </div>
            </div>

            <ul className="divide-y divide-gray-100">
              {guardrails.map((rule) => (
                <li key={rule.id || rule.title} className="px-5 py-4 flex items-start gap-3">
                  <span className="mt-2 w-2 h-2 rounded-full bg-green-500 shrink-0" />
                  <p className="text-sm text-gray-700 leading-relaxed">
                    <span className="font-semibold text-gray-900">{rule.title}:</span> {rule.description}
                  </p>
                </li>
              ))}
            </ul>
          </section>

          {/* Choose what to validate, then run the pipeline. */}
          <section className="rounded-xl border border-gray-200 bg-white shadow-sm p-5">
            <h3 className="text-sm font-semibold text-gray-900">Validate a requisition</h3>

            <div className="mt-3 rounded-lg border border-dashed border-gray-300 bg-gray-50 p-3">
              <FileUpload onUploadSuccess={handleUploadSuccess} className="" />
            </div>

            <div className="mt-4 flex flex-col sm:flex-row gap-3">
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-500/40 focus:border-green-500"
              >
                <option value="">Reference extraction — {REFERENCE_SOURCE} (no provider call)</option>
                {documents.map((doc) => (
                  <option key={doc.filename} value={doc.filename}>
                    Extract with the model — {doc.filename}
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={runValidation}
                disabled={loading}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Validating…' : 'Run validation'}
              </button>
            </div>
            <p className="mt-2 text-xs text-gray-500">
              {source
                ? 'The document is parsed, the model fills the extraction schema, and the rule pack scores the result.'
                : 'Runs the rule pack against the stored extraction for the reference requisition — no model call.'}
            </p>
          </section>

          {/* What the model produced — the only thing it contributed. */}
          {extracted && (
            <section className="rounded-xl border border-gray-200 bg-white shadow-sm p-5">
              <div className="flex items-baseline justify-between gap-3 flex-wrap">
                <h3 className="text-sm font-semibold text-gray-900">Extracted fields</h3>
                <span className="text-xs text-gray-500">
                  {result.extraction_source === 'llm'
                    ? `Extracted by ${result.provider?.label} · ${result.provider?.model}`
                    : result.extraction_source === 'client'
                      ? 'Client-supplied payload'
                      : 'Reference payload'}
                </span>
              </div>
              <dl className="mt-3 grid sm:grid-cols-2 gap-x-6 gap-y-2">
                {schemaFields.map((field) => (
                  <div key={field} className="flex items-start justify-between gap-3 py-1 border-b border-gray-100">
                    <dt className="text-xs font-mono text-gray-500 shrink-0">{field}</dt>
                    <dd className="text-sm text-right break-words">
                      <FieldValue value={extracted[field]} />
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          <section>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Validation verdict</h3>
            <VerdictPanel result={result} loading={loading} error={error} />
          </section>
        </div>
      </main>
    </div>
  )
}
