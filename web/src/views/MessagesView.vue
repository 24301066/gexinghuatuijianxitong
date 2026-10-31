<script setup>
import { onMounted } from 'vue'
import { useShopStore } from '../stores/shop'

const shop = useShopStore()

function preview(room) {
  const last = room.messages[room.messages.length - 1]
  return last ? last.text : ''
}

onMounted(() => {
  shop.startAutoSave()
})
</script>

<template>
  <section>
    <div class="page-head"><h1>消息</h1><p>和商家、其他买家以及官方客服的对话。</p></div>

    <div class="row-list">
      <RouterLink v-for="room in shop.conversations" :key="room.id"
                  class="row-item" :to="{ name: 'chat', params: { id: room.id } }">
        <span class="avatar">{{ room.avatar }}</span>
        <div class="grow">
          <div style="font-weight: 700">
            {{ room.name }}
            <span class="tag" style="margin-left: 6px">{{ room.kind === 'service' ? '官方' : room.kind === 'merchant' ? '商家' : '买家' }}</span>
          </div>
          <div class="meta">{{ preview(room) }}</div>
        </div>
        <span v-if="room.unread" class="dot-badge">{{ room.unread }}</span>
      </RouterLink>
    </div>
  </section>
</template>
