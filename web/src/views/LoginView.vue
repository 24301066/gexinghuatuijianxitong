<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '../stores'

const session = useSessionStore()
const route = useRoute()
const router = useRouter()

const username = ref('demo')
const password = ref('demo1234')
const error = ref('')

const busy = computed(() => session.loading)

async function submit() {
  error.value = ''
  try {
    await session.login(username.value.trim(), password.value)
    router.push(route.query.redirect || '/')
  } catch (err) {
    error.value = err.message
  }
}

function fill(name) {
  username.value = name
  password.value = 'demo1234'
}

onMounted(() => {
  if (session.loggedIn) router.replace('/')
})
</script>

<template>
  <section class="card narrow">
    <h1>登录</h1>
    <p class="muted">演示账号：<code>demo</code> / <code>admin</code>，密码都是 <code>demo1234</code>。</p>

    <form class="form" @submit.prevent="submit">
      <label>
        用户名
        <input v-model="username" autocomplete="username" required />
      </label>
      <label>
        密码
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="primary" type="submit" :disabled="busy">
        {{ busy ? '登录中…' : '登录' }}
      </button>
    </form>

    <p class="muted">
      快速填写：
      <button class="link" type="button" @click="fill('demo')">demo</button>
      <button class="link" type="button" @click="fill('admin')">admin</button>
    </p>
  </section>
</template>
