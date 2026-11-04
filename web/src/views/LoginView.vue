<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { useSessionStore, useToastStore } from '../stores'

const session = useSessionStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()

const mode = ref('password')
const error = ref('')
const notice = ref('')
const busy = ref(false)
const countdown = ref(0)

const form = reactive({
  username: 'demo',
  password: 'demo1234',
  phone: '',
  code: '',
  regUsername: '',
  regPassword: '',
  regConfirm: ''
})

const bindModal = ref(null)
const bindForm = reactive({ phone: '', code: '', username: '' })
const afterRegister = ref(false)

const loading = computed(() => busy.value || session.loading)

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

async function sendCode(phone, purpose) {
  if (!/^1[3-9]\d{9}$/.test(phone)) {
    error.value = '请输入 11 位手机号'
    return
  }
  try {
    const result = await api.sendSmsCode(phone, purpose)
    notice.value = result.dev_code
      ? `演示模式：验证码是 ${result.dev_code}（5 分钟内有效）`
      : '验证码已发送'
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
    } else if (mode.value === 'code') {
      session.applyAuth(await api.loginPhone(form.phone, form.code))
    } else {
      if (form.regPassword.length < 6) throw new Error('密码至少 6 位')
      if (form.regPassword !== form.regConfirm) throw new Error('两次密码不一致')
      session.applyAuth(await api.registerPhone(form.phone, form.code,
                                                form.regUsername, form.regPassword))
      toast.push('注册成功')
      afterRegister.value = true
      return
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
    if (result.registered && result.token) {
      session.applyAuth({ token: result.token, user: result.user })
      toast.push(`已用${provider === 'wechat' ? '微信' : 'QQ'}登录`)
      router.push(route.query.redirect || '/')
      return
    }
    bindForm.phone = ''
    bindForm.code = ''
    bindForm.username = ''
    bindModal.value = { provider, openId: result.open_id, bindToken: result.bind_token }
  } catch (err) {
    error.value = err.message
  }
}

async function submitBind() {
  if (!bindModal.value) return
  busy.value = true
  error.value = ''
  try {
    session.applyAuth(await api.bindPhone(bindModal.value.bindToken, bindForm.phone,
                                          bindForm.code, bindForm.username || null))
    toast.push('手机号绑定成功')
    bindModal.value = null
    router.push(route.query.redirect || '/')
  } catch (err) {
    error.value = err.message
  } finally {
    busy.value = false
  }
}

