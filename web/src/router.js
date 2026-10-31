import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import DiscoverView from './views/DiscoverView.vue'
import SearchView from './views/SearchView.vue'
import MeView from './views/MeView.vue'
import LoginView from './views/LoginView.vue'
import ItemView from './views/ItemView.vue'
import PostView from './views/PostView.vue'
import AboutView from './views/AboutView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/discover', name: 'discover', component: DiscoverView },
    { path: '/search', name: 'search', component: SearchView },
    { path: '/me', name: 'me', component: MeView },
    { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
    { path: '/items/:itemId', name: 'item', component: ItemView },
    { path: '/posts/:postId', name: 'post', component: PostView },
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
