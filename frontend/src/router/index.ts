import { createRouter, createWebHistory, type RouterHistory } from 'vue-router'
import AssociationView from '../views/AssociationView.vue'
import CreateAccountView from '../views/CreateAccountView.vue'
import MyAssociationsView from '../views/MyAssociationsView.vue'

/** Routes other than signup show Sign in while signed out (see App.vue). */
export function createGildaRouter(history: RouterHistory = createWebHistory()) {
  return createRouter({
    history,
    routes: [
      { path: '/', name: 'my-associations', component: MyAssociationsView },
      { path: '/signup', name: 'signup', component: CreateAccountView, meta: { public: true } },
      { path: '/associations/:id', name: 'association', component: AssociationView, props: true },
    ],
  })
}
