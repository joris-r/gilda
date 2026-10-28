<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { getSession, signOut } from './api'
import LanguageSelector from './components/LanguageSelector.vue'
import { provideSession } from './session'
import SignInView from './views/SignInView.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { user } = provideSession()

onMounted(async () => {
  user.value = (await getSession()) ?? null
})

async function leave() {
  await signOut()
  user.value = null
  await router.push('/')
}
</script>

<template>
  <header class="top">
    <RouterLink to="/" class="brand" aria-label="Gilda">
      <svg class="logo" viewBox="0 0 32 32" aria-hidden="true">
        <path
          d="M24.49 7.51A12 12 0 1 0 28 16H21"
          fill="none"
          stroke="currentColor"
          stroke-width="4"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <circle cx="16" cy="16" r="3" fill="var(--accent)" />
      </svg>
    </RouterLink>
    <div class="top-actions">
      <template v-if="user">
        <span>{{ user.display_name }}</span>
        <button type="button" class="link" @click="leave">{{ t('signOut') }}</button>
      </template>
      <LanguageSelector />
    </div>
  </header>
  <main v-if="user !== undefined">
    <SignInView v-if="user === null && !route.meta.public" />
    <RouterView v-else />
  </main>
</template>
