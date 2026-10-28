import { createRouter, createWebHistory, type RouterHistory } from 'vue-router'
import StatusView from '../views/StatusView.vue'

export function createGildaRouter(history: RouterHistory = createWebHistory()) {
  return createRouter({
    history,
    routes: [{ path: '/', name: 'status', component: StatusView }],
  })
}
