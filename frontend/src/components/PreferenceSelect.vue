<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { PreferenceValue } from '../api'

const VALUES: PreferenceValue[] = ['preferred', 'possible', 'unavailable']

defineProps<{ value: PreferenceValue | null }>()
const emit = defineEmits<{ change: [value: PreferenceValue | null] }>()
const { t } = useI18n()

function select(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  emit('change', value === '' ? null : (value as PreferenceValue))
}
</script>

<template>
  <select :value="value ?? ''" :class="value && `preference-${value}`" @change="select">
    <option value="">{{ t('settings.noPreference') }}</option>
    <option v-for="v in VALUES" :key="v" :value="v">{{ t(`preferences.${v}`) }}</option>
  </select>
</template>
