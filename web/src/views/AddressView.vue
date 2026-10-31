<script setup>
import { ref } from 'vue'
import { useShopStore } from '../stores/shop'
import { useToastStore } from '../stores'

const shop = useShopStore()
const toast = useToastStore()

const selected = ref([])
const form = ref({ name: '', phone: '', region: '', detail: '', is_default: false })
const editing = ref(false)

function toggle(id) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((row) => row !== id)
    : [...selected.value, id]
}

function removeSelected() {
  if (!selected.value.length) {
    toast.push('先勾选要删除的地址', 'error')
    return
  }
  selected.value.forEach((id) => shop.removeAddress(id))
  selected.value = []
  toast.push('已删除所选地址')
}

function save() {
  if (!form.value.name || !form.value.phone || !form.value.region || !form.value.detail) {
    toast.push('姓名、电话、地区、详细地址都要填', 'error')
    return
  }
  shop.addAddress({ ...form.value })
  form.value = { name: '', phone: '', region: '', detail: '', is_default: false }
  editing.value = false
  toast.push('地址已保存')
}
</script>

<template>
  <section>
    <div class="page-head"><h1>收货地址</h1><p>可以新增、删除，也可以设置默认地址。</p></div>

    <div class="section-card">
      <div class="section-head" style="margin-bottom: 12px">
        <h2>我的地址（{{ shop.addresses.length }}）</h2>
        <button class="btn ghost small" type="button" @click="editing = !editing">
          {{ editing ? '收起' : '新增地址' }}
        </button>
      </div>

      <div v-if="!shop.addresses.length" class="empty" style="padding: 24px">还没有地址</div>

      <div class="row-list">
        <label v-for="row in shop.addresses" :key="row.id" class="row-item">
          <input type="checkbox" :checked="selected.includes(row.id)" @change="toggle(row.id)" />
          <div class="grow">
            <div style="font-weight: 700">{{ row.name }} · {{ row.phone }}</div>
            <div class="meta">{{ row.region }} {{ row.detail }}</div>
          </div>
          <span v-if="row.is_default" class="status-pill">默认</span>
          <button v-else class="link" type="button" @click.prevent="shop.setDefaultAddress(row.id)">设为默认</button>
        </label>
      </div>

      <div v-if="shop.addresses.length" style="margin-top: 14px">
        <button class="btn ghost small" type="button" @click="removeSelected">删除所选（{{ selected.length }}）</button>
      </div>
    </div>

    <div v-if="editing" class="section-card">
      <div class="section-head" style="margin-bottom: 12px"><h2>新增地址</h2></div>
      <div class="form-grid">
        <div class="field"><label>收货人</label><input v-model="form.name" placeholder="姓名" /></div>
        <div class="field"><label>手机号</label><input v-model="form.phone" placeholder="11 位手机号" /></div>
        <div class="field" style="grid-column: span 2"><label>所在地区</label><input v-model="form.region" placeholder="省 市 区" /></div>
        <div class="field" style="grid-column: span 2"><label>详细地址</label><input v-model="form.detail" placeholder="街道、门牌号" /></div>
      </div>
      <label class="check-line" style="margin: 10px 0">
        <input v-model="form.is_default" type="checkbox" /> 设为默认地址
      </label>
      <button class="btn" type="button" @click="save">保存地址</button>
    </div>
  </section>
</template>
