<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ name: string; size?: number }>(), { size: 18 })
const style = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
  maskImage: `url('/icons/game-icon-pack/${props.name}.svg')`,
  WebkitMaskImage: `url('/icons/game-icon-pack/${props.name}.svg')`,
}))
</script>

<template><span class="game-icon" :style="style" aria-hidden="true" /></template>

<style scoped>
.game-icon { display: inline-block; flex: 0 0 auto; background: currentColor; mask-repeat: no-repeat; mask-position: center; mask-size: contain; -webkit-mask-repeat: no-repeat; -webkit-mask-position: center; -webkit-mask-size: contain; }
</style>
