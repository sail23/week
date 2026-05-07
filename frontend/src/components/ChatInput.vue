<template>
  <div class="chat-input">
    <div class="template-buttons">
      <button
        v-for="tpl in templates"
        :key="tpl.type"
        class="tpl-btn"
        :class="tpl.type"
        @click="fillTemplate(tpl.type)"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="12" y1="18" x2="12" y2="12"/>
          <line x1="9" y1="15" x2="15" y2="15"/>
        </svg>
        {{ tpl.label }}
      </button>
    </div>

    <div class="input-row">
      <button
        class="kb-toggle"
        :class="{ active: kbMode }"
        @click="$emit('toggleKb')"
        :title="kbMode ? '知识库模式已开启，点击关闭' : '知识库模式已关闭，点击开启'"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
        </svg>
        <span class="toggle-track">
          <span class="toggle-thumb"></span>
        </span>
        <span class="toggle-label">{{ kbMode ? '开' : '关' }}</span>
      </button>
      <textarea
        ref="inputRef"
        v-model="inputText"
        class="input-area"
        :placeholder="placeholder"
        :disabled="disabled"
        @keydown.enter.exact.prevent="handleSend"
        @keydown.shift.enter="newline"
        @input="autoResize"
        rows="1"
      ></textarea>
      <button
        class="send-btn"
        :disabled="disabled || !inputText.trim()"
        @click="handleSend"
      >
        <svg v-if="!isGenerating" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
        <span v-else class="generating-dot">···</span>
      </button>
    </div>
    <div class="input-hint">Enter 发送，Shift+Enter 换行</div>
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'

const props = defineProps({
  disabled: Boolean,
  isGenerating: Boolean,
  kbMode: Boolean,
  placeholder: {
    type: String,
    default: '输入消息，AI 自动识别你的需求...',
  },
})

const emit = defineEmits(['send', 'toggleKb'])

const inputText = ref('')
const inputRef = ref(null)

const templates = [
  {
    type: 'daily',
    label: '日报',
    text: '【日报】\n日期：\n\n一、今日工作完成情况\n\n二、存在的问题\n\n三、明日工作计划',
  },
  {
    type: 'weekly',
    label: '周报',
    text: '【周报】\n时间范围（第__周 / __月__日 - __月__日）：\n\n一、本周工作完成情况\n\n二、存在的问题\n\n三、下周工作计划',
  },
  {
    type: 'monthly',
    label: '月报',
    text: '【月报】\n时间范围（__年__月）：\n\n一、本月工作完成情况\n\n二、存在的问题\n\n三、下月工作计划',
  },
  {
    type: 'quarterly',
    label: '季度报告',
    text: '【季度报告】\n时间范围（__年第__季度）：\n\n一、本季度工作完成情况\n\n二、存在的问题\n\n三、下季度工作计划',
  },
]

function fillTemplate(type) {
  const tpl = templates.find(t => t.type === type)
  if (!tpl) return
  inputText.value = tpl.text
  nextTick(() => {
    autoResize()
    inputRef.value?.focus()
    inputRef.value?.setSelectionRange(0, 0)
  })
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.isGenerating) return
  emit('send', text)
  inputText.value = ''
  nextTick(() => autoResize())
}

function newline() {}

function autoResize() {
  const el = inputRef.value
  if (el) {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }
}
</script>

<style scoped>
.chat-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tpl-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s;
  font-family: inherit;
  border: 1.5px solid;
}

.tpl-btn.daily {
  background: #fefce8;
  border-color: #fde047;
  color: #a16207;
}

.tpl-btn.daily:hover {
  background: #fef9c3;
  border-color: #eab308;
}

.tpl-btn.weekly {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}

.tpl-btn.weekly:hover {
  background: #dbeafe;
  border-color: #3b82f6;
}

.tpl-btn.monthly {
  background: #f0fdf4;
  border-color: #86efac;
  color: #15803d;
}

.tpl-btn.monthly:hover {
  background: #dcfce7;
  border-color: #22c55e;
}

.tpl-btn.quarterly {
  background: #fdf4ff;
  border-color: #e879f9;
  color: #7e22ce;
}

.tpl-btn.quarterly:hover {
  background: #fae8ff;
  border-color: #d946ef;
}

.input-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.kb-toggle {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  height: 44px;
  border-radius: 22px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
  border: 1.5px solid #d1d5db;
  background: #f9fafb;
  color: #6b7280;
}

.kb-toggle:hover {
  border-color: #9ca3af;
  background: #f3f4f6;
}

.kb-toggle.active {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #3b82f6;
}

.toggle-track {
  position: relative;
  width: 34px;
  height: 18px;
  border-radius: 9px;
  background: #d1d5db;
  transition: background 0.2s;
}

.kb-toggle.active .toggle-track {
  background: #3b82f6;
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform 0.2s;
}

.kb-toggle.active .toggle-thumb {
  transform: translateX(16px);
}

.toggle-label {
  min-width: 12px;
  text-align: center;
  font-weight: 600;
}

.input-area {
  flex: 1;
  padding: 12px 16px;
  border: 1.5px solid #e5e7eb;
  border-radius: 12px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  line-height: 1.5;
  min-height: 44px;
  max-height: 200px;
  transition: border-color 0.2s;
  outline: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  color: #1f2937;
}

.input-area:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.input-area:disabled {
  background: #f9fafb;
  cursor: not-allowed;
}

.input-area::placeholder {
  color: #9ca3af;
}

.send-btn {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn:hover:not(:disabled) {
  background: #2563eb;
}

.send-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.generating-dot {
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.input-hint {
  font-size: 12px;
  color: #9ca3af;
  text-align: right;
}
</style>
