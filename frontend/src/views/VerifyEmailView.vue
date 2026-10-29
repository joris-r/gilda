<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute } from 'vue-router'
import { verifyEmail } from '../api'

const { t } = useI18n()
const route = useRoute()
const confirmed = ref<boolean>()

onMounted(async () => {
  try {
    await verifyEmail(String(route.query.token ?? ''))
    confirmed.value = true
  } catch {
    confirmed.value = false
  }
})
</script>

<template>
  <p v-if="confirmed === true">{{ t('verifyEmail.confirmed') }}</p>
  <template v-else-if="confirmed === false">
    <p>{{ t('verifyEmail.invalid') }}</p>
    <RouterLink to="/signup">{{ t('signIn.createAccount') }}</RouterLink>
  </template>
</template>
