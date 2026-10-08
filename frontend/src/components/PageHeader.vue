<script setup lang="ts">
defineProps<{ title: string; description: string }>()
</script>

<template>
  <div class="page-header">
    <div>
      <div class="breadcrumb">锦安特种设备检测 / {{ title }}</div>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
    <div class="page-actions"><slot /></div>
  </div>
</template>
