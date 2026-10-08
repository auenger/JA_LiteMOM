<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api, { errorMessage } from '../api'
import type { ReceiptReport } from '../receiptWord'
import GameIcon from './GameIcon.vue'

const props = defineProps<{ inboundIds: number[]; outboundIds: number[] }>()
const emit = defineEmits<{ clear: [] }>()
const dialog = ref(false), loading = ref(false), exporting = ref(false)
const report = ref<ReceiptReport | null>(null)
function quantitySummary(direction: 'inbound' | 'outbound') {
  const grouped = new Map<string, { business_date: string; spec_name: string; quantity: number }>()
  for (const document of report.value?.documents.filter(item => item.direction === direction) || []) {
    for (const line of document.lines) {
      const key = `${document.business_date}|${line.spec_id}`
      const current = grouped.get(key) || { business_date: document.business_date, spec_name: line.spec_name, quantity: 0 }
      current.quantity += line.total
      grouped.set(key, current)
    }
  }
  return Array.from(grouped.values()).sort((a, b) => a.business_date.localeCompare(b.business_date) || a.spec_name.localeCompare(b.spec_name))
}
const inboundSummary = computed(() => quantitySummary('inbound'))
const outboundSummary = computed(() => quantitySummary('outbound'))
const qualitySummary = computed(() => (report.value?.documents || []).flatMap(document => document.quality_bottles.map(item => ({
  ...item, business_date: document.business_date,
}))).sort((a, b) => a.business_date.localeCompare(b.business_date) || a.spec_name.localeCompare(b.spec_name) || a.zone_name.localeCompare(b.zone_name)))
const inboundTotal = computed(() => inboundSummary.value.reduce((sum, item) => sum + item.quantity, 0))
const outboundTotal = computed(() => outboundSummary.value.reduce((sum, item) => sum + item.quantity, 0))
const qualityTotal = computed(() => qualitySummary.value.reduce((sum, item) => sum + item.quantity, 0))

async function open() {
  loading.value = true
  try {
    const { data } = await api.post<ReceiptReport>('/bottle-receipt/preview', { inbound_ids: props.inboundIds, outbound_ids: props.outboundIds })
    report.value = data
    dialog.value = true
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
async function download() {
  if (!report.value) return
  exporting.value = true
  try {
    const { buildReceiptWord } = await import('../receiptWord')
    const blob = await buildReceiptWord(report.value)
    const url = URL.createObjectURL(blob), link = document.createElement('a')
    link.href = url
    link.download = `出入库数据汇总-${report.value.customer.replace(/[\\/:*?"<>|]/g, '_')}.docx`
    document.body.appendChild(link); link.click(); link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 30000)
    ElMessage.success('Word 已导出')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { exporting.value = false }
}
</script>

<template>
  <div class="receipt-tools">
    <span>已选入库 {{ inboundIds.length }} 单、出库 {{ outboundIds.length }} 单（支持跨页）</span>
    <el-button :disabled="!inboundIds.length && !outboundIds.length" @click="emit('clear')">清空勾选</el-button>
    <el-button type="primary" :loading="loading" :disabled="!inboundIds.length && !outboundIds.length" @click="open"><GameIcon name="save" />导出 Word</el-button>
  </div>
  <el-dialog v-model="dialog" title="出入库数据汇总 · 导出预览" width="min(1020px, 94vw)" :close-on-click-modal="false">
    <div v-if="report" class="receipt-preview">
      <div class="receipt-summary"><strong>{{ report.customer }}</strong><span>相同日期、规格已合并数量</span></div>
      <section class="summary-section"><h3>入库汇总（共 {{ inboundTotal }} 只）</h3><table v-if="inboundSummary.length" class="preview-table"><thead><tr><th>入库日期</th><th>规格</th><th>数量</th></tr></thead><tbody><tr v-for="item in inboundSummary" :key="`${item.business_date}-${item.spec_name}`"><td>{{ item.business_date }}</td><td>{{ item.spec_name }}</td><td>{{ item.quantity }}</td></tr></tbody></table><p v-else class="empty-summary">无入库数据</p></section>
      <section class="summary-section"><h3>出库汇总（共 {{ outboundTotal }} 只）</h3><table v-if="outboundSummary.length" class="preview-table"><thead><tr><th>出库日期</th><th>规格</th><th>数量</th></tr></thead><tbody><tr v-for="item in outboundSummary" :key="`${item.business_date}-${item.spec_name}`"><td>{{ item.business_date }}</td><td>{{ item.spec_name }}</td><td>{{ item.quantity }}</td></tr></tbody></table><p v-else class="empty-summary">无出库数据</p></section>
      <section class="summary-section quality-detail"><h3>报废 / 不良品瓶子信息（共 {{ qualityTotal }} 只）</h3><table v-if="qualitySummary.length" class="preview-table"><thead><tr><th>日期</th><th>规格</th><th>类别</th><th>数量</th><th>瓶身编号</th><th>备注</th></tr></thead><tbody><tr v-for="item in qualitySummary" :key="`${item.business_date}-${item.zone}-${item.spec_id}-${item.body_code}`"><td>{{ item.business_date }}</td><td>{{ item.spec_name }}</td><td>{{ item.zone_name }}</td><td>{{ item.quantity }}</td><td class="numeric">{{ item.body_code || '未绑定瓶号' }}</td><td>{{ item.note || '-' }}</td></tr></tbody></table><p v-else class="empty-summary">无报废或不良品瓶子信息</p></section>
    </div>
    <template #footer><el-button @click="dialog = false">关闭</el-button><el-button type="primary" :loading="exporting" @click="download"><GameIcon name="save" />下载 Word</el-button></template>
  </el-dialog>
</template>

<style scoped>
.receipt-tools{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:12px 16px;border-bottom:1px solid var(--ja-border)}.receipt-tools>span{margin-right:auto;color:var(--ja-muted);font-size:13px}.receipt-preview{max-height:68vh;overflow:auto;padding-right:6px}.receipt-summary{display:flex;gap:12px;justify-content:space-between;flex-wrap:wrap;padding:12px;background:#f3f6f9;border:1px solid #e2e8f0;border-radius:6px}.receipt-summary span,.empty-summary{color:var(--ja-muted)}.summary-section{margin-top:18px}.summary-section h3{margin:0 0 8px;font-size:14px}.empty-summary{margin:0;padding:12px;background:#f7f8f9;border-radius:7px;font-size:12px}.preview-table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;border:1px solid var(--ja-line);border-radius:7px;font-size:12px}.preview-table th,.preview-table td{padding:8px 10px;border-right:1px solid var(--ja-line);border-bottom:1px solid var(--ja-line);text-align:right}.preview-table th:first-child,.preview-table td:first-child,.quality-detail .preview-table th:last-child,.quality-detail .preview-table td:last-child{text-align:left}.preview-table th{color:var(--ja-muted);background:#f5f7f8}.preview-table th:last-child,.preview-table td:last-child{border-right:0}.preview-table tbody tr:last-child td{border-bottom:0}@media(max-width:600px){.receipt-tools>span{width:100%}.receipt-preview{max-height:65vh}}
</style>
