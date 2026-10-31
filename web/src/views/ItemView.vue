<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, mediaUrl } from '../api'
import { useToastStore } from '../stores'
import { useShopStore } from '../stores/shop'
import ProductCard from '../components/ProductCard.vue'
import PostCard from '../components/PostCard.vue'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const shop = useShopStore()

const detail = ref(null)
const similar = ref([])
const posts = ref([])
const loading = ref(true)
const error = ref('')
const busy = ref(false)
const galleryIndex = ref(0)

const item = computed(() => detail.value?.item || null)
const merchant = computed(() => detail.value?.merchant || null)
const reviews = computed(() => detail.value?.reviews || [])
const cover = computed(() => (item.value ? mediaUrl(item.value.cover_url) : ''))
const images = computed(() => {
  const list = item.value?.images || []
  return list.length ? list : (item.value ? [item.value.cover_url] : [])
})
const currentImage = computed(() => mediaUrl(images.value[galleryIndex.value] || ''))

function step(delta) {
  const total = images.value.length
  if (!total) return
  galleryIndex.value = (galleryIndex.value + delta + total) % total
}
const stars = computed(() => {
  const value = Math.round((detail.value?.rating || 0) * 2) / 2
  return [1, 2, 3, 4, 5].map((n) => (value >= n ? 'full' : value >= n - 0.5 ? 'half' : 'empty'))
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.itemDetail(route.params.itemId)
    detail.value = data
    api.postEvent(data.item.item_id, 'view').catch(() => {})
    const [near, shares] = await Promise.all([
      api.similar(data.item.item_id, 6).catch(() => ({ items: [] })),
      api.posts({ productId: data.item.item_id, size: 4 }).catch(() => ({ posts: [] }))
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
    if (type === 'cart') await shop.addToCart(item.value)
    toast.push(type === 'purchase' ? '已模拟购买，推荐会更新' : '已加入购物车')
  } catch (err) {
    toast.push(err.message, 'error')
  } finally {
    busy.value = false
  }
}

const favorite = computed(() => (item.value ? shop.isFavorite(item.value.item_id) : false))

async function toggleFav() {
  if (!item.value) return
  const added = await shop.toggleFavorite(item.value)
  toast.push(added ? '已收藏' : '已取消收藏')
}

onMounted(load)

// 同一个详情组件复用时（商品→相似商品）必须重新加载，否则页面停在上一件商品
watch(() => route.params.itemId, () => {
  galleryIndex.value = 0
  load()
})
</script>

<template>
  <section>
    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="error" class="notice">{{ error }}</div>

    <template v-else-if="detail">
      <div class="detail">
        <div class="gallery">
          <img :src="currentImage" :alt="item.title" />
          <button class="gallery-nav prev" type="button" @click="step(-1)">‹</button>
          <button class="gallery-nav next" type="button" @click="step(1)">›</button>
          <div class="gallery-dots">
            <button v-for="(_, index) in images" :key="index" type="button"
                    :class="index === galleryIndex ? 'active' : ''" @click="galleryIndex = index" />
          </div>
        </div>
        <div>
          <h1>{{ item.title }}</h1>
          <div class="meta" style="margin: 6px 0">
            <span class="stars">
              <span v-for="(kind, index) in stars" :key="index" :class="['star', kind]">★</span>
            </span>
            <b>{{ detail.rating.toFixed(1) }}</b>
            <span class="dot" />
            <span>{{ detail.review_count }} 条评价</span>
            <span class="dot" />
            <span>{{ item.category }}</span>
          </div>
          <div class="price" style="font-size: 26px">¥{{ Number(item.price).toFixed(0) }}</div>
          <div class="tag-row">
            <span v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>
          <p class="body-text">{{ item.description }}</p>

          <div style="display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap">
            <button class="btn" type="button" :disabled="busy" @click="act('cart')">加入购物车</button>
            <button class="btn ghost" type="button" :disabled="busy" @click="act('purchase')">模拟购买</button>
            <button class="btn ghost" type="button" @click="toggleFav">
              {{ favorite ? '♥ 已收藏' : '♡ 收藏' }}
            </button>
          </div>

          <RouterLink v-if="merchant" class="merchant-card"
                      :to="{ name: 'shop', params: { merchantId: merchant.merchant_id } }">
            <span class="avatar">{{ merchant.name.slice(0, 1) }}</span>
            <div class="grow">
              <div style="font-weight: 700">{{ merchant.name }} <span class="tag">官方店铺</span></div>
              <div class="meta">
                评分 {{ merchant.rating }} · {{ merchant.item_count }} 件商品 · {{ merchant.followers }} 关注
              </div>
            </div>
            <span class="arrow">进店 ›</span>
          </RouterLink>
        </div>
      </div>

      <section class="section">
        <div class="section-head">
          <h2>商品评价</h2>
          <span>{{ detail.rating.toFixed(1) }} 分 · 共 {{ detail.review_count }} 条</span>
        </div>
        <div v-if="reviews.length" class="row-list">
          <div v-for="review in reviews" :key="review.review_id" class="row-item review-item">
            <span class="avatar">{{ review.user_name.slice(0, 1) }}</span>
            <div class="grow">
              <div class="meta">
                <b>{{ review.user_name }}</b>
                <span class="stars">
                  <span v-for="n in 5" :key="n" :class="['star', review.rating >= n ? 'full' : 'empty']">★</span>
                </span>
              </div>
              <div>{{ review.content }}</div>
              <div class="meta">{{ new Date(review.created_at).toLocaleDateString('zh-CN') }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty">还没有评价</div>
      </section>

      <section v-if="posts.length" class="section">
        <div class="section-head"><h2>买家安利</h2><span>{{ posts.length }} 条分享</span></div>
        <div class="masonry">
          <PostCard v-for="post in posts" :key="post.post_id" :post="post" />
        </div>
      </section>

      <section v-if="similar.length" class="section">
        <div class="section-head"><h2>相似推荐</h2></div>
        <div class="grid">
          <ProductCard v-for="row in similar" :key="row.item_id" :item="row" />
        </div>
      </section>
    </template>
  </section>
</template>
