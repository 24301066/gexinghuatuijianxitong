<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import ProductCard from '../components/ProductCard.vue'

const route = useRoute()
const router = useRouter()
const shop = ref(null)
const loading = ref(true)
const error = ref('')

const merchant = computed(() => shop.value?.merchant || null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    shop.value = await api.shop(route.params.merchantId)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => route.params.merchantId, load)
</script>

<template>
  <section>
    <button class="link back-link" type="button" @click="router.back()">← 返回</button>

    <div v-if="error" class="notice">{{ error }}</div>
    <div v-if="loading" class="empty">加载店铺…</div>

    <template v-else-if="merchant">
      <div class="section-card" style="display: flex; gap: 16px; align-items: center">
        <span class="avatar avatar-lg">{{ merchant.name.slice(0, 1) }}</span>
        <div style="flex: 1">
          <div style="font-weight: 800; font-size: 20px">
            {{ merchant.name }}
            <span class="tag">官方店铺</span>
          </div>
          <div class="meta">
            评分 {{ merchant.rating }} · {{ merchant.item_count }} 件商品 · {{ merchant.followers }} 关注
          </div>
          <div class="meta" style="margin-top: 4px">{{ merchant.description }}</div>
        </div>
      </div>

      <div class="section-head" style="margin-top: 20px">
        <h2>全部商品</h2>
        <span>{{ shop.items.length }} 件</span>
      </div>
      <div class="grid">
        <ProductCard v-for="item in shop.items" :key="item.item_id" :item="item" />
      </div>
    </template>
  </section>
</template>
