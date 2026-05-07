import { ref } from 'vue'
import { kbApi } from '@/services/api'

export function useKnowledgeBase() {
  const documents = ref([])
  const isLoading = ref(false)
  const isUploading = ref(false)
  const isDeleting = ref(false)
  const error = ref(null)
  const uploadProgress = ref('')
  const kbStatus = ref({ doc_count: 0, chunk_count: 0 })

  async function loadDocuments() {
    isLoading.value = true
    error.value = null
    try {
      const res = await kbApi.listDocuments()
      documents.value = res.data.documents || []
      await loadStatus()
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
    } finally {
      isLoading.value = false
    }
  }

  async function loadStatus() {
    try {
      const res = await kbApi.getStatus()
      kbStatus.value = res.data
    } catch (_) {}
  }

  async function uploadDocument(file) {
    if (!file) return
    isUploading.value = true
    error.value = null
    uploadProgress.value = `正在上传: ${file.name}...`
    try {
      const formData = new FormData()
      formData.append('file', file)
      await kbApi.uploadDocument(formData)
      uploadProgress.value = '上传成功，正在解析...'
      await loadDocuments()
      uploadProgress.value = ''
      return true
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      uploadProgress.value = ''
      return false
    } finally {
      isUploading.value = false
    }
  }

  async function deleteDocument(docId) {
    isDeleting.value = true
    error.value = null
    try {
      await kbApi.deleteDocument(docId)
      await loadDocuments()
      return true
    } catch (e) {
      error.value = e.response?.data?.detail || e.message
      return false
    } finally {
      isDeleting.value = false
    }
  }

  function formatDate(isoString) {
    if (!isoString) return ''
    const d = new Date(isoString)
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  function getFileIcon(fileType) {
    const icons = {
      txt: 'txt',
      docx: 'docx',
      doc: 'docx',
      pdf: 'pdf',
    }
    return icons[fileType] || fileType
  }

  return {
    documents,
    isLoading,
    isUploading,
    isDeleting,
    error,
    uploadProgress,
    kbStatus,
    loadDocuments,
    uploadDocument,
    deleteDocument,
    formatDate,
    getFileIcon,
  }
}
