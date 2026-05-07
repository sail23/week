<template>
  <div class="chat-message" :class="`role-${message.role}`">
    <div class="message-avatar">
      <span v-if="message.role === 'user'">👤</span>
      <span v-else>🤖</span>
    </div>
    <div class="message-content">
      <div class="message-text" v-if="message.role === 'user'">
        {{ message.content }}
      </div>

      <!-- Assistant message -->
      <template v-else>
        <div class="message-text markdown-body" v-html="renderedContent"></div>

        <!-- Streaming indicator -->
        <div v-if="message.streaming && !message.content" class="typing-indicator">
          <span></span><span></span><span></span>
        </div>

        <!-- Stage indicator for report generation -->
        <div v-if="message.streaming && message.stage" class="stage-indicator">
          <div class="stage-steps">
            <div class="stage-step" :class="{ done: stageStep >= 1, active: stageStep === 1 }">
              <div class="step-dot"></div>
              <span>提炼工作内容</span>
            </div>
            <div class="step-line"></div>
            <div class="stage-step" :class="{ done: stageStep >= 2, active: stageStep === 2 }">
              <div class="step-dot"></div>
              <span>生成结构化报告</span>
            </div>
          </div>
        </div>

        <!-- Export buttons for report messages -->
        <div v-if="isReportMessage && !message.streaming" class="export-actions">
          <button class="export-btn export-word" @click="handleExportWord" :disabled="exporting === 'word'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <span>{{ exporting === 'word' ? '导出中...' : '导出 Word' }}</span>
          </button>
          <button class="export-btn export-pdf" @click="handleExportPdf" :disabled="exporting === 'pdf'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <span>{{ exporting === 'pdf' ? '导出中...' : '导出 PDF' }}</span>
          </button>
        </div>

        <!-- Knowledge base reference -->
        <div v-if="message.kbContext && message.kbContext.length > 0" class="kb-reference">
          <button class="kb-toggle" @click="kbExpanded = !kbExpanded">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              class="chevron"
              :class="{ expanded: kbExpanded }"
            >
              <polyline points="9 18 15 12 9 6"/>
            </svg>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
            </svg>
            <span>参考知识库（{{ message.kbContext.length }} 条）</span>
          </button>
          <div class="kb-chunks" v-show="kbExpanded">
            <div
              class="kb-chunk"
              v-for="(chunk, idx) in message.kbContext"
              :key="idx"
            >
              <div class="chunk-header">
                <span class="chunk-source">来源 #{{ idx + 1 }}</span>
                <span class="chunk-score">相关度 {{ chunk.percent }}%</span>
              </div>
              <p class="chunk-content">{{ chunk.content }}</p>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { marked } from 'marked'
import { exportApi } from '@/services/api'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
})

const exporting = ref(null)
const kbExpanded = ref(false)

const isReportMessage = computed(() => {
  return !!props.message.reportType
})

const renderedContent = computed(() => {
  const raw = props.message.content || ''
  if (!raw) return ''
  return marked.parse(raw)
})

const stageStep = computed(() => {
  if (!props.message.stage) return 0
  const stage = props.message.stage.stage
  if (stage === 'extracting') return 1
  if (stage === 'generating') return 2
  return 0
})

function getFilename(prefix) {
  const meta = props.message.reportMeta || {}
  const dateRange = meta.date_range || ''
  const type = meta.type || '报告'
  const safeDate = dateRange.replace(/[^\w\u4e00-\u9fff-]/g, '_')
  return `${type}_${safeDate || prefix}`
}

async function handleExportWord() {
  if (!props.message.content || exporting.value) return
  exporting.value = 'word'
  try {
    const filename = getFilename('周报')
    const res = await exportApi.downloadWord(
      props.message.content,
      filename
    )
    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    downloadBlob(blob, `${filename}.docx`)
  } catch (e) {
    alert('导出失败: ' + e.message)
  } finally {
    exporting.value = null
  }
}

