<script setup>
import { computed } from 'vue'
import { mediaUrl } from '../api'

const props = defineProps({ post: { type: Object, required: true } })

const cover = computed(() => mediaUrl(props.post.cover_url))
const isVideo = computed(() => props.post.media_type === 'video')
const duration = computed(() => {
  const seconds = Number(props.post.video_seconds || 0)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
})
const likes = computed(() => {
  const value = Number(props.post.likes || 0)
  return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(value)
})
</script>

<template>
  <div class="card post-card">
    <RouterLink class="cover" :to="{ name: 'post', params: { postId: post.post_id } }">
      <img :src="cover" :alt="post.title" loading="lazy" />
      <span :class="['badge', isVideo ? 'live' : '']">
        {{ isVideo ? `视频 ${duration}` : '图文' }}
      </span>
    </RouterLink>
    <div class="card-body">
      <RouterLink class="card-title" :to="{ name: 'post', params: { postId: post.post_id } }">
        {{ post.title }}
      </RouterLink>
      <div class="meta">
        <RouterLink class="author-chip" :to="{ name: 'author', params: { authorId: post.author_id } }">
          <span class="avatar mini-avatar">{{ (post.author_name || 'U').slice(0, 1) }}</span>
          {{ post.author_name }}
        </RouterLink>
        <span class="dot" />
        <span>♡ {{ likes }}</span>
      </div>
      <div v-if="post.product" class="reason">
        {{ post.product.title }} · ¥{{ post.product.price.toFixed(0) }}
      </div>
    </div>
  </div>
</template>
