const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

function token() {
  return localStorage.getItem('gt_token') || ''
}

export class ApiError extends Error {
  constructor(message, status, code, requestId) {
    super(message)
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const bearer = token()
  if (auth && bearer) headers.Authorization = `Bearer ${bearer}`

  let response
  try {
    response = await fetch(`${BASE}/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body)
    })
  } catch (error) {
    throw new ApiError('网络不可用，请检查服务是否在运行', 0, 'network_error', '')
  }

  let payload = {}
  try {
    payload = await response.json()
  } catch (error) {
    payload = {}
  }

  if (!response.ok) {
    throw new ApiError(
      payload.message || `请求失败（HTTP ${response.status}）`,
      payload.code || 'error',
      response.status,
      payload.request_id || response.headers.get('X-Request-ID') || ''
    )
  }
  return payload
}

export function mediaUrl(path) {
  if (!path) return ''
  return path.startsWith('http') ? path : `${BASE}${path}`
}

export const api = {
  login: (username, password) =>
    request('/auth/login', { method: 'POST', body: { username, password }, auth: false }),
  register: (username, password) =>
    request('/auth/register', { method: 'POST', body: { username, password }, auth: false }),
  me: () => request('/auth/me'),
  profile: () => request('/me/profile'),
  insights: () => request('/me/insights'),
  health: () => request('/health', { auth: false }),
  items: ({ category = '', page = 1, size = 20 } = {}) => {
    const query = new URLSearchParams({ page, size })
    if (category) query.set('category', category)
    return request(`/items?${query.toString()}`, { auth: false })
  },
  item: (itemId) => request(`/items/${encodeURIComponent(itemId)}`, { auth: false }),
  similar: (itemId, size = 8) =>
    request(`/items/${encodeURIComponent(itemId)}/similar?size=${size}`),
  recommendations: (size = 10, page = 1) => request(`/recommendations?size=${size}&page=${page}`),
  posts: ({ productId = '', authorId = '', page = 1, size = 12 } = {}) => {
    const query = new URLSearchParams({ page, size })
    if (productId) query.set('product_id', productId)
    if (authorId) query.set('author_id', authorId)
    return request(`/posts?${query.toString()}`, { auth: false })
  },
  author: (authorId) => request(`/authors/${encodeURIComponent(authorId)}`, { auth: false }),
  post: (postId) => request(`/posts/${encodeURIComponent(postId)}`, { auth: false }),
  feed: (size = 8) => request(`/feed?size=${size}`),
  search: (q) => request(`/search?q=${encodeURIComponent(q)}`),
  postEvent: (itemId, type, rating) =>
    request('/events', { method: 'POST', body: { item_id: itemId, type, rating } }),
  searchEvent: (keyword) => request('/events', { method: 'POST', body: { type: 'search', keyword } }),
  dwellEvent: (postId, seconds) =>
    request('/events', { method: 'POST', body: { type: 'post_dwell', post_id: postId, seconds } })
}

// ---------------------------------------------------------------- shop API
api.getCart = () => request('/cart')
api.addCart = (itemId, qty = 1) => request('/cart', { method: 'POST', body: { item_id: itemId, qty } })
api.patchCart = (itemId, body) => request(`/cart/${encodeURIComponent(itemId)}`, { method: 'PATCH', body })
api.deleteCart = (itemId) => request(`/cart/${encodeURIComponent(itemId)}`, { method: 'DELETE' })
api.checkAllCart = (checked = true) => request(`/cart/check-all?checked=${checked ? 'true' : 'false'}`, { method: 'POST' })
api.getFavorites = () => request('/favorites')
api.addFavorite = (itemId) => request(`/favorites/${encodeURIComponent(itemId)}`, { method: 'POST' })
api.removeFavorite = (itemId) => request(`/favorites/${encodeURIComponent(itemId)}`, { method: 'DELETE' })
api.getAddresses = () => request('/addresses')
api.createAddress = (payload) => request('/addresses', { method: 'POST', body: payload })
api.updateAddress = (id, payload) => request(`/addresses/${encodeURIComponent(id)}`, { method: 'PATCH', body: payload })
api.deleteAddress = (id) => request(`/addresses/${encodeURIComponent(id)}`, { method: 'DELETE' })
api.setDefaultAddress = (id) => request(`/addresses/${encodeURIComponent(id)}/default`, { method: 'POST' })
api.getOrders = (status = 'all') => request(`/orders?status=${encodeURIComponent(status)}`)
api.createOrder = (addressId, payment) => request('/orders', { method: 'POST', body: { address_id: addressId, payment } })
api.orderAction = (orderId, action) => request(`/orders/${encodeURIComponent(orderId)}/${action}`, { method: 'POST' })

// ------------------------------------------------------------ auth extras
api.sendSmsCode = (phone, purpose = 'register') =>
  request('/auth/sms/send', { method: 'POST', body: { phone, purpose }, auth: false })
api.registerPhone = (phone, code, username, password) =>
  request('/auth/register/phone', { method: 'POST', body: { phone, code, username, password }, auth: false })
api.loginPhone = (phone, code) =>
  request('/auth/login/phone', { method: 'POST', body: { phone, code }, auth: false })
api.oauthLogin = (provider) =>
  request(`/auth/oauth/${provider}`, { method: 'POST', body: {}, auth: false })
api.bindPhone = (bindToken, phone, code, username) =>
  request('/auth/bind-phone', { method: 'POST', body: { bind_token: bindToken, phone, code, username }, auth: false })


// ------------------------------------------------------- catalog extras
api.itemDetail = (itemId) => request(`/items/${encodeURIComponent(itemId)}/detail`, { auth: false })
api.reviews = (itemId) => request(`/items/${encodeURIComponent(itemId)}/reviews`, { auth: false })
api.shop = (merchantId) => request(`/merchants/${encodeURIComponent(merchantId)}`, { auth: false })
api.merchants = () => request('/merchants', { auth: false })


api.reviewItem = (itemId, rating, content) =>
  request(`/items/${encodeURIComponent(itemId)}/reviews`, { method: 'POST', body: { rating, content } })
api.myReviews = () => request('/me/reviews')
