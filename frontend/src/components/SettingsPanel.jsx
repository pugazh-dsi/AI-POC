import { useEffect, useState } from 'react'
import {
  getProviders,
  saveProvider,
  activateProvider,
  testProvider,
  deleteProvider,
} from '../api'

const FIELD_LABELS = {
  api_key: 'API key',
  model: 'Model',
  base_url: 'Endpoint',
  api_version: 'API version',
}

const PLACEHOLDERS = {
  base_url: 'https://<resource>.openai.azure.com',
  api_version: '2024-10-21',
}

export default function SettingsPanel({ open, onClose, onActiveChange }) {
  const [providers, setProviders] = useState([])
  const [drafts, setDrafts] = useState({})
  const [busy, setBusy] = useState('')
  const [status, setStatus] = useState({})

  const load = async () => {
    try {
      const data = await getProviders()
      setProviders(data.providers)
      onActiveChange?.(data.providers.find((p) => p.is_active))
    } catch {
      setStatus({ _global: { type: 'error', text: 'Could not load provider settings.' } })
    }
  }

  useEffect(() => {
    if (open) load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  if (!open) return null

  const draftFor = (p) => drafts[p.id] || {}
  const setDraft = (id, key, value) =>
    setDrafts((prev) => ({ ...prev, [id]: { ...prev[id], [key]: value } }))

  const say = (id, type, text) => setStatus((prev) => ({ ...prev, [id]: { type, text } }))

  const run = async (id, action, done) => {
    setBusy(id)
    setStatus((prev) => ({ ...prev, [id]: null }))
    try {
      await action()
      await load()
      done?.()
    } catch (err) {
      say(id, 'error', err.response?.data?.detail || 'Request failed.')
    } finally {
      setBusy('')
    }
  }

  const handleSave = (p) => {
    const draft = draftFor(p)
    const payload = {}
    for (const field of p.fields) {
      const value = draft[field]
      // Blank API key means "leave the stored key alone"
      if (value !== undefined && !(field === 'api_key' && value === '')) {
        payload[field] = value
      }
    }
    if (Object.keys(payload).length === 0) {
      say(p.id, 'error', 'Nothing to save.')
      return
    }
    run(p.id, () => saveProvider(p.id, payload), () => {
      setDrafts((prev) => ({ ...prev, [p.id]: {} }))
      say(p.id, 'success', 'Saved.')
    })
  }

  const handleTest = (p) =>
    run(p.id, async () => {
      const result = await testProvider(p.id)
      say(p.id, 'success', `Connected to ${result.model}.`)
    })

  const handleActivate = (p) =>
    run(p.id, () => activateProvider(p.id), () => say(p.id, 'success', `${p.label} is now active.`))

  const handleRemove = (p) =>
    run(p.id, () => deleteProvider(p.id), () => say(p.id, 'success', 'Removed.'))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">AI Providers</h2>
            <p className="text-xs text-gray-500">
              Keys are stored encrypted in this app&apos;s local database.
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

        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          <div className="rounded-lg bg-blue-50 border border-blue-200 p-3">
            <p className="text-xs text-blue-800">
              Document search always uses OpenAI embeddings, so an OpenAI key is required
              even when chat runs on another provider.
            </p>
          </div>

          {providers.map((p) => {
            const draft = draftFor(p)
            const note = status[p.id]

            return (
              <div
                key={p.id}
                className={`rounded-lg border p-4 ${
                  p.is_active ? 'border-blue-400 bg-blue-50/40' : 'border-gray-200 bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-gray-900">{p.label}</h3>
                      {p.is_active && (
                        <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
                          Active
                        </span>
                      )}
                      {p.configured && (
                        <span className="text-xs text-gray-500">{p.masked_key}</span>
                      )}
                      {p.key_from_env && (
                        <span className="text-xs text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                          from .env
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{p.notes}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  {p.fields.map((field) => (
                    <label key={field} className="block">
                      <span className="text-xs font-medium text-gray-600">
                        {FIELD_LABELS[field]}
                      </span>
                      <input
                        type={field === 'api_key' ? 'password' : 'text'}
                        list={field === 'model' && p.models.length ? `${p.id}-models` : undefined}
                        value={draft[field] ?? (field === 'api_key' ? '' : p[field] || '')}
                        onChange={(e) => setDraft(p.id, field, e.target.value)}
                        placeholder={
                          field === 'api_key'
                            ? p.configured
                              ? 'Leave blank to keep current key'
                              : 'Paste API key'
                            : PLACEHOLDERS[field] || ''
                        }
                        className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      {field === 'model' && p.models.length > 0 && (
                        <datalist id={`${p.id}-models`}>
                          {p.models.map((m) => (
                            <option key={m} value={m} />
                          ))}
                        </datalist>
                      )}
                    </label>
                  ))}
                </div>

                <div className="flex items-center gap-2 mt-3">
                  <button
                    onClick={() => handleSave(p)}
                    disabled={busy === p.id}
                    className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-all"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => handleTest(p)}
                    disabled={busy === p.id || !p.configured}
                    className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-all"
                  >
                    Test
                  </button>
                  {!p.is_active && (
                    <button
                      onClick={() => handleActivate(p)}
                      disabled={busy === p.id || !p.configured}
                      className="rounded-md border border-blue-300 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-50 transition-all"
                    >
                      Use for chat
                    </button>
                  )}
                  <button
                    onClick={() => handleRemove(p)}
                    disabled={busy === p.id}
                    className="ml-auto rounded-md px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-red-600 hover:bg-red-50 disabled:opacity-50 transition-all"
                  >
                    Remove
                  </button>
                </div>

                {note && (
                  <p
                    className={`mt-2 text-xs ${
                      note.type === 'error' ? 'text-red-600' : 'text-green-700'
                    }`}
                  >
                    {note.text}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
