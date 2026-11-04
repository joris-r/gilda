<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'
import { createAssociation } from '../api'
import SlugField from '../components/SlugField.vue'
import { useLocation } from '../location'
import { slugErrorKey, slugFromName } from '../slug'

const { t } = useI18n()
const router = useRouter()
useLocation().value = {
  parent: { to: '/', screen: 'myAssociations.title' },
  screen: 'myAssociations.create',
}

const name = ref('')
const slug = ref('')
// Association identifier follows Name until the user edits it.
const slugEdited = ref(false)
const error = ref('')

watch(name, (value) => {
  if (!slugEdited.value) slug.value = slugFromName(value)
})

function editSlug(value: string) {
  slug.value = value
  slugEdited.value = true
}

async function create() {
  error.value = ''
  try {
    const association = await createAssociation(name.value, slug.value)
    await router.push(`/association/${association.slug}`)
  } catch (e) {
    error.value = t(slugErrorKey(e))
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
    <SlugField :model-value="slug" @update:model-value="editSlug" />
    <p v-if="error" class="error">{{ error }}</p>
    <div class="dialog-actions">
      <button type="submit" :disabled="!name || !slug">{{ t('myAssociations.submit') }}</button>
      <RouterLink to="/">{{ t('dialog.cancel') }}</RouterLink>
    </div>
  </form>
</template>
