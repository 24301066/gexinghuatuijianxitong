<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, mediaUrl } from '../api'
import { useSessionStore } from '../stores'
import { useShopStore } from '../stores/shop'
import ProductCard from '../components/ProductCard.vue'

const router = useRouter()
const session = useSessionStore()
const shop = useShopStore()

const loading = ref(true)
const error = ref('')
const insights = ref(null)
const myReviews = ref([])
const tab = ref('dwell')
const fileInput = ref(null)
const avatarSrc = ref(session.user?.user_id ? api.avatarUrl(session.user.user_id) : '')
const avatarVersion = ref(Date.now())

const TABS = [
  { key: 'dwell', label: '停留过的安利' },
  { key: 'liked', label: '可能喜欢' },
  { key: 'favorites', label: '我的收藏' },
  { key: 'reviews', label: '我的评价' }
]

const ORDER_LINKS = [
  { key: 'pending_payment', label: '待付款' },
  { key: 'pending_shipment', label: '待发货' },
  { key: 'pending_receipt', label: '待收货' },
  { key: 'pending_review', label: '待评价' },
  { key: 'aftersale', label: '退款/售后' }
]

const recentSearches = computed(() => {
  const seen = new Set()
  return (insights.value?.recent_searches || []).filter((row) => {
    if (seen.has(row.keyword)) return false
    seen.add(row.keyword)
    return true
  })
})

const orderCount = (status) => shop.orders.filter((row) => row.status === status).length

