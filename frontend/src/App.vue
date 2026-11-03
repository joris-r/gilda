<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { deleteAccount, getSession, revokeAccessLink, signOut } from './api'
import ConfirmDialog from './components/ConfirmDialog.vue'
import LanguageSelector from './components/LanguageSelector.vue'
import { provideLocation } from './location'
import { provideSession } from './session'
import SignInView from './views/SignInView.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { user } = provideSession()
const location = provideLocation()
const menuOpen = ref(false)
const confirmingRevoke = ref(false)
const confirmingDelete = ref(false)
const notice = ref('')

onMounted(async () => {
  user.value = (await getSession()) ?? null
})

watch(
  () => route.path,
  () => {
    location.value = {}
    closeMenu()
    notice.value = ''
  },
)

function closeMenu() {
  menuOpen.value = false
  confirmingRevoke.value = false
}

onMounted(() => document.addEventListener('click', closeMenu))
onBeforeUnmount(() => document.removeEventListener('click', closeMenu))

async function revokeLink() {
  closeMenu()
  await revokeAccessLink()
  // R23: a session opened with the link is signed out with it.
  user.value = (await getSession()) ?? null
  if (user.value === null) {
    location.value = {}
    await router.push('/')
  } else {
    notice.value = t('accessLink.revoked')
  }
}

function askDelete() {
  closeMenu()
  confirmingDelete.value = true
}

async function deleteMyAccount() {
  confirmingDelete.value = false
  await deleteAccount()
  user.value = null
  location.value = {}
  await router.push('/')
}

async function leave() {
  menuOpen.value = false
  await signOut()
  user.value = null
  location.value = {}
  await router.push('/')
}
</script>

<template>
  <header class="top">
    <RouterLink to="/" class="brand" aria-label="Gilda">
      <img class="logo" src="/favicon.svg" alt="" />
    </RouterLink>
    <p v-if="location.title" class="where">
      <span>{{ location.title }}</span>
    </p>
    <p v-else-if="user" class="where">
      <RouterLink v-if="location.association" :to="`/associations/${location.association.id}`">{{
        location.association.name
      }}</RouterLink>
      <RouterLink v-if="location.parent" :to="location.parent.to">{{
        t(location.parent.screen)
      }}</RouterLink>
      <span
        v-if="(location.association || location.parent) && location.screen"
        class="sep"
        aria-hidden="true"
        >›</span
      >
      <span v-if="location.screen">{{ t(location.screen) }}</span>
    </p>
    <div class="top-actions">
      <div v-if="user && !route.meta.shared" class="user" @click.stop>
        <button
          type="button"
          class="user-button"
          :aria-expanded="menuOpen"
          @click="menuOpen ? closeMenu() : (menuOpen = true)"
        >
          {{ user.display_name }} <span aria-hidden="true">▾</span>
        </button>
        <div v-if="menuOpen" class="user-menu">
          <LanguageSelector />
          <template v-if="confirmingRevoke">
            <span class="sub">{{ t('accessLink.confirmRevoke') }}</span>
            <div class="actions">
              <button type="button" @click="revokeLink">{{ t('association.confirm') }}</button>
              <button type="button" class="link" @click="confirmingRevoke = false">
                {{ t('association.cancel') }}
              </button>
            </div>
          </template>
          <button v-else type="button" class="link" @click="confirmingRevoke = true">
            {{ t('accessLink.revoke') }}
          </button>
          <button type="button" class="link" @click="askDelete">{{ t('account.delete') }}</button>
          <button type="button" class="link" @click="leave">{{ t('signOut') }}</button>
        </div>
      </div>
      <LanguageSelector v-else />
    </div>
  </header>
  <ConfirmDialog
    v-if="confirmingDelete"
    :question="t('account.confirmDelete')"
    :action="t('account.delete')"
    @confirm="deleteMyAccount"
    @cancel="confirmingDelete = false"
  />
  <main v-if="user !== undefined">
    <p v-if="notice" class="ok">{{ notice }}</p>
    <SignInView v-if="user === null && !route.meta.public" />
    <RouterView v-else />
  </main>
</template>
