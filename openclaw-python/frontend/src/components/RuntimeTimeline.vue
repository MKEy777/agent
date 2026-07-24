<template>
  <section class="timeline">
    <div class="section-head">
      <div>
        <p class="eyebrow">追踪</p>
        <h3>{{ runtime.activeRun?.title || '暂无运行' }}</h3>
      </div>
      <span class="session-key">{{ runtime.activeRun?.sessionKey || '-' }}</span>
    </div>

    <div v-if="runtime.activeRun" class="conversation">
      <article class="bubble user">
        <div class="bubble-label">用户消息</div>
        <p>{{ runtime.activeRun.input || '等待消息进入。' }}</p>
      </article>

      <div v-if="runtime.activeRun.tools.length" class="tool-strip">
        <article v-for="tool in runtime.activeRun.tools" :key="tool.id" class="tool-card">
          <div class="tool-top">
            <span :class="['tool-dot', tool.status]"></span>
            <strong>{{ tool.name }}</strong>
            <em>{{ toolStatus(tool.status) }}</em>
          </div>
          <p>{{ toolBrief(tool.result, tool.params) }}</p>
          <a v-if="toolUrl(tool.result)" :href="toolUrl(tool.result)" target="_blank" rel="noreferrer">
            打开文档链接
          </a>
        </article>
      </div>

      <article class="bubble assistant">
        <div class="bubble-label">最终回复（流式）</div>
        <p>{{ runtime.activeRun.output || '等待模型输出。' }}</p>
      </article>
      <article v-if="runtime.activeRun.replyText" class="bubble reply">
        <div class="bubble-label">通道回写</div>
        <p>{{ runtime.activeRun.replyText }}</p>
      </article>
    </div>

    <div class="event-list">
      <article
        v-for="(event, index) in runtime.activeEvents"
        :key="eventKey(event, index)"
        :class="['event-row', event.status]"
      >
        <div class="event-marker">
          <span>{{ event.layer }}</span>
        </div>
        <div class="event-body">
          <div class="event-top">
            <strong>{{ eventTitle(event) }}</strong>
            <time>{{ formatTime(event.ts) }}</time>
          </div>
          <p v-if="eventDetail(event)">{{ eventDetail(event) }}</p>
        </div>
      </article>
    </div>

    <div v-if="!runtime.activeEvents.length" class="empty">暂无事件。</div>
  </section>
</template>

<script setup lang="ts">
import { useRuntimeStore } from '@/stores/runtime'
import type { RuntimeEventPayload, RuntimeStatus } from '@/api/types'

const runtime = useRuntimeStore()

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour12: false })
}

function eventTitle(event: RuntimeEventPayload) {
  const labels: Record<string, string> = {
    'runtime.channel.inbound': '收到消息',
    'runtime.session.loaded': '读取会话',
    'runtime.run.started': '开始运行',
    'runtime.messages.initial': '组装初始上下文',
    'runtime.model.streaming': '模型流式输出',
    'runtime.usage': 'Token 用量',
    'runtime.tool.started': '开始调用工具',
    'runtime.tool.finished': '工具返回结果',
    'runtime.run.completed': '运行完成',
    'runtime.run.failed': '运行失败',
    'runtime.channel.reply_sent': '回复已发送',
    'runtime.channel.reply_failed': '回复发送失败',
  }
  return labels[event.type] || event.title
}

function eventDetail(event: RuntimeEventPayload) {
  if (event.type === 'runtime.model.streaming') {
    const chars = String(event.detail || '').length
    return chars ? `已输出 ${chars} 个字符，可见回复在上方持续更新。` : ''
  }
  if (event.type === 'runtime.tool.started') {
    const params = asRecord(event.data?.params)
    const title = typeof params?.title === 'string' ? `，标题《${params.title}》` : ''
    return `${event.detail || event.data?.tool || '工具'} 已开始${title}。`
  }
  if (event.type === 'runtime.tool.finished') {
    return toolBrief(event.data?.result, event.data?.params)
  }
  return event.detail || ''
}

function eventKey(event: RuntimeEventPayload, index: number) {
  if (event.type === 'runtime.model.streaming') {
    return `${event.runId || event.sessionKey}:model-stream`
  }
  return `${event.ts}-${event.type}-${event.layer}-${index}`
}

