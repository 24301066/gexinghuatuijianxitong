<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore, useToastStore } from './stores'

const session = useSessionStore()
const toast = useToastStore()
const router = useRouter()
const route = useRoute()
const keyword = ref(route.query.q || '')

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

      <nav class="nav">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/discover">发现</RouterLink>
        <RouterLink to="/search">搜索</RouterLink>
        <RouterLink to="/me">我的</RouterLink>
        <RouterLink to="/about">关于</RouterLink>
      </nav>

      <div class="search-box">
        <span aria-hidden="true">🔍</span>
        <input v-model="keyword" placeholder="搜商品、安利、类目…" @keyup.enter="submitSearch" />
        <span class="hint">回车</span>
      </div>

      <template v-if="session.loggedIn">
        <span class="who">
          <span class="avatar">{{ (session.user?.username || 'U').slice(0, 1).toUpperCase() }}</span>
          {{ session.user?.username }}
          <button class="link" type="button" @click="logout">退出</button>
        </span>
      </template>
      <RouterLink v-else class="btn small" to="/login">登录</RouterLink>
    </header>

    <main class="content">
      <RouterView />
    </main>

    <nav class="bottom-nav">
      <RouterLink to="/">首页</RouterLink>
      <RouterLink to="/discover">发现</RouterLink>
      <RouterLink to="/search">搜索</RouterLink>
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
