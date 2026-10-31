<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, mediaUrl } from '../api'
import { useSessionStore, useToastStore } from '../stores'
import ProductCard from '../components/ProductCard.vue'

const router = useRouter()
const session = useSessionStore()
const toast = useToastStore()

const loading = ref(true)
const error = ref('')
const data = ref(null)

const categories = computed(() => {
  const entries = Object.entries(data.value?.categories || {})
  const max = Math.max(1, ...entries.map(([, value]) => Number(value) || 0))
  return entries
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name, value]) => ({ name, value, percent: Math.round((value / max) * 100) }))
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.insights()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function goSearch(word) {
  router.push({ name: 'search', query: { q: word } })
}

onMounted(load)
</script>

<template>
  <section>
    <div class="page-head">
      <h1>我的</h1>
      <p>看看你的口味、最近搜过什么、在哪些安利上停留最久。</p>
    </div>

    <div v-if="error" class="notice">{{ error }}</div>
    <div v-if="loading" class="empty">加载中…</div>

    <template v-else-if="data">
      <div class="card" style="padding: 22px; display: flex; gap: 16px; align-items: center">
        <span class="avatar" style="width: 54px; height: 54px; font-size: 20px">
          {{ (session.user?.username || 'U').slice(0, 1).toUpperCase() }}
        </span>
        <div>
          <div style="font-weight: 800; font-size: 18px">{{ session.user?.username }}</div>
          <div class="meta">
            <span>活跃度 {{ Number(data.activity_level || 0).toFixed(2) }}</span>
            <span class="dot" />
            <span>客单价偏好 ¥{{ Number(data.avg_price || 0).toFixed(0) }}</span>
          </div>
        </div>
        <button class="btn ghost small" type="button" style="margin-left: auto" @click="load">刷新</button>
      </div>

      <section class="section">
        <div class="section-head"><h2>口味偏好</h2><span>按类目权重</span></div>
        <div v-if="categories.length" class="bars">
          <div v-for="row in categories" :key="row.name" class="bar-row">
            <span>{{ row.name }}</span>
            <span class="bar"><i :style="{ width: `${row.percent}%` }" /></span>
            <span>{{ row.percent }}%</span>
          </div>
        </div>
        <div v-else class="empty">还没有足够的行为数据</div>
      </section>

      <section class="section">
        <div class="section-head"><h2>最近搜索</h2><span>用于关键词推荐</span></div>
        <div v-if="data.recent_searches.length" class="chip-row">
          <button v-for="row in data.recent_searches" :key="row.keyword + row.created_at"
                  class="chip" type="button" @click="goSearch(row.keyword)">
            🔍 {{ row.keyword }}
          </button>
        </div>
        <div v-else class="empty">还没有搜索记录，去搜点什么吧</div>
      </section>

      <section class="section">
        <div class="section-head"><h2>停留过的安利</h2><span>停留越久，越影响推荐</span></div>
        <div v-if="data.recent_dwells.length" class="grid">
          <RouterLink v-for="row in data.recent_dwells" :key="row.post_id"
                      class="card" :to="{ name: 'post', params: { postId: row.post_id } }">
            <div class="cover">
              <img :src="mediaUrl(row.cover_url)" :alt="row.title" loading="lazy" />
              <span class="badge">{{ Math.round(row.seconds) }} 秒</span>
            </div>
            <div class="card-body">
              <h3 class="card-title">{{ row.title }}</h3>
              <div class="meta">
                <span>{{ new Date(row.created_at).toLocaleDateString('zh-CN') }}</span>
              </div>
            </div>
          </RouterLink>
        </div>
        <div v-else class="empty">还没有停留记录</div>
      </section>

      <section class="section">
        <div class="section-head"><h2>可能喜欢</h2><span>综合你的行为与停留</span></div>
        <div class="grid">
          <ProductCard v-for="item in data.liked_items" :key="item.item_id" :item="item" />
        </div>
      </section>
    </template>
  </section>
</template>
