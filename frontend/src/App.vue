<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-brand">
        <span class="brand-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="10" rx="2"/>
            <circle cx="12" cy="5" r="2"/>
            <path d="M12 7v4"/>
            <line x1="8" y1="16" x2="8" y2="16"/>
            <line x1="16" y1="16" x2="16" y2="16"/>
            <path d="M9 18l3 3 3-3"/>
          </svg>
        </span>
        <h1 class="brand-name">智能助手</h1>
      </div>
      <div class="header-right">
        <button
          class="clear-btn"
          @click="clearChat()"
          :disabled="isGenerating"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
            <path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
          </svg>
          清空对话
        </button>
        <button
          class="kb-toggle-btn"
          :class="{ active: showKbPanel }"
          @click="toggleKbPanel"
          :disabled="isGenerating"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          </svg>
          知识库
        </button>
        <div class="health-indicator" :class="healthStatus">
          <span class="status-dot"></span>
          <span class="status-text">{{ healthText }}</span>
        </div>
      </div>
    </header>

    <main class="app-main">
      <div class="chat-area" :class="{ 'with-panel': showKbPanel }">
        <ChatView
          :kb-mode="kbMode"
          :is-generating="isGenerating"
          :messages="messages"
          :send-message="sendMessage"
          @toggle-kb="toggleKb"
        />
      </div>

      <div class="kb-sidebar" v-if="showKbPanel">
        <KnowledgeBasePanel />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { healthApi } from '@/services/api'
import { useChatStream } from '@/composables/useChatStream'
import ChatView from '@/views/ChatView.vue'
import KnowledgeBasePanel from '@/components/KnowledgeBasePanel.vue'

const {
  messages,
  isGenerating,
  kbMode,
  sendMessage,
  clearChat,
} = useChatStream()

const showKbPanel = ref(false)
const healthStatus = ref('checking')
const healthText = ref('连接中...')

function toggleKb() {
  kbMode.value = !kbMode.value
}

function toggleKbPanel() {
  showKbPanel.value = !showKbPanel.value
  if (!showKbPanel.value) {
    kbMode.value = false
  }
}

async function checkHealth() {
  try {
    await healthApi.check()
    healthStatus.value = 'ok'
    healthText.value = '服务正常'
  } catch {
    healthStatus.value = 'error'
    healthText.value = '服务异常'
  }
}

onMounted(() => {
  checkHealth()
})
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f9fafb;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-icon {
  color: #3b82f6;
  display: flex;
  align-items: center;
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
  line-height: 1;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.clear-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.clear-btn:hover:not(:disabled) {
  border-color: #ef4444;
  color: #ef4444;
}

.clear-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.kb-toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  color: #6b7280;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.kb-toggle-btn:hover:not(:disabled) {
  border-color: #3b82f6;
  color: #3b82f6;
}

.kb-toggle-btn.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #3b82f6;
}

.kb-toggle-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.health-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.health-indicator.checking {
  background: #fef3c7;
  color: #b45309;
}

.health-indicator.ok {
  background: #d1fae5;
  color: #065f46;
}

.health-indicator.error {
  background: #fee2e2;
  color: #991b1b;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.app-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.chat-area {
  flex: 1;
  overflow: hidden;
  transition: flex 0.3s;
}

.chat-area > * {
  height: 100%;
}

.kb-sidebar {
  width: 320px;
  flex-shrink: 0;
  background: white;
  border-left: 1px solid #e5e7eb;
  overflow-y: auto;
}
</style>
