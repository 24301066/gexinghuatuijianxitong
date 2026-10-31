<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { mediaUrl } from '../api'
import { useShopStore } from '../stores/shop'
import { useToastStore } from '../stores'

const shop = useShopStore()
const toast = useToastStore()
const router = useRouter()

const rows = computed(() => shop.cart)
const allChecked = computed(() => rows.value.length > 0 && rows.value.every((row) => row.checked))

function goCheckout() {
  if (!shop.cartChecked.length) {
    toast.push('先勾选要结算的商品', 'error')
    return
  }
  router.push({ name: 'checkout' })
}
</script>

<template>
  <section>
    <div class="page-head">
      <h1>购物车</h1>
      <p>重复加入只会增加数量，数量可以自己加减。</p>
    </div>

    <div v-if="!rows.length" class="empty">
      购物车还是空的，<RouterLink class="link" to="/">去逛逛 →</RouterLink>
    </div>

    <template v-else>
      <div class="row-list">
        <div v-for="row in rows" :key="row.item_id" class="row-item">
          <input type="checkbox" :checked="row.checked" @change="shop.toggleChecked(row.item_id, $event.target.checked)" />
          <RouterLink :to="{ name: 'item', params: { itemId: row.item_id } }">
            <img :src="mediaUrl(row.cover_url)" :alt="row.title" class="cart-thumb" />
          </RouterLink>
          <div class="grow">
            <div style="font-weight: 700">{{ row.title }}</div>
            <div class="meta">
              <span>{{ row.category }}</span>
              <span class="dot" />
              <span class="price">¥{{ row.price.toFixed(0) }}</span>
            </div>
          </div>
          <div class="qty">
            <button type="button" @click="shop.setQty(row.item_id, row.qty - 1)">−</button>
            <span>{{ row.qty }}</span>
            <button type="button" @click="shop.setQty(row.item_id, row.qty + 1)">＋</button>
          </div>
          <button class="link" type="button" @click="shop.removeFromCart(row.item_id)">删除</button>
        </div>
      </div>

      <div class="section-card" style="margin-top: 18px; display: flex; align-items: center; gap: 14px">
        <label class="check-line">
          <input type="checkbox" :checked="allChecked" @change="shop.toggleAll($event.target.checked)" />
          全选
        </label>
        <div style="margin-left: auto" class="meta">
          已选 {{ shop.cartChecked.length }} 件 · 合计
          <b class="price" style="font-size: 20px">¥{{ shop.cartTotal.toFixed(2) }}</b>
        </div>
        <button class="btn" type="button" @click="goCheckout">结算</button>
      </div>
    </template>
  </section>
</template>
