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
  aftersale_cancelled: '售后已关闭',
  refunded: '退款成功',
  cancelled: '已取消',
  aftersale: '售后中'
}

const active = ref(String(route.query.status || 'all'))
const AFTersale_STATUSES = ['aftersale', 'aftersale_cancelled', 'refunded']
const orders = computed(() => {
  const rows = shop.orders || []
  if (active.value === 'all') return rows
  if (active.value === 'aftersale') return rows.filter((o) => AFTersale_STATUSES.includes(o.status))
  return rows.filter((o) => o.status === active.value)
})

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
const aftersale = (order) => run(order, 'aftersale', '已提交售后申请')
const cancelAftersale = (order) => run(order, 'cancel_aftersale', '已取消售后申请')
const refund = (order) => run(order, 'refund', '退款成功，已原路退回')
const deleteAftersale = (order) => run(order, 'delete_aftersale', '售后单已删除')

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

      <div v-if="AFTersale_STATUSES.includes(order.status)" class="aftersale-strip">
        <template v-if="order.status === 'aftersale'">
          <b>退款申请已提交</b> 商家正在处理，可随时取消
        </template>
        <template v-else-if="order.status === 'aftersale_cancelled'">
          <b>退款申请已关闭</b> 售后保障期内您可重新发起售后申请
        </template>
        <template v-else>
          <b>退款成功</b> 退回微信支付（零钱通）¥{{ Number(order.total).toFixed(2) }}
        </template>
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
        <button v-if="order.status === 'aftersale'" class="btn ghost small" type="button"
                @click="cancelAftersale(order)">取消售后</button>
        <button v-if="order.status === 'aftersale'" class="btn small" type="button"
                @click="refund(order)">模拟退款成功</button>
        <button v-if="order.status === 'aftersale_cancelled'" class="btn ghost small" type="button"
                @click="aftersale(order)">重新申请</button>
        <button v-if="order.status === 'refunded'" class="btn ghost small" type="button"
                @click="deleteAftersale(order)">删除售后单</button>
      </div>
    </div>
  </section>
</template>
