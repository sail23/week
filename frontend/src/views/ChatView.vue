<template>
  <div class="chat-view">
    <div class="messages-container" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
        <p class="empty-title">你好，有什么可以帮你的？</p>
        <p class="empty-hint">可以询问公司制度、生成工作报告，或进行日常对话</p>
      </div>

      <ChatMessage
        v-for="(msg, idx) in messages"
        :key="idx"
        :message="msg"
      />
    </div>

    <div class="chat-footer">
      <ChatInput
        :is-generating="isGenerating"
        :kb-mode="kbMode"
        @send="handleSend"
        @toggle-kb="$emit('toggleKb')"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import ChatMessage from '@/components/ChatMessage.vue'
import ChatInput from '@/components/ChatInput.vue'

const props = defineProps({
  kbMode: { type: Boolean, required: true },
  isGenerating: { type: Boolean, required: true },
  messages: { type: Array, required: true },
  sendMessage: { type: Function, required: true },
})

defineEmits(['toggleKb'])

const messagesContainer = ref(null)

watch(() => props.messages, () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}, { deep: true })

async function handleSend(text) {
  await props.sendMessage(text)
}
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f9fafb;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 20px;
  text-align: center;
}

.empty-icon {
  color: #d1d5db;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.empty-hint {
  font-size: 13px;
  color: #9ca3af;
  margin: 0;
}

.chat-footer {
  flex-shrink: 0;
  padding: 16px 24px;
  background: white;
  border-top: 1px solid #e5e7eb;
}
</style>
