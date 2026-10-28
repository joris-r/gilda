<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { ApiError, createAccount } from '../api'
import { useSession } from '../session'

const { t } = useI18n()
const router = useRouter()
const { user } = useSession()

const displayName = ref('')
const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    user.value = await createAccount(displayName.value, email.value, password.value)
    await router.push('/')
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 409 ? t('signUp.exists') : t('error')
  }
}
</script>

<template>
  <h1>{{ t('signUp.title') }}</h1>
  <form class="panel" @submit.prevent="submit">
    <label>
      {{ t('fields.displayName') }}
      <input v-model="displayName" autocomplete="nickname" required />
    </label>
    <label>
      {{ t('fields.email') }}
      <input v-model="email" type="email" autocomplete="email" required />
    </label>
    <label>
      {{ t('fields.password') }}
      <input
        v-model="password"
        type="password"
        autocomplete="new-password"
        minlength="8"
        required
      />
    </label>
    <p v-if="error" class="error">{{ error }}</p>
    <button type="submit">{{ t('signUp.submit') }}</button>
  </form>
  <p class="hint">
    {{ t('signUp.haveAccount') }}
    <RouterLink to="/">{{ t('signUp.signIn') }}</RouterLink>
  </p>
</template>
