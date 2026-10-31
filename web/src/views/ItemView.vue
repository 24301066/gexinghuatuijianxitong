<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, mediaUrl } from '../api'
import { useToastStore } from '../stores'
import ProductCard from '../components/ProductCard.vue'
import PostCard from '../components/PostCard.vue'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const item = ref(null)
const similar = ref([])
const posts = ref([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)

const cover = computed(() => (item.value ? mediaUrl(item.value.cover_url) : ''))
const tags = computed(() => item.value?.tags || [])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.item(route.params.itemId)
    item.value = data
    api.postEvent(data.item_id, 'view').catch(() => {})
    const [near, shares] = await Promise.all([
      api.similar(data.item_id, 6).catch(() => ({ items: [] })),
      api.posts({ productId: data.item_id, size: 4 }).catch(() => ({ posts: [] }))
    ])
    similar.value = near.items || []
    posts.value = shares.posts || []
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function act(type) {
  if (!item.value || busy.value) return
  busy.value = true
  try {
    await api.postEvent(item.value.item_id, type)
    toast.push(type === 'purchase' ? '已模拟购买，推荐会更新' : '已加入购物车', 'info')
  } catch (err) {
    toast.push(err.message, 'error')
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <button class="link" type="button" @click="router.back()">← 返回</button>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="error" class="notice">{{ error }}</div>

    <template v-else-if="item">
      <div class="detail">
        <div class="cover">
          <img :src="cover" :alt="item.title" />
        </div>
        <div>
          <h1>{{ item.title }}</h1>
          <div class="meta">
            <span>{{ item.category }}</span>
            <span class="dot" />
            <span class="price" style="font-size: 22px">¥{{ Number(item.price).toFixed(0) }}</span>
          </div>
          <div class="tag-row">
            <span v-for="tag in tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <p class="body-text">{{ item.description }}</p>
          <div style="display: flex; gap: 10px; margin-top: 18px">
            <button class="btn" type="button" :disabled="busy" @click="act('cart')">加入购物车</button>
            <button class="btn ghost" type="button" :disabled="busy" @click="act('purchase')">模拟购买</button>
          </div>
        </div>
      </div>

      <section v-if="posts.length" class="section">
        <div class="section-head">
          <h2>买家安利</h2>
          <span>{{ posts.length }} 条分享</span>
        </div>
        <div class="masonry">
          <PostCard v-for="post in posts" :key="post.post_id" :post="post" />
        </div>
      </section>

      <section v-if="similar.length" class="section">
        <div class="section-head">
          <h2>相似推荐</h2>
          <span>来自 /items/{id}/similar</span>
        </div>
        <div class="grid">
          <ProductCard v-for="row in similar" :key="row.item_id" :item="row" />
        </div>
      </section>
    </template>
  </section>
</template>
