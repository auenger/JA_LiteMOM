<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown, UploadFilled } from '@element-plus/icons-vue'
import api, { errorMessage } from '../api'
import { auth, has } from '../auth'
import type { BottleSource, QuickConfig } from '../types'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import TablePagination from '../components/TablePagination.vue'

const route = useRoute()
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const rows = ref<any[]>([])
const selected = ref<any | null>(null)
const detailLoading = ref(false)
const detailPage = ref(1)
const detailPageSize = ref(50)
const bottleCodeQuery = ref('')
const visibleLines = computed(() => {
  const query = bottleCodeQuery.value.trim().toLowerCase()
  return query ? (selected.value?.lines || []).filter((line: any) => String(line.body_code).toLowerCase().includes(query)) : (selected.value?.lines || [])
})
const pagedVisibleLines = computed(() => visibleLines.value.slice((detailPage.value - 1) * detailPageSize.value, detailPage.value * detailPageSize.value))
watch(bottleCodeQuery, () => { detailPage.value = 1 })
let detailRequestSerial = 0
function afterPaint(): Promise<void> {
  return new Promise((resolve) => {
    let completed = false
    const finish = () => {
      if (completed) return
      completed = true
      window.clearTimeout(fallback)
      resolve()
    }
    const fallback = window.setTimeout(finish, 120)
    requestAnimationFrame(() => requestAnimationFrame(finish))
  })
}
const sources = ref<BottleSource[]>([])
const specs = ref<{ id: number; name: string }[]>([])
const datePresets = ref<QuickConfig[]>([])
const inspectors = ref<any[]>([])
const loading = ref(false)
const generating = ref(false)
const importing = ref(false)
const importDialog = ref(false)
const importDate = ref('')
const importFile = ref<File | null>(null)
const reimportDialog = ref(false)
const reimportFile = ref<File | null>(null)
const reimporting = ref(false)
const deleting = ref(false)
const saving = ref(false)
const syncing = ref(false)
const exporting = ref(false)
const exportingReceiptWord = ref(false)
const xlsExportDialog = ref(false)
const xlsExportMode = ref<ExportMode>('full')
const xlsExportDate = ref(today)
const exportingWord = ref(false)
const wordDialog = ref(false)
const wordReportDate = ref(today)
const wordTemplateKey = ref('default')
const wordTemplates = ref<{ key: string; name: string; description: string }[]>([])
const wordTemplatesLoading = ref(false)
type WordCode = { id: number; report_date: string; first_number: number; regular_code: string; assessment_code: string }
const wordCodesDialog = ref(false)
const wordCodesLoading = ref(false)
const wordCodesSaving = ref(false)
const wordCodesDocument = ref<any | null>(null)
const wordCodes = ref<WordCode[]>([])
const editingWordCodeId = ref<number | null>(null)
const wordCodeForm = reactive({ report_date: today, first_number: 1 })
const wordCodePreview = computed(() => {
  const date = wordCodeForm.report_date
  const number = Number(wordCodeForm.first_number)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isInteger(number) || number < 1 || number > 998) return ''
  const prefix = `WFJA-${date.slice(2, 4)}-${date.slice(5, 7)}${date.slice(8, 10)}`
  return `${prefix}${String(number).padStart(3, '0')} / ${prefix}${String(number + 1).padStart(3, '0')}`
})
const exportingSingleReports = ref(false)
const exportingLineId = ref<number | null>(null)
const singleReportDialog = ref(false)
const singleReportDate = ref(today)
const singleReportTarget = ref<any | null>(null)
const marking = ref(false)
const markDialog = ref(false)
const rejectionText = ref('')
const editLineDialog = ref(false)
const editingLineId = ref<number | null>(null)
const savingLine = ref(false)
const lineForm = reactive({ body_code: '', manufacture_date: '', manufacturer: '', volume: 0, next_inspection_date: '' as string | null, spec_id: undefined as number | undefined })
const originalManufactureDate = ref<string | null>(null)
watch(() => lineForm.manufacture_date, (value) => {
  const cleaned = value.replace(/[^0-9.]/g, '')
  const digits = cleaned.replace(/\D/g, '')
  const normalized = digits.length >= 6 ? `${digits.slice(0, 4)}.${digits.slice(4, 6)}` : cleaned
  if (normalized !== value) lineForm.manufacture_date = normalized
})
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dateRange = ref<[string, string] | null>(null)
const generateDialog = ref(false)
const generateMonth = ref((typeof route.query.date === 'string' ? route.query.date : today).slice(0, 7))
type GenerationDay = { date: string; quantity: number; customer_count: number; generated: boolean; selectable: boolean }
const generationDays = ref<GenerationDay[]>([])
const generationDatesLoading = ref(false)
const generationDatesError = ref(false)
const chosenDates = ref<string[]>([])
const generationDocumentDate = ref('')
const availableDays = computed(() => generationDays.value.filter(day => day.selectable))
const chosenQuantity = computed(() => generationDays.value.filter(day => chosenDates.value.includes(day.date)).reduce((sum, day) => sum + day.quantity, 0))
let generationRequestSerial = 0
async function loadGenerationDates() {
  const serial = ++generationRequestSerial
  chosenDates.value = []
  generationDocumentDate.value = ''
  generationDays.value = []
  generationDatesLoading.value = true
  generationDatesError.value = false
  try {
    const { data } = await api.get('/inspection-documents/generation-dates', { params: { month: generateMonth.value } })
    if (serial === generationRequestSerial) generationDays.value = data
  } catch (err) {
    if (serial === generationRequestSerial) { generationDatesError.value = true; ElMessage.error(errorMessage(err)) }
  } finally { if (serial === generationRequestSerial) generationDatesLoading.value = false }
}
function openGenerateDialog() {
  generateDialog.value = true
  loadGenerationDates()
}
watch(generateMonth, () => { if (generateDialog.value) loadGenerationDates() })
function sourceDatesText(document: any) {
  return (document.source_dates || [document.inspection_date]).join('、')
}
const splitDialog = ref(false)
const splitForm = reactive({ start_sequence: 1, end_sequence: 1, customer_id: undefined as number | undefined, target_document_id: undefined as number | undefined })
const splitPreview = ref<any | null>(null)
const splitTargets = ref<any[]>([])
const splitPreviewLoading = ref(false)
const splitting = ref(false)
const splitHistory = ref<any[]>([])
const splitHistoryTotal = ref(0)
const splitHistoryPage = ref(1)
const splitHistoryPageSize = ref(20)
const splitHistoryLoading = ref(false)
const splitSnapshot = ref<any | null>(null)
let splitPreviewSerial = 0
let splitHistoryRequestSerial = 0
watch(() => [splitForm.start_sequence, splitForm.end_sequence, splitForm.customer_id], () => {
  ++splitPreviewSerial
  splitPreview.value = null
  splitTargets.value = []
  splitForm.target_document_id = undefined
  splitPreviewLoading.value = false
})
watch(() => splitForm.target_document_id, () => { ++splitPreviewSerial; splitPreview.value = null; splitPreviewLoading.value = false })
async function loadSplitHistory() {
  const id = selected.value?.id
  if (!id) return
  const serial = ++splitHistoryRequestSerial
  splitHistoryLoading.value = true
  try {
    const { data } = await api.get(`/inspection-documents/${id}/split-history`, { params: { page: splitHistoryPage.value, page_size: splitHistoryPageSize.value } })
    if (serial === splitHistoryRequestSerial && selected.value?.id === id) { splitHistory.value = data.items || []; splitHistoryTotal.value = data.total || 0 }
  } catch (err) { if (serial === splitHistoryRequestSerial) ElMessage.error(errorMessage(err)) } finally { if (serial === splitHistoryRequestSerial) splitHistoryLoading.value = false }
}
function splitHistoryPageChanged(nextPage: number, nextSize: number) { splitHistoryPage.value = nextPage; splitHistoryPageSize.value = nextSize; loadSplitHistory() }
async function openSplitDialog() {
  if (!selected.value) return
  splitPreview.value = null
  splitTargets.value = []
  Object.assign(splitForm, { start_sequence: 1, end_sequence: selected.value.lines.length, customer_id: undefined, target_document_id: undefined })
  splitDialog.value = true
  await nextTick()
}
async function previewSplit() {
  if (!selected.value || !splitForm.customer_id) return ElMessage.warning('请选择目标客户')
  if (splitForm.end_sequence < splitForm.start_sequence) return ElMessage.warning('结束序号不能小于起始序号')
  const serial = ++splitPreviewSerial
  splitPreview.value = null
  splitPreviewLoading.value = true
  try {
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/split-preview`, { ...splitForm })
    if (serial !== splitPreviewSerial) return
    splitTargets.value = data.target_candidates
    splitPreview.value = data
  } catch (err) { if (serial === splitPreviewSerial) ElMessage.error(errorMessage(err)) }
  finally { if (serial === splitPreviewSerial) splitPreviewLoading.value = false }
}
async function confirmSplit() {
  const preview = splitPreview.value
  if (!preview || preview.requires_target_selection || !selected.value) return
  splitting.value = true
  try {
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/split`, {
      ...splitForm, expected_line_ids: preview.line_ids, expected_source_updated_at: preview.source_updated_at,
      expected_target_id: preview.target?.id || null, expected_target_updated_at: preview.target?.updated_at || null,
      confirm_create: preview.will_create,
    })
    splitDialog.value = false
    await load()
    await openDocument(data.source)
    ElMessage.success(`已拆出 ${data.history.quantity} 只，${data.history.target_created ? '新建' : '合并到'} ${data.target.document_no}${data.history.source_emptied ? '；原单已拆空，单号和历史保留' : ''}`)
  } catch (err) { ElMessage.error(errorMessage(err)); splitPreview.value = null }
  finally { splitting.value = false }
}
const form = reactive<{ customer_name: string; inspector_id?: number }>({ customer_name: '', inspector_id: undefined })

