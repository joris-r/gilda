<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { getSession, signOut } from './api'
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

onMounted(async () => {
  user.value = (await getSession()) ?? null
})

watch(
  () => route.path,
  () => {
    location.value = {}
    menuOpen.value = false
  },
)

function closeMenu() {
  menuOpen.value = false
}

onMounted(() => document.addEventListener('click', closeMenu))
onBeforeUnmount(() => document.removeEventListener('click', closeMenu))

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
      <svg class="logo" viewBox="0 0 32 32" aria-hidden="true">
        <path
          d="M24.49 24.49A12 12 0 1 0 16 28V22"
          fill="none"
          stroke="currentColor"
          stroke-width="4"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <circle cx="16" cy="16" r="3" fill="var(--accent)" />
      </svg>
    </RouterLink>
    <p v-if="user" class="where">
      <RouterLink v-if="location.association" :to="`/associations/${location.association.id}`">{{
        location.association.name
      }}</RouterLink>
      <span v-if="location.association && location.screen" class="sep" aria-hidden="true">›</span>
      <span v-if="location.screen">{{ t(location.screen) }}</span>
    </p>
    <div class="top-actions">
      <div v-if="user" class="user" @click.stop>
        <button
          type="button"
          class="user-button"
          :aria-expanded="menuOpen"
          @click="menuOpen = !menuOpen"
        >
          {{ user.display_name }} <span aria-hidden="true">▾</span>
        </button>
        <div v-if="menuOpen" class="user-menu">
          <LanguageSelector />
          <button type="button" class="link" @click="leave">{{ t('signOut') }}</button>
        </div>
      </div>
      <LanguageSelector v-else />
    </div>
  </header>
  <main v-if="user !== undefined">
    <SignInView v-if="user === null && !route.meta.public" />
    <RouterView v-else />
  </main>
</template>
