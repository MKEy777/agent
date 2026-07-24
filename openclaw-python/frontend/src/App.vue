<template>
  <div class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">OPENCLAW</p>
        <h1>运行时控制台</h1>
      </div>
      <div class="top-metrics">
        <span>Gateway: 18789</span>
        <span>前端: 3001</span>
        <span>WebSocket: {{ connectionLabel(runtime.wsStatus) }}</span>
      </div>
    </header>

    <main class="workspace">
      <RunList />
      <section class="main-stage">
        <div class="center-scroll">
          <ArchitectureMap />
          <RuntimeTimeline />
        </div>
        <Composer />
      </section>
      <InspectorPanel />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import ArchitectureMap from '@/components/ArchitectureMap.vue'
import Composer from '@/components/Composer.vue'
import InspectorPanel from '@/components/InspectorPanel.vue'
import RunList from '@/components/RunList.vue'
import RuntimeTimeline from '@/components/RuntimeTimeline.vue'
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

onMounted(async () => {
  await Promise.allSettled([runtime.connect(), runtime.loadSnapshot()])
})
</script>

<style>
:root {
  --bg: #f4f5f7;
  --text: #1a1d21;
  --muted: #6b7280;
  --border: #d1d5db;
  --accent: #0055ff;
  --green: #16a34a;
  --red: #dc2626;
  --amber: #d97706;
  --sans: 'Inter Tight', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --mono: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
}
* {
  box-sizing: border-box;
}
html,
body,
#app {
  height: 100%;
  overflow: hidden;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
}
button,
textarea {
  font-family: inherit;
}
::selection {
  background: var(--accent);
  color: #fff;
}
.app-shell {
  height: 100dvh;
  max-height: 100dvh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.topbar {
  flex: 0 0 72px;
  height: 72px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.82);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}
.eyebrow {
  margin: 0 0 5px;
  color: var(--accent);
  font: 800 10px/1 var(--mono);
  letter-spacing: 0.04em;
}
h1 {
  margin: 0;
  font-size: 24px;
  line-height: 1.1;
}
.top-metrics {
  display: flex;
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
}
.top-metrics span {
  background: #fff;
  padding: 9px 11px;
  font: 700 10px/1 var(--mono);
  color: var(--muted);
}
.workspace {
  flex: 0 0 calc(100dvh - 72px);
  height: calc(100dvh - 72px);
  min-height: 0;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr) 410px;
  overflow: hidden;
}
.workspace > * {
  height: 100%;
  max-height: 100%;
  min-height: 0;
}
.main-stage {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  overflow: hidden;
  background:
    linear-gradient(to right, rgba(209, 213, 219, 0.32) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(209, 213, 219, 0.32) 1px, transparent 1px);
  background-size: 36px 36px;
}
.center-scroll {
  height: 100%;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}
@media (max-width: 960px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 820px) {
  .topbar {
    flex-basis: 128px;
    height: 128px;
    align-items: flex-start;
    gap: 14px;
    padding: 16px;
    flex-direction: column;
  }
  .top-metrics {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr;
  }
  .workspace {
    grid-template-columns: 1fr;
    flex-basis: calc(100dvh - 128px);
    height: calc(100dvh - 128px);
  }
}
</style>
