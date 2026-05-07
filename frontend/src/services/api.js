import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 300000,
})

export const chatApi = {
  createSession() {
    return api.post('/chat/session', {})
  },
  streamChat(sessionId, message) {
    return api.post(
      '/chat/stream',
      { session_id: sessionId, message },
      { responseType: 'text' }
    )
  },
  clearSession(sessionId) {
    return api.post('/chat/clear', null, { params: { session_id: sessionId } })
  },
  getHistory(sessionId) {
    return api.get(`/chat/history/${sessionId}`)
  },
}

export const reportApi = {
  generate(payload) {
    return api.post('/report/generate', payload, { responseType: 'text' })
  },
}

export const generateApi = {
  generate(payload) {
    return api.post('/generate', payload)
  },
}

export const exportApi = {
  downloadWord(content, filename) {
    return api.post('/export/word', { content, filename }, { responseType: 'arraybuffer' })
  },
  downloadPdf(content, filename) {
    return api.post('/export/pdf', { content, filename }, { responseType: 'arraybuffer' })
  },
}

export const kbApi = {
  uploadDocument(formData) {
    return api.post('/kb/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listDocuments() {
    return api.get('/kb/documents')
  },
  deleteDocument(docId) {
    return api.delete(`/kb/documents/${docId}`)
  },
  getStatus() {
    return api.get('/kb/status')
  },
  search(query, top_k = 5) {
    return api.post('/kb/search', { query, top_k })
  },
}

export const healthApi = {
  check() {
    return axios.get('/health')
  },
}

export default api
