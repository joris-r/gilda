<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { requestAccessLink } from '../api'

const { t } = useI18n()

const email = ref('')
const error = ref('')
const sentTo = ref('')

async function submit() {
  error.value = ''
  try {
    await requestAccessLink(email.value)
    sentTo.value = email.value
  } catch {
    error.value = t('error')
  }
}
</script>

<template>
  <h1>{{ t('signInLink.title') }}</h1>
  <p v-if="sentTo">{{ t('signInLink.sent', { email: sentTo }) }}</p>
  <form v-else class="panel" @submit.prevent="submit">
    <label>
      {{ t('fields.email') }}
      <input v-model="email" type="email" autocomplete="email" required />
    </label>
    <p v-if="error" class="error">{{ error }}</p>
    <button type="submit">{{ t('signInLink.submit') }}</button>
  </form>
  <p class="hint">
    <RouterLink to="/">{{ t('signInLink.back') }}</RouterLink>
  </p>
</template>
