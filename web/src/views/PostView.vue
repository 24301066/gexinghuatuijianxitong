<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, mediaUrl } from '../api'
import PostCard from '../components/PostCard.vue'

const route = useRoute()
const router = useRouter()
const post = ref(null)
const related = ref([])
const loading = ref(true)
const error = ref('')
const galleryIndex = ref(0)
const merchant = ref(null)
const reviews = ref([])
const rating = ref({ average: 0, count: 0 })
let enteredAt = 0
let reported = false

const isVideo = computed(() => post.value?.media_type === 'video')
const images = computed(() => {
  const list = post.value?.images || []
  return list.length ? list : (post.value ? [post.value.cover_url] : [])
})
const currentImage = computed(() => mediaUrl(images.value[galleryIndex.value] || ''))
const duration = computed(() => {
  const seconds = Number(post.value?.video_seconds || 0)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
})

function step(delta) {
  const total = images.value.length
  if (!total) return
  galleryIndex.value = (galleryIndex.value + delta + total) % total
}

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
    const data = await api.post(route.params.postId)
    post.value = data
    galleryIndex.value = 0
    enteredAt = Date.now()
    reported = false
    if (data.product) {
      const detail = await api.itemDetail(data.product.item_id).catch(() => null)
      if (detail) {
        merchant.value = detail.merchant
        reviews.value = detail.reviews || []
        rating.value = { average: detail.rating || 0, count: detail.review_count || 0 }
      }
    }
    const linked = await api.posts({ productId: data.product?.item_id || '', size: 4 })
    related.value = linked.posts.filter((row) => row.post_id !== data.post_id)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  window.addEventListener('pagehide', reportDwell)
})
watch(() => route.params.postId, () => {
  galleryIndex.value = 0
  load()
})

onBeforeUnmount(() => {
  reportDwell()
  window.removeEventListener('pagehide', reportDwell)
})
</script>

<template>
  <section>
    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="error" class="notice">{{ error }}</div>

    <template v-else-if="post">
      <div class="detail">
        <div>
          <div v-if="isVideo" class="video-shell">
            <video v-if="post.has_video" :src="mediaUrl(post.video_url)" controls autoplay muted playsinline />
            <template v-else>
              <img :src="mediaUrl(post.cover_url)" :alt="post.title" style="width: 100%; height: 100%; object-fit: cover" />
              <div class="video-fallback">
                <span class="play-dot">▶</span>
                <span>视频 {{ duration }}</span>
                <span style="font-size: 12px; opacity: 0.85">演示封面 · 放入 mp4 后可播放</span>
              </div>
            </template>
          </div>

          <div v-else class="gallery">
            <img :src="currentImage" :alt="post.title" />
            <button class="gallery-nav prev" type="button" @click="step(-1)">‹</button>
            <button class="gallery-nav next" type="button" @click="step(1)">›</button>
            <div class="gallery-dots">
              <button v-for="(_, index) in images" :key="index" type="button"
                      :class="index === galleryIndex ? 'active' : ''" @click="galleryIndex = index" />
            </div>
          </div>
        </div>

        <div>
          <h1>{{ post.title }}</h1>
          <div class="meta">
            <RouterLink :to="{ name: 'author', params: { authorId: post.author_id } }" class="author-chip">
              <span class="avatar mini-avatar">{{ post.author_name.slice(0, 1) }}</span>
              {{ post.author_name }}
            </RouterLink>
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
              <button class="btn" type="button"
                      @click="router.push({ name: 'item', params: { itemId: post.product.item_id } })">
                购买同款
              </button>
            </div>
          </div>
        </div>
      </div>

      <section v-if="merchant" class="section">
        <div class="section-head"><h2>售卖商家</h2><span>安利作者与商家不是同一个人</span></div>
        <RouterLink class="merchant-card" :to="{ name: 'shop', params: { merchantId: merchant.merchant_id } }">
          <span class="avatar">{{ merchant.name.slice(0, 1) }}</span>
          <div class="grow">
            <div style="font-weight: 700">{{ merchant.name }} <span class="tag">商家</span></div>
            <div class="meta">评分 {{ merchant.rating }} · {{ merchant.item_count }} 件商品</div>
          </div>
          <span class="arrow">进店 ›</span>
        </RouterLink>
      </section>

      <section v-if="reviews.length" class="section">
        <div class="section-head">
          <h2>买家秀评价</h2>
          <span>{{ rating.average.toFixed(1) }} 分 · 共 {{ rating.count }} 条</span>
        </div>
        <div class="row-list">
          <div v-for="review in reviews.slice(0, 6)" :key="review.review_id" class="row-item review-item">
            <span class="avatar">{{ review.user_name.slice(0, 1) }}</span>
            <div class="grow">
              <div class="meta">
                <b>{{ review.user_name }}</b>
                <span class="stars">
                  <span v-for="n in 5" :key="n" :class="['star', review.rating >= n ? 'full' : 'empty']">★</span>
                </span>
              </div>
              <div>{{ review.content }}</div>
            </div>
          </div>
        </div>
      </section>

      <section v-if="related.length" class="section">
        <div class="section-head"><h2>同类安利</h2><span>同一个商品的其他分享</span></div>
        <div class="masonry">
          <PostCard v-for="row in related" :key="row.post_id" :post="row" />
        </div>
      </section>
    </template>
  </section>
</template>