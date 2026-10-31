import { defineStore } from 'pinia'
import { watch } from 'vue'

const STORAGE_KEY = 'gt_shop_v1'

function blankState() {
  return {
    cart: [],
    favorites: [],
    addresses: [
      {
        id: 'ADDR-DEMO',
        name: '林小满',
        phone: '13800138000',
        region: '浙江省 杭州市 西湖区',
        detail: '文三路 90 号 3 幢 502',
        is_default: true
      }
    ],
    orders: [],
    wallet: { coupons: 3, points: 1280, red_packets: 2, balance: 0 },
    profile: {
      nickname: '种草少女',
      gender: '女',
      birthday: '1998-06-18',
      joined: '2025-03-12',
      level: 2,
      spent: 1288,
      active: 0.42,
      sizes: { height: '165', weight: '52', shoe: '38', top: 'M', bottom: 'M' }
    },
    conversations: [],
    reviews: []
  }
}

function loadState() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    return { ...blankState(), ...raw }
  } catch (error) {
    return blankState()
  }
}

function seedConversations() {
  const now = Date.now()
  return [
    {
      id: 'service',
      name: '官方客服',
      avatar: '客',
      kind: 'service',
      unread: 1,
      messages: [
        { from: 'other', text: '你好，我是种草集官方客服，订单、退款、账号问题都可以问我。', at: now - 3600_000 },
        { from: 'other', text: '如果想投诉商家或反馈体验，直接把情况发在这里即可。', at: now - 3500_000 }
      ]
    },
    {
      id: 'shop-1',
      name: '京造旗舰店',
      avatar: '京',
      kind: 'merchant',
      unread: 0,
      messages: [
        { from: 'other', text: '亲，你收藏的砂锅今晚 8 点有活动，记得来看～', at: now - 86400_000 }
      ]
    },
    {
      id: 'user-1',
      name: '小鹿',
      avatar: '鹿',
      kind: 'user',
      unread: 0,
      messages: [{ from: 'other', text: '你安利的那款咖啡我也买了，确实好喝！', at: now - 172800_000 }]
    }
  ]
}

