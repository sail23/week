<template>
  <div class="kb-panel">
    <div class="panel-header">
      <h3 class="panel-title">知识库管理</h3>
      <span class="stat-badge" v-if="kbStatus.doc_count > 0">
        {{ kbStatus.doc_count }} 文档 · {{ kbStatus.chunk_count }} 块
      </span>
    </div>

    <!-- 上传区域 -->
    <div
      class="upload-zone"
      :class="{ dragging: isDragging, uploading: isUploading }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInputRef"
        type="file"
        accept=".txt,.docx,.doc,.pdf"
        multiple
        style="display: none"
        @change="handleFileChange"
      />
      <div class="upload-icon">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
      </div>
      <p class="upload-text">{{ isUploading ? uploadProgress || '处理中...' : '点击或拖拽上传文件' }}</p>
      <p class="upload-hint">支持 .txt .docx .pdf</p>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-msg">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
      </svg>
      {{ error }}
    </div>

    <!-- 文档列表 -->
    <div class="doc-list" v-if="!isLoading && documents.length > 0">
      <div class="doc-item" v-for="doc in documents" :key="doc.id">
        <div class="doc-icon" :class="`ft-${getFileIcon(doc.file_type)}`">
          {{ getFileIcon(doc.file_type).toUpperCase() }}
        </div>
        <div class="doc-info">
          <span class="doc-name" :title="doc.name">{{ doc.name }}</span>
          <span class="doc-meta">{{ formatDate(doc.created_at) }} · {{ doc.chunk_count }} 块</span>
        </div>
        <button
          class="delete-btn"
          @click="handleDelete(doc.id)"
          :disabled="isDeleting"
          title="删除"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>
            <path d="M9 6V4h6v2"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!isLoading && documents.length === 0" class="empty-docs">
      <p>暂无文档，上传制度文件开始构建知识库</p>
    </div>

    <!-- 加载中 -->
    <div v-if="isLoading" class="loading-state">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useKnowledgeBase } from '@/composables/useKnowledgeBase'

const {
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
} = useKnowledgeBase()

const isDragging = ref(false)
const fileInputRef = ref(null)

onMounted(() => {
  loadDocuments()
})

function triggerFileInput() {
  if (!isUploading.value) {
    fileInputRef.value?.click()
  }
}

async function handleFileChange(e) {
  const files = Array.from(e.target.files || [])
  for (const file of files) {
    await uploadDocument(file)
  }
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

async function handleDrop(e) {
  isDragging.value = false
  if (isUploading.value) return
  const files = Array.from(e.dataTransfer?.files || [])
  for (const file of files) {
    await uploadDocument(file)
  }
}

async function handleDelete(docId) {
  if (!confirm('确定要删除这个文档吗？')) return
  await deleteDocument(docId)
}
</script>

<style scoped>
.kb-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.stat-badge {
  font-size: 11px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 10px;
}

.upload-zone {
  margin: 12px 16px;
  padding: 20px 16px;
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.upload-zone:hover,
.upload-zone.dragging {
  border-color: #3b82f6;
  background: #eff6ff;
}

.upload-zone.uploading {
  cursor: wait;
  opacity: 0.7;
}

.upload-icon {
  color: #9ca3af;
  margin-bottom: 8px;
  display: flex;
  justify-content: center;
}

.upload-zone:hover .upload-icon,
.upload-zone.dragging .upload-icon {
  color: #3b82f6;
}

.upload-text {
  font-size: 13px;
  color: #374151;
  margin: 0 0 4px;
  font-weight: 500;
}

.upload-hint {
  font-size: 11px;
  color: #9ca3af;
  margin: 0;
}

.error-msg {
  margin: 0 16px 8px;
  padding: 8px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.doc-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 16px 16px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-radius: 8px;
  transition: background 0.15s;
}

.doc-item:hover {
  background: #f9fafb;
}

.doc-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.ft-txt {
  background: #dbeafe;
  color: #1d4ed8;
}

.ft-docx {
  background: #dcfce7;
  color: #15803d;
}

.ft-pdf {
  background: #fee2e2;
  color: #dc2626;
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-name {
  display: block;
  font-size: 13px;
  color: #1f2937;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta {
  display: block;
  font-size: 11px;
  color: #9ca3af;
  margin-top: 1px;
}

.delete-btn {
  flex-shrink: 0;
  padding: 6px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.delete-btn:hover:not(:disabled) {
  background: #fef2f2;
  color: #ef4444;
}

.delete-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.empty-docs {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.empty-docs p {
  font-size: 13px;
  color: #9ca3af;
  text-align: center;
  margin: 0;
  line-height: 1.6;
}

.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #9ca3af;
  font-size: 13px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
