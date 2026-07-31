import { createRouter, createWebHistory } from 'vue-router'
import { AuthStorage } from '@/utils/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页', requiresAuth: true },
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('@/views/Products.vue'),
    meta: { title: '产品管理', requiresAuth: true },
  },
  {
    path: '/boms',
    name: 'Boms',
    component: () => import('@/views/Boms.vue'),
    meta: { title: 'BOM管理', requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  document.title = to.meta.title as string || 'Mobile App'
  const requiresAuth = to.meta.requiresAuth !== false
  const isLoggedIn = AuthStorage.isLoggedIn()
  if (requiresAuth && !isLoggedIn) {
    next({ name: 'Login' })
  } else if (!requiresAuth && isLoggedIn && to.name === 'Login') {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
