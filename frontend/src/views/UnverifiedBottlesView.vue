<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import TablePagination from '../components/TablePagination.vue'

const router = useRouter()
const rows = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dateRange = ref<[string, string] | null>(null)
const documentNo = ref('')
const bodyCode = ref('')
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const retryDate = ref(today)
const creatingRetry = ref(false)
const retryResults = ref<any[]>([])
const retryResultsDialog = ref(false)
const exporting = ref(false)
const appliedFilters = ref<{ document_no?: string; body_code?: string; date_from?: string; date_to?: string }>({})
const editDialog = ref(false)
const editingId = ref<number | null>(null)
const savingEdit = ref(false)
const deletingId = ref<number | null>(null)
const originalManufactureDate = ref<string | null>(null)
const editingSpec = ref<any | null>(null)
const editForm = reactive({ body_code: '', manufacture_date: '', manufacturer: '' })
watch(() => editForm.manufacture_date, (value) => {
  const cleaned = value.replace(/[^0-9.]/g, '')
  const digits = cleaned.replace(/\D/g, '')
  const normalized = digits.length >= 6 ? `${digits.slice(0, 4)}.${digits.slice(4, 6)}` : cleaned
  if (normalized !== value) editForm.manufacture_date = normalized
})

async function load() {
  loading.value = true
  try {
    const filters = {
      document_no: documentNo.value || undefined,
      body_code: bodyCode.value || undefined,
      date_from: dateRange.value?.[0], date_to: dateRange.value?.[1],
    }
    const { data } = await api.get('/unverified-bottles', { params: { ...filters, page: page.value, page_size: pageSize.value } })
    appliedFilters.value = filters
    rows.value = data.items; total.value = data.total
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function search() { page.value = 1; load() }
function reset() { documentNo.value = ''; bodyCode.value = ''; dateRange.value = null; search() }
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
async function exportAll() {
  if (exporting.value) return
  exporting.value = true
  try {
    const response = await api.get('/unverified-bottles/export-xls', { responseType: 'blob' })
    const encodedName = String(response.headers['content-disposition'] || '').match(/filename\*=UTF-8''([^;]+)/i)?.[1]
    const filename = encodedName ? decodeURIComponent(encodedName) : '未经系统验证瓶子池全量.xls'
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    ElMessage.success('已导出未验证池全部数据')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { exporting.value = false }
}
function openDocument(row: any) { router.push({ path: '/inspection-documents', query: { date: row.inspection_date, document: row.inspection_document_id } }) }
function openEdit(row: any) {
  editingId.value = row.id
  originalManufactureDate.value = row.manufacture_date || null
  editingSpec.value = row
  Object.assign(editForm, {
    body_code: row.body_code,
    manufacture_date: row.manufacture_date?.slice(0, 7).replace('-', '.') || '',
    manufacturer: row.manufacturer || '',
  })
  editDialog.value = true
}
async function saveEdit() {
  if (editingId.value === null) return
  if (!editForm.body_code.trim()) return ElMessage.warning('请填写瓶身编号')
  const inputMonth = editForm.manufacture_date.trim()
  if (inputMonth && !/^\d{4}\.\d{2}$/.test(inputMonth)) return ElMessage.warning('生产日期请填写完整年月，如 2022.09')
  if (inputMonth && (Number(inputMonth.slice(5)) < 1 || Number(inputMonth.slice(5)) > 12)) return ElMessage.warning('生产日期的月份应在 01 至 12 之间')
  const manufactureDate = !inputMonth ? null : inputMonth === originalManufactureDate.value?.slice(0, 7).replace('-', '.')
    ? originalManufactureDate.value : `${inputMonth.replace('.', '-')}-01`
  savingEdit.value = true
  try {
    await api.put(`/unverified-bottles/${editingId.value}`, {
      body_code: editForm.body_code.trim(), manufacture_date: manufactureDate, manufacturer: editForm.manufacturer.trim(),
    })
    editDialog.value = false
    await load()
    ElMessage.success(editingSpec.value?.bottle_id ? '已同步更新检验单、未验证池及关联的库存钢瓶' : '已同步更新归档检验单和未验证池，不涉及库存钢瓶')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { savingEdit.value = false }
}
async function deleteBottle(row: any) {
  if (deletingId.value !== null) return
  const targetDescription = row.bottle_id ? '驳回记录、检验单明细及关联的库存钢瓶' : '驳回记录和归档检验单明细（该记录未关联库存钢瓶）'
  try {
    await ElMessageBox.prompt(`将永久删除 ${row.document_no} 第 ${row.sequence} 行的瓶身编号 ${row.body_code}、${targetDescription}，无法恢复。若钢瓶已出库，出库单规格和数量保留，系统会将其占用转为匿名数量记录。原入库批次会重新出现一个待抄码名额。请输入完整瓶身编号确认：`, '彻底删除钢瓶', {
      type: 'error', confirmButtonText: '确认彻底删除', cancelButtonText: '取消',
      inputPlaceholder: row.body_code,
      inputValidator: (value: string) => value.trim() === row.body_code || '请输入完全一致的瓶身编号',
    })
  } catch { return }
  deletingId.value = row.id
  try {
    await api.delete(`/unverified-bottles/${row.id}`)
    if (rows.value.length === 1 && page.value > 1) page.value -= 1
    await load()
    ElMessage.success(`${row.body_code} 已从未验证池、检验单${row.bottle_id ? '及关联库存' : ''}中彻底删除`)
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { deletingId.value = null }
}
async function createRetryDocument() {
  if (!total.value || creatingRetry.value || loading.value) return
  if (!retryDate.value) return ElMessage.warning('请选择重检日期')
  try {
    await ElMessageBox.confirm(`将按当前查询结果的排序，把全部 ${total.value} 只钢瓶按原检验单当前客户分别生成 ${retryDate.value} 的重检单，同一客户合并、不同客户分单；原检验单驳回历史保留，这些钢瓶会从待处理池移出。确认继续？`, '生成重检单', { type: 'warning', confirmButtonText: '确认生成' })
  } catch { return }
  creatingRetry.value = true
  try {
    const { data } = await api.post('/unverified-bottles/create-retry-document', { ...appliedFilters.value, inspection_date: retryDate.value })
    page.value = 1
    await load()
    const documents = Array.isArray(data) ? data : [data]
    retryResults.value = documents
    const quantity = documents.reduce((sum: number, item: any) => sum + item.total_quantity, 0)
    ElMessage.success(`已按客户生成 ${documents.length} 张重检单，共 ${quantity} 只钢瓶`)
    if (documents.length === 1) openRetryDocument(documents[0])
    else retryResultsDialog.value = true
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { creatingRetry.value = false }
}
function openRetryDocument(document: any) {
  router.push({ path: '/inspection-documents', query: { date: document.inspection_date, document: document.id } })
}
onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="未经系统验证瓶子池" description="集中保存检验单上传上游系统后被驳回的钢瓶，并保留原检验单、固定序号和驳回信息。"><el-button v-if="has('unverified_bottles:export')" :loading="exporting" @click="exportAll"><GameIcon name="save" />导出全部 Excel</el-button><el-button @click="load"><GameIcon name="refresh" />刷新</el-button></PageHeader>
    <section class="surface">
      <div class="surface-header pool-filters"><el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="检验开始日期" end-placeholder="检验结束日期" clearable /><el-input v-model="documentNo" clearable placeholder="检验单号" @keyup.enter="search" /><el-input v-model="bodyCode" clearable placeholder="瓶身编号" @keyup.enter="search" /><el-button type="primary" @click="search"><GameIcon name="search" />查询</el-button><el-button @click="reset">重置</el-button></div>
      <div v-if="total > 0 && has('unverified_bottles:batch') && has('inspection_documents:create')" class="batch-toolbar"><span>当前筛选结果 {{ total }} 只，将按客户分别生成所选日期的重检单，同一客户合并。</span><div class="retry-actions"><label>重检日期</label><el-date-picker v-model="retryDate" type="date" value-format="YYYY-MM-DD" :clearable="false" :editable="false" :disabled="creatingRetry || loading" placeholder="选择重检日期" /><el-button type="warning" :loading="creatingRetry" :disabled="loading" @click="createRetryDocument">按客户生成重检单</el-button></div></div>
      <el-table v-if="rows.length" v-loading="loading" :data="rows" stripe>
        <el-table-column prop="document_no" label="检验单号" min-width="145"><template #default="{ row }"><el-button link type="primary" @click="openDocument(row)">{{ row.document_no }}</el-button></template></el-table-column>
        <el-table-column prop="inspection_date" label="检验日期" width="115" />
        <el-table-column prop="sequence" label="单据序号" width="95" align="right"><template #default="{ row }"><strong>{{ row.sequence }}</strong></template></el-table-column>
        <el-table-column prop="body_code" label="瓶身编号" min-width="165"><template #default="{ row }"><strong class="numeric">{{ row.body_code }}</strong></template></el-table-column>
        <el-table-column prop="manufacture_date" label="生产日期" width="115"><template #default="{ row }">{{ row.manufacture_date?.slice(0, 7) || '-' }}</template></el-table-column>
        <el-table-column prop="manufacturer" label="生产厂家" min-width="160"><template #default="{ row }">{{ row.manufacturer || '-' }}</template></el-table-column>
        <el-table-column prop="spec_name" label="钢瓶规格" width="120"><template #default="{ row }">{{ row.spec_name || '-' }}</template></el-table-column>
        <el-table-column prop="volume" label="容积（L）" width="95" align="right"><template #default="{ row }">{{ Number(row.volume || 0).toFixed(2) }}</template></el-table-column>
        <el-table-column prop="customer_name" label="客户" min-width="150"><template #default="{ row }">{{ row.customer_name || '-' }}</template></el-table-column>
        <el-table-column prop="inspector_name" label="检验人员" width="110"><template #default="{ row }">{{ row.inspector_name || '-' }}</template></el-table-column>
        <el-table-column prop="error_message" label="上游驳回信息" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="120" fixed="right"><template #default><el-tag type="danger" size="small">未经系统验证</el-tag></template></el-table-column>
        <el-table-column v-if="has('unverified_bottles:update') || has('unverified_bottles:delete')" label="操作" width="170" fixed="right"><template #default="{ row }"><el-button v-if="has('unverified_bottles:update')" link type="primary" @click="openEdit(row)">编辑</el-button><el-button v-if="has('unverified_bottles:delete')" link type="danger" :loading="deletingId === row.id" :disabled="deletingId !== null" @click="deleteBottle(row)">彻底删除</el-button></template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : '未经系统验证瓶子池为空'" description="请在检验单详情中录入上游系统返回的错误信息。" />
      <TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>
    <el-dialog v-model="retryResultsDialog" title="已按客户生成重检单" width="min(680px, 94vw)" destroy-on-close>
      <p>共 {{ retryResults.length }} 张重检单，每张单据只包含同一客户的钢瓶，单内序号从 1 开始。</p>
      <el-table :data="retryResults" stripe max-height="460">
        <el-table-column prop="customer_name" label="客户" min-width="160" />
        <el-table-column prop="document_no" label="重检单号" min-width="170" />
        <el-table-column prop="total_quantity" label="钢瓶数" width="90" align="right" />
        <el-table-column label="操作" width="90" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openRetryDocument(row)">打开</el-button></template></el-table-column>
      </el-table>
      <template #footer><el-button @click="retryResultsDialog = false">关闭</el-button></template>
    </el-dialog>

    <el-dialog v-model="editDialog" title="更正未验证钢瓶" width="620px" destroy-on-close>
      <el-alert title="更正后会同步到原检验单及对应库存钢瓶；归档检验单只修改归档明细。规格参数来自共享规格档案，此处仅供核对。" type="info" :closable="false" />
      <el-form class="edit-form" label-position="top">
        <el-form-item label="瓶身编号"><el-input v-model="editForm.body_code" maxlength="100" /></el-form-item>
        <el-form-item label="生产日期"><el-input v-model="editForm.manufacture_date" clearable autocomplete="off" placeholder="输入年月，如 2022.09" /></el-form-item>
        <el-form-item label="生产厂家"><el-input v-model="editForm.manufacturer" maxlength="160" /></el-form-item>
      </el-form>
      <div class="spec-summary"><strong>关联钢瓶规格</strong><div><span>规格名称</span><b>{{ editingSpec?.spec_name || '未关联' }}</b></div><div><span>公称容积</span><b>{{ editingSpec?.volume != null ? `${Number(editingSpec.volume).toFixed(2)} L` : '-' }}</b></div><div><span>设计壁厚</span><b>{{ editingSpec?.wall_thickness != null ? `${Number(editingSpec.wall_thickness).toFixed(2)} mm` : '-' }}</b></div><div><span>检验价格</span><b>{{ editingSpec?.inspection_price != null ? `¥${Number(editingSpec.inspection_price).toFixed(2)}` : '-' }}</b></div></div>
      <template #footer><el-button @click="editDialog = false">取消</el-button><el-button type="primary" :loading="savingEdit" @click="saveEdit">保存更正</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.pool-filters{display:grid;grid-template-columns:320px 180px 180px max-content max-content;justify-content:start;align-items:center;gap:10px}
.pool-filters>*{min-width:0}
.pool-filters :deep(.el-date-editor){width:100%;min-width:0}
.batch-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 18px;border-bottom:1px solid var(--ja-line);background:var(--ja-red-soft);font-size:12px;color:var(--ja-text)}
.retry-actions{display:flex;align-items:center;gap:10px;flex:none}
.retry-actions label{white-space:nowrap;color:var(--ja-muted)}
.retry-actions :deep(.el-date-editor){width:150px}
.edit-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 14px;margin-top:16px}
.edit-form :deep(.el-input){width:100%}
.spec-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 14px;padding:14px;border:1px solid var(--ja-line);border-radius:var(--ja-radius);background:var(--ja-bg)}
.spec-summary>strong{grid-column:1/-1;font-size:13px}
.spec-summary>div{display:flex;justify-content:space-between;gap:8px;font-size:12px}
.spec-summary span{color:var(--ja-muted)}
.spec-summary b{font-weight:600}
@media(max-width:1180px){.pool-filters{grid-template-columns:repeat(2,minmax(0,1fr))}.pool-filters>*{width:100%}}
@media(max-width:560px){.pool-filters,.edit-form,.spec-summary{grid-template-columns:minmax(0,1fr)}.spec-summary>strong{grid-column:auto}.batch-toolbar{align-items:stretch;flex-direction:column}.retry-actions{display:grid;grid-template-columns:auto minmax(0,1fr)}.retry-actions :deep(.el-date-editor){width:100%}.retry-actions .el-button{grid-column:1/-1;margin:0}}
</style>
