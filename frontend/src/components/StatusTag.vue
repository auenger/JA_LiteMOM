<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()
const labels: Record<string, string> = {
  DRAFT: '草稿', POSTED: '已生效', CONFIRMED: '已确认', VOID: '已作废',
  DISABLED: '不预警', NORMAL: '库存正常', LOW: '库存不足',
  PENDING: '待检测', GOOD: '良品', BAD: '不良品', SCRAP: '报废', ACTIVE: '有效', SPLIT_EMPTY: '已拆空',
  CODED: '已抄码待检测', INSPECTED: '检测完成',
}
const type = computed(() => {
  if (['POSTED', 'CONFIRMED', 'NORMAL', 'GOOD', 'ACTIVE'].includes(props.status)) return 'success'
  if (['LOW', 'BAD', 'SCRAP', 'VOID'].includes(props.status)) return 'danger'
  if (['DRAFT', 'PENDING', 'CODED'].includes(props.status)) return 'warning'
  return 'info'
})
</script>

<template><el-tag :type="type" effect="light" size="small">{{ labels[status] || status }}</el-tag></template>
