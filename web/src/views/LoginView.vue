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
  <div class="login-shell">
    <div class="login-card">
      <h1>种草集</h1>
      <p>看买家安利，顺手把喜欢的买回家。<br />演示账号 <code>demo</code> / <code>admin</code>，密码都是 <code>demo1234</code>。</p>

      <form @submit.prevent="submit">
        <div class="field">
          <label for="username">用户名</label>
          <input id="username" v-model="username" autocomplete="username" required />
        </div>
        <div class="field">
          <label for="password">密码</label>
          <input id="password" v-model="password" type="password"
                 autocomplete="current-password" required />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button class="btn" type="submit" :disabled="busy" style="width: 100%">
          {{ busy ? '登录中…' : '登录' }}
        </button>
      </form>

      <p style="margin-top: 18px; font-size: 13px">
        快速填写：
        <button class="link" type="button" @click="fill('demo')">demo</button>
        ·
        <button class="link" type="button" @click="fill('admin')">admin</button>
      </p>
    </div>
  </div>
</template>
