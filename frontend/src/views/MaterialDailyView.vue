<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import type { Material } from '../types'
import PageHeader from '../components/PageHeader.vue'
import { useRouter } from 'vue-router'
const router = useRouter()
interface Row { material: Material; inbound: number; outbound: number; opening: number; closing: number; document_inbound: number; document_outbound: number; version: number; savedIn: number; savedOut: number }
const today = new Date()
const businessDate = ref(`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`)
const selectedMaterialIds = ref<number[]>([])
const rows = ref<Row[]>([]), loading = ref(false), saving = ref<number | null>(null), loadError = ref(''), saved = ref('')
const filtered = computed(() => rows.value.filter(row => !selectedMaterialIds.value.length || selectedMaterialIds.value.includes(row.material.id)))
const materialLabel = (material: Material) => `${material.name}${material.specification ? `（${material.specification}）` : ''}`
const busy = computed(() => loading.value || saving.value !== null)
const number = (value: string | number) => Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
const normalize = (row: Row): Row => ({ ...row, inbound: Number(row.inbound), outbound: Number(row.outbound), savedIn: Number(row.inbound), savedOut: Number(row.outbound) })
async function load() {
  loading.value = true; loadError.value = ''; saved.value = ''; rows.value = []
  try {
    const { data } = await api.get('/material-daily', { params: { business_date: businessDate.value } })
    rows.value = data.items.filter((row: Row) => row.material.is_active).map(normalize)
    const available = new Set(rows.value.map(row => row.material.id))
    selectedMaterialIds.value = selectedMaterialIds.value.filter(id => available.has(id))
  }
  catch (err) { loadError.value = errorMessage(err) } finally { loading.value = false }
}
async function save(row: Row) {
  if (row.inbound === row.savedIn && row.outbound === row.savedOut) return
  if (row.inbound == null || row.outbound == null || !Number.isFinite(row.inbound) || !Number.isFinite(row.outbound)) {
    row.inbound = row.savedIn; row.outbound = row.savedOut; ElMessage.warning('请输入有效数量，清零请填写 0'); return
  }
  saving.value = row.material.id; saved.value = ''
  try {
    const { data } = await api.put(`/material-daily/${row.material.id}`, { inbound: row.inbound, outbound: row.outbound, version: row.version }, { params: { business_date: businessDate.value } })
    Object.assign(row, normalize(data)); saved.value = `${row.material.name} 已自动保存`
  } catch (err) { row.inbound = row.savedIn; row.outbound = row.savedOut; ElMessage.error(errorMessage(err)) }
  finally { saving.value = null }
}
const copying = ref(false)
async function copyInformation() {
  if (busy.value || loadError.value || !rows.value.length) return
  const lines = rows.value.map((row, index) => {
    const material = row.material
    const unit = material.material_unit
    const incoming = row.savedIn + Number(row.document_inbound)
    const outgoing = row.savedOut + Number(row.document_outbound)
    const change = Math.round((incoming - outgoing) * 100) / 100
    const converted = material.conversion_enabled
      ? `（折合 ${number(Number(row.closing) * Number(material.conversion_ratio))} ${material.stock_unit}）` : ''
    return `${index + 1}. ${material.name}${material.specification ? `（${material.specification}）` : ''}\n` +
      `期初：${number(row.opening)} ${unit}；入库：${number(incoming)} ${unit}；出库：${number(outgoing)} ${unit}；净变更：${change > 0 ? '+' : ''}${number(change)} ${unit}\n` +
      `当日剩余：${number(row.closing)} ${unit}${converted}；当前总库存：${number(material.stock)} ${unit}`
  })
  const text = [`原材料出入库信息`, `日期：${businessDate.value}`, '入库、出库数量包含已生效单据。', '', lines.join('\n\n')].join('\n')
  copying.value = true
  try {
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      textarea.setAttribute('readonly', '')
      document.body.appendChild(textarea)
      try {
        textarea.select()
        if (!document.execCommand('copy')) throw new Error('复制失败，请检查浏览器剪贴板权限后重试')
      } finally { textarea.remove() }
    }
    ElMessage.success(`已复制 ${rows.value.length} 项原材料信息`)
  } catch { ElMessage.error('复制失败，请检查浏览器剪贴板权限后重试') }
  finally { copying.value = false }
}
onMounted(load)
</script>
<template>
  <div>
    <PageHeader title="原材料出入库管理" description="仅展示启用的原材料，选择日期后直接修改当天出入库数量。">
      <el-button :disabled="busy || !!loadError || !rows.length" :loading="copying" @click="copyInformation">复制信息</el-button>
      <el-button v-if="has('material_daily_logs:view')" :disabled="busy" @click="router.push('/material-daily-logs')">出入库日志</el-button>
    </PageHeader>
    <section class="surface daily-materials">
      <div class="surface-header toolbar">
        <span>业务日期</span><el-date-picker v-model="businessDate" type="date" value-format="YYYY-MM-DD" :clearable="false" :editable="false" :disabled="busy" @change="load" />
        <el-select v-model="selectedMaterialIds" class="material-filter" multiple filterable clearable collapse-tags collapse-tags-tooltip :max-collapse-tags="2" :disabled="busy" placeholder="全部启用原材料（可多选）" aria-label="筛选原材料" no-match-text="没有匹配的原材料" no-data-text="暂无启用的原材料">
          <el-option v-for="row in rows" :key="row.material.id" :label="materialLabel(row.material)" :value="row.material.id" />
        </el-select>
        <el-button :disabled="busy" @click="load">刷新</el-button><span class="grow" /><span class="muted" role="status">{{ saving !== null ? '正在保存…' : saved || `共 ${filtered.length} 项` }}</span>
      </div>
      <div class="entry-help">按物料单位填写，输入完成后自动保存。剩余 = 期初 + 当天入库 − 当天出库 + 单据入库 − 单据出库；单据数量来自已生效单据。</div>
      <el-alert v-if="loadError" :title="loadError" type="error" :closable="false" show-icon />
      <el-table v-loading="loading" :data="filtered" stripe row-key="material.id" empty-text="没有匹配的原材料，请在原材料档案中配置">
        <el-table-column label="原材料" min-width="170" fixed><template #default="{ row }"><strong>{{ row.material.name }}</strong><div class="muted">{{ row.material.specification || '无规格' }}</div></template></el-table-column>
        <el-table-column label="类型" width="115"><template #default="{ row }">{{ row.material.material_type === 'SCRAP' ? '废料' : '原料' }}</template></el-table-column>
        <el-table-column label="单位" width="75"><template #default="{ row }">{{ row.material.material_unit }}</template></el-table-column>
        <el-table-column label="期初结余" width="115" align="right"><template #default="{ row }">{{ number(row.opening) }}</template></el-table-column>
        <el-table-column label="当天入库" width="155"><template #default="{ row }"><el-input-number v-model="row.inbound" :aria-label="`${row.material.name}当天入库`" :min="0" :precision="2" :controls="false" :disabled="busy || !row.material.is_active || !has('material_daily:update')" @change="save(row)" /></template></el-table-column>
        <el-table-column label="当天出库" width="155"><template #default="{ row }"><el-input-number v-model="row.outbound" :aria-label="`${row.material.name}当天出库`" :min="0" :precision="2" :controls="false" :disabled="busy || !row.material.is_active || !has('material_daily:update')" @change="save(row)" /></template></el-table-column>
        <el-table-column label="单据入 / 出" width="125" align="right"><template #default="{ row }">{{ number(row.document_inbound) }} / {{ number(row.document_outbound) }}</template></el-table-column>
        <el-table-column label="当日剩余" width="130" align="right"><template #default="{ row }"><strong class="balance">{{ number(row.closing) }}</strong></template></el-table-column>
        <el-table-column label="换算后剩余" min-width="155" align="right"><template #default="{ row }"><span v-if="row.material.conversion_enabled">{{ number(Number(row.closing) * Number(row.material.conversion_ratio)) }} {{ row.material.stock_unit }}<div class="muted">1 {{ row.material.material_unit }} = {{ number(row.material.conversion_ratio) }} {{ row.material.stock_unit }}</div></span><span v-else>—</span></template></el-table-column>
        <el-table-column label="当前总库存" width="130" align="right"><template #default="{ row }">{{ number(row.material.stock) }}</template></el-table-column>
      </el-table>
    </section>

  </div>
</template>
<style scoped>
.toolbar { flex-wrap: wrap; gap: 12px; }
.material-filter { width: 320px; max-width: 100%; }
.entry-help { padding: 12px 20px; color: var(--ja-muted); font-size: 13px; line-height: 1.7; }
.el-input-number { width: 130px; }
.balance { color: var(--ja-red); font-variant-numeric: tabular-nums; }
.daily-materials { overflow: hidden; }
</style>
