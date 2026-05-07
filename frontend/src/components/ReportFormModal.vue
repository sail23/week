<template>
  <Teleport to="body">
    <div class="modal-overlay" v-if="visible" @click.self="handleClose">
      <div class="modal-card">
        <div class="modal-header">
          <div class="modal-title-row">
            <span class="modal-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
            </span>
            <h3 class="modal-title">{{ modalTitle }}</h3>
          </div>
          <button class="close-btn" @click="handleClose">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <div class="modal-body">
          <div class="form-hint">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            请填写以下信息，我将为你生成 {{ typeLabel }} 内容
          </div>

          <!-- 时间范围 -->
          <div class="form-group">
            <label class="form-label">时间范围 <span class="required">*</span></label>
            <div class="time-inputs">
              <input
                v-if="reportType === 'daily'"
                type="date"
                class="form-input"
                v-model="form.date_range"
              />
              <input
                v-else-if="reportType === 'weekly'"
                type="week"
                class="form-input"
                v-model="form.date_range"
              />
              <input
                v-else-if="reportType === 'monthly'"
                type="month"
                class="form-input"
                v-model="form.date_range"
              />
              <input
                v-else
                type="text"
                class="form-input"
                placeholder="例如：2024年第15周 或 2024年4月1日-4月7日"
                v-model="form.date_range"
              />
            </div>
          </div>

          <!-- 主要工作 -->
          <div class="form-group">
            <label class="form-label">主要工作内容 <span class="required">*</span></label>
            <textarea
              class="form-textarea"
              placeholder="请描述你本周/日/月的主要工作内容..."
              v-model="form.main_work"
              rows="3"
            ></textarea>
          </div>

          <!-- 工作成果 -->
          <div class="form-group">
            <label class="form-label">工作成果或完成情况</label>
            <textarea
              class="form-textarea"
              placeholder="本月完成的主要成果或关键里程碑..."
              v-model="form.achievements"
              rows="3"
            ></textarea>
          </div>

          <!-- 遇到的问题 -->
          <div class="form-group">
            <label class="form-label">遇到的问题</label>
            <textarea
              class="form-textarea"
              placeholder="工作过程中遇到的问题或挑战（可选）..."
              v-model="form.problems"
              rows="2"
            ></textarea>
          </div>

          <!-- 下一步计划 -->
          <div class="form-group">
            <label class="form-label">下一步计划</label>
            <textarea
              class="form-textarea"
              placeholder="下周/日/月的计划（可选）..."
              v-model="form.next_plan"
              rows="2"
            ></textarea>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-cancel" @click="handleClose">取消</button>
          <button
            class="btn-generate"
            @click="handleSubmit"
            :disabled="!canGenerate"
          >
            开始生成
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  reportType: {
    type: String,
    default: 'weekly',
  },
  extractedParams: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['close', 'submit'])

const form = ref({
  date_range: '',
  main_work: '',
  achievements: '',
  problems: '',
  next_plan: '',
})

const typeLabels = { daily: '日报', weekly: '周报', monthly: '月报', custom: '报告' }
const typeLabel = computed(() => typeLabels[props.reportType] || '报告')
const modalTitle = computed(() => `生成 ${typeLabel.value}`)

const canGenerate = computed(() => {
  return form.value.date_range && form.value.main_work.trim()
})

watch(() => props.visible, (val) => {
  if (val) {
    resetForm()
    if (props.extractedParams) {
      if (props.extractedParams.date_range) form.value.date_range = props.extractedParams.date_range
      if (props.extractedParams.main_work) form.value.main_work = props.extractedParams.main_work
      if (props.extractedParams.achievements) form.value.achievements = props.extractedParams.achievements
      if (props.extractedParams.problems) form.value.problems = props.extractedParams.problems
      if (props.extractedParams.next_plan) form.value.next_plan = props.extractedParams.next_plan
    }
  }
})

function resetForm() {
  form.value = { date_range: '', main_work: '', achievements: '', problems: '', next_plan: '' }
}

function handleClose() {
  emit('close')
}

function handleSubmit() {
  if (!canGenerate.value) return
  emit('submit', { ...form.value })
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.modal-card {
  background: white;
  border-radius: 16px;
  width: 580px;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.modal-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-icon {
  width: 36px;
  height: 36px;
  background: #eff6ff;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
}

.modal-title {
  font-size: 17px;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.close-btn {
  padding: 6px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #9ca3af;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.15s;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.form-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #eff6ff;
  border-radius: 8px;
  color: #3b82f6;
  font-size: 13px;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
}

.required {
  color: #ef4444;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  color: #1f2937;
  transition: border-color 0.2s;
  outline: none;
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 70px;
  line-height: 1.6;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.btn-cancel {
  padding: 9px 20px;
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  background: white;
  color: #6b7280;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-cancel:hover {
  background: #f9fafb;
  color: #374151;
}

.btn-generate {
  padding: 9px 24px;
  border: none;
  border-radius: 8px;
  background: #3b82f6;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-generate:hover:not(:disabled) {
  background: #2563eb;
}

.btn-generate:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}
</style>
