<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { useToastStore } from '../stores'
import PostCard from '../components/PostCard.vue'

const toast = useToastStore()
const posts = ref([])
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const error = ref('')
const size = 8

async function loadMore() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await api.posts({ page: page.value, size })
    const known = new Set(posts.value.map((post) => post.post_id))
    posts.value = [...posts.value, ...data.posts.filter((post) => !known.has(post.post_id))]
    total.value = data.total
    page.value += 1
  } catch (err) {
    error.value = err.message
    toast.push(err.message, 'error')
  } finally {
    loading.value = false
  }
}

onMounted(loadMore)
</script>

<template>
  <section>
    <div class="page-head">
      <h1>发现安利</h1>
      <p>买家们正在晒的好物，点进去看同款。</p>
    </div>

    <div v-if="error" class="notice">{{ error }}</div>

    <div v-if="posts.length" class="masonry">
      <PostCard v-for="post in posts" :key="post.post_id" :post="post" />
    </div>
    <div v-else-if="!loading" class="empty">还没有安利内容</div>

    <div style="text-align: center; margin-top: 22px">
      <button class="btn ghost" type="button" :disabled="loading || posts.length >= total" @click="loadMore">
        {{ posts.length >= total ? `已经到底啦（${total} 条）` : loading ? '加载中…' : '加载更多' }}
      </button>
    </div>
  </section>
</template>
