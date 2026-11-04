<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

const { t } = useI18n()
</script>

<template>
  <p>{{ t('association.unknown') }}</p>
  <p>
    <RouterLink to="/">{{ t('myAssociations.title') }}</RouterLink>
  </p>
</template>
