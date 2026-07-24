<template>
  <section class="messages-panel">
    <div class="tabs">
      <button :class="{ active: tab === 'current' }" @click="tab = 'current'">当前上下文</button>
      <button :class="{ active: tab === 'initial' }" @click="tab = 'initial'">初始消息</button>
    </div>

    <div class="message-list">
      <article v-for="(message, index) in messages" :key="index" class="message-row">
        <div class="message-meta">
          <span>{{ message.role }}</span>
          <span v-if="message.name">{{ message.name }}</span>
        </div>
        <pre>{{ formatMessage(message) }}</pre>
      </article>
    </div>

    <div v-if="!messages.length" class="empty">暂无消息上下文。</div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'
import type { RuntimeMessage } from '@/api/types'

const runtime = useRuntimeStore()
const tab = ref<'current' | 'initial'>('current')

const messages = computed(() => {
  const run = runtime.activeRun
  if (!run) return []
  return tab.value === 'initial' ? run.initialMessages : runtime.activeMessages
})

function formatMessage(message: RuntimeMessage) {
  if (message.tool_call) return JSON.stringify(message.tool_call, null, 2)
  if (typeof message.content === 'string') return message.content
  return JSON.stringify(message, null, 2)
}
</script>

<style scoped>
.messages-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--border);
}
.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid var(--border);
}
.tabs button {
  height: 38px;
  border: 0;
  border-right: 1px solid var(--border);
  background: #f9fafb;
  color: var(--muted);
  font: 700 10px/1 var(--mono);
  cursor: pointer;
}
.tabs button:last-child {
  border-right: 0;
}
.tabs button.active {
  background: #fff;
  color: var(--accent);
}
.message-list {
  padding: 12px;
}
.message-row {
  border: 1px solid var(--border);
  background: #fff;
  margin-bottom: 10px;
}
.message-meta {
  display: flex;
  justify-content: space-between;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font: 700 10px/1 var(--mono);
  text-transform: uppercase;
}
pre {
  padding: 10px;
  margin: 0;
  color: #111827;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 500 11px/1.55 var(--mono);
}
.empty {
  padding: 16px;
  color: var(--muted);
  font-size: 13px;
}
</style>
