import { createRouter, createWebHistory, type RouterHistory } from 'vue-router'
import AssociationView from '../views/AssociationView.vue'
import CreateAccountView from '../views/CreateAccountView.vue'
import MyAssociationsView from '../views/MyAssociationsView.vue'
import OpeningHoursView from '../views/OpeningHoursView.vue'
import ScheduleView from '../views/ScheduleView.vue'

/** Routes other than signup show Sign in while signed out (see App.vue). */
export function createGildaRouter(history: RouterHistory = createWebHistory()) {
  return createRouter({
    history,
    routes: [
      { path: '/', name: 'my-associations', component: MyAssociationsView },
      { path: '/signup', name: 'signup', component: CreateAccountView, meta: { public: true } },
      { path: '/associations/:id', name: 'association', component: AssociationView, props: true },
      {
        path: '/associations/:id/schedule',
        name: 'schedule',
        component: ScheduleView,
        props: true,
      },
      {
        path: '/associations/:id/opening',
        name: 'opening',
        component: OpeningHoursView,
        props: true,
      },
    ],
  })
}
