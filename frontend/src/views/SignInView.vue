<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ApiError, signIn } from '../api'
import { useSession } from '../session'

const { t } = useI18n()
const { user } = useSession()

const email = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    user.value = await signIn(email.value, password.value)
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 401 ? t('signIn.wrong') : t('error')
  }
}
</script>

<template>
  <h1>{{ t('signIn.title') }}</h1>
  <form class="panel" @submit.prevent="submit">
    <label>
      {{ t('fields.email') }}
      <input v-model="email" type="email" autocomplete="email" required />
    </label>
    <label>
      {{ t('fields.password') }}
      <input v-model="password" type="password" autocomplete="current-password" required />
    </label>
    <p v-if="error" class="error">{{ error }}</p>
    <button type="submit">{{ t('signIn.submit') }}</button>
  </form>
  <p class="hint">
    {{ t('signIn.noAccount') }}
    <RouterLink to="/signup">{{ t('signIn.createAccount') }}</RouterLink>
  </p>
</template>
