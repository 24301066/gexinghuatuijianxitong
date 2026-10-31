<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { useToastStore } from '../stores'
import ProductCard from '../components/ProductCard.vue'
import PostCard from '../components/PostCard.vue'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const keyword = ref('')
const loading = ref(false)
const error = ref('')
const result = ref({ query: '', items: [], posts: [], recommended: [] })
const suggestions = ['咖啡', '收纳', '键盘', '面膜', '露营']

const hasResult = computed(() => Boolean(result.value.query))

async function run(query) {
  const text = String(query || '').trim()
  if (!text) return
  keyword.value = text
  loading.value = true
  error.value = ''
  try {
    // 记录搜索，推荐侧会据此加入关键词信号（失败不影响浏览）
    api.searchEvent(text).catch(() => {})
    result.value = await api.search(text)
  } catch (err) {
    error.value = err.message
    toast.push(err.message, 'error')
  } finally {
    loading.value = false
  }
}

function pick(word) {
  router.push({ name: 'search', query: { q: word } })
}

watch(
  () => route.query.q,
  (value) => {
    if (value) run(value)
  }
)

onMounted(() => {
  keyword.value = route.query.q || ''
  if (route.query.q) run(route.query.q)
})
</script>

<template>
  <section>
    <div class="page-head">
      <h1>搜索</h1>
      <p>搜商品、安利或类目；搜索词会用于"可能喜欢"的推荐。</p>
    </div>

    <div class="search-box" style="margin: 0 0 18px; max-width: 560px">
      <span aria-hidden="true">🔍</span>
      <input v-model="keyword" placeholder="例如：咖啡、收纳、键盘" @keyup.enter="run(keyword)" />
      <button class="btn small" type="button" @click="run(keyword)">搜索</button>
    </div>

    <div class="chip-row" style="margin-bottom: 20px">
      <button v-for="word in suggestions" :key="word" class="chip" type="button" @click="pick(word)">
        # {{ word }}
      </button>
    </div>

    <div v-if="error" class="notice">{{ error }}</div>
    <div v-if="loading" class="empty">搜索中…</div>

    <template v-else-if="hasResult">
      <section class="section" style="margin-top: 0">
        <div class="section-head">
          <h2>“{{ result.query }}”的商品</h2>
          <span>{{ result.items.length }} 件</span>
        </div>
        <div v-if="result.items.length" class="grid">
          <ProductCard v-for="item in result.items" :key="item.item_id" :item="item" />
        </div>
        <div v-else class="empty">没有找到商品，换个关键词试试</div>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>相关安利</h2>
          <span>{{ result.posts.length }} 条</span>
        </div>
        <div v-if="result.posts.length" class="masonry">
          <PostCard v-for="post in result.posts" :key="post.post_id" :post="post" />
        </div>
        <div v-else class="empty">还没有相关安利</div>
      </section>

      <section class="section">
        <div class="section-head">
          <h2>根据搜索推荐</h2>
          <span>结合你最近的搜索</span>
        </div>
        <div class="grid">
          <ProductCard v-for="item in result.recommended" :key="item.item_id" :item="item" />
        </div>
      </section>
    </template>

    <div v-else class="empty">输入关键词开始搜索</div>
  </section>
</template>
