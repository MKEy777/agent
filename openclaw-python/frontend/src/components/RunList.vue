<template>
  <aside class="run-list">
    <div class="panel-head">
      <div>
        <p class="eyebrow">运行</p>
        <h2>实时会话</h2>
      </div>
      <button class="ghost-btn" @click="runtime.loadSnapshot">刷新</button>
    </div>

    <div class="meta-grid">
      <div>
        <span class="meta-label">WebSocket</span>
        <strong :class="['status-text', runtime.wsStatus]">{{ connectionLabel(runtime.wsStatus) }}</strong>
      </div>
      <div>
        <span class="meta-label">通道</span>
        <strong>{{ runtime.channels.length }}</strong>
      </div>
    </div>

    <div class="runs">
      <button
        v-for="run in runtime.runs"
        :key="run.id"
        :class="['run-row', { active: run.id === runtime.activeRunId }]"
        @click="runtime.selectRun(run.id)"
      >
        <span :class="['dot', run.status]"></span>
        <span class="run-main">
          <span class="run-title">{{ run.title || run.sessionKey }}</span>
          <span class="run-sub">{{ run.channel || 'WebChat' }} · {{ run.model || '等待中' }}</span>
        </span>
        <span class="run-time">{{ formatTime(run.updatedAt) }}</span>
      </button>
    </div>

    <div v-if="!runtime.runs.length" class="empty">
      正在等待运行时事件。
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRuntimeStore } from '@/stores/runtime'

const runtime = useRuntimeStore()

function connectionLabel(status: string) {
  const labels: Record<string, string> = {
    connected: '已连接',
    handshake: '握手中',
    disconnected: '未连接',
    error: '异常',
  }
  return labels[status] || status
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour12: false })
}
</script>

<style scoped>
.run-list {
  border-right: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.72);
  min-width: 280px;
  height: 100%;
  max-height: 100%;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  display: flex;
  flex-direction: column;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 20px;
  border-bottom: 1px solid var(--border);
}
.eyebrow {
  font: 600 11px/1 var(--mono);
  color: var(--accent);
  margin-bottom: 6px;
}
h2 {
  font-size: 20px;
  font-weight: 650;
}
.ghost-btn {
  height: 32px;
  padding: 0 12px;
  border: 1px solid var(--border);
  background: #fff;
  color: var(--text);
  font: 600 11px/1 var(--mono);
  cursor: pointer;
}
.ghost-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid var(--border);
}
.meta-grid > div {
  padding: 14px 20px;
}
.meta-grid > div + div {
  border-left: 1px solid var(--border);
}
.meta-label {
  display: block;
  color: var(--muted);
  font: 600 10px/1 var(--mono);
  margin-bottom: 6px;
}
.status-text.connected,
.status-text.handshake {
  color: var(--green);
}
.status-text.error,
.status-text.disconnected {
  color: var(--red);
}
.runs {
  min-height: 0;
  overflow: visible;
  padding: 8px;
}
.run-row {
  width: 100%;
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  color: var(--text);
  cursor: pointer;
}
.run-row:hover,
.run-row.active {
  background: #fff;
  border-color: var(--border);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--muted);
}
.dot.active {
  background: var(--accent);
}
.dot.done {
  background: var(--green);
}
.dot.failed {
  background: var(--red);
}
.run-main {
  min-width: 0;
}
.run-title,
.run-sub {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.run-title {
  font-size: 13px;
  font-weight: 650;
}
.run-sub,
.run-time {
  color: var(--muted);
  font: 500 11px/1.4 var(--mono);
}
.empty {
  padding: 20px;
  color: var(--muted);
  font-size: 13px;
}
</style>
