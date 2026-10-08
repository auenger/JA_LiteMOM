<script setup lang="ts">
import GameIcon from './GameIcon.vue'
defineProps<{ title?: string; description?: string }>()
</script>

<template>
  <div class="empty-state">
    <GameIcon name="chest" :size="38" />
    <strong>{{ title || '暂无数据' }}</strong>
    <span>{{ description || '完成第一笔录入后，数据会显示在这里。' }}</span>
    <slot />
  </div>
</template>
