<template>
  <aside class="inspector">
    <div class="summary">
      <p class="eyebrow">检查器</p>
      <h2>{{ statusLabel(runtime.activeRun?.status || 'idle') }}</h2>
      <div class="facts">
        <span>{{ runtime.activeRun?.provider || '-' }}</span>
        <span>{{ runtime.activeRun?.model || '-' }}</span>
      </div>
    </div>

    <div class="output">
      <div class="output-head">
        <span>最终回复 / 可见输出</span>
        <strong>{{ runtime.activeRun?.output.length || 0 }}</strong>
      </div>
      <pre>{{ runtime.activeRun?.output || '暂无模型输出。' }}</pre>
    </div>

    <ToolCallPanel />
    <MessageContextPanel />
  </aside>
</template>

<script setup lang="ts">
import MessageContextPanel from '@/components/MessageContextPanel.vue'
import ToolCallPanel from '@/components/ToolCallPanel.vue'
import { useRuntimeStore } from '@/stores/runtime'

const runtime = useRuntimeStore()

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    idle: '空闲',
    active: '运行中',
    done: '已完成',
    failed: '失败',
  }
  return labels[status] || status
}
</script>

<style scoped>
.inspector {
  border-left: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.78);
  min-width: 390px;
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}
.summary {
  padding: 20px;
  border-bottom: 1px solid var(--border);
  background: #fff;
}
.eyebrow {
  font: 700 10px/1 var(--mono);
  color: var(--accent);
  margin-bottom: 6px;
}
h2 {
  font-size: 28px;
  text-transform: uppercase;
}
.facts {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.facts span {
  border: 1px solid var(--border);
  padding: 5px 8px;
  color: var(--muted);
  font: 700 10px/1 var(--mono);
}
.output {
  border-bottom: 1px solid var(--border);
}
.output-head {
  display: flex;
  justify-content: space-between;
  padding: 11px 14px;
  color: var(--muted);
  font: 700 10px/1 var(--mono);
  border-bottom: 1px solid var(--border);
}
pre {
  margin: 0;
  padding: 14px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 500 12px/1.6 var(--mono);
  color: #111827;
  background: #f9fafb;
}
@media (max-width: 960px) {
  .inspector {
    min-width: 0;
    border-left: 0;
    border-top: 1px solid var(--border);
  }
}
</style>
