<script setup lang="ts">
import { RouterView } from 'vue-router'
import LanguageSelector from './components/LanguageSelector.vue'
</script>

<template>
  <header>
    <LanguageSelector />
  </header>
  <RouterView />
</template>