async function load() {
  loading.value = true
  try {
    const [records, options] = await Promise.all([
      api.get('/inspection-documents', { params: { date_from: dateRange.value?.[0], date_to: dateRange.value?.[1], page: page.value, page_size: pageSize.value } }),
      api.get('/options'),
    ])
    rows.value = records.data.items
    total.value = records.data.total
    sources.value = options.data.sources || []
    specs.value = options.data.specs || []
    datePresets.value = options.data.date_presets || []
    inspectors.value = (options.data.users || []).filter((item: any) => item.is_active !== false && !item.is_superadmin)
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}

async function openDocument(row: any) {
  const serial = ++detailRequestSerial
  detailLoading.value = true
  selected.value = null
  await nextTick()
  await afterPaint()
  try {
    const { data } = await api.get(`/inspection-documents/${row.id}`)
    if (serial !== detailRequestSerial) return
    selected.value = data
    splitHistory.value = []
    splitHistoryTotal.value = 0
    splitHistoryPage.value = 1
    loadSplitHistory()
    bottleCodeQuery.value = ''
    detailPage.value = 1
    form.customer_name = data.customer_name || ''
    form.inspector_id = data.inspector_id || undefined
    await nextTick()
    await afterPaint()
  } catch (err) { if (serial === detailRequestSerial) ElMessage.error(errorMessage(err)) }
  finally { if (serial === detailRequestSerial) detailLoading.value = false }
}

async function generate() {
  if (!chosenDates.value.length) return ElMessage.warning('请选择需要合并生成的数据日期')
  if (!generationDocumentDate.value) return ElMessage.warning('请选择检验单日期')
  generating.value = true
  try {
    const { data } = await api.post('/inspection-documents/generate', {
      inspection_dates: [...chosenDates.value].sort(),
      document_date: generationDocumentDate.value,
    })
    generateDialog.value = false
    await load()
    await openDocument(data[0])
    ElMessage.success(`已按客户合并生成 ${data.length} 张检验单，共 ${data.reduce((sum: number, document: any) => sum + document.total_quantity, 0)} 只钢瓶`)
  } catch (err) {
    ElMessage.error(errorMessage(err))
    await loadGenerationDates()
  } finally { generating.value = false }
}

function openImportDialog() {
  importDate.value = ''
  importFile.value = null
  importDialog.value = true
}

function chooseImportFile(event: Event) {
  importFile.value = (event.target as HTMLInputElement).files?.[0] || null
}

async function importHistoricalDocument() {
  if (!importDate.value) return ElMessage.warning('请选择未生成过检验单的日期')
  if (!importFile.value) return ElMessage.warning('请选择全量检验单 Excel 文件')
  importing.value = true
  try {
    const payload = new FormData()
    payload.append('inspection_date', importDate.value)
    payload.append('file', importFile.value)
    const { data } = await api.post('/inspection-documents/import', payload, { timeout: 60000 })
    importFile.value = null
    importDialog.value = false
    await load()
    await openDocument(data)
    ElMessage.success(`已归档 ${data.document_no}，共 ${data.total_quantity} 条明细；未写入库存`)
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { importing.value = false }
}

function openReimportDialog() {
  reimportFile.value = null
  reimportDialog.value = true
}

function chooseReimportFile(event: Event) {
  reimportFile.value = (event.target as HTMLInputElement).files?.[0] || null
}

async function reimportDocument() {
  if (!selected.value || !reimportFile.value) return ElMessage.warning('请选择修改后的全量检验单 Excel 文件')
  reimporting.value = true
  try {
    const payload = new FormData()
    payload.append('file', reimportFile.value)
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/reimport`, payload, { timeout: 60000 })
    reimportDialog.value = false
    reimportFile.value = null
    await openDocument(data)
    await load()
    ElMessage.success('已按原序号更新检验单明细，并按生产日期重新排序')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { reimporting.value = false }
}

async function saveUnifiedFields() {
  if (!selected.value) return
  saving.value = true
  try {
    const { data } = await api.put(`/inspection-documents/${selected.value.id}`, form)
    selected.value = data
    ElMessage.success('客户和检验人员已统一应用到整张检验单')
    await load()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { saving.value = false }
}

function openEditLine(row: any) {
  editingLineId.value = row.id
  originalManufactureDate.value = row.manufacture_date || null
  Object.assign(lineForm, {
    body_code: row.body_code,
    manufacture_date: row.manufacture_date?.slice(0, 7).replace('-', '.') || '',
    manufacturer: row.manufacturer || '',
    volume: Number(row.volume || 0),
    next_inspection_date: row.next_inspection_date || '',
    spec_id: row.spec_id || undefined,
  })
  editLineDialog.value = true
}

async function saveLine() {
  if (!selected.value || editingLineId.value === null) return
  if (!lineForm.body_code.trim()) return ElMessage.warning('请填写产品编号')
  const inputMonth = lineForm.manufacture_date.trim()
  if (inputMonth && !/^\d{4}\.\d{2}$/.test(inputMonth)) return ElMessage.warning('生产日期请填写完整年月，如 2022.09')
  if (inputMonth && (Number(inputMonth.slice(5)) < 1 || Number(inputMonth.slice(5)) > 12)) return ElMessage.warning('生产日期的月份应在 01 至 12 之间')
  // 旧记录可能保存了具体日期：只改其他字段时保留原日，改了月份才按快捷抄码规则取当月 1 日。
  const manufactureDate = !inputMonth ? null : inputMonth === originalManufactureDate.value?.slice(0, 7).replace('-', '.')
    ? originalManufactureDate.value : `${inputMonth.replace('.', '-')}-01`
  savingLine.value = true
  try {
    const { data } = await api.put(`/inspection-documents/${selected.value.id}/lines/${editingLineId.value}`, {
      body_code: lineForm.body_code.trim(),
      manufacture_date: manufactureDate,
      manufacturer: lineForm.manufacturer.trim(),
      ...(selected.value.is_archived ? {
        volume: lineForm.volume,
        next_inspection_date: lineForm.next_inspection_date || null,
        spec_id: lineForm.spec_id || null,
      } : {}),
    })
    selected.value = data
    bottleCodeQuery.value = ''
    editLineDialog.value = false
    ElMessage.success('明细已保存，生产日期和序号已按最新数据重新排序')
    await load()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { savingLine.value = false }
}

async function syncLines() {
  if (!selected.value) return
  syncing.value = true
  const before = selected.value.total_quantity
  try {
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/sync`)
    selected.value = data
    ElMessage.success(data.total_quantity > before ? `已新增 ${data.total_quantity - before} 条当日钢瓶` : '当日没有新的良品钢瓶')
    await load()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { syncing.value = false }
}

async function voidDocument() {
  if (!selected.value) return
  try {
    await ElMessageBox.confirm(`确认作废这张包含 ${selected.value.total_quantity} 只钢瓶的检验单？`, '作废检验单', { type: 'warning', confirmButtonText: '确认作废' })
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/void`)
    selected.value = data
    ElMessage.success(selected.value.is_retry ? '重检单已作废，来源钢瓶已返回未验证池' : '检验单已作废，相关钢瓶已解除“已检验”标记')
    await load()
  } catch (err: any) { if (err !== 'cancel' && err !== 'close') ElMessage.error(errorMessage(err)) }
}

async function deleteVoidDocument() {
  if (!selected.value || selected.value.status !== 'VOID' || !auth.user?.is_superadmin) return
  const documentId = selected.value.id
  const documentNo = selected.value.document_no
  try {
    await ElMessageBox.prompt(`此操作将永久删除 ${documentNo} 及其明细和专属驳回记录，且无法撤销。库存钢瓶不会删除。请输入完整单号确认：`, '彻底删除作废检验单', {
      type: 'error',
      confirmButtonText: '确认永久删除',
      cancelButtonText: '取消',
      inputPlaceholder: documentNo,
      inputValidator: (value: string) => value.trim() === documentNo || '请输入完全一致的检验单号',
    })
  } catch { return }
  deleting.value = true
  try {
    await api.delete(`/inspection-documents/${documentId}`)
    ++detailRequestSerial
    selected.value = null
    bottleCodeQuery.value = ''
    if (rows.value.length === 1 && page.value > 1) page.value -= 1
    await load()
    ElMessage.success(`${documentNo} 已彻底删除`)
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { deleting.value = false }
}

function openMarkDialog() {
  rejectionText.value = ''
  markDialog.value = true
}

async function submitUnverifiedMarks() {
  if (!selected.value || !rejectionText.value.trim()) return ElMessage.warning('请粘贴上游系统返回的错误信息')
  marking.value = true
  try {
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/mark-unverified`, { raw_text: rejectionText.value })
    await openDocument(selected.value)
    markDialog.value = false
    const unmatched = data.unmatched_sequences.length ? `；未找到序号：${data.unmatched_sequences.join('、')}` : ''
    ElMessage.success(`已标注 ${data.total_marked} 只未经系统验证钢瓶${unmatched}`)
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { marking.value = false }
}

type ExportMode = 'full' | 'verified' | 'unverified'

async function downloadXls(kind: ExportMode, filename: string) {
  const { data } = await api.post(`/inspection-documents/${selected.value.id}/export-xls`, null, {
    params: { kind, export_date: xlsExportDate.value }, responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function exportFilename(prefix: 'JY-', category: string, quantity: number) {
  const customer = String(selected.value.customer_name || '未设置客户').replace(/[\\/:*?"<>|]/g, '_')
  const date = xlsExportDate.value.replaceAll('-', '')
  return `${prefix}${customer}${date}${category}[${quantity}].xls`
}

function previousExportDate(kind: string, lines: any[]) {
  return selected.value?.export_dates?.[kind]
    || lines.find((line: any) => line.inspection_time)?.inspection_time
    || today
}

function openXlsExportDialog(mode: ExportMode) {
  if (!selected.value) return
  if (mode === 'unverified' && !selected.value.lines.some((line: any) => line.is_unverified)) return ElMessage.warning('当前检验单没有标黄的未经系统验证钢瓶')
  if (!selected.value.customer_name) return ElMessage.warning('请先统一设置客户/充装单位')
  if (!selected.value.inspector_name) return ElMessage.warning('请先统一设置检验人员')
  xlsExportMode.value = mode
  const lines = selected.value.lines.filter((line: any) => mode === 'full' || (mode === 'unverified' ? line.is_unverified : !line.is_unverified))
  xlsExportDate.value = previousExportDate(`xls:${mode}`, lines)
  xlsExportDialog.value = true
}

async function exportXls() {
  if (!selected.value || !xlsExportDate.value) return ElMessage.warning('请选择检验日期')
  exporting.value = true
  try {
    const verifiedLines = selected.value.lines.filter((item: any) => !item.is_unverified)
    const unverifiedLines = selected.value.lines.filter((item: any) => item.is_unverified)

    if (xlsExportMode.value === 'full') {
      await downloadXls('full', exportFilename('JY-', '全量检测单', selected.value.lines.length))
      ElMessage.success(`已导出全量 ${selected.value.lines.length} 只钢瓶的 Excel`)
    } else if (xlsExportMode.value === 'verified') {
      await downloadXls('verified', exportFilename('JY-', '成功上传', verifiedLines.length))
      ElMessage.success(`已剔除 ${selected.value.lines.length - verifiedLines.length} 只，导出 ${verifiedLines.length} 只钢瓶`)
    } else {
      await downloadXls('unverified', exportFilename('JY-', '未经系统验证', unverifiedLines.length))
      ElMessage.success(`已导出标黄的 ${unverifiedLines.length} 只未经系统验证钢瓶`)
    }
    selected.value.lines.forEach((line: any) => {
      if (xlsExportMode.value !== 'unverified' || line.is_unverified) line.inspection_time = xlsExportDate.value
    })
    selected.value.export_dates[`xls:${xlsExportMode.value}`] = xlsExportDate.value
    xlsExportDialog.value = false
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { exporting.value = false }
}

async function exportReceiptWord() {
  if (!selected.value) return
  if (!selected.value.customer_name) return ElMessage.warning('请先统一设置客户/充装单位')
  if (!selected.value.inspector_name) return ElMessage.warning('请先统一设置检验人员')
  exportingReceiptWord.value = true
  try {
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/export-receipt-word`, null, {
      responseType: 'blob', timeout: 60000,
    })
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    const customer = String(selected.value.customer_name).replace(/[\\/:*?"<>|]/g, '_')
    link.download = `${customer}${selected.value.inspection_date.replaceAll('-', '')}来瓶登记[${selected.value.lines.length}].docx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    ElMessage.success('来瓶登记 Word 已导出')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { exportingReceiptWord.value = false }
}

async function openWordDialog() {
  if (!selected.value) return
  if (!selected.value.customer_name) return ElMessage.warning('请先统一设置客户/充装单位')
  wordReportDate.value = previousExportDate('word:all', selected.value.lines.filter((line: any) => !line.is_unverified))
  wordDialog.value = true
  wordTemplatesLoading.value = true
  try {
    const { data } = await api.get('/inspection-word-templates', { params: { customer_name: selected.value.customer_name } })
    wordTemplates.value = data.templates
    wordTemplateKey.value = data.selected_key
  } catch (err) { ElMessage.error(errorMessage(err)) }
  finally { wordTemplatesLoading.value = false }
}

async function openWordCodes(row: any) {
  wordCodesDocument.value = row
  wordCodes.value = []
  editingWordCodeId.value = null
  wordCodesDialog.value = true
  wordCodesLoading.value = true
  try {
    const { data } = await api.get(`/inspection-documents/${row.id}/word-codes`)
    if (wordCodesDocument.value?.id === row.id) wordCodes.value = data
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { wordCodesLoading.value = false }
}

function editWordCode(item: WordCode) {
  editingWordCodeId.value = item.id
  wordCodeForm.report_date = item.report_date
  wordCodeForm.first_number = item.first_number
}

async function saveWordCode() {
  const doc = wordCodesDocument.value
  const id = editingWordCodeId.value
  if (!doc || id === null || !wordCodePreview.value) return ElMessage.warning('请选择日期并填写 001 至 998 的起始序号')
  wordCodesSaving.value = true
  try {
    const params = { report_date: wordCodeForm.report_date, first_number: Number(wordCodeForm.first_number) }
    const { data: check } = await api.get(`/inspection-documents/${doc.id}/word-codes/${id}/check`, { params })
    if (check.conflict) return ElMessage.error(check.conflict_reason)
    if (check.existing_count > 0) {
      await ElMessageBox.confirm(
        `目标日期已有 ${check.existing_count} 组其他检验单的 Word 编码。本次将使用 ${check.regular_code}、${check.assessment_code}，保存后下次默认按该日期导出。确认修改？`,
        '目标日期已有报告', { type: 'warning', confirmButtonText: '确认修改', cancelButtonText: '取消' },
      )
    }
    await api.put(`/inspection-documents/${doc.id}/word-codes/${id}`, params)
    const { data } = await api.get(`/inspection-documents/${doc.id}/word-codes`)
    wordCodes.value = data
    if (selected.value?.id === doc.id) selected.value.export_dates['word:all'] = params.report_date
    editingWordCodeId.value = null
    ElMessage.success('Word 编码已更新，下次默认按修改后的日期导出')
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') ElMessage.error(errorMessage(err))
  } finally { wordCodesSaving.value = false }
}

async function exportWordReports() {
  if (!selected.value || !wordReportDate.value) return ElMessage.warning('请选择检测日期')
  exportingWord.value = true
  try {
    await api.put('/inspection-word-templates/choice', { template_key: wordTemplateKey.value }, {
      params: { customer_name: selected.value.customer_name },
    })
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/export-word-pair`, null, {
      params: { report_date: wordReportDate.value },
    })
    for (const report of data.reports as { filename: string; content_base64: string }[]) {
      const binary = atob(report.content_base64)
      const bytes = new Uint8Array(binary.length)
      for (let index = 0; index < binary.length; index++) bytes[index] = binary.charCodeAt(index)
      const url = URL.createObjectURL(new Blob([bytes.buffer as ArrayBuffer], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }))
      const link = document.createElement('a')
      link.href = url
      link.download = report.filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    }
    const quantity = selected.value.lines.filter((item: any) => !item.is_unverified).length
    selected.value.lines.forEach((line: any) => { if (!line.is_unverified) line.inspection_time = wordReportDate.value })
    selected.value.export_dates['word:all'] = wordReportDate.value
    wordDialog.value = false
    const numbers = (data.reports as { report_number: number }[]).map((item) => String(item.report_number).padStart(3, '0')).join('、')
    ElMessage.success(`已下载定检与评定两份 Word，报告序号 ${numbers}，共 ${quantity} 只钢瓶`)
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { exportingWord.value = false }
}

function openSingleReportDialog(row: any | null = null) {
  if (!selected.value) return
  if (!selected.value.customer_name) return ElMessage.warning('请先统一设置客户/充装单位')
  if (row?.is_unverified) return ElMessage.warning('被上游驳回的钢瓶不能导出单瓶检测报告')
  if (!row && !selected.value.lines.some((line: any) => !line.is_unverified)) return ElMessage.warning('检验单中没有未被上游驳回的钢瓶')
  singleReportTarget.value = row
  singleReportDate.value = row
    ? previousExportDate(`bottle:${row.id}`, [row])
    : previousExportDate('bottle:all', selected.value.lines.filter((line: any) => !line.is_unverified))
  singleReportDialog.value = true
}

async function confirmSingleReportExport() {
  if (!singleReportDate.value) return ElMessage.warning('请选择检测日期')
  if (singleReportTarget.value) await exportOneBottleReport(singleReportTarget.value, singleReportDate.value)
  else await exportSingleReports(singleReportDate.value)
}

async function exportSingleReports(reportDate: string) {
  if (!selected.value) return
  if (!selected.value.customer_name) return ElMessage.warning('请先统一设置客户/充装单位')
  const eligibleCount = selected.value.lines.filter((item: any) => !item.is_unverified).length
  if (!eligibleCount) return ElMessage.warning('检验单中没有未被上游驳回的钢瓶')
  exportingSingleReports.value = true
  try {
    await nextTick()
    await afterPaint()
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/export-bottle-reports`, null, {
      params: { report_date: reportDate }, responseType: 'blob',
    })
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = `${selected.value.document_no}-单瓶检测报告[${eligibleCount}].zip`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    selected.value.lines.forEach((line: any) => { if (!line.is_unverified) line.inspection_time = reportDate })
    selected.value.export_dates['bottle:all'] = reportDate
    singleReportDialog.value = false
    ElMessage.success(`已生成 ${eligibleCount} 份未被驳回钢瓶的单瓶检测报告，保存在 ZIP 压缩包中`)
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { exportingSingleReports.value = false }
}

async function exportOneBottleReport(row: any, reportDate: string) {
  if (!selected.value) return
  if (!selected.value.customer_name) return ElMessage.warning('请先统一设置客户/充装单位')
  if (row.is_unverified) return ElMessage.warning('被上游驳回的钢瓶不能导出单瓶检测报告')
  exportingLineId.value = row.id
  try {
    const { data } = await api.post(`/inspection-documents/${selected.value.id}/lines/${row.id}/export-bottle-report`, null, {
      params: { report_date: reportDate }, responseType: 'blob',
    })
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    const safeCode = String(row.body_code).replace(/[\\/:*?"<>|]/g, '_')
    const exportDate = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()).replaceAll('-', '')
    link.download = `${safeCode}[${exportDate}].docx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    row.inspection_time = reportDate
    selected.value.export_dates[`bottle:${row.id}`] = reportDate
    singleReportDialog.value = false
    ElMessage.success(`已导出 ${row.body_code} 的单瓶检测报告`)
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { exportingLineId.value = null }
}

function search() { page.value = 1; load() }
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
function detailPageChanged(nextPage: number, nextSize: number) { detailPage.value = nextPage; detailPageSize.value = nextSize }
function timeText(value?: string) { return value ? new Date(`${value}Z`).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '-' }
function inspectionRowClassName({ row }: { row: any }) { return row.is_unverified ? 'unverified-row' : '' }

onMounted(async () => {
  await load()
  if (route.query.generate === '1' && has('inspection_documents:create')) {
    openGenerateDialog()
  } else if (typeof route.query.document === 'string') {
    await openDocument({ id: Number(route.query.document) })
  }
})
</script>

<template>
  <div>
    <PageHeader title="钢瓶检验单" description="选择同月多个未生成日期，按客户合并生成检验单；钢瓶仍属于良品库存并可出库。">
      <el-button v-if="has('inspection_documents:create')" type="primary" :loading="generating" @click="openGenerateDialog"><GameIcon name="plus" />生成检验单</el-button>
      <el-button v-if="has('inspection_documents:create')" :icon="UploadFilled" @click="openImportDialog">导入历史检验单</el-button>
    </PageHeader>

    <el-dialog v-model="generateDialog" title="按客户合并生成检验单" width="min(680px, 94vw)" :close-on-click-modal="false" :close-on-press-escape="!generating" :show-close="!generating">
      <div class="generation-toolbar">
        <el-date-picker v-model="generateMonth" type="month" value-format="YYYY-MM" :clearable="false" :disabled="generating" />
        <el-button :disabled="generationDatesLoading || generating || !availableDays.length" @click="chosenDates = availableDays.map(day => day.date)">全选未生成日期</el-button>
        <el-button :disabled="generating || !chosenDates.length" @click="chosenDates = []">清空</el-button>
      </div>
      <p class="muted">第一步选择要合并的良品数据日期。同一客户的多天数据合并为一张检验单，单内序号从 1 开始。</p>
      <div v-loading="generationDatesLoading" class="generation-calendar">
        <el-checkbox-group v-model="chosenDates" class="generation-days" :disabled="generating">
          <el-checkbox v-for="day in generationDays" :key="day.date" :value="day.date" :disabled="!day.selectable" border>
            <strong>{{ Number(day.date.slice(-2)) }} 日</strong>
            <small>{{ day.generated ? '已生成' : day.quantity ? `${day.quantity} 只 · ${day.customer_count} 客户` : '无良品数据' }}</small>
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <el-alert v-if="!generationDatesLoading && generationDatesError" title="日期加载失败，请重试。" type="error" :closable="false" />
      <el-button v-if="generationDatesError" @click="loadGenerationDates">重新加载</el-button>
      <el-alert v-else-if="!generationDatesLoading && !availableDays.length" title="该月没有可生成的日期，可切换月份查看。" type="info" :closable="false" />
      <div v-if="chosenDates.length" class="generation-document-date">
        <div><strong>第二步：选择检验单日期</strong><p class="muted">已选 {{ chosenDates.length }} 天数据，共 {{ chosenQuantity }} 只钢瓶。检验单日期将用于单据编号和检验日期。</p></div>
        <el-date-picker v-model="generationDocumentDate" type="date" value-format="YYYY-MM-DD" placeholder="选择检验单日期" :disabled="generating" />
      </div>
      <template #footer><el-button :disabled="generating" @click="generateDialog = false">取消</el-button><el-button type="primary" :loading="generating" :disabled="generationDatesLoading || !chosenDates.length || !generationDocumentDate" @click="generate">按客户合并生成</el-button></template>
    </el-dialog>

    <section class="surface">
      <div class="surface-header filters"><el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" clearable /><el-button type="primary" @click="search"><GameIcon name="search" />查询</el-button><span class="grow" /><span class="muted">共 {{ total }} 张</span></div>
      <el-table v-if="rows.length" v-loading="loading" :data="rows" stripe>
        <el-table-column prop="document_no" label="单据编号" min-width="155"><template #default="{ row }"><strong class="numeric">{{ row.document_no }}</strong></template></el-table-column>
        <el-table-column prop="inspection_date" label="检验日期" width="115" />
        <el-table-column label="来源日期" min-width="190"><template #default="{ row }">{{ sourceDatesText(row) }}</template></el-table-column>
        <el-table-column prop="customer_name" label="客户/充装单位" min-width="180"><template #default="{ row }">{{ row.customer_name || '待设置' }}</template></el-table-column>
        <el-table-column prop="inspector_name" label="检验人员" width="120"><template #default="{ row }">{{ row.inspector_name || '待设置' }}</template></el-table-column>
        <el-table-column prop="total_quantity" label="钢瓶数" width="90" align="right" />
        <el-table-column label="来源" width="105"><template #default="{ row }"><el-tag v-if="row.is_retry" type="warning" size="small">重检单</el-tag><el-tag v-else-if="row.is_archived" type="info" size="small">归档导入</el-tag><span v-else>系统生成</span></template></el-table-column>
        <el-table-column label="状态" width="90"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
        <el-table-column prop="created_by_name" label="创建人" width="110" />
        <el-table-column label="操作" width="175"><template #default="{ row }"><el-button link type="primary" @click="openDocument(row)">查看</el-button><el-button link type="primary" @click="openWordCodes(row)">Word 编码</el-button></template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : '还没有检验单'" description="选择月份和未生成日期，系统按客户合并良品数据，并按生产日期从近到远排序。" />
      <TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>

    <section v-if="selected || detailLoading" v-loading="detailLoading || exportingSingleReports" :element-loading-text="exportingSingleReports ? '正在生成并打包全部单瓶报告…' : '正在加载检验单…'" class="surface document-detail">
      <div v-if="!selected" class="detail-loading-placeholder">正在读取检验单明细…</div>
      <template v-else>
      <div class="surface-header detail-header">
        <div><h2>{{ selected.document_no }}</h2><span class="muted">检验日期 {{ selected.inspection_date }} · 来源日期 {{ sourceDatesText(selected) }} · {{ selected.total_quantity }} 只 · 创建于 {{ timeText(selected.created_at) }}</span></div>
        <span class="grow" />
        <el-tag v-if="selected.is_retry" type="warning">重检单</el-tag><el-tag v-else-if="selected.is_archived" type="info">归档导入</el-tag>
        <StatusTag :status="selected.status" />
        <el-button v-if="selected.status === 'ACTIVE' && !selected.is_archived && !selected.is_retry && has('inspection_documents:update')" @click="openSplitDialog">拆单 / 分单</el-button>
        <el-button v-if="selected.status === 'ACTIVE' && has('unverified_bottles:create')" type="warning" plain @click="openMarkDialog">录入上游驳回信息</el-button>
        <el-button v-if="selected.status === 'ACTIVE' && !selected.is_archived && has('inspection_documents:create')" :loading="syncing" @click="syncLines"><GameIcon name="refresh" />同步所选日期新增</el-button>
        <el-dropdown v-if="selected.status === 'ACTIVE' && has('inspection_documents:export')" trigger="click" @command="openXlsExportDialog"><el-button type="primary" :loading="exporting">导出 XLS<el-icon class="el-icon--right"><arrow-down /></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="full">导出全量检验单数据</el-dropdown-item><el-dropdown-item command="verified">导出剔除未经验证数据</el-dropdown-item><el-dropdown-item command="unverified">仅导出标黄未通过数据</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
        <el-button v-if="selected.status === 'ACTIVE' && has('inspection_documents:export')" :loading="exportingReceiptWord" @click="exportReceiptWord">导出来瓶登记 Word</el-button>
        <el-button v-if="selected.status === 'ACTIVE' && has('inspection_documents:update')" :icon="UploadFilled" :loading="reimporting" @click="openReimportDialog">回导修改后的检验单</el-button>
        <el-button v-if="selected.status === 'ACTIVE' && has('inspection_documents:export')" :loading="exportingWord" @click="openWordDialog">导出 Word</el-button>
        <el-button @click="openWordCodes(selected)">查看 Word 编码</el-button>
        <el-button v-if="selected.status === 'ACTIVE' && has('inspection_documents:export')" :loading="exportingSingleReports" @click="openSingleReportDialog()">导出未被驳回的单瓶检测报告</el-button>
        <el-button v-if="selected.status === 'ACTIVE' && has('inspection_documents:void')" type="danger" plain @click="voidDocument">作废</el-button>
        <el-button v-if="selected.status === 'VOID' && auth.user?.is_superadmin" type="danger" :loading="deleting" @click="deleteVoidDocument">彻底删除</el-button>
      </div>
      <el-alert v-if="selected.status === 'SPLIT_EMPTY'" title="原单明细已全部拆出。原单号及拆单历史保留，可在下方查看去向和原序号快照。" type="info" :closable="false" />
      <el-alert v-if="selected.status === 'ACTIVE'" :title="selected.is_retry ? '本单由未验证钢瓶池当前筛选结果生成，按生产日期重排序号；原检验单驳回历史保留。本单仅保存快照，不再次修改库存钢瓶。' : selected.is_archived ? '历史归档明细可编辑，修改生产日期后将重排序号；不写入库存。单瓶报告需要明确的钢瓶规格，容积唯一匹配时自动识别。' : '以下钢瓶按生产日期从近到远排列，表格序号与 Excel 完全一致；更正编号、生产日期和厂家时会同步修改关联的真实钢瓶。'" type="info" :closable="false" />
      <el-form class="unified-form" label-position="top">
        <el-form-item label="客户/充装单位"><el-select v-model="form.customer_name" filterable clearable placeholder="选择客户/充装单位"><el-option v-for="item in sources" :key="item.id" :label="item.name" :value="item.name" /></el-select></el-form-item>
        <el-form-item label="检验人员"><el-select v-model="form.inspector_id" filterable clearable placeholder="选择检验人员"><el-option v-for="item in inspectors" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-button v-if="selected.status === 'ACTIVE' && has('inspection_documents:update')" type="primary" :loading="saving" @click="saveUnifiedFields">批量应用到整单</el-button>
      </el-form>
      <div class="detail-search"><el-input v-model="bottleCodeQuery" clearable placeholder="输入瓶子编码搜索定位"><template #prefix><GameIcon name="search" /></template></el-input><span class="muted">{{ bottleCodeQuery.trim() ? `找到 ${visibleLines.length} / ${selected.lines.length} 只` : `共 ${selected.lines.length} 只` }}</span></div>
      <el-table :data="pagedVisibleLines" stripe max-height="560" :row-class-name="inspectionRowClassName">
        <el-table-column prop="sequence" label="序号" width="70" align="right" />
        <el-table-column prop="body_code" label="产品编号" min-width="170"><template #default="{ row }"><strong class="numeric">{{ row.body_code }}</strong></template></el-table-column>
        <el-table-column prop="manufacture_date" label="生产日期" width="115"><template #default="{ row }">{{ row.manufacture_date?.slice(0, 7) || '-' }}</template></el-table-column>
        <el-table-column prop="manufacturer" label="生产厂家" min-width="180"><template #default="{ row }">{{ row.manufacturer || '-' }}</template></el-table-column>
        <el-table-column prop="volume" label="容积" width="90" align="right"><template #default="{ row }">{{ Number(row.volume || 0).toFixed(2) }}</template></el-table-column>
        <el-table-column label="瓶子入库时间" width="180"><template #default="{ row }">{{ timeText(row.inbound_at) }}</template></el-table-column>
        <el-table-column label="检验时间" width="115"><template #default="{ row }">{{ row.inspection_time || '' }}</template></el-table-column>
        <el-table-column label="客户" min-width="160"><template #default>{{ selected.customer_name || '待设置' }}</template></el-table-column>
        <el-table-column label="检验人员" width="110"><template #default="{ row }">{{ row.inspector_name || selected.inspector_name || '待设置' }}</template></el-table-column>
        <el-table-column label="上游验证" min-width="180" fixed="right"><template #default="{ row }"><el-tooltip v-if="row.is_unverified" :content="row.validation_error" placement="top"><el-tag type="danger" size="small">未经系统验证</el-tag></el-tooltip><el-tag v-else type="success" size="small" effect="plain">未发现驳回</el-tag></template></el-table-column>
        <el-table-column v-if="selected.status === 'ACTIVE' && has('inspection_documents:update')" label="操作" width="78" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openEditLine(row)">编辑</el-button></template></el-table-column>
        <el-table-column v-if="selected.status === 'ACTIVE' && has('inspection_documents:export')" label="单瓶报告" width="115" fixed="right"><template #default="{ row }"><el-tooltip content="被上游驳回的钢瓶不能导出" :disabled="!row.is_unverified" placement="top"><span><el-button link type="primary" :disabled="row.is_unverified || exportingLineId !== null" :loading="exportingLineId === row.id" @click="openSingleReportDialog(row)">导出 Word</el-button></span></el-tooltip></template></el-table-column>
      </el-table>
      <TablePagination :page="detailPage" :page-size="detailPageSize" :total="visibleLines.length" @change="detailPageChanged" />
      <div class="split-history" v-loading="splitHistoryLoading">
        <h3>拆单 / 合并历史</h3>
        <el-table v-if="splitHistory.length" :data="splitHistory" stripe>
          <el-table-column label="原单 → 目标单" min-width="245"><template #default="{ row }"><el-button link type="primary" @click="openDocument({ id: row.source_document_id })">{{ row.source_document_no }}</el-button> → <el-button link type="primary" @click="openDocument({ id: row.target_document_id })">{{ row.target_document_no }}</el-button></template></el-table-column>
          <el-table-column label="客户变更" min-width="180"><template #default="{ row }">{{ row.source_customer_name }} → {{ row.target_customer_name }}</template></el-table-column>
          <el-table-column label="原序号区间" width="120"><template #default="{ row }">{{ row.start_sequence }}～{{ row.end_sequence }}</template></el-table-column>
          <el-table-column prop="quantity" label="拆出数量" width="95" />
          <el-table-column label="处理方式" width="135"><template #default="{ row }">{{ row.target_created ? '新建目标单' : '合并已有单' }}<el-tag v-if="row.source_emptied" size="small" type="info">原单已拆空</el-tag></template></el-table-column>
          <el-table-column prop="created_by_name" label="操作人" width="100" />
          <el-table-column label="操作时间" width="180"><template #default="{ row }">{{ timeText(row.created_at) }}</template></el-table-column>
          <el-table-column label="快照" width="90"><template #default="{ row }"><el-button link type="primary" @click="splitSnapshot = row">查看快照</el-button></template></el-table-column>
        </el-table>
        <p v-else class="muted">暂无拆单历史</p>
        <TablePagination v-if="splitHistoryTotal" :page="splitHistoryPage" :page-size="splitHistoryPageSize" :total="splitHistoryTotal" @change="splitHistoryPageChanged" />
      </div>
      </template>
    </section>

    <el-dialog v-model="splitDialog" title="按连续序号拆单 / 分单" width="min(760px, 94vw)" :close-on-click-modal="false" :show-close="!splitting" :close-on-press-escape="!splitting">
      <el-alert title="拆出的钢瓶从原单移除，抄码客户同步改为目标客户。库存原供瓶单位、入库和出库记录保留原归属。两张单据会重新排序编号，请重新导出受影响的文件。" type="info" :closable="false" />
      <div class="split-fields">
        <label>起始序号<el-input-number v-model="splitForm.start_sequence" :min="1" :max="selected?.lines.length || 1" :precision="0" :disabled="splitting" /></label>
        <label>结束序号<el-input-number v-model="splitForm.end_sequence" :min="1" :max="selected?.lines.length || 1" :precision="0" :disabled="splitting" /></label>
        <label>目标客户<el-select v-model="splitForm.customer_id" filterable :disabled="splitting" placeholder="选择目标客户"><el-option v-for="source in sources.filter(item => item.is_active)" :key="source.id" :label="source.name" :value="source.id" /></el-select></label>
      </div>
      <div v-if="splitTargets.length > 1" class="split-target"><label>该客户同日有多张检验单，请选择合并目标</label><el-select v-model="splitForm.target_document_id" :disabled="splitting" placeholder="选择目标检验单"><el-option v-for="target in splitTargets" :key="target.id" :label="`${target.document_no}（${target.total_quantity} 只）`" :value="target.id" /></el-select></div>
      <el-button :loading="splitPreviewLoading" :disabled="splitting" @click="previewSplit">预览拆单</el-button>
      <div v-if="splitPreview" class="split-preview">
        <el-alert v-if="splitPreview.will_create" :title="`检验日期 ${selected?.inspection_date} 下，${splitPreview.customer_name} 尚无检验单。继续拆单将创建该客户的新检验单。`" type="warning" :closable="false" />
        <el-alert v-else-if="splitPreview.target" :title="`将合并到 ${splitPreview.target.document_no}，目标单由 ${splitPreview.target.total_quantity} 只变为 ${splitPreview.target.total_quantity + splitPreview.quantity} 只。`" type="success" :closable="false" />
        <p>原序号 {{ splitForm.start_sequence }}～{{ splitForm.end_sequence }}，共 {{ splitPreview.quantity }} 只。原单剩余 {{ splitPreview.source_quantity_after }} 只{{ splitPreview.source_quantity_after === 0 ? '，拆空后保留单号和历史' : '' }}。</p>
        <el-table :data="splitPreview.lines" max-height="280" stripe><el-table-column prop="sequence" label="原序号" width="80" /><el-table-column prop="body_code" label="产品编号" min-width="160" /><el-table-column prop="manufacture_date" label="生产日期" width="115" /><el-table-column prop="manufacturer" label="生产厂家" min-width="150" /></el-table>
        <p v-if="splitPreview.will_create && !has('inspection_documents:create')" class="muted">你没有创建检验单的权限，无法新建目标单。</p>
      </div>
      <template #footer><el-button :disabled="splitting" @click="splitDialog = false">取消</el-button><el-button type="primary" :loading="splitting" :disabled="!splitPreview || splitPreview.requires_target_selection || (splitPreview.will_create && !has('inspection_documents:create'))" @click="confirmSplit">{{ splitPreview?.will_create ? '创建新单并拆分' : '确认拆分并合并' }}</el-button></template>
    </el-dialog>

    <el-dialog :model-value="!!splitSnapshot" title="拆单时的明细快照" width="min(900px, 94vw)" @close="splitSnapshot = null">
      <template v-if="splitSnapshot"><p>{{ splitSnapshot.source_document_no }} → {{ splitSnapshot.target_document_no }} · 原序号 {{ splitSnapshot.start_sequence }}～{{ splitSnapshot.end_sequence }} · {{ splitSnapshot.quantity }} 只 · {{ timeText(splitSnapshot.created_at) }}</p><p class="muted">以下是拆单前保存的原序号和明细，不受后续修改影响。</p><el-table :data="splitSnapshot.snapshot" max-height="460" stripe><el-table-column prop="sequence" label="原序号" width="80" /><el-table-column prop="body_code" label="产品编号" min-width="160" /><el-table-column prop="manufacture_date" label="生产日期" width="115" /><el-table-column prop="manufacturer" label="生产厂家" min-width="150" /><el-table-column prop="volume" label="容积" width="90" /><el-table-column prop="validation_error" label="当时驳回信息" min-width="180" /></el-table></template>
    </el-dialog>

    <el-dialog v-model="editLineDialog" title="编辑检验单明细" width="620px" destroy-on-close>
      <el-alert :title="selected?.is_retry ? '重检单只修正本单快照，不再次修改库存或原检验单；生产日期变更后自动重排并更新序号。' : selected?.is_archived ? '历史归档只修正检验单快照，不关联库存；生产日期变更后自动重排并更新序号。' : '编号、生产日期和厂家会同步修改真实钢瓶；生产日期变更后自动重排并更新序号。已标注的驳回信息会继续关联该钢瓶。'" type="info" :closable="false" />
      <el-form class="line-edit-form" label-position="top">
        <el-form-item label="产品编号"><el-input v-model="lineForm.body_code" maxlength="100" /></el-form-item>
        <el-form-item label="生产日期"><div class="date-field-with-shortcuts"><div v-if="datePresets.length" class="date-shortcut-row"><button v-for="item in datePresets" :key="item.id" type="button" @click="lineForm.manufacture_date = item.value">{{ item.name }} · {{ item.value }}</button></div><el-input v-model="lineForm.manufacture_date" clearable autocomplete="off" placeholder="输入生产日期，如 2022.09" /></div></el-form-item>
        <el-form-item label="生产厂家"><el-input v-model="lineForm.manufacturer" maxlength="160" /></el-form-item>
        <el-form-item v-if="selected?.is_archived" label="容积（L）"><el-input-number v-model="lineForm.volume" :min="0" :precision="2" :controls="false" /></el-form-item>
        <el-form-item v-if="selected?.is_archived" label="下次检验日期"><el-date-picker v-model="lineForm.next_inspection_date" type="date" value-format="YYYY-MM-DD" clearable placeholder="选择下次检验日期" /></el-form-item>
        <el-form-item v-if="selected?.is_archived" label="钢瓶规格（单瓶 Word 报告使用）"><el-select v-model="lineForm.spec_id" filterable clearable placeholder="选择钢瓶规格"><el-option v-for="spec in specs" :key="spec.id" :label="spec.name" :value="spec.id" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="editLineDialog = false">取消</el-button><el-button type="primary" :loading="savingLine" @click="saveLine">保存明细</el-button></template>
    </el-dialog>

    <el-dialog v-model="importDialog" title="导入历史检验单" width="620px" destroy-on-close>
      <el-alert title="支持全量检验单格式的 .xlsx 和 .xls 文件；Excel 日期可填写到月份（如 2026.09）。检验月份须与所选日期一致，只有年月的下次检验日期按当月 1 日归档。同日期已有检验单时，请打开该单使用“回导修改后的检验单”。原文件导入后即清理，不写入良品库存。" type="info" :closable="false" />
      <div class="import-fields"><label>检验日期<el-date-picker v-model="importDate" type="date" value-format="YYYY-MM-DD" placeholder="选择尚未生成检验单的日期" /></label><div class="import-file-field"><span>Excel 文件</span><label class="upload-dropzone"><input class="file-picker-input" type="file" accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel" :disabled="importing" @change="chooseImportFile" /><el-icon class="upload-icon"><UploadFilled /></el-icon><strong>{{ importFile ? importFile.name : '点击选择全量检验单 Excel' }}</strong><small>{{ importFile ? '已选择文件，重新点击可更换' : '支持 .xlsx / .xls，大小不超过 10 MB' }}</small></label></div></div>
      <template #footer><el-button @click="importDialog = false">取消</el-button><el-button type="primary" :loading="importing" @click="importHistoricalDocument">确认导入</el-button></template>
    </el-dialog>

    <el-dialog v-model="reimportDialog" title="回导修改后的全量检验单" width="620px" destroy-on-close>
      <el-alert :title="`仅更新 ${selected?.document_no || '当前检验单'}。请使用本单的“导出全量检验单数据”文件，保留所有明细和原序号；可调整 Excel 行顺序，但不要增删或重复序号。普通检验单的编号、生产日期、厂家会同步库存，驳回标注仍跟随原钢瓶。`" type="warning" :closable="false" />
      <div class="import-fields"><div class="import-file-field"><span>修改后的 Excel 文件</span><label class="upload-dropzone"><input class="file-picker-input" type="file" accept=".xls,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" :disabled="reimporting" @change="chooseReimportFile" /><el-icon class="upload-icon"><UploadFilled /></el-icon><strong>{{ reimportFile ? reimportFile.name : '点击选择修改后的全量检验单' }}</strong><small>{{ reimportFile ? '已选择文件，重新点击可更换' : '支持 .xls / .xlsx，大小不超过 10 MB' }}</small></label></div></div>
      <template #footer><el-button :disabled="reimporting" @click="reimportDialog = false">取消</el-button><el-button type="primary" :loading="reimporting" @click="reimportDocument">校验并更新</el-button></template>
    </el-dialog>

    <el-dialog v-model="xlsExportDialog" :title="xlsExportMode === 'full' ? '导出全量检验单数据' : xlsExportMode === 'verified' ? '导出剔除未经验证数据' : '仅导出标黄未通过数据'" width="520px" destroy-on-close>
      <el-alert :title="`优先使用上次导出此类 Excel 的检测日期；改选后会覆盖对应明细的检验时间。下次检验日期按所选日期加四年减一天计算；${xlsExportMode === 'unverified' ? '仅更新标黄明细，并保留原检验单序号。' : '更新本单所有明细。'}瓶子入库时间与原检验单日期不变。`" type="info" :closable="false" />
      <div class="import-fields"><label>检验日期<el-date-picker v-model="xlsExportDate" type="date" value-format="YYYY-MM-DD" :clearable="false" placeholder="选择检验日期" /></label></div>
      <template #footer><el-button :disabled="exporting" @click="xlsExportDialog = false">取消</el-button><el-button type="primary" :loading="exporting" @click="exportXls">导出 XLS</el-button></template>
    </el-dialog>

    <el-dialog v-model="wordDialog" title="导出定检与评定 Word 报告" width="680px" destroy-on-close>
      <el-alert title="优先使用上次导出这两份报告的检测日期；同一日期的报告序号连续递增，新日期从 001 开始。改选日期后会覆盖对应明细的检验时间。浏览器可能提示允许多个文件下载。" type="info" :closable="false" />
      <div class="import-fields"><label>检测日期<el-date-picker v-model="wordReportDate" type="date" value-format="YYYY-MM-DD" :clearable="false" placeholder="选择检测日期" /></label></div>
      <div class="word-template-library" v-loading="wordTemplatesLoading">
        <strong>客户模板 · {{ selected?.customer_name }}</strong>
        <p class="muted">选择会在本次导出时保存为该客户的默认 Word 模板；两份报告使用同一套版式。</p>
        <el-radio-group v-model="wordTemplateKey" class="word-template-options">
          <el-radio v-for="item in wordTemplates" :key="item.key" :value="item.key" border class="word-template-option">
            <span class="template-name">{{ item.name }}</span>
            <small>{{ item.description }}</small>
            <span v-if="item.key === 'photo'" class="template-miniature">
              <span>检 验 报 告</span><i>委托单位 · 项目名称 · 报告日期</i>
              <span>气瓶定期检验报告</span><i>报告结论 · 签批栏</i>
            </span>
          </el-radio>
        </el-radio-group>
      </div>
      <template #footer><el-button :disabled="exportingWord" @click="wordDialog = false">取消</el-button><el-button type="primary" :loading="exportingWord" :disabled="wordTemplatesLoading || !wordTemplates.length" @click="exportWordReports">导出两份 Word</el-button></template>
    </el-dialog>

    <el-dialog v-model="wordCodesDialog" :title="`${wordCodesDocument?.document_no || ''} · Word 报告编码`" width="680px" destroy-on-close>
      <div v-loading="wordCodesLoading">
        <el-empty v-if="!wordCodesLoading && !wordCodes.length" description="尚未导出 Word 报告，没有已分配编码" />
        <el-table v-else :data="wordCodes" stripe>
          <el-table-column prop="report_date" label="报告日期" width="125" />
          <el-table-column prop="regular_code" label="定检编码" min-width="165" />
          <el-table-column prop="assessment_code" label="评定编码" min-width="165" />
          <el-table-column v-if="auth.user?.is_superadmin && wordCodesDocument?.status === 'ACTIVE'" label="操作" width="70"><template #default="{ row }"><el-button link type="primary" @click="editWordCode(row)">修改</el-button></template></el-table-column>
        </el-table>
        <div v-if="editingWordCodeId !== null" class="word-code-editor">
          <el-alert title="修改日期会改变下次 Word 导出的默认检测日期；两份报告共用日期、占用连续两个序号。已下载的旧文件不会自动更改。" type="info" :closable="false" />
          <div class="word-code-fields"><label>报告日期<el-date-picker v-model="wordCodeForm.report_date" type="date" value-format="YYYY-MM-DD" :clearable="false" /></label><label>定检起始序号<el-input-number v-model="wordCodeForm.first_number" :min="1" :max="998" :precision="0" :controls="false" /></label></div>
          <p class="muted">修改后：{{ wordCodePreview || '请选择有效日期和序号' }}</p>
          <el-button :disabled="wordCodesSaving" @click="editingWordCodeId = null">取消</el-button><el-button type="primary" :loading="wordCodesSaving" @click="saveWordCode">保存编码</el-button>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="singleReportDialog" :title="singleReportTarget ? '导出单瓶检测报告' : '导出未被驳回的单瓶检测报告'" width="520px" destroy-on-close>
      <el-alert title="优先使用上次导出对应报告的检测日期；改选后会覆盖对应钢瓶的检验时间。报告正文和下次检验日期按所选日期计算，下次检验日期为所选日期加四年减一天。" type="info" :closable="false" />
      <div class="import-fields"><label>检测日期<el-date-picker v-model="singleReportDate" type="date" value-format="YYYY-MM-DD" :clearable="false" placeholder="选择检测日期" /></label></div>
      <template #footer><el-button :disabled="exportingSingleReports || exportingLineId !== null" @click="singleReportDialog = false">取消</el-button><el-button type="primary" :loading="exportingSingleReports || exportingLineId !== null" @click="confirmSingleReportExport">导出 Word</el-button></template>
    </el-dialog>

    <el-dialog v-model="markDialog" title="录入上游系统驳回信息" width="760px" destroy-on-close>
      <el-alert title="直接粘贴完整错误文本，系统会提取所有“气瓶列表第 N 行”，并按当前检验单序号标注对应钢瓶。" type="info" :closable="false" />
      <el-input v-model="rejectionText" class="rejection-input" type="textarea" :rows="14" maxlength="50000" show-word-limit placeholder="例如：气瓶列表第2行【气瓶信息不存在，请检查】" />
      <template #footer><el-button @click="markDialog = false">取消</el-button><el-button type="primary" :loading="marking" @click="submitUnverifiedMarks">识别并标注</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.split-fields{display:grid;grid-template-columns:1fr 1fr 1.5fr;gap:14px;margin:20px 0}.split-fields label{display:grid;gap:8px}.split-fields :deep(.el-input-number){width:100%}.split-target{display:grid;gap:8px;margin-bottom:16px}.split-preview{margin-top:18px}.split-history{padding:16px 18px;border-top:1px solid var(--el-border-color-light)}@media(max-width:600px){.split-fields{grid-template-columns:1fr}.split-fields :deep(.el-select){width:100%}}

.generation-toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.generation-calendar{min-height:140px;max-height:360px;overflow-y:auto;margin:18px 0}.generation-days{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.generation-days :deep(.el-checkbox){margin:0;height:64px;padding:10px;min-width:0}.generation-days :deep(.el-checkbox__label){display:grid;gap:5px;min-width:0}.generation-days small{font-size:11px;white-space:normal}.generation-document-date{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:14px 16px;border:1px solid var(--el-border-color);border-radius:10px;background:var(--el-fill-color-light)}.generation-document-date p{margin:6px 0 0}.generation-document-date :deep(.el-date-editor){flex:0 0 190px}@media(max-width:600px){.generation-days{grid-template-columns:repeat(3,minmax(0,1fr))}.generation-document-date{align-items:stretch;flex-direction:column}.generation-document-date :deep(.el-date-editor){width:100%;flex-basis:auto}}@media(max-width:430px){.generation-days{grid-template-columns:repeat(2,minmax(0,1fr))}}

.filters{display:flex;gap:10px;align-items:center}.document-detail{margin-top:16px}.detail-loading-placeholder{min-height:220px;display:flex;align-items:center;justify-content:center;color:var(--ja-muted)}.detail-header{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.detail-header h2{margin:0 0 3px}.unified-form{display:grid;grid-template-columns:320px 240px auto;gap:12px;align-items:end;justify-content:start;padding:18px}.unified-form :deep(.el-form-item){display:block;margin:0}.unified-form :deep(.el-form-item__label){height:24px;padding:0 0 6px;line-height:18px}.unified-form :deep(.el-form-item__content){display:block;line-height:normal}.unified-form :deep(.el-select){width:100%}.unified-form :deep(.el-select__wrapper){height:34px;min-height:34px}.unified-form>.el-button{height:34px;min-height:34px}.detail-search{display:flex;align-items:center;gap:14px;padding:0 18px 14px}.detail-search .el-input{width:300px;max-width:100%}.line-edit-form{display:grid;grid-template-columns:1fr 1fr;gap:0 14px;margin-top:16px}.line-edit-form :deep(.el-input),.line-edit-form :deep(.el-input-number),.line-edit-form :deep(.el-select),.line-edit-form :deep(.el-date-editor){width:100%}.date-field-with-shortcuts{width:100%}.date-shortcut-row{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:8px}.date-shortcut-row button{padding:6px 10px;color:var(--ja-red);background:var(--ja-red-soft);border:1px solid #f4b8bd;border-radius:8px}.import-fields{display:grid;gap:18px;margin:22px 0 8px}.import-fields>label,.import-file-field{display:grid;gap:8px;color:var(--el-text-color-regular)}.upload-dropzone{position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;min-height:146px;border:1px dashed var(--el-border-color-darker);border-radius:10px;background:var(--el-fill-color-lighter);color:var(--el-text-color-primary);text-align:center;cursor:pointer;transition:border-color .2s,background .2s}.upload-dropzone:hover,.upload-dropzone:focus-within{border-color:var(--el-color-primary);background:var(--el-color-primary-light-9)}.upload-dropzone .upload-icon{font-size:30px;color:var(--el-color-primary)}.upload-dropzone strong{max-width:90%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.upload-dropzone small{color:var(--el-text-color-secondary)}.file-picker-input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}.file-picker-input:disabled{cursor:not-allowed}.rejection-input{margin-top:14px}.rejection-input :deep(.el-textarea__inner){font-family:ui-monospace,SFMono-Regular,Menlo,monospace;line-height:1.65}:deep(.el-table .unverified-row>td.el-table__cell){background:#fff0d6!important}:deep(.el-table .unverified-row:hover>td.el-table__cell){background:#ffe2b3!important}@media(max-width:760px){.filters{flex-wrap:wrap}.unified-form,.line-edit-form{grid-template-columns:1fr}.detail-header .grow{display:none}}
.word-code-editor{margin-top:18px;padding-top:18px;border-top:1px solid var(--el-border-color-light)}.word-code-fields{display:flex;gap:16px;flex-wrap:wrap;margin-top:16px}.word-code-fields label{display:grid;gap:8px}.word-code-fields :deep(.el-input-number){width:170px}
.word-template-library{margin-top:20px}.word-template-library>p{margin:6px 0 14px}.word-template-options{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;width:100%}.word-template-option{display:flex!important;align-items:flex-start!important;height:auto!important;min-height:112px;margin:0!important;padding:14px!important;white-space:normal!important}.word-template-option :deep(.el-radio__label){display:grid;gap:5px;min-width:0;white-space:normal}.word-template-option small{color:var(--el-text-color-secondary);line-height:1.4}.template-name{font-weight:700}.template-miniature{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:7px;color:#545454;font-family:serif;font-size:11px}.template-miniature span{display:grid;align-items:center;min-height:54px;padding:6px;border:1px solid #d9d9d9;background:#fff;text-align:center}.template-miniature i{display:grid;align-items:end;min-height:54px;padding:6px;border:1px solid #d9d9d9;background:#fff;font-style:normal}@media(max-width:600px){.word-template-options{grid-template-columns:1fr}}
</style>
