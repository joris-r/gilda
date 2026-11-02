<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppDialog from './AppDialog.vue'

defineProps<{ question: string; action: string }>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()
const { t } = useI18n()
</script>

<template>
  <AppDialog @close="emit('cancel')">
    <p class="question">{{ question }}</p>
    <div class="dialog-actions">
      <button type="button" data-default @click="emit('confirm')">{{ action }}</button>
      <button type="button" class="link" @click="emit('cancel')">{{ t('dialog.cancel') }}</button>
    </div>
  </AppDialog>
</template>

<style scoped>
.question {
  margin: 0 0 16px;
}
</style>
