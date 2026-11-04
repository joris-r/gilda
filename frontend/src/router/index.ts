import { createRouter, createWebHistory, type RouterHistory } from 'vue-router'
import CreateAccountView from '../views/CreateAccountView.vue'
import AccessLinkView from '../views/AccessLinkView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import MyAvailabilityView from '../views/MyAvailabilityView.vue'
import MembersView from '../views/MembersView.vue'
import MyAssociationsView from '../views/MyAssociationsView.vue'
import NewAssociationView from '../views/NewAssociationView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'
import ScheduleSettingsView from '../views/ScheduleSettingsView.vue'
import ScheduleView from '../views/ScheduleView.vue'
import SharedScheduleView from '../views/SharedScheduleView.vue'
import SignInLinkView from '../views/SignInLinkView.vue'
import VerifyEmailView from '../views/VerifyEmailView.vue'

/** Routes not marked public show Sign in while signed out (see App.vue). */
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
      {
        path: '/forgot-password',
        name: 'forgot-password',
        component: ForgotPasswordView,
        meta: { public: true },
      },
      {
        path: '/reset-password',
        name: 'reset-password',
        component: ResetPasswordView,
        meta: { public: true },
      },
      {
        path: '/sign-in-link',
        name: 'sign-in-link',
        component: SignInLinkView,
        meta: { public: true },
      },
      { path: '/access', name: 'access', component: AccessLinkView, meta: { public: true } },
      {
        path: '/shared/:token',
        name: 'shared-schedule',
        component: SharedScheduleView,
        props: true,
        meta: { public: true, shared: true },
      },
      { path: '/association/new', name: 'new-association', component: NewAssociationView },
      { path: '/association/:slug', name: 'schedule', component: ScheduleView, props: true },
      {
        path: '/association/:slug/members',
        name: 'members',
        component: MembersView,
        props: true,
      },
      {
        path: '/association/:slug/settings',
        name: 'settings',
        component: ScheduleSettingsView,
        props: true,
      },
      {
        path: '/association/:slug/availability',
        name: 'availability',
        component: MyAvailabilityView,
        props: true,
      },
    ],
  })
}
