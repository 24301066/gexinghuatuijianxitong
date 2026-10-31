<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore, useToastStore } from './stores'
import { useShopStore } from './stores/shop'

const session = useSessionStore()
const toast = useToastStore()
const shop = useShopStore()
shop.startAutoSave()
if (session.loggedIn) { shop.init().catch(() => {}) }

const router = useRouter()
const route = useRoute()
const keyword = ref('')

const isLogin = computed(() => route.name === 'login')
const showBack = computed(() => !['home', 'discover', 'messages', 'me', 'login', 'about'].includes(String(route.name)))

watch(
  () => route.name,
  (name) => {
    // 搜索完跳走以后搜索框恢复初始状态
    if (name !== 'search') keyword.value = ''
  },
  { immediate: true }
)

watch(
  () => route.query.q,
  (value) => {
    if (route.name === 'search') keyword.value = String(value || '')
  },
  { immediate: true }
)

function submitSearch() {
  const query = keyword.value.trim()
  if (!query) return
  router.push({ name: 'search', query: { q: query } })
}

function logout() {
  session.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="app">
    <header class="topbar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">种</span>
        <span>种草集</span>
      </RouterLink>

      <nav v-if="!isLogin" class="nav">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/discover">发现</RouterLink>
        <RouterLink to="/messages" class="nav-msg">
          消息
          <span v-if="shop.unreadCount" class="dot-badge">{{ shop.unreadCount }}</span>
        </RouterLink>
        <RouterLink to="/me">我的</RouterLink>
      </nav>

      <div v-if="!isLogin" class="search-box">
        <span aria-hidden="true">🔍</span>
        <input v-model="keyword" placeholder="搜商品、安利、类目…" @keyup.enter="submitSearch" />
        <button class="link" type="button" @click="submitSearch">搜索</button>
      </div>

      <RouterLink v-if="!isLogin" to="/cart" class="cart-pill" :title="`购物车 ${shop.cartCount} 件`">
        🛒<span v-if="shop.cartCount" class="count">{{ shop.cartCount }}</span>
      </RouterLink>

      <template v-if="session.loggedIn && !isLogin">
        <RouterLink class="who" to="/me">
          <span class="avatar">{{ (session.user?.username || 'U').slice(0, 1).toUpperCase() }}</span>
          {{ session.user?.username }}
        </RouterLink>
        <button class="link" type="button" @click="logout">退出</button>
      </template>
      <RouterLink v-else-if="!isLogin" class="btn small" to="/login">登录</RouterLink>
    </header>

    <main class="content">
      <button v-if="showBack" class="link back-link" type="button" @click="router.back()">← 返回</button>
      <RouterView />
    </main>

    <nav class="bottom-nav">
      <RouterLink to="/">首页</RouterLink>
      <RouterLink to="/discover">发现</RouterLink>
      <RouterLink to="/messages">消息</RouterLink>
      <RouterLink to="/me">我的</RouterLink>
    </nav>

    <div class="toasts">
      <div v-for="item in toast.messages" :key="item.id" :class="['toast', item.kind]">
        <span>{{ item.text }}</span>
        <button class="link" type="button" @click="toast.dismiss(item.id)">关闭</button>
      </div>
    </div>
  </div>
</template>
