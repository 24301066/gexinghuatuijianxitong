<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import PostCard from '../components/PostCard.vue'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const author = ref(null)

const initial = computed(() => (author.value?.username || 'U').slice(0, 1))

async function load() {
  loading.value = true
  error.value = ''
  try {
    author.value = await api.author(route.params.authorId)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => route.params.authorId, load)
</script>

<template>
  <section>
    <div v-if="error" class="notice">{{ error }}</div>
    <div v-if="loading" class="empty">加载作者主页…</div>

    <template v-else-if="author">
      <div class="section-card" style="display: flex; gap: 18px; align-items: center">
        <span class="avatar avatar-lg">{{ initial }}</span>
        <div style="flex: 1">
          <div style="font-weight: 800; font-size: 20px">{{ author.username }}</div>
          <div class="meta">
            <span>{{ author.post_count }} 篇安利</span>
            <span class="dot" />
            <span>♡ {{ author.total_likes }}</span>
            <span class="dot" />
            <span v-if="author.categories.length">偏爱 {{ author.categories.join(' / ') }}</span>
          </div>
        </div>
      </div>

      <div class="tabs">
        <button class="active" type="button">TA 的安利与视频</button>
        <button type="button" disabled>TA 的买家评价</button>
      </div>

      <div v-if="author.posts.length" class="masonry">
        <PostCard v-for="post in author.posts" :key="post.post_id" :post="post" />
      </div>
      <div v-else class="empty">TA 还没有发布安利</div>
    </template>
  </section>
</template>
