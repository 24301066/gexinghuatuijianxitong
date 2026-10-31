<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { mediaUrl } from '../api'
import { useShopStore } from '../stores/shop'
import { useToastStore } from '../stores'

const shop = useShopStore()
const toast = useToastStore()
const router = useRouter()

const items = computed(() => shop.cartChecked)
const addressId = ref(shop.defaultAddress?.id || '')
const payment = ref('微信支付')
const payments = ['微信支付', '支付宝', '银行卡', '货到付款']
const total = computed(() => items.value.reduce((sum, row) => sum + row.price * row.qty, 0))

async function submit() {
  if (!items.value.length) {
    toast.push('没有可结算的商品', 'error')
    return
  }
  const address = shop.addresses.find((row) => row.id === addressId.value) || null
  if (!address) {
    toast.push('请先选择收货地址', 'error')
    return
  }
  try {
    await shop.createOrder({ addressId: address.id, payment: payment.value })
    toast.push('订单已创建，请完成支付')
    router.push({ name: 'orders', query: { status: 'pending_payment' } })
  } catch (err) {
    toast.push(err.message, 'error')
  }
}
</script>

<template>
  <section>
    <div class="page-head"><h1>确认订单</h1><p>选择地址与支付方式后提交。</p></div>

    <div v-if="!items.length" class="empty">
      没有可结算的商品，<RouterLink class="link" to="/cart">回购物车</RouterLink>
    </div>

    <template v-else>
      <div class="section-card">
        <div class="section-head" style="margin-bottom: 10px">
          <h2>收货地址</h2>
          <RouterLink class="link" to="/me/address">管理地址 →</RouterLink>
        </div>
        <div v-if="!shop.addresses.length" class="empty" style="padding: 20px">
          还没有地址，<RouterLink class="link" to="/me/address">去新增</RouterLink>
        </div>
        <div v-else class="row-list">
          <label v-for="row in shop.addresses" :key="row.id" class="row-item" style="cursor: pointer">
            <input v-model="addressId" type="radio" :value="row.id" />
            <div class="grow">
              <div style="font-weight: 700">{{ row.name }} · {{ row.phone }}</div>
              <div class="meta">{{ row.region }} {{ row.detail }}</div>
            </div>
            <span v-if="row.is_default" class="status-pill">默认</span>
          </label>
        </div>
      </div>

      <div class="section-card">
        <div class="section-head" style="margin-bottom: 10px"><h2>支付方式</h2></div>
        <div class="chip-row">
          <button v-for="method in payments" :key="method" type="button"
                  :class="['chip', payment === method ? 'chip-active' : '']"
                  @click="payment = method">
            {{ method }}
          </button>
        </div>
      </div>

      <div class="section-card">
        <div class="section-head" style="margin-bottom: 10px"><h2>商品清单</h2></div>
        <div class="row-list">
          <div v-for="row in items" :key="row.item_id" class="row-item">
            <img :src="mediaUrl(row.cover_url)" :alt="row.title" class="cart-thumb" />
            <div class="grow">
              <div style="font-weight: 700">{{ row.title }}</div>
              <div class="meta">¥{{ row.price.toFixed(0) }} × {{ row.qty }}</div>
            </div>
            <b class="price">¥{{ (row.price * row.qty).toFixed(2) }}</b>
          </div>
        </div>
        <div style="display: flex; align-items: center; margin-top: 16px; gap: 14px">
          <span class="meta">共 {{ items.length }} 种商品</span>
          <b class="price" style="margin-left: auto; font-size: 22px">¥{{ total.toFixed(2) }}</b>
          <button class="btn" type="button" @click="submit">提交订单</button>
        </div>
      </div>
    </template>
  </section>
</template>
