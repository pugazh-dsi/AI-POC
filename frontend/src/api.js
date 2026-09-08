import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function queryDocuments(question) {
  const response = await api.post('/query', { question })
  return response.data
}

export async function getDocuments() {
  const response = await api.get('/documents')
  return response.data
}

export async function deleteDocument(filename) {
  const response = await api.delete(`/documents/${encodeURIComponent(filename)}`)
  return response.data
}

// ── Tool calling ──────────────────────────────────────────
export async function getTools() {
  const response = await api.get('/tools')
  return response.data
}

// Switching a tool off removes it from the schemas the model is given, not
// just from the list — the backend refuses to run a disabled tool.
export async function setToolEnabled(name, enabled) {
  const response = await api.patch(`/tools/${encodeURIComponent(name)}`, { enabled })
  return response.data
}

// ── Connections (AWS account + MCP servers) ───────────────
// The systems the Tool Calling tile reaches out to. Credentials go up and
// never come back: every response masks them, so a stored key can be shown as
// present without the browser ever holding it.
export async function getConnections() {
  const response = await api.get('/connections')
  return response.data
}

// Verified with sts:GetCallerIdentity before it is stored — a rejected key
// never becomes the account the tools believe they are connected to. Send a
// blank secret to keep the one already stored.
export async function connectAws(payload) {
  const response = await api.put('/connections/aws', payload)
  return response.data
}

export async function testAws() {
  const response = await api.post('/connections/aws/test')
  return response.data
}

// Off keeps the credentials but returns the S3 / CloudWatch tools to demo data.
export async function setAwsEnabled(enabled) {
  const response = await api.patch('/connections/aws', { enabled })
  return response.data
}

export async function disconnectAws() {
  const response = await api.delete('/connections/aws')
  return response.data
}

// Adding a server pulls its tool catalog into the same registry the model is
// given, so its tools appear in the tools popup with the usual switches.
export async function connectMcpServer(payload) {
  const response = await api.post('/connections/mcp', payload)
  return response.data
}

export async function updateMcpServer(id, payload) {
  const response = await api.patch(`/connections/mcp/${encodeURIComponent(id)}`, payload)
  return response.data
}

export async function refreshMcpServer(id) {
  const response = await api.post(`/connections/mcp/${encodeURIComponent(id)}/refresh`)
  return response.data
}

export async function disconnectMcpServer(id) {
  const response = await api.delete(`/connections/mcp/${encodeURIComponent(id)}`)
  return response.data
}

// ── Guardrails ────────────────────────────────────────────
// The rule pack the deterministic engine enforces — the same YAML the backend
// evaluates, so the "Active Compliance Guardrails" panel can never drift from
// what is actually running.
export async function getGuardrailRules() {
  const response = await api.get('/guardrails/rules')
  return response.data
}

export async function getGuardrailSample() {
  const response = await api.get('/guardrails/sample')
  return response.data
}

// Send nothing to validate the reference extraction, `filename` to extract an
// uploaded document with the LLM first, or `extracted` to score a payload you
// already have. The verdict is computed in Python either way.
export async function validateRequisition(payload = {}) {
  const response = await api.post('/guardrails/validate', payload)
  return response.data
}

// ── Chat history ──────────────────────────────────────────
// Conversations are stored per tile ('rag', 'tools', ...) so each sidebar
// lists only its own chats.
export async function getChats(mode) {
  const response = await api.get('/chats', { params: mode ? { mode } : {} })
  return response.data
}

export async function createChat(mode, title) {
  const response = await api.post('/chats', { mode, title })
  return response.data
}

export async function getChat(id) {
  const response = await api.get(`/chats/${id}`)
  return response.data
}

export async function renameChat(id, title) {
  const response = await api.patch(`/chats/${id}`, { title })
  return response.data
}

export async function deleteChat(id) {
  const response = await api.delete(`/chats/${id}`)
  return response.data
}

// ── AI provider settings ──────────────────────────────────
export async function getProviders() {
  const response = await api.get('/providers')
  return response.data
}

export async function saveProvider(id, payload) {
  const response = await api.put(`/providers/${id}`, payload)
  return response.data
}

export async function activateProvider(id) {
  const response = await api.post(`/providers/${id}/activate`)
  return response.data
}

export async function testProvider(id) {
  const response = await api.post(`/providers/${id}/test`)
  return response.data
}

export async function deleteProvider(id) {
  const response = await api.delete(`/providers/${id}`)
  return response.data
}
