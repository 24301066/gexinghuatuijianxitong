<script setup>
import { computed } from 'vue'
import { mediaUrl } from '../api'

const props = defineProps({ post: { type: Object, required: true } })

const cover = computed(() => mediaUrl(props.post.cover_url))
const isVideo = computed(() => props.post.media_type === 'video')
const duration = computed(() => {
  const seconds = Number(props.post.video_seconds || 0)
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`
})
const likes = computed(() => {
  const value = Number(props.post.likes || 0)
  return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(value)
})
</script>

<template>
  <RouterLink class="card" :to="{ name: 'post', params: { postId: post.post_id } }">
    <div class="cover">
      <img :src="cover" :alt="post.title" loading="lazy" />
      <span :class="['badge', isVideo ? 'live' : '']">{{ isVideo ? `视频 ${duration}` : '图文' }}</span>
    </div>
    <div class="card-body">
      <h3 class="card-title">{{ post.title }}</h3>
      <div class="meta">
        <span>{{ post.author_name }}</span>
        <span class="dot" />
        <span>♡ {{ likes }}</span>
      </div>
      <div v-if="post.product" class="reason">
        {{ post.product.title }} · ¥{{ post.product.price.toFixed(0) }}
      </div>
    </div>
  </RouterLink>
</template>
