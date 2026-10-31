<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { mediaUrl } from '../api'
import { useShopStore } from '../stores/shop'
import { useToastStore } from '../stores'

const props = defineProps({ item: { type: Object, required: true } })
const router = useRouter()
const shop = useShopStore()
const toast = useToastStore()

const cover = computed(() => mediaUrl(props.item.cover_url))
const favorite = computed(() => shop.favoriteIds.has(props.item.item_id))

function addCart(event) {
  event.preventDefault()
  shop.addToCart(props.item)
  toast.push('已加入购物车')
}

async function buyNow(event) {
  event.preventDefault()
  await shop.addToCart(props.item)
  router.push({ name: 'checkout' })
}

function toggleFav(event) {
  event.preventDefault()
  const added = shop.toggleFavorite(props.item)
  toast.push(added ? '已收藏' : '已取消收藏')
}
</script>

<template>
  <div class="card product-card">
    <RouterLink class="cover" :to="{ name: 'item', params: { itemId: item.item_id } }">
      <img :src="cover" :alt="item.title" loading="lazy" />
      <span v-if="item.reason" class="badge reason-badge">{{ item.reason }}</span>
    </RouterLink>
    <div class="card-body">
      <RouterLink :to="{ name: 'item', params: { itemId: item.item_id } }" class="card-title">
        {{ item.title }}
      </RouterLink>
      <div class="meta">
        <span class="price">¥{{ Number(item.price).toFixed(0) }}</span>
        <span class="dot" />
        <span>{{ item.category }}</span>
      </div>
      <div class="quick-actions">
        <button class="mini" type="button" :class="{ on: favorite }" @click="toggleFav">
          {{ favorite ? '♥' : '♡' }} 收藏
        </button>
        <button class="mini" type="button" @click="addCart">加购</button>
        <button class="mini accent" type="button" @click="buyNow">购买</button>
      </div>
    </div>
  </div>
</template>
