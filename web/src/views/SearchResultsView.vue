<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import ProductCard from '../components/ProductCard.vue'
import PostCard from '../components/PostCard.vue'

const route = useRoute()
const loading = ref(false)
const error = ref('')
const result = ref({ query: '', items: [], posts: [], recommended: [] })

async function run(query) {
  const text = String(query || '').trim()
  if (!text) return
  loading.value = true
  error.value = ''
  try {
    api.searchEvent(text).catch(() => {})
    result.value = await api.search(text)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

watch(() => route.query.q, (value) => { if (value) run(value) })
onMounted(() => { if (route.query.q) run(route.query.q) })
</script>

<template>
  <section>
    <div class="page-head">
      <h1>“{{ route.query.q }}” 的搜索结果</h1>
      <p>商品 {{ result.items.length }} 件 · 安利 {{ result.posts.length }} 条</p>
    </div>

    <div v-if="error" class="notice">{{ error }}</div>
    <div v-if="loading" class="empty">搜索中…</div>

    <template v-else>
      <section class="section" style="margin-top: 0">
        <div class="section-head"><h2>商品</h2></div>
        <div v-if="result.items.length" class="grid">
          <ProductCard v-for="item in result.items" :key="item.item_id" :item="item" />
        </div>
        <div v-else class="empty">没有匹配的商品，换个关键词试试</div>
      </section>

      <section v-if="result.posts.length" class="section">
        <div class="section-head"><h2>相关安利</h2></div>
        <div class="masonry">
          <PostCard v-for="post in result.posts" :key="post.post_id" :post="post" />
        </div>
      </section>

      <section v-if="result.recommended.length" class="section">
        <div class="section-head"><h2>根据搜索推荐</h2></div>
        <div class="grid">
          <ProductCard v-for="item in result.recommended" :key="item.item_id" :item="item" />
        </div>
      </section>
    </template>
  </section>
</template>