export const useShopStore = defineStore('shop', {
  state: () => {
    const state = loadState()
    if (!state.conversations.length) state.conversations = seedConversations()
    return state
  },
  getters: {
    cartCount: (state) => state.cart.reduce((sum, row) => sum + row.qty, 0),
    cartChecked: (state) => state.cart.filter((row) => row.checked),
    cartTotal() {
      return this.cartChecked.reduce((sum, row) => sum + row.price * row.qty, 0)
    },
    unreadCount: (state) => state.conversations.reduce((sum, row) => sum + row.unread, 0),
    defaultAddress: (state) => state.addresses.find((row) => row.is_default) || state.addresses[0] || null,
    favoriteIds: (state) => new Set(state.favorites.map((row) => row.item_id)),
    ordersByStatus: (state) => (status) => (status === 'all'
      ? state.orders
      : state.orders.filter((row) => row.status === status))
  },
  actions: {
    persist() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        cart: this.cart,
        favorites: this.favorites,
        addresses: this.addresses,
        orders: this.orders,
        wallet: this.wallet,
        profile: this.profile,
        conversations: this.conversations,
        reviews: this.reviews
      }))
    },
    startAutoSave() {
      watch(() => this.$state, () => this.persist(), { deep: true })
    },
    // ---------------------------------------------------------------- cart
    addToCart(item, qty = 1) {
      const existing = this.cart.find((row) => row.item_id === item.item_id)
      if (existing) {
        existing.qty += qty
      } else {
        this.cart.push({
          item_id: item.item_id,
          title: item.title,
          price: Number(item.price),
          cover_url: item.cover_url,
          category: item.category,
          qty,
          checked: true
        })
      }
      this.persist()
    },
    setQty(itemId, qty) {
      const row = this.cart.find((entry) => entry.item_id === itemId)
      if (!row) return
      row.qty = Math.max(1, Math.min(99, Number(qty) || 1))
      this.persist()
    },
    toggleChecked(itemId, value) {
      const row = this.cart.find((entry) => entry.item_id === itemId)
      if (!row) return
      row.checked = value === undefined ? !row.checked : Boolean(value)
      this.persist()
    },
    toggleAll(value) {
      this.cart.forEach((row) => { row.checked = value })
      this.persist()
    },
    removeFromCart(itemId) {
      this.cart = this.cart.filter((row) => row.item_id !== itemId)
      this.persist()
    },
    clearChecked() {
      this.cart = this.cart.filter((row) => !row.checked)
      this.persist()
    },
    // ------------------------------------------------------------ favorites
    toggleFavorite(item) {
      const exists = this.favorites.some((row) => row.item_id === item.item_id)
      if (exists) {
        this.favorites = this.favorites.filter((row) => row.item_id !== item.item_id)
      } else {
        this.favorites.push({
          item_id: item.item_id,
          title: item.title,
          price: Number(item.price),
          cover_url: item.cover_url,
          category: item.category,
          added_at: Date.now()
        })
      }
      this.persist()
      return !exists
    },
    isFavorite(itemId) {
      return this.favorites.some((row) => row.item_id === itemId)
    },
    // -------------------------------------------------------------- address
    addAddress(payload) {
      const row = { ...payload, id: `ADDR${Date.now()}` }
      if (!this.addresses.length || payload.is_default) {
        this.addresses.forEach((entry) => { entry.is_default = false })
        row.is_default = true
      }
      this.addresses.push(row)
      this.persist()
      return row
    },
    updateAddress(id, payload) {
      const row = this.addresses.find((entry) => entry.id === id)
      if (!row) return
      Object.assign(row, payload)
      if (payload.is_default) {
        this.addresses.forEach((entry) => { entry.is_default = entry.id === id })
      }
      this.persist()
    },
    removeAddress(id) {
      this.addresses = this.addresses.filter((row) => row.id !== id)
      if (this.addresses.length && !this.addresses.some((row) => row.is_default)) {
        this.addresses[0].is_default = true
      }
      this.persist()
    },
    setDefaultAddress(id) {
      this.addresses.forEach((row) => { row.is_default = row.id === id })
      this.persist()
    },
    // --------------------------------------------------------------- orders
    createOrder({ items, address, payment, status = 'pending_payment' }) {
      const total = items.reduce((sum, row) => sum + row.price * row.qty, 0)
      const order = {
        id: `GT${Date.now()}`,
        status,
        items,
        address,
        payment,
        total,
        created_at: Date.now()
      }
      this.orders.unshift(order)
      this.persist()
      return order
    },
    updateOrderStatus(id, status) {
      const order = this.orders.find((row) => row.id === id)
      if (!order) return
      order.status = status
      this.persist()
    },
    payOrder(id) {
      this.updateOrderStatus(id, 'pending_shipment')
      this.wallet.points += 10
      this.profile.spent += this.orders.find((row) => row.id === id)?.total || 0
      this.persist()
    },
    // -------------------------------------------------------------- profile
    updateProfile(payload) {
      Object.assign(this.profile, payload)
      this.persist()
    },
    updateSizes(payload) {
      Object.assign(this.profile.sizes, payload)
      this.persist()
    },
    addReview(review) {
      this.reviews.unshift({ ...review, at: Date.now() })
      this.persist()
    },
    // ----------------------------------------------------------- messaging
    sendMessage(conversationId, text) {
      const room = this.conversations.find((row) => row.id === conversationId)
      if (!room || !text.trim()) return
      room.messages.push({ from: 'me', text: text.trim(), at: Date.now() })
      room.unread = 0
      this.persist()
      const reply = room.kind === 'service'
        ? '已记录你的问题，客服会在 24 小时内跟进。退款/投诉请补充订单号或截图～'
        : room.kind === 'merchant'
          ? '收到！稍后给你发优惠链接～'
          : '哈哈好呀，回头一起拼单！'
      setTimeout(() => {
        room.messages.push({ from: 'other', text: reply, at: Date.now() })
        this.persist()
      }, 900)
    },
    markRead(conversationId) {
      const room = this.conversations.find((row) => row.id === conversationId)
      if (room) {
        room.unread = 0
        this.persist()
      }
    }
  }
})
