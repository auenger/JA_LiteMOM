<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import PageHeader from '../components/PageHeader.vue'
import EmptyState from '../components/EmptyState.vue'

type Assignment = {
  id: number
  document_id: number
  document_no: string
  inspection_date: string
  customer_name: string
  document_status: string
  report_date: string
  regular_code: string
  assessment_code: string
  default_report_date: string | null
}
type Day = {
  report_date: string
  last_number: number
  required_number: number
  unassigned_numbers: number[]
  unassigned_pairs: number[]
  released_pairs: number[]
  next_first_number: number | null
  assignments: Assignment[]
}
type Legacy = { document_id: number; document_no: string; inspection_date: string; customer_name: string; report_date: string }

const router = useRouter()
const days = ref<Day[]>([])
const legacy = ref<Legacy[]>([])
const loading = ref(false)
const deletingId = ref<number | null>(null)
const resettingDate = ref<string | null>(null)
const releasingPair = ref<string | null>(null)
const filterDate = ref('')
const searchText = ref('')
const selectedDate = ref('')
const filteredDays = computed(() => days.value.filter((day) =>
  (!filterDate.value || day.report_date === filterDate.value)
  && (!searchText.value.trim() || day.assignments.some((item) =>
    `${item.document_no} ${item.customer_name}`.toLowerCase().includes(searchText.value.trim().toLowerCase()),
  )),
))
const selectedDay = computed(() => filteredDays.value.find((day) => day.report_date === selectedDate.value) || null)
const visibleAssignments = computed(() => (selectedDay.value?.assignments || []).filter((item) =>
  !searchText.value.trim() || `${item.document_no} ${item.customer_name}`.toLowerCase().includes(searchText.value.trim().toLowerCase()),
))
const visibleLegacy = computed(() => legacy.value.filter((item) =>
  (!filterDate.value || item.report_date === filterDate.value)
  && (!searchText.value.trim() || `${item.document_no} ${item.customer_name}`.toLowerCase().includes(searchText.value.trim().toLowerCase())),
))

watch(filteredDays, (items) => {
  if (!items.some((item) => item.report_date === selectedDate.value)) selectedDate.value = items[0]?.report_date || ''
})

function nextCodes(day: Day) {
  if (day.next_first_number === null) return '已到 999，无法再分配一组'
  const prefix = `WFJA-${day.report_date.slice(2, 4)}-${day.report_date.slice(5, 7)}${day.report_date.slice(8, 10)}`
  return `${prefix}${String(day.next_first_number).padStart(3, '0')}、${prefix}${String(day.next_first_number + 1).padStart(3, '0')}`
}

function pairCodes(day: Day, firstNumber: number) {
  const prefix = `WFJA-${day.report_date.slice(2, 4)}-${day.report_date.slice(5, 7)}${day.report_date.slice(8, 10)}`
  return `${prefix}${String(firstNumber).padStart(3, '0')}、${prefix}${String(firstNumber + 1).padStart(3, '0')}`
}

function missingCodes(day: Day) {
  const numbers = day.unassigned_numbers || []
  if (!numbers.length) return '无'
  const shown = numbers.slice(0, 8).map((number) => String(number).padStart(3, '0')).join('、')
  return numbers.length > 8 ? `${shown} 等 ${numbers.length} 个` : shown
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/inspection-word-code-ledger')
    days.value = data.days
    legacy.value = data.without_saved_code
    if (!days.value.some((item) => item.report_date === selectedDate.value)) selectedDate.value = days.value[0]?.report_date || ''
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}

