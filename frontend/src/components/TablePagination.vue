<script setup lang="ts">
defineProps<{ page: number; pageSize: number; total: number }>()
const emit = defineEmits<{ change: [page: number, pageSize: number] }>()
</script>

<template>
  <div v-if="total > 0" class="table-pagination">
    <el-pagination :current-page="page" :page-size="pageSize" :page-sizes="[10, 20, 50, 100]" :total="total" layout="total, sizes, prev, pager, next" background @update:current-page="emit('change', $event, pageSize)" @update:page-size="emit('change', 1, $event)" />
  </div>
</template>

<style scoped>.table-pagination{display:flex;justify-content:flex-end;padding:16px 18px;border-top:1px solid var(--ja-line)}@media(max-width:760px){.table-pagination{overflow-x:auto;justify-content:flex-start}}</style>
