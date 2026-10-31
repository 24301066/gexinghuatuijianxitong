<script setup>
import { computed, ref, watch } from 'vue'
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
  { key: 'pending_payment', label: '待付款' },
  { key: 'pending_shipment', label: '待发货' },
  { key: 'pending_receipt', label: '待收货' },
  { key: 'pending_review', label: '待评价' },
  { key: 'aftersale', label: '退款/售后' }
]

const STATUS_TEXT = {
  pending_payment: '待付款',
  pending_shipment: '待发货',
  pending_receipt: '待收货',
  pending_review: '待评价',
  completed: '已完成',
  aftersale: '售后中'
}

const active = ref(String(route.query.status || 'all'))
const orders = computed(() => shop.ordersByStatus(active.value))

watch(() => route.query.status, (value) => { active.value = String(value || 'all') })

function pick(key) {
  active.value = key
  router.replace({ name: 'orders', query: key === 'all' ? {} : { status: key } })
}

function pay(order) {
  shop.payOrder(order.id)
  toast.push('支付成功，等待发货')
}

function cancel(order) {
  shop.updateOrderStatus(order.id, 'completed')
  toast.push('订单已取消')
}

function receive(order) {
  shop.updateOrderStatus(order.id, 'pending_review')
  toast.push('已确认收货，记得评价')
}

function review(order) {
  shop.addReview({ order_id: order.id, text: '默认好评：包装完好，物流很快，和安利里说的一样。' })
  shop.updateOrderStatus(order.id, 'completed')
  toast.push('已提交评价')
}

function aftersale(order) {
  shop.updateOrderStatus(order.id, 'aftersale')
  toast.push('已申请售后，客服会联系你')
}
</script>

<template>
  <section>
    <div class="page-head"><h1>我的订单</h1><p>付款、收货、评价都能在这里处理。</p></div>

    <div class="tabs">
      <button v-for="tab in TABS" :key="tab.key" type="button"
              :class="active === tab.key ? 'active' : ''" @click="pick(tab.key)">
        {{ tab.label }}
      </button>
    </div>

    <div v-if="!orders.length" class="empty">这个分类还没有订单</div>

    <div v-for="order in orders" :key="order.id" class="order-card">
      <div class="meta" style="justify-content: space-between; margin-bottom: 10px">
        <span>订单号 {{ order.id }} · {{ new Date(order.created_at).toLocaleString('zh-CN') }}</span>
        <span class="status-pill">{{ STATUS_TEXT[order.status] || order.status }}</span>
      </div>

      <div class="row-list">
        <div v-for="row in order.items" :key="row.item_id" class="row-item" style="box-shadow: none">
          <img :src="mediaUrl(row.cover_url)" :alt="row.title" class="cart-thumb" />
          <div class="grow">
            <div style="font-weight: 700">{{ row.title }}</div>
            <div class="meta">¥{{ row.price.toFixed(0) }} × {{ row.qty }}</div>
          </div>
        </div>
      </div>

      <div class="meta" style="margin-top: 10px; gap: 12px; flex-wrap: wrap">
        <span>{{ order.address?.name }} · {{ order.address?.region }} {{ order.address?.detail }}</span>
        <span class="dot" />
        <span>{{ order.payment }}</span>
        <b class="price" style="margin-left: auto">¥{{ Number(order.total).toFixed(2) }}</b>
      </div>

      <div style="display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end">
        <button v-if="order.status === 'pending_payment'" class="link" type="button" @click="cancel(order)">取消订单</button>
        <button v-if="order.status === 'pending_payment'" class="btn small" type="button" @click="pay(order)">去支付</button>
        <button v-if="order.status === 'pending_shipment'" class="btn ghost small" type="button"
                @click="toast.push('已提醒商家尽快发货')">提醒发货</button>
        <button v-if="order.status === 'pending_receipt'" class="btn small" type="button" @click="receive(order)">确认收货</button>
        <button v-if="order.status === 'pending_review'" class="btn small" type="button" @click="review(order)">去评价</button>
        <button v-if="order.status === 'completed'" class="btn ghost small" type="button" @click="aftersale(order)">申请售后</button>
      </div>
    </div>
  </section>
</template>
