import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import DiscoverView from './views/DiscoverView.vue'
import SearchResultsView from './views/SearchResultsView.vue'
import MeView from './views/MeView.vue'
import LoginView from './views/LoginView.vue'
import ItemView from './views/ItemView.vue'
import PostView from './views/PostView.vue'
import AuthorView from './views/AuthorView.vue'
import CartView from './views/CartView.vue'
import CheckoutView from './views/CheckoutView.vue'
import OrdersView from './views/OrdersView.vue'
import AddressView from './views/AddressView.vue'
import SettingsView from './views/SettingsView.vue'
import WalletView from './views/WalletView.vue'
import MessagesView from './views/MessagesView.vue'
import ChatView from './views/ChatView.vue'
import ProfileView from './views/ProfileView.vue'
import AboutView from './views/AboutView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/discover', name: 'discover', component: DiscoverView },
    { path: '/search', name: 'search', component: SearchResultsView },
    { path: '/me', name: 'me', component: MeView },
    { path: '/me/profile', name: 'profile', component: ProfileView },
    { path: '/me/wallet', name: 'wallet', component: WalletView },
    { path: '/me/orders', name: 'orders', component: OrdersView },
    { path: '/me/address', name: 'address', component: AddressView },
    { path: '/me/settings', name: 'settings', component: SettingsView },
    { path: '/messages', name: 'messages', component: MessagesView },
    { path: '/messages/:id', name: 'chat', component: ChatView },
    { path: '/cart', name: 'cart', component: CartView },
    { path: '/checkout', name: 'checkout', component: CheckoutView },
    { path: '/items/:itemId', name: 'item', component: ItemView },
    { path: '/posts/:postId', name: 'post', component: PostView },
    { path: '/authors/:authorId', name: 'author', component: AuthorView },
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/about', name: 'about', component: AboutView, meta: { public: true } }
  ]
})

router.beforeEach((to) => {
  const loggedIn = Boolean(localStorage.getItem('gt_token'))
  if (!to.meta.public && !loggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