function toolStatus(status: RuntimeStatus) {
  const labels: Record<RuntimeStatus, string> = {
    idle: '等待',
    active: '调用中',
    done: '已完成',
    failed: '失败',
  }
  return labels[status]
}

function parseJsonish(value: unknown): unknown {
  if (typeof value !== 'string') return value
  const trimmed = value.trim()
  if (!trimmed) return ''
  try {
    return JSON.parse(trimmed)
  } catch {
    return value
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function toolBrief(result: unknown, params: unknown) {
  const parsed = asRecord(parseJsonish(result))
  if (parsed) {
    const title = typeof parsed.title === 'string' ? `《${parsed.title}》` : ''
    const blocks = typeof parsed.blocks_created === 'number' ? `，写入 ${parsed.blocks_created} 个块` : ''
    const reply = typeof parsed.reply_text === 'string' ? parsed.reply_text.split('\n')[0] : ''
    return reply || `工具已返回${title}${blocks}。`
  }
  const parsedParams = asRecord(params)
  if (parsedParams && typeof parsedParams.title === 'string') {
    return `准备处理《${parsedParams.title}》。`
  }
  return result ? '工具已返回结果。' : '等待工具结果。'
}

function toolUrl(result: unknown) {
  const parsed = asRecord(parseJsonish(result))
  if (parsed && typeof parsed.url === 'string') return parsed.url
  if (typeof result !== 'string') return ''
  return result.match(/https?:\/\/\S+/)?.[0] || ''
}
</script>

<style scoped>
.timeline {
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 18px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(249, 250, 251, 0.9);
}
.eyebrow {
  font: 700 10px/1 var(--mono);
  color: var(--accent);
  margin-bottom: 6px;
}
h3 {
  font-size: 20px;
  line-height: 1.2;
}
.session-key {
  color: var(--muted);
  font: 600 11px/1.4 var(--mono);
  max-width: 42%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-list {
  padding: 16px 20px 22px;
}
.conversation {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.74);
}
.bubble {
  border: 1px solid var(--border);
  background: #fff;
  padding: 11px 12px;
}
.bubble.user {
  border-left: 3px solid var(--text);
}
.bubble.assistant {
  border-left: 3px solid var(--accent);
}
.bubble.reply {
  border-left: 3px solid var(--green);
}
.tool-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.tool-card {
  border: 1px solid var(--border);
  background: #fbfdff;
  padding: 10px 12px;
}
.tool-top {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
}
.tool-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--muted);
}
.tool-dot.active {
  background: var(--accent);
}
.tool-dot.done {
  background: var(--green);
}
.tool-dot.failed {
  background: var(--red);
}
.tool-top strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}
.tool-top em {
  color: var(--muted);
  font: normal 700 10px/1 var(--mono);
}
.tool-card p {
  margin: 8px 0 0;
  color: #374151;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.tool-card a {
  display: inline-block;
  margin-top: 8px;
  color: var(--accent);
  font-size: 12px;
  text-decoration: none;
  border-bottom: 1px solid currentColor;
}
.bubble-label {
  color: var(--muted);
  font: 700 10px/1 var(--mono);
  margin-bottom: 7px;
}
.bubble p {
  margin: 0;
  color: #111827;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.event-row {
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(209, 213, 219, 0.7);
}
.event-marker span {
  display: inline-block;
  width: 76px;
  padding: 5px 7px;
  border: 1px solid var(--border);
  background: #fff;
  font: 700 10px/1 var(--mono);
  text-align: center;
  color: var(--muted);
}
.event-row.active .event-marker span {
  border-color: var(--accent);
  color: var(--accent);
}
.event-row.done .event-marker span {
  border-color: var(--green);
  color: var(--green);
}
.event-row.failed .event-marker span {
  border-color: var(--red);
  color: var(--red);
}
.event-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.event-top strong {
  font-size: 13px;
}
.event-top time {
  color: var(--muted);
  font: 600 10px/1 var(--mono);
}
p {
  margin-top: 6px;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.empty {
  padding: 20px;
  color: var(--muted);
}
</style>
