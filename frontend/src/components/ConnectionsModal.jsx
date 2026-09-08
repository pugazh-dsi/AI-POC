import { useEffect, useState } from 'react'
import IntegrationIcon from './IntegrationIcon'
import { Switch } from './ToolsModal'
import {
  getConnections,
  connectAws,
  testAws,
  setAwsEnabled,
  disconnectAws,
  connectMcpServer,
  updateMcpServer,
  refreshMcpServer,
  disconnectMcpServer,
} from '../api'

/**
 * Connections: the systems the Tool Calling tile reaches out to.
 *
 * Two kinds in one popup, because they answer the same question — what can the
 * model actually reach right now:
 *
 *   AWS  one account. Connecting it flips the S3 / CloudWatch tools from the
 *        fixture account to real, read-only calls; the "Demo data" pills in
 *        the tools popup disappear with it.
 *   MCP  any number of remote servers. Connecting one pulls its tools into the
 *        same catalog, with the same on/off switches as everything else.
 *
 * Credentials only ever travel upwards. The backend masks every secret, so a
 * stored key renders as `AKI...MPLE` and the form's secret field stays blank —
 * submitting it blank means "keep the stored one".
 *
 * `onChange` fires after anything that alters what the model can call, so the
 * tile re-fetches the tool catalog and the two views cannot disagree.
 */

const REGIONS = [
  'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
  'eu-west-1', 'eu-west-2', 'eu-central-1',
  'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1',
  'sa-east-1', 'ca-central-1',
]

function errorText(err, fallback) {
  return err?.response?.data?.detail || err?.message || fallback
}

function Field({ label, hint, ...props }) {
  return (
    <label className="block">
      <span className="text-[11px] font-medium text-gray-600">{label}</span>
      <input
        className="mt-1 w-full rounded-md border border-gray-200 px-2.5 py-1.5 text-xs text-gray-900 placeholder:text-gray-400 focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-200"
        {...props}
      />
      {hint && <span className="mt-1 block text-[10px] text-gray-400">{hint}</span>}
    </label>
  )
}

function Note({ type = 'error', children }) {
  if (!children) return null
  const tone =
    type === 'success'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : 'bg-red-50 text-red-700 border-red-200'
  return (
    <p className={`rounded-md border px-2.5 py-2 text-[11px] leading-relaxed ${tone}`}>
      {children}
    </p>
  )
}

