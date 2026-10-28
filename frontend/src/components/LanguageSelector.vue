<script setup lang="ts">
import { watchEffect } from 'vue'
import { useI18n } from 'vue-i18n'
import { LOCALES, storeLocale, type Locale } from '../i18n'

const { t, locale } = useI18n()

const names: Record<Locale, string> = { en: 'English', fr: 'Français' }

watchEffect(() => {
  document.documentElement.lang = locale.value
})

function select(event: Event) {
  const value = (event.target as HTMLSelectElement).value as Locale
  locale.value = value
  storeLocale(value)
}
</script>

<template>
  <label>
    {{ t('language') }}
    <select :value="locale" @change="select">
      <option v-for="code in LOCALES" :key="code" :value="code">{{ names[code] }}</option>
    </select>
  </label>
</template>
