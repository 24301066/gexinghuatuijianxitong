<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { mediaUrl } from '../api'
import { useShopStore } from '../stores/shop'
import { useToastStore } from '../stores'

const shop = useShopStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()

const TABS = [
  { key: 'all', label: '全部' },
  { key: 'pending_payment', label: '待支付' },
  { key: 'pending_shipment', label: '待发货' },
  { key: 'pending_receipt', label: '待收货/使用' },
  { key: 'pending_review', label: '评价' },
  { key: 'aftersale', label: '售后' }
]

const STATUS_TEXT = {
  pending_payment: '待支付',
  pending_shipment: '待发货',
  pending_receipt: '运输中',
  pending_review: '待评价',
  completed: '已完成',
  cancelled: '已取消',
  aftersale: '售后中'
}

const active = ref(String(route.query.status || 'all'))
const orders = computed(() => shop.ordersByStatus(active.value))

watch(() => route.query.status, (value) => { active.value = String(value || 'all') })

function pick(key) {
  active.value = key
  router.replace({ name: 'orders', query: key === 'all' ? {} : { status: key } })
}

function shopName(order) {
  const first = order.items?.[0] || {}
  if (first.merchant_name) return first.merchant_name
  const category = first.category || ''
  return category ? `${category}旗舰店` : '种草集自营'
}

async function run(order, action, message) {
  try {
    await shop.orderAction(order.id, action)
    if (message) toast.push(message)
  } catch (err) {
    toast.push(err.message, 'error')
  }
}

const pay = (order) => run(order, 'pay', '支付成功，等待发货')
const cancel = (order) => run(order, 'cancel', '订单已取消')
const receive = (order) => run(order, 'receive', '已确认收货，记得评价')
const aftersale = (order) => run(order, 'aftersale', '已申请售后，客服会联系你')

function goDetail(order) {
  router.push({ name: 'order-detail', params: { id: order.id } })
}

function goLogistics(order) {
  router.push({ name: 'logistics', params: { id: order.id } })
}

onMounted(() => { shop.loadOrders('all') })
</script>

<template>
  <section>
    <div class="page-head"><h1>我的订单</h1><p>支付、物流、售后都可以在这里处理。</p></div>

    <div class="tabs">
      <button v-for="tab in TABS" :key="tab.key" type="button"
              :class="active === tab.key ? 'active' : ''" @click="pick(tab.key)">
        {{ tab.label }}
      </button>
    </div>

    <div v-if="!orders.length" class="empty">这个分类还没有订单</div>

    <div v-for="order in orders" :key="order.id" class="order-card">
      <div class="order-shop">
        <span>{{ shopName(order) }}</span>
        <span class="tag">官方</span>
        <span class="order-status">{{ STATUS_TEXT[order.status] || order.status }}</span>
      </div>

      <div class="order-goods" @click="goDetail(order)">
        <img :src="mediaUrl(order.items[0]?.cover_url)" :alt="order.items[0]?.title" />
        <div class="grow">
          <div class="goods-title">{{ order.items[0]?.title }}</div>
          <div class="meta">{{ order.items[0]?.category }} · 共 {{ order.items.length }} 件</div>
          <div class="meta">实付 ¥{{ Number(order.total).toFixed(2) }}</div>
        </div>
        <div class="goods-price">
          <b>¥{{ Number(order.items[0]?.price || 0).toFixed(2) }}</b>
          <span class="meta">x{{ order.items[0]?.qty || 1 }}</span>
        </div>
      </div>

      <div class="order-actions">
        <button class="link" type="button" @click="goDetail(order)">更多</button>
        <button class="btn ghost small" type="button" @click="goLogistics(order)">查看物流</button>
        <button v-if="order.status === 'pending_payment'" class="btn small" type="button"
                @click="pay(order)">立即支付</button>
        <button v-if="order.status === 'pending_payment'" class="btn ghost small" type="button"
                @click="cancel(order)">取消订单</button>
        <button v-if="order.status === 'pending_receipt'" class="btn small" type="button"
                @click="receive(order)">确认收货</button>
        <button v-if="order.status === 'pending_review'" class="btn small" type="button"
                @click="goDetail(order)">去评价</button>
        <button v-if="order.status === 'completed'" class="btn ghost small" type="button"
                @click="aftersale(order)">申请售后</button>
      </div>
    </div>
  </section>
</template>
