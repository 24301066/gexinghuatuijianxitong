<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { mediaUrl } from '../api'
import { useShopStore } from '../stores/shop'
import { useToastStore } from '../stores'
import { api } from '../api'

const route = useRoute()
const router = useRouter()
const shop = useShopStore()
const toast = useToastStore()
const showMore = ref(false)

const STATUS_TEXT = {
  pending_payment: '待支付',
  pending_shipment: '待发货',
  pending_receipt: '运输中',
  pending_review: '待评价',
  completed: '已完成',
  cancelled: '已取消',
  aftersale: '售后中'
}

const order = computed(() => shop.orders.find((row) => row.id === route.params.id) || null)

async function run(action, message) {
  try {
    await shop.orderAction(order.value.id, action)
    if (message) toast.push(message)
  } catch (err) {
    toast.push(err.message, 'error')
  }
}

const showSnapshot = ref(false)

function shareProduct() {
  const title = order.value?.items?.[0]?.title || '商品'
  const link = `${location.origin}/items/${order.value?.items?.[0]?.item_id || ''}`
  if (navigator.clipboard) {
    navigator.clipboard.writeText(`${title} ${link}`).catch(() => {})
  }
  toast.push('商品链接已复制，去分享给朋友吧')
}

async function buyAgain() {
  try {
    for (const row of order.value.items) {
      await api.addCart(row.item_id, row.qty)
    }
    await shop.refreshCart()
    toast.push('已加入购物车，可直接结算')
    router.push({ name: 'cart' })
  } catch (err) {
    toast.push(err.message, 'error')
  }
}

onMounted(() => { if (!shop.orders.length) shop.loadOrders('all') })
</script>

<template>
  <section>
    <div v-if="!order" class="empty">
      订单不存在，<RouterLink class="link" :to="{ name: 'orders' }">回订单列表</RouterLink>
    </div>

    <template v-else>
      <div class="order-detail-head">
        <div style="font-size: 20px; font-weight: 800">{{ STATUS_TEXT[order.status] || order.status }}</div>
        <div class="meta" v-if="order.status === 'pending_receipt'">预计明天送达 · 物流已更新</div>
        <div class="meta" v-else-if="order.status === 'pending_payment'">请尽快完成支付</div>
      </div>

      <div class="section-card">
        <div class="order-shop">
          <span>{{ order.items[0]?.category }}官方旗舰店</span>
          <span class="tag">官方</span>
        </div>
        <div class="row-list" style="margin-top: 10px">
          <div v-for="row in order.items" :key="row.item_id" class="row-item" style="box-shadow: none">
            <img :src="mediaUrl(row.cover_url)" :alt="row.title" class="cart-thumb" />
            <div class="grow">
              <div style="font-weight: 700">{{ row.title }}</div>
              <div class="meta">{{ row.category }}</div>
              <div class="meta">¥{{ row.price.toFixed(2) }} × {{ row.qty }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="section-card">
        <div class="kv"><span>实付</span><b class="price">¥{{ Number(order.total).toFixed(2) }}</b></div>
        <div class="kv"><span>订单编号</span><span>{{ order.id }}</span></div>
        <div class="kv"><span>支付方式</span><span>{{ order.payment }}</span></div>
        <div class="kv"><span>收货地址</span><span style="text-align: right; max-width: 60%">{{ order.address?.name }} {{ order.address?.region }} {{ order.address?.detail }}</span></div>
        <div class="kv"><span>下单时间</span><span>{{ new Date(order.created_at).toLocaleString('zh-CN') }}</span></div>
        <div style="display: flex; gap: 10px; margin-top: 8px; flex-wrap: wrap">
          <button class="link" type="button" @click="showMore = !showMore">
            更多信息 {{ showMore ? '收起' : '展开' }}
          </button>
          <button class="link" type="button" @click="showSnapshot = !showSnapshot">交易快照</button>
        </div>
        <div v-if="showSnapshot" class="meta" style="margin-top: 8px; white-space: pre-wrap">{{ JSON.stringify({
          order: order.id, status: order.status, payment: order.payment,
          total: order.total, address: order.address,
          items: order.items.map((row) => ({ item_id: row.item_id, title: row.title,
            price: row.price, qty: row.qty, merchant: row.merchant_name }))
        }, null, 2) }}</div>
        <div v-if="showMore" class="meta" style="margin-top: 8px">
          交易快照：发生争议时可作为判断依据。本单由 {{ order.items.length }} 件商品组成，合计
          ¥{{ Number(order.total).toFixed(2) }}。
        </div>
      </div>

      <div class="section-card">
        <div class="section-head" style="margin-bottom: 10px"><h2>服务保障</h2></div>
        <div class="kv"><span>✓ 运费险</span><span class="meta">退换货自动理赔</span></div>
        <div class="kv"><span>✓ 7 天无理由退货</span><span class="meta">未拆封可申请</span></div>
        <div class="kv"><span>✓ 号码保护</span><span class="meta">隐藏手机号，保护隐私</span></div>
      </div>

      <RouterLink class="btn ghost" style="width: 100%; margin-bottom: 12px"
                  :to="{ name: 'chat', params: { id: 'service' } }">联系商家 / 客服</RouterLink>

      <div class="order-bottom">
        <button class="link" type="button" @click="shareProduct">分享商品</button>
        <button class="link" type="button" @click="buyAgain">再买一单</button>
        <button class="link" type="button"
                @click="router.push({ name: 'address' })">修改地址</button>
        <button class="btn ghost small" type="button"
                @click="router.push({ name: 'logistics', params: { id: order.id } })">查看物流</button>
        <button v-if="order.status === 'pending_payment'" class="btn small" type="button"
                @click="run('pay', '支付成功')">立即支付</button>
        <button v-else-if="order.status === 'pending_receipt'" class="btn small" type="button"
                @click="run('receive', '已确认收货')">确认收货</button>
        <button v-else-if="order.status === 'pending_review'" class="btn small" type="button"
                @click="router.push({ name: 'orders', query: { status: 'pending_review' } })">去评价</button>
        <button v-else class="btn small" type="button" @click="run('aftersale', '已申请售后')">申请售后</button>
      </div>
    </template>
  </section>
</template>
