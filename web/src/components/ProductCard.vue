<script setup>
import { computed } from 'vue'
import { mediaUrl } from '../api'

const props = defineProps({ item: { type: Object, required: true } })

const cover = computed(() => mediaUrl(props.item.cover_url))
const tags = computed(() => {
  if (Array.isArray(props.item.tags)) return props.item.tags
  return String(props.item.tags || '').split(',').filter(Boolean)
})
</script>

<template>
  <RouterLink class="card" :to="{ name: 'item', params: { itemId: item.item_id } }">
    <div class="cover">
      <img :src="cover" :alt="item.title" loading="lazy" />
    </div>
    <div class="card-body">
      <h3 class="card-title">{{ item.title }}</h3>
      <div class="meta">
        <span>{{ item.category }}</span>
        <span class="dot" />
        <span class="price">¥{{ Number(item.price).toFixed(0) }}</span>
      </div>
      <div v-if="tags.length" class="tag-row" style="margin: 8px 0 0">
        <span v-for="tag in tags.slice(0, 2)" :key="tag" class="tag">{{ tag }}</span>
      </div>
      <div v-if="item.reason" class="reason">{{ item.reason }}</div>
    </div>
  </RouterLink>
</template>
