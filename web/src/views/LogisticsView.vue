<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useShopStore } from '../stores/shop'

const route = useRoute()
const shop = useShopStore()

const order = computed(() => shop.orders.find((row) => row.id === route.params.id) || null)

const steps = computed(() => {
  if (!order.value) return []
  const status = order.value.status
  const base = order.value.created_at
  const list = [
    { key: 'created', title: '订单已创建', time: base, done: true },
    { key: 'paid', title: '支付成功', time: base, done: status !== 'pending_payment' },
    { key: 'shipped', title: '商家已发货', time: base, done: ['pending_receipt', 'pending_review', 'completed'].includes(status) },
    { key: 'transit', title: '运输中', time: base, done: ['pending_receipt'].includes(status) },
    { key: 'received', title: '已签收', time: base, done: ['pending_review', 'completed'].includes(status) }
  ]
  return list
})

onMounted(() => { if (!shop.orders.length) shop.loadOrders('all') })
</script>

<template>
  <section>
    <div v-if="!order" class="empty">订单不存在</div>

    <template v-else>
      <div class="logistics-map">
        <div class="logistics-badge">运输中</div>
        <div class="logistics-city">当前在 · 中转仓</div>
        <div class="logistics-line" />
        <div class="meta" style="color: #fff; opacity: 0.9">目的地：{{ order.address?.region }}</div>
      </div>

      <div class="section-card" style="margin-top: -18px; position: relative; z-index: 2">
        <div style="font-size: 18px; font-weight: 800">运输中 · 预计明天送达</div>
        <div class="meta" style="margin-top: 4px">订单号 {{ order.id }}</div>
        <div class="meta">收货人 {{ order.address?.name }}，{{ order.address?.region }} {{ order.address?.detail }}</div>
      </div>

      <div class="section-card">
        <div class="section-head" style="margin-bottom: 10px"><h2>物流跟踪</h2></div>
        <div class="timeline">
          <div v-for="(step, index) in steps" :key="step.key" :class="['timeline-item', step.done ? 'done' : '']">
            <span class="timeline-dot" />
            <div class="grow">
              <div style="font-weight: 600">{{ step.title }}</div>
              <div class="meta">{{ new Date(step.time).toLocaleString('zh-CN') }}</div>
            </div>
            <span v-if="index === 0" class="tag">最新</span>
          </div>
        </div>
      </div>

      <RouterLink class="btn ghost" style="width: 100%" :to="{ name: 'orders' }">返回订单列表</RouterLink>
    </template>
  </section>
</template>
