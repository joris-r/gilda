<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { verifyEmail } from '../api'
import { useSession } from '../session'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { user } = useSession()
const invalid = ref(false)

onMounted(async () => {
  try {
    user.value = await verifyEmail(String(route.query.token ?? ''))
    await router.push('/')
  } catch {
    invalid.value = true
  }
})
</script>

<template>
  <template v-if="invalid">
    <p>{{ t('verifyEmail.invalid') }}</p>
    <RouterLink to="/signup">{{ t('signIn.createAccount') }}</RouterLink>
  </template>
</template>
