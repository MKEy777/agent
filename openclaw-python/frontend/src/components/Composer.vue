<template>
  <form class="composer" @submit.prevent="runtime.sendLocalMessage">
    <textarea
      v-model="runtime.draft"
      rows="3"
      placeholder="通过本地 WebChat 发送一条消息，走 sessions.send"
    ></textarea>
    <div class="composer-actions">
      <span>{{ runtime.sendStatus || 'web:local' }}</span>
      <button :disabled="!runtime.draft.trim()">发送</button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { useRuntimeStore } from '@/stores/runtime'

const runtime = useRuntimeStore()
</script>

<style scoped>
.composer {
  border-top: 1px solid var(--border);
  background: #fff;
  padding: 14px 16px;
}
textarea {
  width: 100%;
  resize: vertical;
  border: 1px solid var(--border);
  background: #f9fafb;
  color: var(--text);
  padding: 10px 12px;
  outline: none;
  font: 500 13px/1.5 var(--sans);
}
textarea:focus {
  border-color: var(--accent);
  background: #fff;
}
.composer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  color: var(--muted);
  font: 700 10px/1 var(--mono);
}
button {
  border: 0;
  background: var(--text);
  color: #fff;
  height: 34px;
  padding: 0 18px;
  font: 700 11px/1 var(--mono);
  cursor: pointer;
}
button:hover {
  background: var(--accent);
}
button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
