<script setup lang="ts">
/** A button showing only an icon, named by `label`. */
defineProps<{ icon: 'edit' | 'delete' | 'note' | 'absence'; label: string }>()
</script>

<template>
  <button type="button" class="icon-button" :aria-label="label" :title="label">
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <template v-if="icon === 'edit'">
        <path d="M4 20h4L19 9l-4-4L4 16v4z" />
        <path d="M13.5 6.5l4 4" />
      </template>
      <template v-else-if="icon === 'note'">
        <path d="M4 5h16v11H9l-5 4V5z" />
        <path d="M8 9h8M8 12h5" />
      </template>
      <template v-else-if="icon === 'absence'">
        <path d="M4 21c3-1.5 13-1.5 16 0" />
        <path d="M10 20.5c.5-4 1.5-7.5 3-10.5" />
        <path d="M13 10c-1.5-2.5-4.5-3-7.5-1.5M13 10c2-2.5 5-2.5 7.5-.5" />
        <path d="M13 10c-.5-3-2.5-5-5.5-5.5M13 10c1-3 3-4.5 6-4.5" />
      </template>
      <path v-else d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6" />
    </svg>
  </button>
</template>
