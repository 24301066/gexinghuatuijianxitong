<script setup>
import { computed, reactive, ref } from 'vue'
import { useShopStore } from '../stores/shop'
import { useToastStore } from '../stores'
import { regions, citiesOf, districtsOf } from '../data/regions'

const shop = useShopStore()
const toast = useToastStore()

const selected = ref([])
const editing = ref(false)
const form = reactive({
  name: '',
  phone: '',
  province: '',
  city: '',
  district: '',
  detail: '',
  is_default: false
})

const cityList = computed(() => citiesOf(form.province))
const districtList = computed(() => districtsOf(form.province, form.city))

function onProvince() {
  form.city = ''
  form.district = ''
}

function onCity() {
  form.district = ''
}

function toggle(id) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((row) => row !== id)
    : [...selected.value, id]
}

async function removeSelected() {
  if (!selected.value.length) {
    toast.push('先勾选要删除的地址', 'error')
    return
  }
  for (const id of selected.value) { await shop.removeAddress(id) }
  selected.value = []
  toast.push('已删除所选地址')
}

async function save() {
  if (!form.name || !form.phone || !form.province || !form.city || !form.district || !form.detail) {
    toast.push('姓名、电话、省市区和详细地址都要填', 'error')
    return
  }
  await shop.addAddress({
    name: form.name,
    phone: form.phone,
    region: `${form.province} ${form.city} ${form.district}`,
    detail: form.detail,
    is_default: form.is_default
  })
  form.name = ''
  form.phone = ''
  form.province = ''
  form.city = ''
  form.district = ''
  form.detail = ''
  form.is_default = false
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
      </div>

      <div class="field" style="margin-bottom: 12px">
        <label>所在地区（省 / 市 / 区）</label>
        <div class="region-grid">
          <select v-model="form.province" class="select" @change="onProvince">
            <option value="">选择省份</option>
            <option v-for="row in regions" :key="row.name" :value="row.name">{{ row.name }}</option>
          </select>
          <select v-model="form.city" class="select" :disabled="!form.province" @change="onCity">
            <option value="">选择城市</option>
            <option v-for="row in cityList" :key="row.name" :value="row.name">{{ row.name }}</option>
          </select>
          <select v-model="form.district" class="select" :disabled="!form.city">
            <option value="">选择区/县</option>
            <option v-for="row in districtList" :key="row" :value="row">{{ row }}</option>
          </select>
        </div>
        <div v-if="form.province" class="meta" style="margin-top: 6px">
          已选：{{ form.province }} {{ form.city }} {{ form.district }}
        </div>
      </div>

      <div class="field" style="margin-bottom: 12px">
        <label>详细地址</label>
        <input v-model="form.detail" placeholder="街道、门牌号、楼栋" />
      </div>

      <label class="check-line" style="margin: 10px 0">
        <input v-model="form.is_default" type="checkbox" /> 设为默认地址
      </label>
      <button class="btn" type="button" @click="save">保存地址</button>
    </div>
  </section>
</template>
