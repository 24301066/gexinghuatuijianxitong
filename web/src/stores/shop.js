import { defineStore } from 'pinia'
import { api } from '../api'

const LOCAL_KEY = 'gt_shop_local_v2'

function blankLocal() {
  return {
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

function loadLocal() {
  try {
    return { ...blankLocal(), ...(JSON.parse(localStorage.getItem(LOCAL_KEY) || '{}')) }
  } catch (error) {
    return blankLocal()
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
        { from: 'other', text: '如果要投诉商家或反馈体验，把情况发在这里就行。', at: now - 3500_000 }
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
    const local = loadLocal()
    if (!local.conversations.length) local.conversations = seedConversations()
    return {
      cart: [],
      favorites: [],
      addresses: [],
      orders: [],
      ready: false,
      wallet: local.wallet,
      profile: local.profile,
      conversations: local.conversations,
      reviews: local.reviews
    }
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
    // ------------------------------------------------------------ local bits
    persistLocal() {
      localStorage.setItem(LOCAL_KEY, JSON.stringify({
        wallet: this.wallet,
        profile: this.profile,
        conversations: this.conversations,
        reviews: this.reviews
      }))
    },
    startAutoSave() {
      // 本地部分（钱包/资料/消息）按账号保存在浏览器存储里
      this.$subscribe(() => this.persistLocal())
    },
    // ---------------------------------------------------------------- server
    async init() {
      await Promise.all([this.refreshCart(), this.refreshFavorites(), this.refreshAddresses(),
                         this.loadOrders()])
      this.ready = true
    },
    async refreshCart() {
      try {
        this.cart = await api.getCart()
      } catch (error) {
        this.cart = []
      }
    },
    async refreshFavorites() {
      try {
        this.favorites = await api.getFavorites()
      } catch (error) {
        this.favorites = []
      }
    },
    async refreshAddresses() {
      try {
        this.addresses = await api.getAddresses()
      } catch (error) {
        this.addresses = []
      }
    },
    async addToCart(item, qty = 1) {
      this.cart = await api.addCart(item.item_id, qty)
    },
    async setQty(itemId, qty) {
      this.cart = await api.patchCart(itemId, { qty })
    },
    async toggleChecked(itemId, value) {
      const row = this.cart.find((entry) => entry.item_id === itemId)
      const next = value === undefined ? !row?.checked : Boolean(value)
      this.cart = await api.patchCart(itemId, { checked: next })
    },
    async toggleAll(value) {
      this.cart = await api.checkAllCart(value)
    },
    async removeFromCart(itemId) {
      this.cart = await api.deleteCart(itemId)
    },
    isFavorite(itemId) {
      return this.favorites.some((row) => row.item_id === itemId)
    },
    async toggleFavorite(item) {
      if (this.isFavorite(item.item_id)) {
        await api.removeFavorite(item.item_id)
        await this.refreshFavorites()
        return false
      }
      await api.addFavorite(item.item_id)
      await this.refreshFavorites()
      return true
    },
    // -------------------------------------------------------------- address
    async addAddress(payload) {
      const row = await api.createAddress(payload)
      await this.refreshAddresses()
      return row
    },
    async removeAddress(id) {
      await api.deleteAddress(id)
      await this.refreshAddresses()
    },
    async setDefaultAddress(id) {
      this.addresses = await api.setDefaultAddress(id)
    },
    // --------------------------------------------------------------- orders
    async loadOrders(status = 'all') {
      try {
        this.orders = await api.getOrders(status)
      } catch (error) {
        this.orders = []
      }
    },
    async createOrder({ addressId, payment }) {
      const order = await api.createOrder(addressId, payment)
      await Promise.all([this.refreshCart(), this.loadOrders()])
      return order
    },
    async orderAction(orderId, action) {
      const order = await api.orderAction(orderId, action)
      await this.loadOrders()
      return order
    },
    // -------------------------------------------------------------- profile
    updateProfile(payload) {
      Object.assign(this.profile, payload)
      this.persistLocal()
    },
    updateSizes(payload) {
      Object.assign(this.profile.sizes, payload)
      this.persistLocal()
    },
    addReview(review) {
      this.reviews.unshift({ ...review, at: Date.now() })
      this.persistLocal()
    },
    // ----------------------------------------------------------- messaging
    sendMessage(conversationId, text) {
      const room = this.conversations.find((row) => row.id === conversationId)
      if (!room || !text.trim()) return
      room.messages.push({ from: 'me', text: text.trim(), at: Date.now() })
      room.unread = 0
      this.persistLocal()
      const reply = room.kind === 'service'
        ? '已记录你的问题，客服会在 24 小时内跟进。退款/投诉请补充订单号或截图～'
        : room.kind === 'merchant'
          ? '收到！稍后给你发优惠链接～'
          : '哈哈好呀，回头一起拼单！'
      setTimeout(() => {
        room.messages.push({ from: 'other', text: reply, at: Date.now() })
        this.persistLocal()
      }, 900)
    },
    markRead(conversationId) {
      const room = this.conversations.find((row) => row.id === conversationId)
      if (room) {
        room.unread = 0
        this.persistLocal()
      }
    }
  }
})