function Button({ variant = 'ghost', className = '', ...props }) {
  const styles = {
    primary:
      'bg-violet-600 text-white hover:bg-violet-700 disabled:bg-violet-300',
    ghost:
      'border border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50',
    danger:
      'border border-red-200 bg-white text-red-600 hover:border-red-300 hover:bg-red-50',
  }
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${styles[variant]} ${className}`}
      {...props}
    />
  )
}

/* ── AWS ─────────────────────────────────────────────────── */

function AwsSection({ aws, busy, onRun }) {
  // Seeded from what is stored, minus the secret — the browser never has it.
  // The parent remounts this on a new `updated_at`, which is what re-seeds it;
  // syncing in an effect would fight the user's typing instead.
  const [form, setForm] = useState(() => ({
    access_key_id: aws?.config?.access_key_id || '',
    secret_access_key: '',
    session_token: '',
    region: aws?.config?.region || 'us-east-1',
  }))
  const [editing, setEditing] = useState(false)
  const connected = Boolean(aws?.connected)
  const showForm = !connected || editing

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))

  const handleConnect = () =>
    onRun('aws', () => connectAws(form), () => {
      setEditing(false)
      setForm((prev) => ({ ...prev, secret_access_key: '', session_token: '' }))
      return 'Connected. The S3 and CloudWatch tools now read the live account.'
    })

  return (
    <section>
      <div className="flex items-start gap-3">
        <IntegrationIcon slug="aws" tile />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-900">AWS account</h3>
            {connected ? (
              <span className="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                {aws.live ? 'Live' : 'Connected · using demo data'}
              </span>
            ) : (
              <span className="rounded border border-orange-200 bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-700">
                Demo data
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs leading-relaxed text-gray-500">
            Connect an account and the S3 and CloudWatch tools call it for real,
            read-only. Without one they answer from a simulated account, so the
            tile still works with nothing configured.
          </p>
        </div>
      </div>

      <div className="mt-3 space-y-3">
        {connected && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[11px]">
              <div>
                <dt className="text-gray-400">Account</dt>
                <dd className="font-mono text-gray-900">{aws.account || '—'}</dd>
              </div>
              <div>
                <dt className="text-gray-400">Region</dt>
                <dd className="font-mono text-gray-900">{aws.config?.region || '—'}</dd>
              </div>
              <div className="col-span-2 min-w-0">
                <dt className="text-gray-400">Identity</dt>
                <dd className="truncate font-mono text-gray-900" title={aws.arn}>{aws.arn || '—'}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-gray-400">Access key</dt>
                <dd className="font-mono text-gray-900">{aws.config?.access_key_id || '—'}</dd>
              </div>
            </dl>

            <div className="mt-3 flex items-center justify-between gap-3 border-t border-gray-200 pt-3">
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-gray-700">Use the live account</p>
                {/* Not a display toggle: off makes is_live() false, so the very
                    next tool call answers from the fixture instead of AWS. */}
                <p className="text-[10px] text-gray-400">
                  Off keeps the credentials but returns the tools to demo data.
                </p>
              </div>
              <Switch
                checked={Boolean(aws.enabled)}
                disabled={busy === 'aws'}
                onChange={(next) =>
                  onRun('aws', () => setAwsEnabled(next), () =>
                    next ? 'Now calling the live account.' : 'Back to demo data.'
                  )
                }
                label={aws.enabled ? 'Use demo data' : 'Use the live account'}
              />
            </div>
          </div>
        )}

        {showForm && (
          <div className="space-y-2.5 rounded-lg border border-gray-200 p-3">
            <Field
              label="Access key ID"
              value={form.access_key_id}
              onChange={set('access_key_id')}
              placeholder="AKIA…"
              autoComplete="off"
              spellCheck={false}
            />
            <Field
              label="Secret access key"
              type="password"
              value={form.secret_access_key}
              onChange={set('secret_access_key')}
              placeholder={connected ? 'Leave blank to keep the stored key' : '••••••••'}
              autoComplete="new-password"
              hint="Encrypted at rest in this app's local database — never returned to the browser."
            />
            <Field
              label="Session token (optional)"
              type="password"
              value={form.session_token}
              onChange={set('session_token')}
              placeholder="Only for temporary STS credentials"
              autoComplete="new-password"
            />
            <label className="block">
              <span className="text-[11px] font-medium text-gray-600">Default region</span>
              <input
                list="aws-regions"
                value={form.region}
                onChange={set('region')}
                className="mt-1 w-full rounded-md border border-gray-200 px-2.5 py-1.5 text-xs text-gray-900 focus:border-violet-400 focus:outline-none focus:ring-1 focus:ring-violet-200"
              />
              <datalist id="aws-regions">
                {REGIONS.map((r) => <option key={r} value={r} />)}
              </datalist>
            </label>

            <div className="flex flex-wrap gap-2 pt-0.5">
              <Button
                variant="primary"
                disabled={busy === 'aws' || !form.access_key_id.trim()}
                onClick={handleConnect}
              >
                {busy === 'aws' ? 'Checking…' : connected ? 'Update credentials' : 'Connect account'}
              </Button>
              {connected && (
                <Button onClick={() => setEditing(false)} disabled={busy === 'aws'}>
                  Cancel
                </Button>
              )}
            </div>
            <p className="text-[10px] leading-relaxed text-gray-400">
              Checked with <span className="font-mono">sts:GetCallerIdentity</span> before it
              is stored. Give the key read-only access — every call this app makes is a
              list or get.
            </p>
          </div>
        )}

        {connected && !editing && (
          <div className="flex flex-wrap gap-2">
            <Button disabled={busy === 'aws'} onClick={() =>
              onRun('aws', testAws, (data) => `Still valid — account ${data.account}.`)
            }>
              Test connection
            </Button>
            <Button disabled={busy === 'aws'} onClick={() => setEditing(true)}>
              Update credentials
            </Button>
            <Button variant="danger" disabled={busy === 'aws'} onClick={() =>
              onRun('aws', disconnectAws, () => 'Account disconnected — back to demo data.')
            }>
              Disconnect
            </Button>
          </div>
        )}
      </div>
    </section>
  )
}

/* ── MCP ─────────────────────────────────────────────────── */

function McpServerRow({ server, busy, onRun }) {
  const [open, setOpen] = useState(false)
  const pending = busy === server.id

  return (
    <li className={`rounded-lg border bg-white transition-all ${
      server.connected ? 'border-gray-200' : 'border-dashed border-red-200'
    }`}>
      <div className="flex items-start gap-2.5 p-3">
        <IntegrationIcon slug="mcp" tile />

        <button type="button" onClick={() => setOpen((v) => !v)} className="min-w-0 flex-1 text-left">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-gray-900">{server.label}</span>
            {server.connected ? (
              <span className="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                {server.tool_count} {server.tool_count === 1 ? 'tool' : 'tools'}
              </span>
            ) : (
              <span className="rounded border border-red-200 bg-red-50 px-1.5 py-0.5 text-[10px] font-medium text-red-600">
                Unreachable
              </span>
            )}
            {!server.enabled && (
              <span className="rounded border border-gray-200 bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500">
                Off
              </span>
            )}
          </div>
          <p className="mt-0.5 truncate font-mono text-[11px] text-gray-400" title={server.config?.url}>
            {server.config?.url}
          </p>
        </button>

        <Switch
          checked={Boolean(server.enabled)}
          disabled={pending}
          onChange={(next) =>
            onRun(server.id, () => updateMcpServer(server.id, { enabled: next }), () =>
              next ? `${server.label} is on.` : `${server.label} is off — its tools are no longer offered to the model.`
            )
          }
          label={`${server.enabled ? 'Disable' : 'Enable'} ${server.label}`}
        />
      </div>

      {open && (
        <div className="space-y-2.5 border-t border-gray-200 px-3 py-2.5">
          {!server.connected && server.error && <Note>{server.error}</Note>}

          {server.server_name && (
            <p className="text-[11px] text-gray-500">
              Server: <span className="font-mono text-gray-700">{server.server_name}</span>
              {server.server_version && <span className="text-gray-400"> v{server.server_version}</span>}
              {server.config?.auth_token_set && <span className="text-gray-400"> · authenticated</span>}
            </p>
          )}

          {server.tools?.length > 0 && (
            <div>
              <p className="mb-1.5 text-[11px] font-medium text-gray-500">
                Tools the model sees
              </p>
              <ul className="space-y-1">
                {server.tools.map((tool) => (
                  <li key={tool.name} className="text-[11px]">
                    <span className="font-mono text-gray-900">{tool.name}</span>
                    <span className="text-gray-400"> ← {tool.remote_name}</span>
                    {tool.description && (
                      <p className="mt-0.5 leading-snug text-gray-500 line-clamp-2">{tool.description}</p>
                    )}
                  </li>
                ))}
              </ul>
              <p className="mt-1.5 text-[10px] text-gray-400">
                Switch individual tools off under <strong>View all tools</strong>.
              </p>
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button disabled={pending} onClick={() =>
              onRun(server.id, () => refreshMcpServer(server.id), (data) =>
                data.connected
                  ? `${data.label}: ${data.tool_count} tools.`
                  : `${data.label} is still unreachable.`
              )
            }>
              {pending ? 'Refreshing…' : 'Refresh catalog'}
            </Button>
            <Button variant="danger" disabled={pending} onClick={() =>
              onRun(server.id, () => disconnectMcpServer(server.id), () =>
                `Removed ${server.label} and its tools.`
              )
            }>
              Remove
            </Button>
          </div>
        </div>
      )}
    </li>
  )
}

const EMPTY_MCP = { label: '', url: '', auth_token: '' }

function McpSection({ servers, busy, onRun }) {
  const [form, setForm] = useState(EMPTY_MCP)
  const [adding, setAdding] = useState(false)

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))

  const handleAdd = () =>
    onRun('mcp-new', () => connectMcpServer(form), (data) => {
      setForm(EMPTY_MCP)
      setAdding(false)
      return data.connected
        ? `Connected ${data.label} — ${data.tool_count} tools added to the catalog.`
        : `Saved ${data.label}, but it could not be reached: ${data.error}`
    })

  return (
    <section>
      <div className="flex items-start gap-3">
        <IntegrationIcon slug="mcp" tile />
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-gray-900">MCP servers</h3>
          <p className="mt-0.5 text-xs leading-relaxed text-gray-500">
            Connect a remote MCP server and its tools join this tile&apos;s catalog —
            same switches, same cards in the transcript. Streamable HTTP endpoints
            (<span className="font-mono">https://…/mcp</span>); local stdio servers
            are not reachable from the browser.
          </p>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {servers.length > 0 && (
          <ul className="space-y-2">
            {servers.map((server) => (
              <McpServerRow key={server.id} server={server} busy={busy} onRun={onRun} />
            ))}
          </ul>
        )}

        {adding ? (
          <div className="space-y-2.5 rounded-lg border border-gray-200 p-3">
            <Field
              label="Name"
              value={form.label}
              onChange={set('label')}
              placeholder="e.g. Company Wiki"
              hint="Used as the tool-name prefix, so keep it short."
            />
            <Field
              label="Server URL"
              value={form.url}
              onChange={set('url')}
              placeholder="https://example.com/mcp"
              autoComplete="off"
              spellCheck={false}
            />
            <Field
              label="Auth token (optional)"
              type="password"
              value={form.auth_token}
              onChange={set('auth_token')}
              placeholder="Sent as Authorization: Bearer …"
              autoComplete="new-password"
            />
            <div className="flex flex-wrap gap-2 pt-0.5">
              <Button
                variant="primary"
                disabled={busy === 'mcp-new' || !form.url.trim()}
                onClick={handleAdd}
              >
                {busy === 'mcp-new' ? 'Connecting…' : 'Connect server'}
              </Button>
              <Button disabled={busy === 'mcp-new'} onClick={() => { setAdding(false); setForm(EMPTY_MCP) }}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-gray-300 px-3 py-2.5 text-xs font-medium text-gray-500 transition-colors hover:border-violet-300 hover:bg-violet-50 hover:text-violet-700"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Add an MCP server
          </button>
        )}
      </div>
    </section>
  )
}

/* ── The popup ───────────────────────────────────────────── */

export default function ConnectionsModal({ open, onClose, onChange }) {
  const [aws, setAws] = useState(null)
  const [servers, setServers] = useState([])
  const [busy, setBusy] = useState('')
  const [note, setNote] = useState(null)
  const [loadError, setLoadError] = useState('')

  const load = async () => {
    try {
      const data = await getConnections()
      setAws(data.aws)
      setServers(data.mcp || [])
      setLoadError('')
    } catch (err) {
      setLoadError(errorText(err, 'Could not load connections.'))
    }
  }

  useEffect(() => {
    if (!open) return
    setNote(null)
    load()
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  /**
   * Run one connection action, then re-read the whole snapshot.
   *
   * Reloading rather than patching state locally is deliberate: connecting a
   * server changes what the model can call, and the tool catalog has to be
   * re-fetched anyway — one source of truth beats two that can drift.
   */
  const run = async (key, action, describe) => {
    setBusy(key)
    setNote(null)
    try {
      const data = await action()
      await load()
      onChange?.()
      setNote({ type: 'success', text: describe?.(data) })
    } catch (err) {
      setNote({ type: 'error', text: errorText(err, 'That request failed.') })
    } finally {
      setBusy('')
    }
  }

  const liveCount = (aws?.live ? 1 : 0) + servers.filter((s) => s.enabled && s.connected).length

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Connections</h2>
            <p className="text-xs text-gray-500">
              {liveCount === 0
                ? 'Nothing connected — the tools answer from demo data.'
                : `${liveCount} live ${liveCount === 1 ? 'connection' : 'connections'} feeding the tool catalog.`}
            </p>
          </div>
          <button
            onClick={onClose}
            title="Close"
            className="rounded-md p-2 text-gray-400 transition-all hover:bg-gray-100 hover:text-gray-700"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-4">
          {loadError && <Note>{loadError}</Note>}
          {note?.text && <Note type={note.type}>{note.text}</Note>}

          <AwsSection
            key={aws?.updated_at || 'disconnected'}
            aws={aws}
            busy={busy}
            onRun={run}
          />
          <div className="border-t border-gray-100" />
          <McpSection servers={servers} busy={busy} onRun={run} />
        </div>

        <div className="border-t border-gray-200 px-6 py-3">
          <p className="text-[11px] leading-relaxed text-gray-400">
            Credentials are encrypted at rest in this app&apos;s local database and are
            never sent back to the browser. Anything a connected system returns is
            treated as data for the model to report on, never as instructions.
          </p>
        </div>
      </div>
    </div>
  )
}
