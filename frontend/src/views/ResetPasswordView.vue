<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ApiError, resetPassword } from '../api'
import { useSession } from '../session'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { user } = useSession()

const password = ref('')
const error = ref('')
const invalid = ref(false)

async function submit() {
  error.value = ''
  try {
    user.value = await resetPassword(String(route.query.token ?? ''), password.value)
    await router.push('/')
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) invalid.value = true
    else error.value = t('error')
  }
}
</script>

<template>
  <template v-if="invalid">
    <p>{{ t('resetPassword.invalid') }}</p>
    <RouterLink to="/forgot-password">{{ t('resetPassword.requestNew') }}</RouterLink>
  </template>
  <template v-else>
    <h1>{{ t('resetPassword.title') }}</h1>
    <form class="panel" @submit.prevent="submit">
      <label>
        {{ t('resetPassword.password') }}
        <input
          v-model="password"
          type="password"
          autocomplete="new-password"
          minlength="8"
          required
        />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit">{{ t('resetPassword.submit') }}</button>
    </form>
  </template>
</template>
