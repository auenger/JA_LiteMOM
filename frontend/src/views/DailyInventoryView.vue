<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import PageHeader from '../components/PageHeader.vue'
import InventoryImageCopy from '../components/InventoryImageCopy.vue'

type Metric =
  | 'INBOUND_PENDING' | 'INBOUND_TEMPORARY' | 'INBOUND_SCRAP'
  | 'OUTBOUND_PENDING' | 'OUTBOUND_TEMPORARY' | 'OUTBOUND_SCRAP' | 'OUTBOUND_BAD'
  | 'BALANCE_PENDING' | 'BALANCE_TEMPORARY' | 'BALANCE_SCRAP' | 'BALANCE_BAD'
interface MonthOption { key: string; label: string }
interface InventoryRow {
  metric: Metric
  category: string
  category_label: string
  category_first: boolean
  category_rowspan: number
  spec_id: number
  spec_name: string
  values: Record<string, number>
  modified_months: string[]
  summary: number
}
interface InventoryTable {
  rows: InventoryRow[]
  totals: Record<string, number>
  summary: number
}
interface Report {
  date_from: string
  date_to: string
  months: MonthOption[]
  source_id: number | null
  source_name: string
  editable: boolean
  sources: Array<{ id: number; name: string; is_active: boolean }>
  tables: { inbound: InventoryTable; outbound: InventoryTable; balance: InventoryTable }
}

const now = new Date()
const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
const monthRange = ref<[string, string]>([`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`, today])
const sourceId = ref<number | null>(null)
const loading = ref(false)
const loadError = ref('')
const report = ref<Report | null>(null)
const editing = ref<{ metric: Metric; specId: number; month: string } | null>(null)
const draftValue = ref(0)
const savingKey = ref('')
const logDrawer = ref(false)
const logLoading = ref(false)
const logs = ref<any[]>([])
const logPage = ref(1)
const logTotal = ref(0)

const canUpdate = computed(() => has('daily_inventory:update'))
const tableConfigs = computed(() => report.value ? [
  { key: 'inbound' as const, title: '入库', description: '按待检、暂存、报废分别汇总已生效入库单', summaryLabel: '区间入库' },
  { key: 'outbound' as const, title: '出库', description: '按待检验、暂存、报废、不良品分别汇总已生效出库单', summaryLabel: '区间出库' },
  { key: 'balance' as const, title: '结余', description: '待检结余扣除已进入良品、不良品库的钢瓶，后续出库不重复扣减；不良品负数表示累计出库扣减', summaryLabel: '期末结余' },
] : [])

const imageCards = computed(() => report.value ? tableConfigs.value.map(config => ({ title: config.title, summaryLabel: config.summaryLabel, ...report.value!.tables[config.key] })) : [])

function cellKey(metric: Metric, specId: number, month: string) {
  return `${metric}-${specId}-${month}`
}

function isEditing(metric: Metric, specId: number, month: string) {
  return editing.value?.metric === metric && editing.value.specId === specId && editing.value.month === month
}

function isModified(row: InventoryRow, month: string) {
  return row.modified_months.includes(month)
}

