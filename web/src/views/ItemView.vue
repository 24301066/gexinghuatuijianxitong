<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { useToastStore } from '../stores'
import ProductCard from '../components/ProductCard.vue'

const route = useRoute()
const toast = useToastStore()

const item = ref(null)
const similar = ref([])
const loading = ref(true)
const error = ref('')
const reporting = ref(false)
const viewReported = ref(false)

const VIEW_GUARD_MS = 30_000

function guardKey(itemId) {
  return `gt_view_${itemId}`
}

async function reportView(itemId) {
  const last = Number(sessionStorage.getItem(guardKey(itemId)) || 0)
  if (Date.now() - last < VIEW_GUARD_MS) return
  sessionStorage.setItem(guardKey(itemId), String(Date.now()))
  try {
    await api.postEvent(itemId, 'view')
    viewReported.value = true
  } catch (err) {
    sessionStorage.removeItem(guardKey(itemId))
    toast.push(`浏览行为上报失败：${err.message}`, 'error')
  }
}

async function load(itemId) {
  loading.value = true
  error.value = ''
  similar.value = []
  try {
    item.value = await api.item(itemId)
    const result = await api.similar(itemId, 6)
    similar.value = result.items
    await reportView(itemId)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function report(type) {
  if (!item.value || reporting.value) return
  reporting.value = true
  try {
    await api.postEvent(item.value.item_id, type)
    toast.push(type === 'cart' ? '已加入购物车' : '已记录购买', 'info')
  } catch (err) {
    toast.push(`上报失败：${err.message}，可以再点一次重试`, 'error')
  } finally {
    reporting.value = false
  }
}

onMounted(() => load(route.params.itemId))
watch(() => route.params.itemId, (next) => {
  if (next) load(next)
})
</script>

<template>
  <section class="stack">
    <RouterLink class="muted" to="/">← 返回推荐流</RouterLink>

    <div v-if="loading" class="state">加载中…</div>
    <div v-else-if="error" class="state error">
      <p>{{ error }}</p>
      <button class="primary" type="button" @click="load(route.params.itemId)">重试</button>
    </div>

    <template v-else-if="item">
      <article class="card detail">
        <h1>{{ item.title }}</h1>
        <p class="meta">
          <span class="tag">{{ item.category }}</span>
          <span class="price">¥{{ Number(item.price).toFixed(2) }}</span>
        </p>
        <p v-if="item.tags.length" class="tags">
          <span v-for="tag in item.tags" :key="tag" class="chip">{{ tag }}</span>
        </p>
        <p>{{ item.description }}</p>
        <div class="actions">
          <button class="primary" type="button" :disabled="reporting" @click="report('cart')">
            加入购物车
          </button>
          <button class="secondary" type="button" :disabled="reporting" @click="report('purchase')">
            模拟购买
          </button>
          <span v-if="viewReported" class="muted small">已记录这次浏览</span>
        </div>
      </article>

      <div class="section-head">
        <h2>相似推荐</h2>
        <p class="muted">来自后端 /items/{id}/similar，不是前端静态数据。</p>
      </div>
      <div v-if="similar.length === 0" class="state">这个商品暂时没有相似推荐。</div>
      <div v-else class="grid">
        <ProductCard v-for="row in similar" :key="row.item_id" :item="row" />
      </div>
    </template>
  </section>
</template>
