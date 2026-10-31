<script setup>
import { reactive, ref } from 'vue'
import { useShopStore } from '../stores/shop'
import { useToastStore } from '../stores'

const shop = useShopStore()
const toast = useToastStore()

const profile = reactive({ ...shop.profile })
const sizes = reactive({ ...shop.profile.sizes })
const editingSizes = ref(false)

function save() {
  shop.updateProfile({
    nickname: profile.nickname,
    gender: profile.gender,
    birthday: profile.birthday
  })
  toast.push('资料已保存')
}

function saveSizes() {
  shop.updateSizes({ ...sizes })
  editingSizes.value = false
  toast.push('尺码档案已更新')
}
</script>

<template>
  <section>
    <div class="page-head"><h1>个人信息</h1><p>资料、尺码档案和账号数据。</p></div>

    <div class="stat-grid" style="margin-bottom: 18px">
      <div class="stat"><b>{{ shop.profile.level }}</b><span>活跃等级</span></div>
      <div class="stat"><b>{{ shop.profile.spent }}</b><span>消费额度（元）</span></div>
      <div class="stat"><b>{{ shop.profile.active }}</b><span>活跃度</span></div>
      <div class="stat"><b>{{ shop.profile.joined }}</b><span>注册时间</span></div>
    </div>

    <div class="section-card">
      <div class="section-head" style="margin-bottom: 12px"><h2>基本资料</h2></div>
      <div class="form-grid">
        <div class="field"><label>昵称</label><input v-model="profile.nickname" /></div>
        <div class="field">
          <label>性别</label>
          <select v-model="profile.gender" class="select">
            <option>女</option><option>男</option><option>保密</option>
          </select>
        </div>
        <div class="field"><label>生日</label><input v-model="profile.birthday" type="date" /></div>
      </div>
      <button class="btn" type="button" @click="save">保存资料</button>
    </div>

    <div class="section-card">
      <div class="section-head" style="margin-bottom: 12px">
        <h2>我的尺码档案</h2>
        <button class="btn ghost small" type="button" @click="editingSizes = !editingSizes">
          {{ editingSizes ? '收起' : '编辑' }}
        </button>
      </div>
      <div v-if="!editingSizes" class="chip-row">
        <span class="chip-static">身高 {{ sizes.height }} cm</span>
        <span class="chip-static">体重 {{ sizes.weight }} kg</span>
        <span class="chip-static">鞋码 {{ sizes.shoe }}</span>
        <span class="chip-static">上衣 {{ sizes.top }}</span>
        <span class="chip-static">裤装 {{ sizes.bottom }}</span>
      </div>
      <div v-else>
        <div class="form-grid">
          <div class="field"><label>身高（cm）</label><input v-model="sizes.height" /></div>
          <div class="field"><label>体重（kg）</label><input v-model="sizes.weight" /></div>
          <div class="field"><label>鞋码</label><input v-model="sizes.shoe" /></div>
          <div class="field"><label>上衣</label><input v-model="sizes.top" /></div>
          <div class="field"><label>裤装</label><input v-model="sizes.bottom" /></div>
        </div>
        <button class="btn" type="button" @click="saveSizes">保存尺码</button>
      </div>
    </div>
  </section>
</template>
