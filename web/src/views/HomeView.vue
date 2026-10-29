<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { useToastStore } from '../stores'
import ProductCard from '../components/ProductCard.vue'

const PAGE_SIZE = 6

const items = ref([])
const page = ref(1)
const loading = ref(false)
const more = ref(true)
const partial = ref(false)
const degraded = ref(false)
const error = ref('')
const loaded = ref(false)

const toast = useToastStore()

async function load(reset = false) {
  if (loading.value) return
  loading.value = true
  error.value = ''
  const targetPage = reset ? 1 : page.value
  try {
    const data = await api.recommendations(PAGE_SIZE, targetPage)
    const known = new Set(items.value.map((item) => item.item_id))
    const incoming = data.items.filter((item) => !known.has(item.item_id))
    items.value = reset ? data.items : items.value.concat(incoming)
    page.value = targetPage + 1
    partial.value = data.partial
    degraded.value = data.degraded
    more.value = !data.partial && incoming.length > 0
    if (data.cold_start) {
      toast.push('还没有你的行为记录，先按热门推荐；浏览几个商品后推荐会更准', 'info')
    }
    if (data.degraded) {
      toast.push('推荐服务降级为热门兜底', 'warn')
    }
  } catch (err) {
    error.value = err.message
    if (err.status === 401) {
      error.value = '登录状态已失效，请重新登录'
    }
  } finally {
    loading.value = false
    loaded.value = true
  }
}

function retry() {
  load(items.value.length === 0)
}

onMounted(() => load(true))
</script>

<template>
  <section class="stack">
    <div class="section-head">
      <h1>猜你喜欢</h1>
      <p class="muted">基于你的浏览/加购/购买行为，融合协同过滤、内容相似与近期热度。</p>
    </div>

    <p v-if="degraded" class="banner warn">当前为热门兜底结果（推荐服务降级）</p>

    <div v-if="loading && items.length === 0" class="state">加载中…</div>

    <div v-else-if="error" class="state error">
      <p>{{ error }}</p>
      <button class="primary" type="button" @click="retry">重试</button>
    </div>

    <div v-else-if="loaded && items.length === 0" class="state">
      <p>暂时没有可推荐的商品。</p>
      <p class="muted">商品目录可能为空，先运行 <code>python tools/seed_demo.py</code> 生成演示数据。</p>
      <button class="primary" type="button" @click="retry">重试</button>
    </div>

    <div v-else class="grid">
      <ProductCard v-for="item in items" :key="item.item_id" :item="item" />
    </div>

    <div v-if="items.length > 0" class="actions">
      <button v-if="more" class="primary" type="button" :disabled="loading" @click="load(false)">
        {{ loading ? '加载中…' : '加载更多' }}
      </button>
      <span v-else-if="partial" class="muted">已到最后一页（候选商品用完了）</span>
      <span v-else class="muted">没有更多了</span>
    </div>
  </section>
</template>
