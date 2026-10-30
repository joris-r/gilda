import { createRouter, createWebHistory, type RouterHistory } from 'vue-router'
import CreateAccountView from '../views/CreateAccountView.vue'
import MembersView from '../views/MembersView.vue'
import MyAssociationsView from '../views/MyAssociationsView.vue'
import ScheduleSettingsView from '../views/ScheduleSettingsView.vue'
import ScheduleView from '../views/ScheduleView.vue'
import VerifyEmailView from '../views/VerifyEmailView.vue'

/** Routes other than signup and verify-email show Sign in while signed out (see App.vue). */
export function createGildaRouter(history: RouterHistory = createWebHistory()) {
  return createRouter({
    history,
    routes: [
      { path: '/', name: 'my-associations', component: MyAssociationsView },
      { path: '/signup', name: 'signup', component: CreateAccountView, meta: { public: true } },
      {
        path: '/verify-email',
        name: 'verify-email',
        component: VerifyEmailView,
        meta: { public: true },
      },
      { path: '/associations/:id', name: 'schedule', component: ScheduleView, props: true },
      {
        path: '/associations/:id/members',
        name: 'members',
        component: MembersView,
        props: true,
      },
      {
        path: '/associations/:id/settings',
        name: 'settings',
        component: ScheduleSettingsView,
        props: true,
      },
    ],
  })
}
