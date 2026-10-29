import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import LoginView from './views/LoginView.vue'
import ItemView from './views/ItemView.vue'
import AboutView from './views/AboutView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/items/:itemId', name: 'item', component: ItemView },
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
