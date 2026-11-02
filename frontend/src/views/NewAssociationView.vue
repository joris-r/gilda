<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { createAssociation } from '../api'
import { useLocation } from '../location'

const { t } = useI18n()
const router = useRouter()
useLocation().value = {
  parent: { to: '/', screen: 'myAssociations.title' },
  screen: 'myAssociations.create',
}

const name = ref('')
const error = ref('')

async function create() {
  error.value = ''
  try {
    const association = await createAssociation(name.value)
    await router.push(`/associations/${association.id}`)
  } catch {
    error.value = t('error')
  }
}
</script>

<template>
  <h1>{{ t('myAssociations.create') }}</h1>
  <form class="panel" @submit.prevent="create">
    <label>
      {{ t('fields.name') }}
      <input v-model="name" required />
    </label>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="dialog-actions">
      <button type="submit">{{ t('myAssociations.submit') }}</button>
      <RouterLink to="/">{{ t('dialog.cancel') }}</RouterLink>
    </div>
  </form>
</template>
