<script setup lang="ts">
import { onMounted } from 'vue'
import { loadMe } from './auth'

onMounted(loadMe)
</script>

<template>
  <router-view />
</template>

