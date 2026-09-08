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
