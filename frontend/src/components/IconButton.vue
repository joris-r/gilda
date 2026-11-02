<script setup lang="ts">
/** A button showing only an icon, named by `label`. */
defineProps<{ icon: 'edit' | 'delete'; label: string }>()
</script>

<template>
  <button type="button" class="icon-button" :aria-label="label" :title="label">
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <template v-if="icon === 'edit'">
        <path d="M4 20h4L19 9l-4-4L4 16v4z" />
        <path d="M13.5 6.5l4 4" />
      </template>
      <path v-else d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" />
    </svg>
  </button>
</template>
