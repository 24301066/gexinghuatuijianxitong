<script setup>
defineProps({
  item: { type: Object, required: true }
})

function money(value) {
  return Number(value || 0).toFixed(2)
}
</script>

<template>
  <article class="product card">
    <RouterLink :to="{ name: 'item', params: { itemId: item.item_id } }" class="product-link">
      <span class="rank">#{{ item.rank }}</span>
      <h2>{{ item.title }}</h2>
      <p class="meta">
        <span class="tag">{{ item.category }}</span>
        <span class="price">¥{{ money(item.price) }}</span>
      </p>
      <p class="reason">{{ item.reason }}</p>
      <p class="muted small">
        命中来源：
        <span v-for="(value, key) in item.sources" :key="key">{{ key }}={{ value.toFixed(3) }}</span>
      </p>
    </RouterLink>
  </article>
</template>
