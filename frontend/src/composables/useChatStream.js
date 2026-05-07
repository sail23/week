import { ref } from 'vue'
import { chatApi } from '@/services/api'

export function useChatStream() {
  const messages = ref([])
  const isGenerating = ref(false)
  const error = ref(null)
  const sessionId = ref(null)
  const stage = ref('')

  async function createSession() {
    if (sessionId.value) return sessionId.value
    messages.value = []
    error.value = null
    try {
      const res = await chatApi.createSession()
      sessionId.value = res.data.session_id
      return sessionId.value
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  const kbMode = ref(false)

  async function sendMessage(userMessage) {
    if (isGenerating.value) return

    await createSession()

    messages.value.push({ role: 'user', content: userMessage })
    messages.value.push({ role: 'assistant', content: '', streaming: true, kbContext: [] })
    isGenerating.value = true
    error.value = null

    const assistantIdx = messages.value.length - 1
    let firstTokenReceived = false
    let pendingKbContext = null

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId.value,
          message: userMessage,
          kb_mode: kbMode.value,
        }),
      })

      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`)
      }

      await _readSSEResponse(response, (event, data) => {
        if (event === 'error') {
          error.value = data
          messages.value[assistantIdx].content = `\n[错误] ${data}`
          return
        }
        if (event === 'kb_context') {
          try {
            const parsed = JSON.parse(data)
            if (firstTokenReceived) {
              messages.value[assistantIdx].kbContext = parsed.chunks || []
            } else {
              pendingKbContext = parsed.chunks || []
            }
          } catch (_) {}
        } else if (event === 'stage') {
          try {
            const parsed = JSON.parse(data)
            stage.value = parsed.stage || ''
            messages.value[assistantIdx].stage = parsed
          } catch (_) {}
        } else if (event === 'token' || (!event && data)) {
          if (!firstTokenReceived) {
            firstTokenReceived = true
            if (pendingKbContext !== null) {
              messages.value[assistantIdx].kbContext = pendingKbContext
              pendingKbContext = null
            }
          }
          messages.value[assistantIdx].content += data
        }
      })
    } catch (e) {
      error.value = e.message
      messages.value[assistantIdx].content = `\n[错误] ${e.message}`
    } finally {
      if (!firstTokenReceived && pendingKbContext !== null) {
        messages.value[assistantIdx].kbContext = pendingKbContext
      }
      messages.value[assistantIdx].streaming = false
      isGenerating.value = false
    }
  }

  async function clearChat() {
    if (sessionId.value) {
      try {
        await chatApi.clearSession(sessionId.value)
      } catch (_) {}
    }
    messages.value = []
    sessionId.value = null
  }

  async function loadHistory() {
    if (!sessionId.value) return
    try {
      const res = await chatApi.getHistory(sessionId.value)
      messages.value = res.data.history || []
    } catch (_) {}
  }

  function _dispatchEvent(onEvent, eventType, data) {
    if (!data && eventType !== 'error') return

    if (data.startsWith('{')) {
      try {
        const parsed = JSON.parse(data)
        if (parsed.content) {
          onEvent(eventType, parsed.content)
        } else {
          onEvent(eventType, data)
        }
      } catch (_) {
        onEvent(eventType, data)
      }
    } else {
      onEvent(eventType, data)
    }
  }

  async function _readSSEResponse(response, onEvent) {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = null
    let dataLines = []

    function flushEvent() {
      if (dataLines.length > 0) {
        const data = dataLines.join('\n')
        dataLines = []
        if (data !== '[DONE]') {
          _dispatchEvent(onEvent, currentEvent, data)
        }
      }
      currentEvent = null
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split(/\r?\n/)
      buffer = lines.pop() || ''

      for (const line of lines) {
        // Strip trailing \r (Windows line ending artifact)
        const clean = line.endsWith('\r') ? line.slice(0, -1) : line
        if (!clean) {
          flushEvent()
          continue
        }

        if (clean.startsWith('event:')) {
          currentEvent = clean.slice(6).trimStart() || null
          continue
        }
        if (clean.startsWith('data:')) {
          // Remove exactly one leading space (SSE "field: value" format)
          dataLines.push(clean.slice(5).replace(/^ /, ''))
          continue
        }
        // Other SSE fields (id, retry) — ignored
      }
    }

    flushEvent()
  }

  return {
    messages,
    isGenerating,
    kbMode,
    sendMessage,
    clearChat,
  }
}
