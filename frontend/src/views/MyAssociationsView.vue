<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { createAssociation, listAssociations, type AssociationSummary } from '../api'
import { useLocation } from '../location'

const { t } = useI18n()
const router = useRouter()
useLocation().value = { screen: 'myAssociations.title' }

const associations = ref<AssociationSummary[]>()
const creating = ref(false)
const name = ref('')
const error = ref('')

onMounted(async () => {
  associations.value = await listAssociations()
})

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
  <div class="toolbar">
    <button
      type="button"
      class="icon"
      :aria-label="t('myAssociations.create')"
      :title="t('myAssociations.create')"
      :aria-expanded="creating"
      @click="creating = !creating"
    >
      +
    </button>
  </div>
  <template v-if="associations">
    <ul v-if="associations.length" class="list">
      <li v-for="association in associations" :key="association.id">
        <RouterLink :to="`/associations/${association.id}`">{{ association.name }}</RouterLink>
        <span :class="['role', association.role]">{{ t(`roles.${association.role}`) }}</span>
      </li>
    </ul>
    <p v-else class="hint">{{ t('myAssociations.none') }}</p>
  </template>
  <template v-if="creating">
    <h2>{{ t('myAssociations.create') }}</h2>
    <form class="panel" @submit.prevent="create">
      <label>
        {{ t('fields.name') }}
        <input v-model="name" required />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit">{{ t('myAssociations.submit') }}</button>
    </form>
  </template>
</template>
