<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import type { Bottle, BottleManufacturer, BottleSource, BottleSpec } from '../types'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import ReportActions from '../components/ReportActions.vue'
import StatusTag from '../components/StatusTag.vue'
import TablePagination from '../components/TablePagination.vue'

const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const suspectRows = ref<Bottle[]>([])
const suspectPage = ref(1)
const suspectPageSize = ref(20)
const suspectTotal = ref(0)
const suspectCount = ref(0)
const suspectLoading = ref(false)
const suspectQuery = ref('')
const suspectDateRange = ref<[string, string]>([today, today])
const customerQuery = ref<number | undefined>()
const suspectFilters = ref({ date_from: today, date_to: today, body_code: '', coding_customer_id: undefined as number | undefined })
const suspectIsToday = computed(() => suspectFilters.value.date_from === today && suspectFilters.value.date_to === today)
let suspectRequestId = 0
const sources = ref<BottleSource[]>([])
const specs = ref<BottleSpec[]>([])
const manufacturers = ref<BottleManufacturer[]>([])
const summary = ref<any>({ total: 0, items: [] })
const editingSuspectId = ref<number | null>(null)
const savingSuspect = ref(false)
const undoingId = ref<number | null>(null)
const mutating = computed(() => savingSuspect.value || undoingId.value !== null)
const suspectForm = reactive({ body_code: '', manufacture_date: '', manufacturer: '', source_id: undefined as number | undefined, spec_id: undefined as number | undefined })
watch(() => suspectForm.manufacture_date, (value) => {
  const cleaned = value.replace(/[^0-9.]/g, '')
  const digits = cleaned.replace(/\D/g, '')
  const normalized = digits.length >= 6 ? `${digits.slice(0, 4)}.${digits.slice(4, 6)}` : cleaned
  if (normalized !== value) suspectForm.manufacture_date = normalized
})
const reportLines = computed(() => [
  `查询日期：${suspectFilters.value.date_from} 至 ${suspectFilters.value.date_to}`,
  ...summary.value.items.map((item: any) => `${item.customer_name ? `${item.customer_name} / ` : ''}${item.user_name} / ${item.spec_name}：${item.quantity} 只`),
  `抄码总量：${summary.value.total} 只`,
])

