<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ApiError, createAccount, resendVerification } from '../api'

const { t } = useI18n()

const displayName = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const createdEmail = ref('')
const resent = ref(false)

async function submit() {
  error.value = ''
  try {
    await createAccount(displayName.value, email.value, password.value)
    createdEmail.value = email.value
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 409 ? t('signUp.exists') : t('error')
  }
}

async function resend() {
  resent.value = false
  await resendVerification(createdEmail.value)
  resent.value = true
}
</script>

<template>
  <template v-if="createdEmail">
    <h1>{{ t('signUp.title') }}</h1>
    <p>{{ t('signUp.checkEmail', { email: createdEmail }) }}</p>
    <button type="button" class="link" @click="resend">{{ t('signUp.resend') }}</button>
    <p v-if="resent" class="ok">{{ t('signUp.resent') }}</p>
  </template>
  <template v-else>
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
</template>