async function loadReport(showLoading = true) {
  if (!monthRange.value?.[0] || !monthRange.value?.[1]) return ElMessage.warning('请选择日度区间')
  if (showLoading) loading.value = true
  loadError.value = ''
  try {
    const params: Record<string, string | number> = { date_from: monthRange.value[0], date_to: monthRange.value[1] }
    if (sourceId.value !== null) params.source_id = sourceId.value
    report.value = (await api.get('/daily-inventory', { params })).data
  } catch (err) {
    loadError.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function beginEdit(metric: Metric, row: InventoryRow, month: string) {
  if (!canUpdate.value || !report.value?.editable || savingKey.value) return
  if (report.value.source_id !== sourceId.value || report.value.date_from !== monthRange.value[0] || report.value.date_to !== monthRange.value[1]) {
    ElMessage.warning('筛选条件已变化，请先查询再修改')
    return
  }
  editing.value = { metric, specId: row.spec_id, month }
  draftValue.value = row.values[month]
  await nextTick()
  const input = document.querySelector<HTMLInputElement>(`[data-edit-key="${cellKey(metric, row.spec_id, month)}"] input`)
  input?.focus()
  input?.select()
}

function cancelEdit() {
  editing.value = null
}

async function saveEdit() {
  const target = editing.value
  if (!target || report.value?.source_id === null || !report.value) return
  const value = Math.max(0, Math.trunc(Number(draftValue.value) || 0))
  const key = cellKey(target.metric, target.specId, target.month)
  editing.value = null
  savingKey.value = key
  try {
    const response = await api.put('/daily-inventory/value', {
      business_date: target.month,
      source_id: report.value.source_id,
      spec_id: target.specId,
      metric: target.metric,
      value,
    })
    if (response.data.changed) {
      ElMessage.success(`已从 ${response.data.old_value} 修改为 ${response.data.new_value}，变更日志已保存`)
      await loadReport(false)
    }
  } catch (err) {
    ElMessage.error(errorMessage(err))
    await loadReport(false)
  } finally {
    savingKey.value = ''
  }
}

async function openLogs() {
  logDrawer.value = true
  logPage.value = 1
  await loadLogs()
}

async function loadLogs() {
  logLoading.value = true
  try {
    const params: Record<string, string | number> = {
      date_from: monthRange.value[0], date_to: monthRange.value[1], page: logPage.value, page_size: 20,
    }
    if (sourceId.value !== null) params.source_id = sourceId.value
    const { data } = await api.get('/daily-inventory/logs', { params })
    logs.value = data.items
    logTotal.value = data.total
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    logLoading.value = false
  }
}

function metricName(metric: Metric | string) {
  const names: Record<string, string> = {
    INBOUND_PENDING: '入库 / 待检', INBOUND_TEMPORARY: '入库 / 暂存', INBOUND_SCRAP: '入库 / 报废',
    OUTBOUND_PENDING: '出库 / 待检验', OUTBOUND_TEMPORARY: '出库 / 暂存', OUTBOUND_SCRAP: '出库 / 报废', OUTBOUND_BAD: '出库 / 不良品',
    BALANCE_PENDING: '结余 / 待检', BALANCE_TEMPORARY: '结余 / 暂存', BALANCE_SCRAP: '结余 / 报废', BALANCE_BAD: '结余 / 不良品',
    INBOUND: '入库（历史）', OUTBOUND: '出库（历史）', BALANCE: '结余（历史）',
  }
  return names[metric] || metric
}

function formatTime(value: string) {
  return value ? new Date(value.endsWith('Z') ? value : `${value}Z`).toLocaleString('zh-CN', { hour12: false }) : '-'
}

onMounted(() => loadReport())
</script>

<template>
  <div class="monthly-inventory-page">
    <PageHeader title="日度盘点" description="按状态核对钢瓶入库、出库和累计结余，所有人工修改均保留审计日志。">
      <InventoryImageCopy v-if="report" title="日度盘点" :source="report.source_name" :columns="report.months" :cards="imageCards" :disabled="loading || !!savingKey || !!editing || !!loadError" />
      <el-button @click="openLogs">查看变更日志</el-button>
    </PageHeader>

    <section class="surface inventory-filter">
      <label>
        <span>日度区间</span>
        <el-date-picker
          v-model="monthRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          format="YYYY年MM月DD日"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          unlink-panels
          :clearable="false"
        />
      </label>
      <label>
        <span>公司</span>
        <el-select v-model="sourceId" filterable placeholder="全部公司">
          <el-option label="全部公司" :value="null" />
          <el-option
            v-for="item in report?.sources || []"
            :key="item.id"
            :label="item.is_active ? item.name : `${item.name}（已停用）`"
            :value="item.id"
          />
        </el-select>
      </label>
      <el-button type="primary" :loading="loading" @click="loadReport()">查询</el-button>
      <div class="filter-note">
        <template v-if="sourceId === null">最多查询连续 31 天；全部公司为汇总视图，选择具体公司后可修改盘点值。</template>
        <template v-else-if="canUpdate">最多查询连续 31 天；点击数值修改，保存后自动重算后续结余。</template>
        <template v-else>当前账号只有查看权限。</template>
      </div>
    </section>

    <el-alert v-if="loadError" class="load-error" :title="loadError" type="error" :closable="false" show-icon />

    <div v-loading="loading" class="inventory-content">
      <template v-if="report">
        <section v-for="config in tableConfigs" :key="config.key" class="surface inventory-section">
          <div class="surface-header inventory-heading">
            <div>
              <h2>{{ config.title }}</h2>
              <span>{{ config.description }}</span>
            </div>
            <div class="inventory-card-actions">
              <strong>{{ report.source_name }}</strong>
              <InventoryImageCopy :title="`日度盘点 · ${config.title}`" :source="report.source_name" :columns="report.months" :cards="imageCards.filter(card => card.title === config.title)" :disabled="loading || !!savingKey || !!editing || !!loadError" />
            </div>
          </div>
          <div class="inventory-table-wrap">
            <table class="inventory-table">
              <thead>
                <tr>
                  <th class="sticky-category">状态</th>
                  <th class="sticky-spec">钢瓶规格</th>
                  <th v-for="month in report.months" :key="month.key">{{ month.label }}</th>
                  <th class="sticky-right">{{ config.summaryLabel }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in report.tables[config.key].rows" :key="`${row.metric}-${row.spec_id}`">
                  <th
                    v-if="row.category_first"
                    class="sticky-category category-name"
                    :rowspan="row.category_rowspan"
                  >{{ row.category_label }}</th>
                  <th class="sticky-spec spec-name">{{ row.spec_name }}</th>
                  <td
                    v-for="month in report.months"
                    :key="month.key"
                    :class="{
                      editable: report.editable && canUpdate,
                      modified: isModified(row, month.key),
                      saving: savingKey === cellKey(row.metric, row.spec_id, month.key),
                    }"
                    :title="isModified(row, month.key) ? '该数值有人工盘点修改记录' : (report.editable && canUpdate ? '点击修改' : '')"
                    @click="beginEdit(row.metric, row, month.key)"
                  >
                    <el-input-number
                      v-if="isEditing(row.metric, row.spec_id, month.key)"
                      v-model="draftValue"
                      :data-edit-key="cellKey(row.metric, row.spec_id, month.key)"
                      :min="0"
                      :precision="0"
                      :controls="false"
                      size="small"
                      @blur="saveEdit"
                      @keyup.enter="($event.target as HTMLInputElement).blur()"
                      @keyup.esc="cancelEdit"
                      @click.stop
                    />
                    <span v-else>{{ row.values[month.key] }}</span>
                  </td>
                  <td class="sticky-right summary-cell">{{ row.summary }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <th class="sticky-category">合计</th>
                  <th class="sticky-spec">全部状态</th>
                  <td v-for="month in report.months" :key="month.key">{{ report.tables[config.key].totals[month.key] }}</td>
                  <td class="sticky-right summary-cell">{{ report.tables[config.key].summary }}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </section>
      </template>
    </div>

    <el-drawer v-model="logDrawer" title="盘点变更日志" size="min(920px, 92vw)" destroy-on-close>
      <div class="log-context">当前筛选：{{ sourceId === null ? '全部公司' : report?.source_name }}，{{ monthRange[0] }} 至 {{ monthRange[1] }}</div>
      <el-table v-loading="logLoading" :data="logs" stripe>
        <el-table-column prop="created_at" label="修改时间" width="170">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="created_by_name" label="操作人" width="110" />
        <el-table-column prop="source_name" label="公司" min-width="150" show-overflow-tooltip />
        <el-table-column prop="month" label="日期" width="115" />
        <el-table-column prop="spec_name" label="规格" width="110" />
        <el-table-column prop="metric" label="盘点项" width="150">
          <template #default="{ row }">{{ metricName(row.metric) }}</template>
        </el-table-column>
        <el-table-column label="变更" width="145" align="right">
          <template #default="{ row }"><span class="change-value">{{ row.old_value }} → {{ row.new_value }}</span></template>
        </el-table-column>
        <el-table-column prop="reason" label="说明" min-width="180" show-overflow-tooltip />
      </el-table>
      <div class="log-pagination">
        <el-pagination
          v-model:current-page="logPage"
          background
          layout="total, prev, pager, next"
          :page-size="20"
          :total="logTotal"
          @current-change="loadLogs"
        />
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.inventory-filter { display: flex; align-items: flex-end; gap: 12px; padding: 16px 18px; margin-bottom: 16px; }
.inventory-filter label { display: grid; gap: 6px; color: var(--ja-muted); font-size: 11px; }
.inventory-filter label:first-child :deep(.el-date-editor) { width: 330px; }
.inventory-filter label:nth-child(2) :deep(.el-select) { width: 240px; }
.filter-note { flex: 1; min-width: 240px; padding-bottom: 7px; color: var(--ja-muted); font-size: 11px; text-align: right; }
.load-error { margin-bottom: 16px; }
.inventory-content { min-height: 260px; }
.inventory-section { overflow: hidden; }
.inventory-section + .inventory-section { margin-top: 16px; }
.inventory-heading > div { min-width: 0; }
.inventory-heading span { display: block; margin-top: 4px; color: var(--ja-muted); font-size: 11px; }
.inventory-card-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }
.inventory-card-actions strong { flex: 0 0 auto; color: var(--ja-text); font-size: 12px; }
.inventory-table-wrap { max-width: 100%; overflow: auto; }
.inventory-table { width: max-content; min-width: 100%; border-collapse: separate; border-spacing: 0; font-variant-numeric: tabular-nums; }
.inventory-table th, .inventory-table td { width: 118px; min-width: 118px; height: 50px; padding: 8px 12px; border-right: 1px solid var(--ja-line); border-bottom: 1px solid var(--ja-line); background: #fff; text-align: right; }
.inventory-table thead th { position: sticky; top: 0; z-index: 3; height: 43px; color: #646971; background: #f6f7f8; font-size: 12px; font-weight: 600; }
.inventory-table .sticky-category { position: sticky; left: 0; z-index: 3; width: 88px; min-width: 88px; text-align: left; }
.inventory-table .sticky-spec { position: sticky; left: 88px; z-index: 2; width: 126px; min-width: 126px; text-align: left; }
.inventory-table thead .sticky-category, .inventory-table thead .sticky-spec { z-index: 5; background: #f6f7f8; }
.inventory-table .sticky-right { position: sticky; right: 0; z-index: 2; width: 128px; min-width: 128px; border-right: 0; background: #fafafa; }
.inventory-table thead .sticky-right { z-index: 5; background: #f0f1f3; }
.inventory-table .spec-name { color: var(--ja-text); font-size: 13px; font-weight: 600; }
.inventory-table .category-name { color: #555b63; background: #fafafa; font-size: 12px; font-weight: 700; vertical-align: top; }
.inventory-table tbody td { position: relative; color: #2e3033; font-family: "SFMono-Regular", Consolas, monospace; font-size: 14px; }
.inventory-table tbody tr:hover td, .inventory-table tbody tr:hover th { background: #fafafa; }
.inventory-table tbody td.editable { cursor: text; }
.inventory-table tbody td.editable:hover { color: var(--ja-red); background: #fff8f8; box-shadow: inset 0 0 0 1px #efb8bb; }
.inventory-table tbody td.modified::after { content: ""; position: absolute; top: 0; right: 0; width: 0; height: 0; border-top: 8px solid var(--ja-red); border-left: 8px solid transparent; }
.inventory-table tbody td.saving { color: var(--ja-muted); background: #f7f7f8; }
.inventory-table :deep(.el-input-number) { width: 92px; }
.inventory-table :deep(.el-input__wrapper) { padding: 0 7px; box-shadow: 0 0 0 1px var(--ja-red) inset; }
.inventory-table :deep(.el-input__inner) { text-align: right; font-family: "SFMono-Regular", Consolas, monospace; }
.inventory-table .summary-cell { color: #202329; font-weight: 700; }
.inventory-table tfoot th, .inventory-table tfoot td { position: sticky; bottom: 0; z-index: 3; height: 46px; color: #202329; background: #f5f6f7; font-weight: 700; }
.inventory-table tfoot .sticky-category, .inventory-table tfoot .sticky-spec { z-index: 4; background: #f5f6f7; }
.inventory-table tfoot .sticky-right { z-index: 4; background: #eceef0; }
.inventory-table tbody tr:last-child th, .inventory-table tbody tr:last-child td { border-bottom: 1px solid var(--ja-line); }
.log-context { margin-bottom: 14px; padding: 10px 12px; color: var(--ja-muted); background: #f5f6f7; border-radius: var(--ja-control-radius); font-size: 12px; }
.change-value { color: var(--ja-text); font-family: "SFMono-Regular", Consolas, monospace; font-weight: 600; }
.log-pagination { display: flex; justify-content: flex-end; padding-top: 16px; }

@media (max-width: 900px) {
  .inventory-filter { align-items: stretch; flex-direction: column; }
  .inventory-filter label:first-child :deep(.el-date-editor),
  .inventory-filter label:nth-child(2) :deep(.el-select) { width: 100%; }
  .filter-note { min-width: 0; padding: 2px 0 0; text-align: left; }
  .inventory-filter > .el-button { width: 100%; }
  .inventory-heading { align-items: flex-start; }
  .inventory-heading span { max-width: 70vw; }
  .inventory-table th, .inventory-table td { width: 104px; min-width: 104px; padding-right: 9px; padding-left: 9px; }
  .inventory-table .sticky-category { width: 64px; min-width: 64px; }
  .inventory-table .sticky-spec { left: 64px; width: 82px; min-width: 82px; }
  .inventory-table .sticky-right { width: 92px; min-width: 92px; }
}
</style>
