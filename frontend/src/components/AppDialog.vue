<script lang="ts">
/** The close functions of the open dialogs, innermost last: Escape closes only the innermost. */
const open: (() => void)[] = []
let ids = 0

function onEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') open[open.length - 1]?.()
}
</script>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

/** A modal dialog: with a title for a form, without one for a confirmation. */
const props = defineProps<{ title?: string }>()
const emit = defineEmits<{ close: [] }>()
const { t } = useI18n()

const id = `dialog-${++ids}`
const panel = ref<HTMLElement>()
const close = () => emit('close')

onMounted(async () => {
  if (open.length === 0) document.addEventListener('keydown', onEscape)
  open.push(close)
  await nextTick()
  panel.value?.querySelector<HTMLElement>('input, select, button[data-default]')?.focus()
})

onBeforeUnmount(() => {
  open.splice(open.indexOf(close), 1)
  if (open.length === 0) document.removeEventListener('keydown', onEscape)
})

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  // Handled here, so the document listener and any outer dialog leave it alone.
  event.stopPropagation()
  close()
}
</script>

<template>
  <div class="scrim" @click.self="close">
    <div
      ref="panel"
      class="dialog"
      :role="props.title ? 'dialog' : 'alertdialog'"
      aria-modal="true"
      :aria-labelledby="props.title ? id : undefined"
      @keydown="onKeydown"
    >
      <div v-if="props.title" class="dialog-head">
        <h2 :id="id">{{ props.title }}</h2>
        <button type="button" class="icon-button" :aria-label="t('dialog.close')" @click="close">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      </div>
      <slot />
    </div>
  </div>
</template>
