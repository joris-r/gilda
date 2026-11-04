<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const slug = defineModel<string>({ required: true })
const { t } = useI18n()
</script>

<template>
  <label>
    {{ t('fields.associationIdentifier') }}
    <span class="slug-field">
      <span class="hint">/associations/</span>
      <input v-model="slug" autocomplete="off" maxlength="50" />
    </span>
  </label>
</template>

<style scoped>
.slug-field {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.slug-field input {
  flex: 1;
  min-width: 0;
}
</style>
