<script setup>
import { computed, onMounted, ref } from 'vue'
import { api, mediaUrl } from '../api'
import { useToastStore } from '../stores'
import ProductCard from '../components/ProductCard.vue'
import PostCard from '../components/PostCard.vue'

const toast = useToastStore()
const loading = ref(true)
const error = ref('')
const feed = ref({ hero: null, posts: [], items: [] })
const freshPosts = ref([])

const hero = computed(() => feed.value.hero)
const heroCover = computed(() => (hero.value ? mediaUrl(hero.value.cover_url) : ''))
const heroIsVideo = computed(() => hero.value?.media_type === 'video')
const heroDuration = computed(() => {
  const seconds = Number(hero.value?.video_seconds || 0)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [data, posts] = await Promise.all([api.feed(8), api.posts({ page: 2, size: 4 })])
    feed.value = data
    freshPosts.value = posts.posts
  } catch (err) {
    error.value = err.message
    toast.push(err.message, 'error')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section>
    <div class="page-head">
      <h1>今天逛点什么</h1>
      <p>买家安利 + 为你推荐，边逛边买。</p>
    </div>

    <div v-if="error" class="notice">
      {{ error }} <button class="link" type="button" @click="load">重试</button>
    </div>

    <div v-if="loading" class="empty">正在加载你的首页…</div>

    <template v-else>
      <RouterLink v-if="hero" class="hero" :to="{ name: 'post', params: { postId: hero.post_id } }">
        <div class="cover">
          <img :src="heroCover" :alt="hero.title" />
          <span :class="['badge', heroIsVideo ? 'live' : '']">
            {{ heroIsVideo ? `视频 ${heroDuration}` : '买家安利' }}
          </span>
        </div>
        <div class="hero-text">
          <span class="hero-eyebrow">今日主推 · 买家安利</span>
          <h2>{{ hero.title }}</h2>
          <p>{{ hero.body }}</p>
          <div class="meta">
            <span>{{ hero.author_name }}</span>
            <span class="dot" />
            <span>♡ {{ hero.likes }}</span>
            <span class="dot" />
            <span v-if="hero.product">{{ hero.product.title }} ¥{{ hero.product.price.toFixed(0) }}</span>
          </div>
          <div style="margin-top: auto">
            <span class="btn">看同款</span>
          </div>
        </div>
      </RouterLink>

      <section class="section">
        <div class="section-head">
          <h2>为你推荐</h2>
          <span>综合行为、搜索与停留时长</span>
        </div>
        <div v-if="feed.items.length" class="grid">
          <ProductCard v-for="item in feed.items" :key="item.item_id" :item="item" />
        </div>
        <div v-else class="empty">暂时没有推荐，先去逛逛吧</div>
      </section>

      <section v-if="freshPosts.length" class="section">
        <div class="section-head">
          <h2>更多安利</h2>
          <RouterLink to="/discover" class="link">去发现 →</RouterLink>
        </div>
        <div class="masonry">
          <PostCard v-for="post in freshPosts" :key="post.post_id" :post="post" />
        </div>
      </section>
    </template>
  </section>
</template>
