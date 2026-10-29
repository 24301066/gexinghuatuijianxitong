<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore, useToastStore } from './stores'

const session = useSessionStore()
const toast = useToastStore()
const router = useRouter()

const who = computed(() => session.user?.username || '')

function logout() {
  session.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="app">
    <header class="topbar">
      <RouterLink class="brand" to="/">个性化推荐系统</RouterLink>
      <nav class="nav">
        <RouterLink to="/">猜你喜欢</RouterLink>
        <RouterLink to="/about">关于</RouterLink>
        <template v-if="session.loggedIn">
          <span class="who">{{ who }}</span>
          <button class="link" type="button" @click="logout">退出</button>
        </template>
        <RouterLink v-else to="/login">登录</RouterLink>
      </nav>
    </header>

    <main class="content">
      <RouterView />
    </main>

    <div class="toasts">
      <div v-for="item in toast.messages" :key="item.id" :class="['toast', item.kind]">
        <span>{{ item.text }}</span>
        <button class="link" type="button" @click="toast.dismiss(item.id)">关闭</button>
      </div>
    </div>
  </div>
</template>
