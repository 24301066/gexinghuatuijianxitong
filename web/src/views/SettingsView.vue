<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore, useToastStore } from '../stores'

const router = useRouter()
const session = useSessionStore()
const toast = useToastStore()
const settings = ref({ notify: true, sound: false, autoPlay: true, saveTraffic: false })
const showSecurity = ref(false)

function logout() {
  session.logout()
  toast.push('已退出登录')
  router.push({ name: 'login' })
}

function switchAccount() {
  session.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <section>
    <div class="page-head"><h1>设置</h1><p>账号与安全、功能偏好和版本信息。</p></div>

    <div class="section-card">
      <div class="section-head" style="margin-bottom: 8px"><h2>功能设置</h2></div>
      <div class="menu-list">
        <label class="menu-row">
          <span>消息通知</span>
          <span class="arrow"><input v-model="settings.notify" type="checkbox" /></span>
        </label>
        <label class="menu-row">
          <span>提示音</span>
          <span class="arrow"><input v-model="settings.sound" type="checkbox" /></span>
        </label>
        <label class="menu-row">
          <span>视频自动播放</span>
          <span class="arrow"><input v-model="settings.autoPlay" type="checkbox" /></span>
        </label>
        <label class="menu-row">
          <span>省流量模式</span>
          <span class="arrow"><input v-model="settings.saveTraffic" type="checkbox" /></span>
        </label>
      </div>
    </div>

    <div class="section-card">
      <div class="section-head" style="margin-bottom: 8px"><h2>账号与安全</h2></div>
      <div class="menu-list">
        <button class="menu-row" type="button" @click="showSecurity = !showSecurity">
          <span>账号与安全</span><span class="arrow">›</span>
        </button>
        <div v-if="showSecurity" class="section-card" style="margin: 6px 0 10px; box-shadow: none">
          <div class="menu-row" style="cursor: default">
            <span>当前账号</span><span class="arrow">{{ session.user?.username }}</span>
          </div>
          <div class="menu-row" style="cursor: default">
            <span>登录方式</span><span class="arrow">账号密码</span>
          </div>
          <div class="menu-row" style="cursor: default">
            <span>数据存储</span><span class="arrow">本机 SQLite</span>
          </div>
        </div>
        <button class="menu-row" type="button" @click="switchAccount">
          <span>切换账号</span><span class="arrow">›</span>
        </button>
        <button class="menu-row" type="button" @click="logout">
          <span class="error">退出登录</span><span class="arrow">›</span>
        </button>
      </div>
    </div>
  </section>
</template>