async function load() {
  loading.value = true
  error.value = ''
  try {
    insights.value = await api.insights()
    myReviews.value = await api.myReviews().catch(() => [])
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function goSearch(word) {
  router.push({ name: 'search', query: { q: word } })
}

function pickAvatar() {
  fileInput.value?.click()
}

async function onAvatarChange(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!file.type.startsWith('image/')) {
    toast.push('请选择图片文件', 'error')
    return
  }
  if (file.size > 2 * 1024 * 1024) {
    toast.push('图片不能超过 2MB', 'error')
    return
  }
  const reader = new FileReader()
  reader.onload = async () => {
    try {
      await api.uploadAvatar(String(reader.result))
      avatarVersion.value = Date.now()
      avatarSrc.value = `${api.avatarUrl(session.user.user_id)}?v=${avatarVersion.value}`
      toast.push('头像已更新')
    } catch (error) {
      toast.push(error.message, 'error')
    }
  }
  reader.readAsDataURL(file)
}

onMounted(load)
</script>

<template>
  <section>
    <div v-if="error" class="notice">{{ error }}</div>

    <div class="section-card" style="display: flex; align-items: center; gap: 16px">
      <label class="avatar avatar-lg avatar-btn" title="点击更换头像">
        <img v-if="avatarSrc" :src="avatarSrc" alt="头像" />
        <span v-else>{{ (session.user?.username || 'U').slice(0, 1).toUpperCase() }}</span>
        <span class="avatar-tip">换</span>
        <input class="avatar-input" type="file" accept="image/*" @change="onAvatarChange" />
      </label>
      <div style="flex: 1">
        <RouterLink :to="{ name: 'profile' }" style="font-weight: 800; font-size: 19px">
          {{ shop.profile.nickname }}
        </RouterLink>
        <div class="meta">
          <span>Lv.{{ shop.profile.level }}</span>
          <span class="dot" />
          <span>活跃度 {{ shop.profile.active }}</span>
          <span class="dot" />
          <span>{{ session.user?.username }}</span>
        </div>
      </div>
      <RouterLink class="btn ghost small" :to="{ name: 'profile' }">个人信息 ›</RouterLink>
    </div>

    <div class="section-card">
      <RouterLink class="stat-grid" :to="{ name: 'wallet' }" style="text-decoration: none">
        <div class="stat"><b>{{ shop.wallet.balance }}</b><span>余额</span></div>
        <div class="stat"><b>{{ shop.wallet.coupons }}</b><span>优惠券</span></div>
        <div class="stat"><b>{{ shop.wallet.points }}</b><span>积分</span></div>
        <div class="stat"><b>{{ shop.wallet.red_packets }}</b><span>红包</span></div>
      </RouterLink>
      <div class="meta" style="margin-top: 8px">
        <RouterLink class="link" :to="{ name: 'wallet' }">进入钱包管理 ›</RouterLink>
      </div>
    </div>

    <div class="section-card">
      <div class="section-head" style="margin-bottom: 10px">
        <h2>我的订单</h2>
        <RouterLink class="link" :to="{ name: 'orders' }">全部订单 ›</RouterLink>
      </div>
      <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px">
        <RouterLink v-for="link in ORDER_LINKS" :key="link.key"
                    :to="{ name: 'orders', query: { status: link.key } }"
                    style="text-align: center; padding: 8px 2px; border-radius: 12px; background: #faf5ef">
          <div style="font-size: 18px">
            {{ link.key === 'aftersale' ? '↩' : link.key === 'pending_review' ? '✎' : link.key === 'pending_receipt' ? '📦' : link.key === 'pending_shipment' ? '🚚' : '💳' }}
          </div>
          <div style="font-size: 12px; color: var(--muted)">{{ link.label }}</div>
          <div v-if="orderCount(link.key)" class="dot-badge">{{ orderCount(link.key) }}</div>
        </RouterLink>
      </div>
    </div>

    <div class="section-card">
      <div class="menu-list">
        <RouterLink class="menu-row" :to="{ name: 'cart' }">
          <span>🛒 购物车</span>
          <span class="arrow">{{ shop.cartCount }} 件 ›</span>
        </RouterLink>
        <RouterLink class="menu-row" :to="{ name: 'address' }">
          <span>📍 地址</span><span class="arrow">{{ shop.addresses.length }} 个 ›</span>
        </RouterLink>
        <RouterLink class="menu-row" :to="{ name: 'chat', params: { id: 'service' } }">
          <span>💬 官方客服</span><span class="arrow">›</span>
        </RouterLink>
        <RouterLink class="menu-row" :to="{ name: 'settings' }">
          <span>⚙ 设置</span><span class="arrow">›</span>
        </RouterLink>
        <RouterLink class="menu-row" :to="{ name: 'about' }">
          <span>ℹ 关于版本</span><span class="arrow">›</span>
        </RouterLink>
      </div>
    </div>

    <div class="section-card">
      <div class="section-head" style="margin-bottom: 10px"><h2>最近搜索</h2></div>
      <div v-if="recentSearches.length" class="chip-row">
        <button v-for="row in recentSearches" :key="row.keyword" class="chip" type="button"
                @click="goSearch(row.keyword)">
          {{ row.keyword }}
        </button>
      </div>
      <div v-else class="meta">还没有搜索记录</div>
    </div>

    <div class="tabs">
      <button v-for="item in TABS" :key="item.key" type="button"
              :class="tab === item.key ? 'active' : ''" @click="tab = item.key">
        {{ item.label }}
      </button>
    </div>

    <div class="section-card" style="min-height: 140px">
      <template v-if="tab === 'dwell'">
        <div v-if="loading" class="empty">加载中…</div>
        <div v-else-if="insights?.recent_dwells?.length" class="row-list">
          <RouterLink v-for="row in insights.recent_dwells" :key="row.post_id"
                      class="row-item" :to="{ name: 'post', params: { postId: row.post_id } }">
            <img :src="mediaUrl(row.cover_url)" :alt="row.title" class="cart-thumb" />
            <div class="grow">
              <div style="font-weight: 700">{{ row.title }}</div>
              <div class="meta">停留 {{ Math.round(row.seconds) }} 秒</div>
            </div>
          </RouterLink>
        </div>
        <div v-else class="empty">还没有停留记录，去发现页逛逛</div>
      </template>

      <template v-else-if="tab === 'liked'">
        <div class="grid">
          <ProductCard v-for="item in insights?.liked_items || []" :key="item.item_id" :item="item" />
        </div>
        <div v-if="!(insights?.liked_items || []).length" class="empty">暂无推荐</div>
      </template>

      <template v-else-if="tab === 'favorites'">
        <div v-if="shop.favorites.length" class="grid">
          <ProductCard v-for="item in shop.favorites" :key="item.item_id" :item="item" />
        </div>
        <div v-else class="empty">还没有收藏，点商品上的 ♡ 试试</div>
      </template>

      <template v-else>
        <div v-if="myReviews.length" class="row-list">
          <div v-for="row in myReviews" :key="row.review_id" class="row-item">
            <span class="avatar">我</span>
            <div class="grow">
              <div>{{ row.item_title }}</div>
              <div class="stars">
                <span v-for="n in 5" :key="n" :class="['star', row.rating >= n ? 'full' : 'empty']">★</span>
              </div>
              <div>{{ row.content }}</div>
              <div v-if="(row.media || []).length" class="review-media">
                <template v-for="src in row.media" :key="src">
                  <video v-if="src.endsWith('.mp4') || src.endsWith('.webm')"
                         :src="mediaUrl(src)" controls />
                  <img v-else :src="mediaUrl(src)" alt="评价图片" />
                </template>
              </div>
              <div class="meta">{{ new Date(row.created_at).toLocaleDateString('zh-CN') }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty">还没有评价，收货后可以来评价</div>
      </template>
    </div>
  </section>
</template>
