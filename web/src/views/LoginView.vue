<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { useSessionStore, useToastStore } from '../stores'

const session = useSessionStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()

const mode = ref('phone')
const error = ref('')
const notice = ref('')
const busy = ref(false)
const countdown = ref(0)
const loading = computed(() => busy.value || session.loading)

const form = reactive({
  phone: '',
  code: '',
  username: '',
  password: '',
  confirm: '',
  provider: '',
  bindToken: '',
  nickname: ''
})

function switchMode(next) {
  mode.value = next
  error.value = ''
  notice.value = ''
}

function tick() {
  if (countdown.value <= 0) return
  countdown.value -= 1
  setTimeout(tick, 1000)
}

async function sendCode(purpose) {
  if (!/^1[3-9]\d{9}$/.test(form.phone)) {
    error.value = '请输入 11 位手机号'
    return
  }
  try {
    const result = await api.sendSmsCode(form.phone, purpose)
    notice.value = result.dev_code
      ? `演示模式：验证码是 ${result.dev_code}（5 分钟内有效）`
      : '验证码已发送，请留意短信'
    countdown.value = 60
    tick()
  } catch (err) {
    error.value = err.message
  }
}

async function submit() {
  error.value = ''
  busy.value = true
  try {
    if (mode.value === 'password') {
      await session.login(form.username, form.password)
    } else if (mode.value === 'phone') {
      const result = await api.loginPhone(form.phone, form.code)
      session.applyAuth(result)
    } else if (mode.value === 'register') {
      if (form.password.length < 6) throw new Error('密码至少 6 位')
      if (form.password !== form.confirm) throw new Error('两次输入的密码不一致')
      const result = await api.registerPhone(form.phone, form.code, form.username, form.password)
      session.applyAuth(result)
      toast.push('注册成功，已自动登录')
    } else if (mode.value === 'bind') {
      const result = await api.bindPhone(form.bindToken, form.phone, form.code, form.username || null)
      session.applyAuth(result)
      toast.push('手机号绑定成功')
    }
    router.push(route.query.redirect || '/')
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function oauth(provider) {
  error.value = ''
  try {
    const result = await api.oauthLogin(provider)
    form.provider = result.provider
    form.bindToken = result.bind_token
    form.nickname = result.nickname
    mode.value = 'bind'
    notice.value = `已获取${provider === 'wechat' ? '微信' : 'QQ'}授权（演示），绑定手机号后即可使用`
  } catch (err) {
    error.value = err.message
  }
}

onMounted(() => {
  if (session.loggedIn) router.replace('/')
})
</script>

<template>
  <div class="login-shell">
    <div class="login-card">
      <h1>种草集</h1>
      <p>手机号注册登录，也可以使用微信 / QQ 登录。</p>

      <div class="login-tabs">
        <button type="button" :class="mode === 'phone' ? 'active' : ''" @click="switchMode('phone')">验证码登录</button>
        <button type="button" :class="mode === 'password' ? 'active' : ''" @click="switchMode('password')">密码登录</button>
        <button type="button" :class="mode === 'register' ? 'active' : ''" @click="switchMode('register')">注册</button>
      </div>

      <div v-if="notice" class="notice" style="margin-bottom: 12px">{{ notice }}</div>

      <form @submit.prevent="submit">
        <template v-if="mode !== 'password'">
          <div class="field">
            <label>手机号</label>
            <input v-model="form.phone" maxlength="11" inputmode="numeric" placeholder="11 位手机号" />
          </div>
          <div class="field">
            <label>验证码</label>
            <div style="display: flex; gap: 8px">
              <input v-model="form.code" maxlength="6" inputmode="numeric" placeholder="6 位验证码" style="flex: 1" />
              <button class="btn ghost small" type="button" :disabled="countdown > 0"
                      @click="sendCode(mode === 'register' ? 'register' : mode === 'bind' ? 'bind' : 'login')">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </button>
            </div>
          </div>
        </template>

        <template v-if="mode === 'register'">
          <div class="field">
            <label>账号名称</label>
            <input v-model="form.username" placeholder="3-20 位字母数字下划线" />
          </div>
          <div class="field">
            <label>密码</label>
            <input v-model="form.password" type="password" placeholder="至少 6 位" />
          </div>
          <div class="field">
            <label>确认密码</label>
            <input v-model="form.confirm" type="password" placeholder="再输一次" />
          </div>
        </template>

        <template v-if="mode === 'bind'">
          <div class="field">
            <label>账号名称（可选）</label>
            <input v-model="form.username" placeholder="不填会自动生成" />
          </div>
        </template>

        <template v-if="mode === 'password'">
          <div class="field">
            <label>账号</label>
            <input v-model="form.username" autocomplete="username" placeholder="demo / admin" />
          </div>
          <div class="field">
            <label>密码</label>
            <input v-model="form.password" type="password" autocomplete="current-password" placeholder="demo1234" />
          </div>
        </template>

        <p v-if="error" class="error">{{ error }}</p>

        <button class="btn" type="submit" :disabled="loading" style="width: 100%">
          {{ loading ? '请稍候…'
            : mode === 'register' ? '注册并登录'
            : mode === 'bind' ? '绑定手机号并登录'
            : '登录' }}
        </button>
      </form>

      <div v-if="mode !== 'bind'" style="margin-top: 16px">
        <div class="meta" style="margin-bottom: 8px">第三方登录（演示模式，需绑定手机号）</div>
        <div style="display: flex; gap: 10px">
          <button class="btn ghost small" type="button" style="flex: 1" @click="oauth('wechat')">微信登录</button>
          <button class="btn ghost small" type="button" style="flex: 1" @click="oauth('qq')">QQ 登录</button>
        </div>
      </div>

      <p style="margin-top: 16px; font-size: 12.5px" class="meta">
        演示账号 demo / admin，密码 demo1234。短信与微信/QQ 授权为演示模式：验证码会直接显示在这里，
        换成真实短信服务和开放平台凭据后即可真实发送。
      </p>
    </div>
  </div>
</template>
