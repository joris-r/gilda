<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { getHealth } from '../api'

type State = 'checking' | 'reachable' | 'unreachable' | 'unknown'

const { t } = useI18n()

const api = ref<State>('checking')
const database = ref<State>('checking')

onMounted(async () => {
  const health = await getHealth()
  if (health === undefined) {
    api.value = 'unreachable'
    database.value = 'unknown'
    return
  }
  api.value = 'reachable'
  database.value = health.database === 'ok' ? 'reachable' : 'unreachable'
})
</script>

<template>
  <main>
    <h1>{{ t('status.title') }}</h1>
    <p>{{ t('status.api', { state: t(`status.state.${api}`) }) }}</p>
    <p>{{ t('status.database', { state: t(`status.state.${database}`) }) }}</p>
  </main>
</template>