async function handleExportPdf() {
  if (!props.message.content || exporting.value) return
  exporting.value = 'pdf'
  try {
    const filename = getFilename('周报')
    const res = await exportApi.downloadPdf(
      props.message.content,
      filename
    )
    const blob = new Blob([res.data], { type: 'application/pdf' })
    downloadBlob(blob, `${filename}.pdf`)
  } catch (e) {
    alert('导出失败: ' + e.message)
  } finally {
    exporting.value = null
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 12px;
  padding: 12px 0;
}

.role-user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.role-user .message-avatar {
  background: #e3f2fd;
}

.role-assistant .message-avatar {
  background: #f3e5f5;
}

.message-content {
  max-width: 75%;
  min-width: 60px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.role-user .message-content {
  text-align: right;
  align-items: flex-end;
}

.message-text {
  display: block;
  padding: 10px 16px;
  border-radius: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.role-user .message-text {
  background: #3b82f6;
  color: white;
  border-bottom-right-radius: 4px;
}

.role-assistant .message-text {
  background: #f8f9fa;
  color: #1f2937;
  border-bottom-left-radius: 4px;
  padding: 14px 18px;
}

.role-assistant .message-text .markdown-body {
  margin: 0;
}

/* Stage indicator */
.stage-indicator {
  padding: 8px 0;
}

.stage-steps {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stage-step {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #9ca3af;
  transition: color 0.3s;
}

.stage-step.done {
  color: #16a34a;
}

.stage-step.active {
  color: #3b82f6;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.stage-step.done .step-dot {
  background: #16a34a;
}

.stage-step.active .step-dot {
  background: #3b82f6;
  animation: pulse-dot 1s infinite;
}

.step-line {
  width: 20px;
  height: 1px;
  background: #e5e7eb;
  flex-shrink: 0;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Streaming typing indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
  align-items: center;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
  animation: typing-bounce 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }
.typing-indicator span:nth-child(3) { animation-delay: 0; }

@keyframes typing-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* Export actions */
.export-actions {
  display: flex;
  gap: 8px;
  padding-top: 4px;
}

.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 6px;
  background: white;
  color: #374151;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.export-btn:hover:not(:disabled) {
  border-color: #3b82f6;
  color: #3b82f6;
  background: #eff6ff;
}

.export-pdf:hover:not(:disabled) {
  border-color: #f59e0b;
  color: #b45309;
  background: #fffbeb;
}

.export-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Knowledge base reference */
.kb-reference {
  margin-top: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: #f9fafb;
}

.kb-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: #4b5563;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  font-family: inherit;
  text-align: left;
}

.kb-toggle:hover {
  background: #f3f4f6;
}

.kb-toggle .chevron {
  transition: transform 0.2s;
  flex-shrink: 0;
}

.kb-toggle .chevron.expanded {
  transform: rotate(90deg);
}

.kb-chunks {
  padding: 0 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kb-chunk {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px 12px;
}

.chunk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.chunk-source {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
}

.chunk-score {
  font-size: 11px;
  color: #9ca3af;
}

.chunk-content {
  margin: 0;
  font-size: 12px;
  color: #374151;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Markdown styles */
.markdown-body :deep(h1) {
  font-size: 1.3em;
  font-weight: 700;
  margin: 0.5em 0;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #e5e7eb;
}

.markdown-body :deep(h2) {
  font-size: 1.15em;
  font-weight: 600;
  margin: 0.5em 0;
}

.markdown-body :deep(h3) {
  font-size: 1em;
  font-weight: 600;
  margin: 0.4em 0;
}

.markdown-body :deep(p) {
  margin: 0.4em 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.5em;
}

.markdown-body :deep(li) {
  margin: 0.2em 0;
}

.markdown-body :deep(code) {
  background: #f1f5f9;
  padding: 0.1em 0.4em;
  border-radius: 4px;
  font-family: 'Fira Code', monospace;
  font-size: 0.9em;
}

.markdown-body :deep(pre) {
  background: #f1f5f9;
  padding: 0.8em;
  border-radius: 8px;
  overflow-x: auto;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid #d1d5db;
  margin: 0.4em 0;
  padding-left: 1em;
  color: #6b7280;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5em 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 6px 12px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f9fafb;
  font-weight: 600;
}
</style>
