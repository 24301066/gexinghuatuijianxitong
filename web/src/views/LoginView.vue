<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore, useToastStore } from '../stores'

const session = useSessionStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()

const mode = ref('login')
const username = ref('demo')
const password = ref('demo1234')
const confirm = ref('')
const error = ref('')
const busy = computed(() => session.loading)

function switchMode(next) {
  mode.value = next
  error.value = ''
  confirm.value = ''
  if (next === 'login') {
    username.value = 'demo'
    password.value = 'demo1234'
  } else {
    username.value = ''
    password.value = ''
  }
}

async function submit() {
  error.value = ''
  const name = username.value.trim()
  try {
    if (mode.value === 'login') {
      await session.login(name, password.value)
    } else {
      if (name.length < 3) {
        error.value = '用户名至少 3 个字符'
        return
      }
      if (password.value.length < 6) {
        error.value = '密码至少 6 位'
        return
      }
      if (password.value !== confirm.value) {
        error.value = '两次输入的密码不一致'
        return
      }
      await session.register(name, password.value)
      toast.push('注册成功，已自动登录')
    }
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
      <p>看买家安利，顺手把喜欢的买回家。</p>

      <div class="login-tabs">
        <button type="button" :class="mode === 'login' ? 'active' : ''" @click="switchMode('login')">登录</button>
        <button type="button" :class="mode === 'register' ? 'active' : ''" @click="switchMode('register')">注册</button>
      </div>

      <form @submit.prevent="submit">
        <div class="field">
          <label for="username">用户名</label>
          <input id="username" v-model="username" autocomplete="username"
                 :placeholder="mode === 'register' ? '3-20 位字母数字下划线' : ''" required />
        </div>
        <div class="field">
          <label for="password">密码</label>
          <input id="password" v-model="password" type="password"
                 :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
                 :placeholder="mode === 'register' ? '至少 6 位' : ''" required />
        </div>
        <div v-if="mode === 'register'" class="field">
          <label for="confirm">确认密码</label>
          <input id="confirm" v-model="confirm" type="password" autocomplete="new-password"
                 placeholder="再输一次" required />
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <button class="btn" type="submit" :disabled="busy" style="width: 100%">
          {{ busy ? '请稍候…' : mode === 'login' ? '登录' : '注册并登录' }}
        </button>
      </form>

      <p style="margin-top: 18px; font-size: 13px">
        <template v-if="mode === 'login'">
          演示账号：
          <button class="link" type="button" @click="fill('demo')">demo</button>
          ·
          <button class="link" type="button" @click="fill('admin')">admin</button>
          （密码都是 demo1234）
        </template>
        <template v-else>
          注册后会自动登录；用户名只支持字母、数字和下划线。
        </template>
      </p>
    </div>
  </div>
</template>
