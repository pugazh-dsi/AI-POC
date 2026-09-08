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