async function loadOptions() {
  try {
    const options = await api.get('/options')
    sources.value = options.data.sources; specs.value = options.data.specs
    manufacturers.value = options.data.manufacturers || []
  } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function loadSuspects() {
  const requestId = ++suspectRequestId
  suspectLoading.value = true
  try {
    const params = { ...suspectFilters.value, body_code: suspectFilters.value.body_code || undefined }
    const [{ data }, report] = await Promise.all([
      api.get('/coding/review-bottles', { params: { ...params, page: suspectPage.value, page_size: suspectPageSize.value } }),
      api.get('/coding/summary', { params }),
    ])
    if (requestId !== suspectRequestId) return
    const lastPage = Math.max(1, Math.ceil(data.total / suspectPageSize.value))
    if (suspectPage.value > lastPage) { suspectPage.value = lastPage; await loadSuspects(); return }
    suspectRows.value = data.items; suspectTotal.value = data.total; suspectCount.value = data.suspect_count
    summary.value = report.data
    editingSuspectId.value = null
  } catch (err) { if (requestId === suspectRequestId) ElMessage.error(errorMessage(err)) }
  finally { if (requestId === suspectRequestId) suspectLoading.value = false }
}
function searchSuspects() {
  if (mutating.value) return
  suspectFilters.value = { date_from: suspectDateRange.value[0], date_to: suspectDateRange.value[1], body_code: suspectQuery.value.trim(), coding_customer_id: customerQuery.value }
  suspectPage.value = 1; loadSuspects()
}
function resetSuspects() { suspectQuery.value = ''; customerQuery.value = undefined; suspectDateRange.value = [today, today]; searchSuspects() }
function suspectPageChanged(nextPage: number, nextSize: number) {
  if (mutating.value) return
  suspectPage.value = nextPage; suspectPageSize.value = nextSize; loadSuspects()
}
function sourceName(id: number) { return sources.value.find((item) => item.id === id)?.name || `单位 #${id}` }
function specName(id: number) { return specs.value.find((item) => item.id === id)?.name || `规格 #${id}` }
function manufactureDateInput(value?: string | null) { return value ? value.slice(0, 7).replace('-', '.') : '' }
function manufactureDatePayload() {
  const digits = suspectForm.manufacture_date.replace(/\D/g, '')
  return digits.length >= 6 ? `${digits.slice(0, 4)}-${digits.slice(4, 6)}-01` : null
}
function startSuspectEdit(row: Bottle) {
  editingSuspectId.value = row.id
  Object.assign(suspectForm, {
    body_code: row.body_code,
    manufacture_date: manufactureDateInput(row.manufacture_date),
    manufacturer: row.manufacturer || '',
    source_id: row.source_id,
    spec_id: row.spec_id,
  })
}
function cancelSuspectEdit() { editingSuspectId.value = null }
function suspectCellClass({ row, column }: { row: Bottle; column: { property?: string } }) {
  if (column.property === 'body_code' && row.body_code.trim().length > 13) return 'suspect-warning-cell'
  if (column.property === 'manufacturer' && !row.manufacturer?.trim()) return 'suspect-warning-cell'
  if (column.property === 'manufacture_date' && !row.manufacture_date) return 'suspect-warning-cell'
  return ''
}
async function saveSuspect(row: Bottle) {
  if (savingSuspect.value) return
  if (!suspectForm.body_code.trim()) return ElMessage.warning('请填写瓶身编号')
  if (!suspectForm.source_id || !suspectForm.spec_id) return ElMessage.warning('请选择供瓶单位和瓶子规格')
  savingSuspect.value = true
  try {
    await api.put(`/bottles/${row.id}/coding`, {
      body_code: suspectForm.body_code.trim(),
      manufacture_date: manufactureDatePayload(),
      manufacturer: suspectForm.manufacturer.trim() || null,
      source_id: suspectForm.source_id,
      spec_id: suspectForm.spec_id,
    })
    editingSuspectId.value = null
    ElMessage.success('钢瓶抄码信息已保存')
    await loadSuspects()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { savingSuspect.value = false }
}
async function undoCoding(row: Bottle) {
  if (mutating.value || editingSuspectId.value !== null) return
  undoingId.value = row.id
  try {
    await ElMessageBox.confirm(`确认撤销瓶身编号“${row.body_code}”的抄码？撤销后将从良品库移除${row.inbound_id ? '，并把对应入库规格的待抄码余量加回 1' : ''}。`, '撤销抄码', { type: 'warning' })
    await api.delete(`/bottles/${row.id}/coding`)
    ElMessage.success(row.inbound_id ? '抄码已撤销，待抄码余量已恢复' : '抄码已撤销')
    await loadSuspects()
  } catch (err: any) { if (err !== 'cancel' && err !== 'close') ElMessage.error(errorMessage(err)) }
  finally { undoingId.value = null }
}
onMounted(() => { loadOptions(); loadSuspects() })
</script>

<template>
  <div>
    <PageHeader title="抄码记录" description="默认显示今天所有人员的抄码记录，可按日期、抄码客户和瓶身编号查询，直接核对、编辑或撤销抄码。"><ReportActions title="抄码记录汇总" :filename="`抄码记录-${suspectFilters.date_from}`" :lines="reportLines" /></PageHeader>
    <section class="surface suspect-section" v-loading="suspectLoading">
      <div class="surface-header suspect-header"><div><h2>{{ suspectIsToday ? '今日抄码核对' : '抄码核对' }}</h2><span>{{ suspectIsToday ? '当天' : '查询范围内' }}共 {{ suspectTotal }} 条，其中 {{ suspectCount }} 条疑似有问题；编号超过 13 位、生产厂家为空或生产日期为空的字段标黄并排在前面。</span></div></div>
      <div class="surface-header suspect-filters">
        <el-date-picker v-model="suspectDateRange" type="daterange" :clearable="false" :disabled="mutating" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="抄码开始日期" end-placeholder="抄码结束日期" />
        <el-select v-model="customerQuery" filterable clearable :disabled="mutating" placeholder="筛选抄码客户"><el-option v-for="source in sources" :key="source.id" :label="source.name" :value="source.id" /></el-select>
        <el-input v-model="suspectQuery" clearable :disabled="mutating" placeholder="查询核对瓶身编号" @keyup.enter="searchSuspects"><template #prefix><GameIcon name="search" /></template></el-input>
        <el-button type="primary" :disabled="mutating" @click="searchSuspects">查询</el-button>
        <el-button :disabled="mutating" @click="resetSuspects">重置</el-button>
      </div>
      <el-table v-if="suspectRows.length" :data="suspectRows" stripe :cell-class-name="suspectCellClass">
        <el-table-column prop="coding_sequence" label="序号" width="70" align="right" />
        <el-table-column prop="body_code" label="瓶身编号" min-width="210"><template #default="{ row }"><el-input v-if="editingSuspectId === row.id" v-model="suspectForm.body_code" maxlength="100" /><div v-else class="suspect-value"><strong class="numeric">{{ row.body_code }}</strong><el-tag v-if="row.body_code.trim().length > 13" type="warning" size="small">超过13位</el-tag></div></template></el-table-column>
        <el-table-column prop="manufacturer" label="生产厂家" min-width="210"><template #default="{ row }"><el-select v-if="editingSuspectId === row.id" v-model="suspectForm.manufacturer" filterable allow-create default-first-option clearable placeholder="选择或输入厂家" class="w-full"><el-option v-for="item in manufacturers.filter(item => item.is_active)" :key="item.id" :label="item.name" :value="item.name" /></el-select><div v-else class="suspect-value"><span>{{ row.manufacturer || '未填写' }}</span><el-tag v-if="!row.manufacturer?.trim()" type="warning" size="small">厂家为空</el-tag></div></template></el-table-column>
        <el-table-column prop="manufacture_date" label="生产日期" width="190"><template #default="{ row }"><el-input v-if="editingSuspectId === row.id" v-model="suspectForm.manufacture_date" clearable autocomplete="off" aria-label="生产日期" placeholder="输入生产日期，如 2022.09" class="w-full" /><div v-else class="suspect-value"><span>{{ row.manufacture_date || '未填写' }}</span><el-tag v-if="!row.manufacture_date" type="warning" size="small">日期为空</el-tag></div></template></el-table-column>
        <el-table-column label="抄码客户" min-width="150"><template #default="{ row }">{{ row.coding_customer_name || sourceName(row.effective_coding_customer_id || row.source_id) }}</template></el-table-column>
        <el-table-column prop="source_id" label="原供瓶单位" min-width="180"><template #default="{ row }"><el-select v-if="editingSuspectId === row.id" v-model="suspectForm.source_id" filterable :disabled="row.inspection_document_status === 'INSPECTED'" class="w-full"><el-option v-for="item in sources.filter(item => item.is_active)" :key="item.id" :label="item.name" :value="item.id" /></el-select><span v-else>{{ sourceName(row.source_id) }}</span></template></el-table-column>
        <el-table-column prop="spec_id" label="瓶子规格" width="150"><template #default="{ row }"><el-select v-if="editingSuspectId === row.id" v-model="suspectForm.spec_id" filterable :disabled="row.inspection_document_status === 'INSPECTED'" class="w-full"><el-option v-for="item in specs.filter(item => item.is_active)" :key="item.id" :label="item.name" :value="item.id" /></el-select><span v-else>{{ specName(row.spec_id) }}</span></template></el-table-column>
        <el-table-column prop="coded_by_name" label="抄码人员" width="110" />
        <el-table-column prop="coding_date" label="抄码日期" width="115" />
        <el-table-column label="当前状态" width="100"><template #default="{ row }"><StatusTag :status="row.zone" /></template></el-table-column>
        <el-table-column label="检验单" width="135"><template #default="{ row }"><el-tag v-if="row.inspection_document_status === 'INSPECTED'" type="success" size="small">已检验</el-tag><span v-else class="muted">未生成</span></template></el-table-column>
        <el-table-column prop="coding_note" label="备注" min-width="160"><template #default="{ row }">{{ row.coding_note || '-' }}</template></el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <template v-if="editingSuspectId === row.id">
              <el-button link type="primary" :loading="savingSuspect" @click="saveSuspect(row)">保存</el-button>
              <el-button link :disabled="savingSuspect" @click="cancelSuspectEdit">取消</el-button>
            </template>
            <template v-else>
              <el-button v-if="has('coding:update')" link type="primary" :disabled="editingSuspectId !== null || mutating" @click="startSuspectEdit(row)">编辑</el-button>
              <span v-if="row.inspection_document_status === 'INSPECTED'" class="muted">已锁定</span>
              <el-button v-else-if="has('coding:delete')" link type="danger" :loading="undoingId === row.id" :disabled="editingSuspectId !== null || mutating" @click="undoCoding(row)">撤销抄码</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else :title="suspectLoading ? '正在加载' : '当前条件没有抄码核对记录'" />
      <TablePagination :page="suspectPage" :page-size="suspectPageSize" :total="suspectTotal" @change="suspectPageChanged" />
    </section>
  </div>
</template>

<style scoped>
.suspect-filters{display:grid;grid-template-columns:minmax(0,300px) minmax(150px,220px) minmax(150px,1fr) auto auto;gap:10px}
.suspect-filters>*{min-width:0}
.suspect-filters :deep(.el-date-editor){width:100%;min-width:0}
@media(max-width:1200px){.suspect-filters{grid-template-columns:1fr 1fr}}
@media(max-width:560px){.suspect-filters{grid-template-columns:1fr}}
</style>

<style scoped>.suspect-section{border-color:#e6b83f}.suspect-header{background:#fff8df}.suspect-header h2{margin:0 0 4px;font-size:15px}.suspect-header span{color:var(--ja-muted);font-size:12px}.suspect-value{display:flex;align-items:center;gap:7px}.suspect-section :deep(td.suspect-warning-cell){background:#fff3bf!important}</style>
