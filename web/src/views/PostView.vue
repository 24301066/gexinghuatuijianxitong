<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, mediaUrl } from '../api'
import { useToastStore } from '../stores'
import PostCard from '../components/PostCard.vue'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const post = ref(null)
const related = ref([])
const loading = ref(true)
const error = ref('')
let enteredAt = 0
let reported = false

const cover = computed(() => (post.value ? mediaUrl(post.value.cover_url) : ''))
const isVideo = computed(() => post.value?.media_type === 'video')
const duration = computed(() => {
  const seconds = Number(post.value?.video_seconds || 0)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
})

function reportDwell() {
  if (reported || !post.value || !enteredAt) return
  reported = true
  const seconds = Math.round((Date.now() - enteredAt) / 1000)
  api.dwellEvent(post.value.post_id, Math.max(1, seconds)).catch(() => {})
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.post(post.value?.post_id || route.params.postId)
    post.value = data
    enteredAt = Date.now()
    reported = false
    const linked = await api.posts({ productId: data.product?.item_id || '', size: 4 })
    related.value = linked.posts.filter((row) => row.post_id !== data.post_id)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function buy() {
  if (!post.value?.product) return
  router.push({ name: 'item', params: { itemId: post.value.product.item_id } })
}

onMounted(() => {
  load()
  window.addEventListener('pagehide', reportDwell)
})
onBeforeUnmount(() => {
  reportDwell()
  window.removeEventListener('pagehide', reportDwell)
})
</script>

<template>
  <section>
    <button class="link" type="button" @click="router.back()">← 返回</button>

    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="error" class="notice">{{ error }}</div>

    <template v-else-if="post">
      <div class="detail">
        <div>
          <div v-if="isVideo && post.has_video" class="video-shell">
            <video :src="mediaUrl(post.video_url)" controls autoplay muted playsinline />
          </div>
          <div v-else class="video-shell">
            <img :src="cover" :alt="post.title" style="width: 100%; height: 100%; object-fit: cover" />
            <div class="video-fallback">
              <span class="play-dot">▶</span>
              <span>{{ isVideo ? `视频 ${duration} · 演示封面` : '图文安利' }}</span>
            </div>
          </div>
        </div>

        <div>
          <h1>{{ post.title }}</h1>
          <div class="meta">
            <span>{{ post.author_name }}</span>
            <span class="dot" />
            <span>♡ {{ post.likes }}</span>
            <span class="dot" />
            <span>{{ new Date(post.created_at).toLocaleDateString('zh-CN') }}</span>
          </div>

          <p class="body-text" style="margin-top: 14px">{{ post.body }}</p>

          <div v-if="post.tags.length" class="tag-row">
            <span v-for="tag in post.tags" :key="tag" class="tag">#{{ tag }}</span>
          </div>

          <div v-if="post.product" class="card" style="margin-top: 18px; padding: 14px">
            <div class="meta" style="justify-content: space-between">
              <div>
                <div style="font-weight: 700">{{ post.product.title }}</div>
                <div class="meta">
                  <span>{{ post.product.category }}</span>
                  <span class="dot" />
                  <span class="price">¥{{ post.product.price.toFixed(0) }}</span>
                </div>
              </div>
              <button class="btn" type="button" @click="buy">购买同款</button>
            </div>
          </div>
        </div>
      </div>

      <section v-if="related.length" class="section">
        <div class="section-head">
          <h2>同类安利</h2>
          <span>同一个商品的其他分享</span>
        </div>
        <div class="masonry">
          <PostCard v-for="row in related" :key="row.post_id" :post="row" />
        </div>
      </section>
    </template>
  </section>
</template>