async function deleteAssignment(item: Assignment) {
  try {
    await ElMessageBox.confirm(
      `删除 ${item.document_no} 在 ${item.report_date} 的定检编号 ${item.regular_code} 和评定编号 ${item.assessment_code}？已下载的 Word 不会改变。删除后该日计数暂时不变，可再点击“重置日期计数”。`,
      '删除 Word 编号', { type: 'warning', confirmButtonText: '删除这组编号', cancelButtonText: '取消' },
    )
  } catch { return }
  deletingId.value = item.id
  try {
    await api.delete(`/inspection-word-code-ledger/assignments/${item.id}`)
    await load()
    ElMessage.success('编号分配已删除；需要重新从剩余编号末尾开始时，请重置日期计数')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { deletingId.value = null }
}

async function resetCounter(day: Day) {
  try {
    await ElMessageBox.confirm(
      `将 ${day.report_date} 的已用末尾序号从 ${String(day.last_number).padStart(3, '0')} 调整为该日仍保留编号的末尾 ${String(day.required_number).padStart(3, '0')}。之后导出的新报告会从下一组序号开始。已下载的旧 Word 不会改变；若旧文件未在系统保存编号，重置后可能与它重号。`,
      '重置日期计数', { type: 'warning', confirmButtonText: '确认重置', cancelButtonText: '取消' },
    )
  } catch { return }
  resettingDate.value = day.report_date
  try {
    await api.post(`/inspection-word-code-ledger/dates/${day.report_date}/reset`)
    await load()
    ElMessage.success('日期计数已重置')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { resettingDate.value = null }
}

async function releasePair(day: Day, firstNumber: number) {
  try {
    await ElMessageBox.confirm(
      `将未关联的 ${pairCodes(day, firstNumber)} 从占用中删除，允许下一次 Word 导出重新使用？以前下载的 Word 文件不会改变，可能与新文件重号。`,
      '删除未关联编号', { type: 'warning', confirmButtonText: '删除并允许重用', cancelButtonText: '取消' },
    )
  } catch { return }
  releasingPair.value = `${day.report_date}-${firstNumber}`
  try {
    await api.delete(`/inspection-word-code-ledger/dates/${day.report_date}/unassigned-pairs/${firstNumber}`)
    await load()
    ElMessage.success('这组未关联编号已释放，下次导出会优先使用')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { releasingPair.value = null }
}

function openDocument(documentId: number) {
  router.push({ path: '/inspection-documents', query: { document: String(documentId) } })
}

onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="Word 报告编号管理" description="核对各报告日期的已分配编码与计数；仅超级管理员可删除分配和重置计数。">
      <el-button :loading="loading" @click="load">刷新</el-button>
    </PageHeader>
    <el-alert title="未关联编号表示处于该日已用序号范围内、但目前没有检验单分配记录；无法据此判断原来属于哪张检验单。超级管理员可删除完整的未关联编号组，使下次导出优先重用；以前下载的 Word 文件不会自动更改。" type="info" :closable="false" />
    <section class="surface ledger-section">
      <div class="surface-header ledger-filters"><el-date-picker v-model="filterDate" type="date" value-format="YYYY-MM-DD" clearable placeholder="筛选报告日期" /><el-input v-model="searchText" clearable placeholder="搜索检验单编号或客户" /><span class="grow" /><span class="muted">{{ filteredDays.length }} 个报告日期</span></div>
      <el-table v-if="filteredDays.length" v-loading="loading" :data="filteredDays" stripe max-height="380" highlight-current-row @row-click="(row: Day) => selectedDate = row.report_date">
        <el-table-column prop="report_date" label="报告日期" width="125" />
        <el-table-column label="已分配" width="95" align="right"><template #default="{ row }">{{ row.assignments.length }} 组</template></el-table-column>
        <el-table-column label="当前计数" width="100" align="right"><template #default="{ row }"><strong>{{ String(row.last_number).padStart(3, '0') }}</strong></template></el-table-column>
        <el-table-column label="保留编号末尾" width="125" align="right"><template #default="{ row }">{{ String(row.required_number).padStart(3, '0') }}</template></el-table-column>
        <el-table-column label="未关联编号" min-width="160"><template #default="{ row }">{{ missingCodes(row) }}</template></el-table-column>
        <el-table-column label="下次导出编码" min-width="290"><template #default="{ row }">{{ nextCodes(row) }}</template></el-table-column>
        <el-table-column label="状态" width="135"><template #default="{ row }"><el-tag v-if="row.last_number < row.required_number" type="danger">计数低于已分配</el-tag><el-tag v-else-if="row.unassigned_numbers?.length" type="warning">有编号空缺</el-tag><el-tag v-else-if="row.released_pairs?.length" type="info">有可重用编号</el-tag><el-tag v-else-if="row.last_number > row.required_number" type="warning">可检查并重置</el-tag><el-tag v-else type="success">一致</el-tag></template></el-table-column>
        <el-table-column label="操作" width="130"><template #default="{ row }"><el-button link type="primary" @click="selectedDate = row.report_date">查看明细</el-button><el-button link type="warning" :loading="resettingDate === row.report_date" @click="resetCounter(row)">重置</el-button></template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : '没有匹配的报告日期'" />
    </section>
    <section v-if="selectedDay" class="surface ledger-section">
      <div class="surface-header"><h2>{{ selectedDay.report_date }} 的报告编号</h2><span class="grow" /><span class="muted">{{ visibleAssignments.length }} 张检验单</span></div>
      <el-alert v-if="selectedDay.unassigned_numbers?.length" :title="`未关联编号：${missingCodes(selectedDay)}。这些编号当前没有对应的检验单记录，不能从计数推断原文件或归属。`" type="warning" :closable="false" />
      <el-table v-if="selectedDay.unassigned_pairs?.length" :data="selectedDay.unassigned_pairs" stripe max-height="240">
        <el-table-column label="未关联编号组" min-width="300"><template #default="{ row }">{{ pairCodes(selectedDay, row) }}</template></el-table-column>
        <el-table-column label="状态" width="145"><template #default>占用计数、无检验单</template></el-table-column>
        <el-table-column label="操作" width="160"><template #default="{ row }"><el-button link type="danger" :loading="releasingPair === `${selectedDay.report_date}-${row}`" @click="releasePair(selectedDay, row)">删除并允许重用</el-button></template></el-table-column>
      </el-table>
      <el-alert v-if="selectedDay.released_pairs?.length" :title="`可重用编号组：${selectedDay.released_pairs.map((number) => pairCodes(selectedDay!, number)).join('；')}。下一次导出将优先分配最小的一组。`" type="success" :closable="false" />
      <el-table v-if="visibleAssignments.length" :data="visibleAssignments" stripe max-height="520">
        <el-table-column prop="document_no" label="检验单编号" min-width="160" />
        <el-table-column prop="inspection_date" label="检验单日期" width="115" />
        <el-table-column prop="customer_name" label="客户/充装单位" min-width="160" />
        <el-table-column prop="regular_code" label="定检编号" min-width="155" />
        <el-table-column prop="assessment_code" label="评定编号" min-width="155" />
        <el-table-column prop="default_report_date" label="当前默认导出日期" width="145"><template #default="{ row }">{{ row.default_report_date || '-' }}</template></el-table-column>
        <el-table-column label="操作" width="155"><template #default="{ row }"><el-button link type="primary" @click="openDocument(row.document_id)">检验单</el-button><el-button link type="danger" :loading="deletingId === row.id" @click="deleteAssignment(row)">删除编号</el-button></template></el-table-column>
      </el-table>
      <EmptyState v-else title="该日期没有已分配的检验单编号" />
    </section>
    <section v-if="visibleLegacy.length" class="surface ledger-section">
      <div class="surface-header"><h2>有 Word 导出日期、但没有保存编号的记录</h2><span class="grow" /><span class="muted">{{ visibleLegacy.length }} 张</span></div>
      <el-alert title="这里包含早期未保存编码的导出，也可能包含已删除编号分配的检验单。这些记录本身没有编号；日期计数可能仍保留旧值，请对照上表核查。" type="warning" :closable="false" />
      <el-table :data="visibleLegacy" stripe max-height="360">
        <el-table-column prop="document_no" label="检验单编号" min-width="170" />
        <el-table-column prop="inspection_date" label="检验单日期" width="115" />
        <el-table-column prop="report_date" label="最近 Word 导出日期" width="150" />
        <el-table-column prop="customer_name" label="客户/充装单位" min-width="180" />
        <el-table-column label="操作" width="95"><template #default="{ row }"><el-button link type="primary" @click="openDocument(row.document_id)">检验单</el-button></template></el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.ledger-section{margin-top:16px}.ledger-filters{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.ledger-filters .el-input{width:280px}.ledger-section h2{margin:0;font-size:18px}.ledger-section .el-alert{margin:0 18px 16px}.ledger-section :deep(.el-table__row){cursor:pointer}
</style>
