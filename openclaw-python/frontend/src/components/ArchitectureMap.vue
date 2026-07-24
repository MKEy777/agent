<template>
  <section class="architecture">
    <div class="section-head">
      <div>
        <p class="eyebrow">架构</p>
        <h3>执行链路</h3>
      </div>
      <div class="current-layer">
        <span>当前位置</span>
        <strong>{{ currentLayerLabel }}</strong>
      </div>
    </div>
    <div class="layers">
      <article
        v-for="layer in layerRows"
        :key="layer.id"
        :class="['layer', statusOf(layer.id)]"
      >
        <div class="layer-top">
          <span class="step-index">{{ layer.index }}</span>
          <span class="step-status">{{ statusLabel(layer.status) }}</span>
        </div>
        <strong class="layer-id">{{ layer.label }}</strong>
        <span class="layer-detail">{{ layer.detail }}</span>
        <div class="layer-event">
          <span>最新事件</span>
          <strong>{{ eventTitle(layer.latest) }}</strong>
          <time v-if="layer.latest">{{ formatTime(layer.latest.ts) }}</time>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ARCHITECTURE_LAYERS, useRuntimeStore } from '@/stores/runtime'
import type { LayerId, RuntimeEventPayload, RuntimeStatus } from '@/api/types'

const runtime = useRuntimeStore()

function statusOf(layer: LayerId) {
  return runtime.activeRun?.layerStatus[layer] || 'idle'
}

const layerRows = computed(() =>
  ARCHITECTURE_LAYERS.map((layer, index) => {
    const events = runtime.activeEvents.filter((event) => event.layer === layer.id)
    return {
      ...layer,
      index: index + 1,
      status: statusOf(layer.id),
      latest: events.at(-1),
    }
  }),
)

const currentLayerLabel = computed(() => {
  const rows = layerRows.value
  const current =
    rows.find((row) => row.status === 'failed') ||
    [...rows].reverse().find((row) => row.status === 'active') ||
    [...rows].reverse().find((row) => row.status === 'done')
  return current ? `${current.index}. ${current.label}` : '等待消息'
})

function statusLabel(status: RuntimeStatus) {
  const labels: Record<RuntimeStatus, string> = {
    idle: '等待',
    active: '进行中',
    done: '完成',
    failed: '失败',
  }
  return labels[status]
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour12: false })
}

function eventTitle(event?: RuntimeEventPayload) {
  if (!event) return '尚未进入'
  const labels: Record<string, string> = {
    'runtime.channel.inbound': '收到消息',
    'runtime.session.loaded': '读取会话',
    'runtime.run.started': 'Gateway 启动运行',
    'runtime.messages.initial': '组装上下文',
    'runtime.model.streaming': '模型流式输出',
    'runtime.usage': '统计 Token',
    'runtime.tool.started': '开始调用工具',
    'runtime.tool.finished': '工具返回',
    'runtime.run.completed': '运行完成',
    'runtime.run.failed': '运行失败',
    'runtime.channel.reply_sent': '回复已发出',
    'runtime.channel.reply_failed': '回复发送失败',
  }
  return labels[event.type] || event.title || event.type
}
</script>

<style scoped>
.architecture {
  border-bottom: 1px solid var(--border);
  background: #fff;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 18px;
  padding: 16px 18px 12px;
}
.eyebrow {
  font: 700 10px/1 var(--mono);
  color: var(--accent);
  margin-bottom: 6px;
}
h3 {
  font-size: 14px;
  font-weight: 650;
}
.current-layer {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.current-layer span {
  color: var(--muted);
  font-size: 11px;
}
.current-layer strong {
  font-size: 12px;
  color: #111827;
  white-space: nowrap;
}
.layers {
  display: grid;
  grid-template-columns: repeat(7, minmax(95px, 1fr));
  gap: 1px;
  background: var(--border);
  border-top: 1px solid var(--border);
}
.layer {
  min-height: 132px;
  background: #f9fafb;
  padding: 12px;
  border-top: 3px solid transparent;
  position: relative;
}
.layer:not(:last-child)::after {
  content: "";
  position: absolute;
  right: -1px;
  top: 50%;
  width: 12px;
  height: 12px;
  border-top: 1px solid var(--border);
  border-right: 1px solid var(--border);
  background: inherit;
  transform: translate(50%, -50%) rotate(45deg);
  z-index: 1;
}
.layer.active {
  background: #eef4ff;
  border-top-color: var(--accent);
}
.layer.done {
  border-top-color: var(--green);
}
.layer.failed {
  border-top-color: var(--red);
  background: #fff5f5;
}
.layer-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: 1px solid var(--border);
  background: #fff;
  color: #111827;
  font: 700 11px/1 var(--mono);
}
.step-status {
  color: var(--muted);
  font: 700 10px/1 var(--mono);
}
.layer.active .step-status {
  color: var(--accent);
}
.layer.done .step-status {
  color: var(--green);
}
.layer.failed .step-status {
  color: var(--red);
}
.layer-id,
.layer-detail {
  display: block;
}
.layer-id {
  font-size: 13px;
  line-height: 1.2;
}
.layer-detail {
  margin-top: 7px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.3;
}
.layer-event {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(209, 213, 219, 0.8);
}
.layer-event span,
.layer-event time {
  display: block;
  color: var(--muted);
  font: 700 10px/1.2 var(--mono);
}
.layer-event strong {
  display: block;
  margin: 5px 0;
  color: #111827;
  font-size: 12px;
  line-height: 1.35;
}
@media (max-width: 1100px) {
  .layers {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .layer:not(:last-child)::after {
    display: none;
  }
}
@media (max-width: 720px) {
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .layers {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
