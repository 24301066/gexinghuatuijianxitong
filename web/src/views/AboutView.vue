<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const health = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    health.value = await api.health()
  } catch (err) {
    error.value = err.message
  }
})
</script>

<template>
  <section>
    <div class="page-head"><h1>关于版本</h1><p>版本信息与运行环境。</p></div>

    <div class="section-card">
      <div class="menu-list">
        <div class="menu-row" style="cursor: default">
          <span>应用版本</span><span class="arrow">0.1.0</span>
        </div>
        <div class="menu-row" style="cursor: default">
          <span>后端版本</span><span class="arrow">{{ health?.version || '—' }}</span>
        </div>
        <div class="menu-row" style="cursor: default">
          <span>模型版本</span><span class="arrow">{{ health?.model_version || '—' }}</span>
        </div>
        <div class="menu-row" style="cursor: default">
          <span>数据规模</span>
          <span class="arrow">
            商品 {{ health?.items ?? '—' }} · 安利 {{ health?.posts ?? '—' }}
          </span>
        </div>
        <div class="menu-row" style="cursor: default">
          <span>运行模式</span><span class="arrow">离线桌面应用（本机）</span>
        </div>
      </div>
      <p v-if="error" class="error" style="margin-top: 10px">{{ error }}</p>
      <p class="meta" style="margin-top: 12px">
        当前数据为演示数据，封面为程序生成的示意插画，仅用于功能演示。
      </p>
    </div>
  </section>
</template>