async function bindSocial(provider) {
  try {
    const result = await api.oauthLogin(provider)
    await api.bindSocial(provider, result.open_id)
    toast.push(`已绑定${provider === 'wechat' ? '微信' : 'QQ'}`)
    afterRegister.value = false
    router.push(route.query.redirect || '/')
  } catch (err) {
    toast.push(err.message, 'error')
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
      <p v-if="mode === 'password'">登录后继续逛安利、看推荐。</p>
      <p v-else-if="mode === 'code'">用手机号验证码快速登录。</p>
      <p v-else>注册新账号，几秒钟就好。</p>

      <div v-if="notice" class="notice" style="margin-bottom: 12px">{{ notice }}</div>

      <form @submit.prevent="submit">
        <template v-if="mode === 'password'">
          <div class="field"><label>账号</label>
            <input v-model="form.username" autocomplete="username" placeholder="demo / admin" />
          </div>
          <div class="field"><label>密码</label>
            <input v-model="form.password" type="password" autocomplete="current-password" placeholder="demo1234" />
          </div>
          <div class="login-links">
            <button class="link red" type="button" @click="switchMode('code')">忘记密码</button>
            <span class="sep">｜</span>
            <button class="link red" type="button" @click="switchMode('code')">使用验证码登录</button>
          </div>
        </template>

        <template v-else-if="mode === 'code'">
          <div class="field"><label>手机号</label>
            <input v-model="form.phone" maxlength="11" inputmode="numeric" placeholder="11 位手机号" />
          </div>
          <div class="field"><label>验证码</label>
            <div class="code-row">
              <input v-model="form.code" maxlength="6" inputmode="numeric" placeholder="6 位验证码" />
              <button class="btn ghost small" type="button" :disabled="countdown > 0"
                      @click="sendCode(form.phone, 'login')">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </button>
            </div>
          </div>
          <button class="link red" type="button" style="margin: 4px 0 12px"
                  @click="switchMode('password')">← 用密码登录</button>
        </template>

        <template v-else>
          <div class="field"><label>手机号</label>
            <input v-model="form.phone" maxlength="11" inputmode="numeric" placeholder="11 位手机号" />
          </div>
          <div class="field"><label>验证码</label>
            <div class="code-row">
              <input v-model="form.code" maxlength="6" inputmode="numeric" placeholder="6 位验证码" />
              <button class="btn ghost small" type="button" :disabled="countdown > 0"
                      @click="sendCode(form.phone, 'register')">
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </button>
            </div>
          </div>
          <div class="field"><label>账号名称</label>
            <input v-model="form.regUsername" placeholder="3-20 位字母数字下划线" />
          </div>
          <div class="field"><label>密码</label>
            <input v-model="form.regPassword" type="password" placeholder="至少 6 位" />
          </div>
          <div class="field"><label>确认密码</label>
            <input v-model="form.regConfirm" type="password" placeholder="再输一次" />
          </div>
          <button class="link red" type="button" style="margin: 4px 0 12px"
                  @click="switchMode('password')">← 已有账号，去登录</button>
        </template>

        <p v-if="error" class="error">{{ error }}</p>

        <button class="btn" type="submit" :disabled="loading" style="width: 100%">
          {{ loading ? '请稍候…'
            : mode === 'password' ? '登录'
            : mode === 'code' ? '验证码登录'
            : '注册并登录' }}
        </button>
      </form>

      <div v-if="mode === 'password'" style="margin-top: 16px">
        <div class="meta" style="margin-bottom: 8px">第三方登录（演示授权）</div>
        <div style="display: flex; gap: 10px">
          <button class="btn ghost small" type="button" style="flex: 1" @click="oauth('wechat')">微信登录</button>
          <button class="btn ghost small" type="button" style="flex: 1" @click="oauth('qq')">QQ 登录</button>
        </div>
      </div>

      <div v-if="mode === 'password'" class="login-links" style="margin-top: 14px">
        <button class="link red" type="button" @click="switchMode('register')">还没有账号，点击注册</button>
      </div>

      <p class="meta" style="margin-top: 14px; font-size: 12.5px">
        演示账号 demo / admin，密码 demo1234。短信与微信/QQ 授权为演示模式。
      </p>
    </div>

    <div v-if="bindModal" class="modal-mask">
      <div class="modal">
        <h3>绑定手机号</h3>
        <p class="meta">
          首次使用{{ bindModal.provider === 'wechat' ? '微信' : 'QQ' }}登录，绑定手机号后下次不再提示。
        </p>
        <div class="field"><label>手机号</label>
          <input v-model="bindForm.phone" maxlength="11" inputmode="numeric" placeholder="11 位手机号" />
        </div>
        <div class="field"><label>验证码</label>
          <div class="code-row">
            <input v-model="bindForm.code" maxlength="6" inputmode="numeric" placeholder="6 位验证码" />
            <button class="btn ghost small" type="button" :disabled="countdown > 0"
                    @click="sendCode(bindForm.phone, 'bind')">
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </button>
          </div>
        </div>
        <div class="field"><label>账号名称（可选）</label>
          <input v-model="bindForm.username" placeholder="不填自动生成" />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <div style="display: flex; gap: 10px; margin-top: 8px">
          <button class="btn ghost small" type="button" style="flex: 1"
                  @click="bindModal = null">取消</button>
          <button class="btn small" type="button" style="flex: 1" @click="submitBind">绑定并登录</button>
        </div>
      </div>
    </div>

    <div v-if="afterRegister" class="modal-mask">
      <div class="modal">
        <h3>绑定社交账号</h3>
        <p class="meta">绑定后可用微信 / QQ 直接登录（一个手机号只能绑定一个社交账号）。</p>
        <div style="display: flex; gap: 10px; margin-top: 10px">
          <button class="btn small" type="button" style="flex: 1" @click="bindSocial('wechat')">绑定微信</button>
          <button class="btn small" type="button" style="flex: 1" @click="bindSocial('qq')">绑定 QQ</button>
        </div>
        <button class="link" type="button" style="margin-top: 14px"
                @click="afterRegister = false">稍后再说</button>
      </div>
    </div>
  </div>
</template>
