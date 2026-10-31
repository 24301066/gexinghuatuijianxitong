<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useShopStore } from '../stores/shop'

const route = useRoute()
const shop = useShopStore()
const draft = ref('')
const scroller = ref(null)

const room = computed(() => shop.conversations.find((row) => row.id === route.params.id))

async function scrollDown() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

function send() {
  if (!draft.value.trim() || !room.value) return
  shop.sendMessage(room.value.id, draft.value)
  draft.value = ''
  scrollDown()
}

watch(() => room.value?.messages.length, scrollDown)
watch(() => route.params.id, () => {
  if (room.value) shop.markRead(room.value.id)
  scrollDown()
})

onMounted(() => {
  if (room.value) shop.markRead(room.value.id)
  scrollDown()
})
</script>

<template>
  <section v-if="room">
    <div class="page-head">
      <h1>{{ room.name }}</h1>
      <p v-if="room.kind === 'service'">咨询、投诉、退款都可以直接说，客服会跟进。</p>
      <p v-else-if="room.kind === 'merchant'">商家消息，可在结算时用活动优惠。</p>
      <p v-else>和其他买家交流安利心得。</p>
    </div>

    <div class="section-card">
      <div ref="scroller" class="chat">
        <div v-for="(message, index) in room.messages" :key="index"
             :class="['bubble', message.from === 'me' ? 'me' : '']">
          {{ message.text }}
        </div>
      </div>

      <div class="chat-input">
        <input v-model="draft" :placeholder="room.kind === 'service' ? '描述你的问题…' : '说点什么…'"
               @keyup.enter="send" />
        <button class="btn" type="button" @click="send">发送</button>
      </div>

      <div v-if="room.kind === 'service'" class="chip-row" style="margin-top: 12px">
        <button class="chip" type="button" @click="draft = '我要查一下订单物流'">查物流</button>
        <button class="chip" type="button" @click="draft = '我买的商品有问题，想申请退款'">申请退款</button>
        <button class="chip" type="button" @click="draft = '我要投诉某个商家'">投诉商家</button>
        <button class="chip" type="button" @click="draft = '怎么修改收货地址'">改地址</button>
      </div>
    </div>
  </section>
  <div v-else class="empty">会话不存在，<RouterLink class="link" to="/messages">回消息列表</RouterLink></div>
</template>
