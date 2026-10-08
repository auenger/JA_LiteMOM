<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { auth, has } from '../auth'
import type { Material, MaterialDocument, PurchaseOrder, Supplier } from '../types'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import ReportActions from '../components/ReportActions.vue'
import StatusTag from '../components/StatusTag.vue'
import GameIcon from '../components/GameIcon.vue'
import TablePagination from '../components/TablePagination.vue'

const loading = ref(false)
const props = withDefaults(defineProps<{ documentType?: 'NORMAL_IN' | 'OUTBOUND' | 'RETURN_IN' }>(), { documentType: 'NORMAL_IN' })
const rows = ref<MaterialDocument[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const materials = ref<Material[]>([])
const suppliers = ref<Supplier[]>([])
const purchaseOrders = ref<PurchaseOrder[]>([])
const dialog = ref(false)
const detailDialog = ref(false)
const selected = ref<MaterialDocument | null>(null)
const editingId = ref<number | null>(null)
const formRef = ref()
const dateRange = ref<string[]>([])
const modeFilter = ref<'DIRECT' | 'PURCHASE_ORDER' | undefined>()
const categoryFilter = ref<'MATERIAL' | 'SCRAP' | undefined>()
const materialFilter = ref<number | undefined>()
const outboundCategoryFilter = ref<'MATERIAL' | 'SCRAP' | undefined>()
const today = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}
const blankLine = () => ({ material_id: undefined as number | undefined, quantity: 1, unit_price: 0 })
const blank = () => ({ document_type: props.documentType, business_date: today(), supplier_id: undefined as number | undefined, purchase_order_id: undefined as number | undefined, related_outbound_id: undefined as number | undefined, inbound_mode: 'DIRECT' as 'DIRECT' | 'PURCHASE_ORDER', inbound_category: 'MATERIAL' as 'MATERIAL' | 'SCRAP', outbound_category: 'MATERIAL' as 'MATERIAL' | 'SCRAP', is_paid: false, handler: auth.user?.name || '', note: '', lines: [blankLine()] })
const form = reactive<any>(blank())
const labels: Record<string, string> = { NORMAL_IN: '原材料入库单', OUTBOUND: '出库单', RETURN_IN: '退料入库单' }
const pageConfig = computed(() => ({
  NORMAL_IN: { title: '原材料入库管理', description: '直接入库可手工填写；采购单入库从已确认采购单自动带入供应商、原材料、数量和价格。', action: '新建入库单' },
  OUTBOUND: { title: '材料出库管理', description: '登记生产领料，确认前校验实际物料库存。', action: '新建出库单' },
  RETURN_IN: { title: '退料入库管理', description: '绑定已生效出库单登记剩余退料，累计退料不能超过原出库数量。', action: '新建退料入库单' },
}[props.documentType]))
const permissionPrefix = computed(() => ({ NORMAL_IN: 'material_inbound', OUTBOUND: 'material_outbound', RETURN_IN: 'material_return' }[props.documentType]))
const can = (action: string) => has(`${permissionPrefix.value}:${action}`)
const filtered = computed(() => rows.value.filter((row) => row.document_type === props.documentType))
const postedOutbounds = computed(() => rows.value.filter((row) => row.document_type === 'OUTBOUND' && row.outbound_category === 'MATERIAL' && row.status === 'POSTED'))
const selectableMaterials = computed(() => {
  if (form.document_type !== 'NORMAL_IN' || form.inbound_mode !== 'DIRECT') return materials.value.filter((item) => item.is_active)
  return materials.value.filter((item) => item.is_active && item.material_type === form.inbound_category)
})
const materialReportLines = computed(() => selected.value ? [
  `单据编号：${selected.value.document_no}`,
  `单据类型：${labels[selected.value.document_type]}`,
  `业务日期：${selected.value.business_date}`,
  selected.value.supplier_id ? `供应商：${suppliers.value.find((item) => item.id === selected.value?.supplier_id)?.name || '-'}` : '',
  selected.value.document_type === 'NORMAL_IN' ? `入库方式：${selected.value.inbound_mode === 'PURCHASE_ORDER' ? '采购单入库' : '直接入库'}` : '',
  selected.value.document_type === 'NORMAL_IN' ? `物料类型：${selected.value.inbound_category === 'SCRAP' ? '废料入库' : '原料入库'}` : '',
  selected.value.document_type === 'OUTBOUND' ? `出库类型：${selected.value.outbound_category === 'SCRAP' ? '废料出库（收入）' : '原材料出库（成本）'}` : '',
  `经办人：${selected.value.handler}`,
  ...selected.value.lines.map((line) => `${line.material_name} / ${line.specification || '无规格'}：${formatNumber(line.quantity)} ${line.unit} × ¥${Number(line.unit_price).toFixed(2)} = ¥${Number(line.amount).toFixed(2)}`),
  `合计金额：¥${docTotal(selected.value).toFixed(2)}`,
  `单据状态：${selected.value.status}`,
  `备注：${selected.value.note || '-'}`,
].filter(Boolean) : [])

async function load() {
  loading.value = true
  try {
    const [docs, options, outbounds, orders] = await Promise.all([
      api.get('/material-documents', { params: {
        document_type: props.documentType, page: page.value, page_size: pageSize.value,
        date_from: dateRange.value?.[0] || undefined,
        date_to: dateRange.value?.[1] || undefined,
        material_id: props.documentType === 'NORMAL_IN' ? materialFilter.value : undefined,
        inbound_mode: props.documentType === 'NORMAL_IN' ? modeFilter.value : undefined,
        inbound_category: props.documentType === 'NORMAL_IN' ? categoryFilter.value : undefined,
        outbound_category: props.documentType === 'OUTBOUND' ? outboundCategoryFilter.value : undefined,
      } }),
      api.get('/options'),
      props.documentType === 'RETURN_IN' ? api.get('/material-documents/return-options', { params: { page_size: 100 } }) : Promise.resolve({ data: { items: [] } }),
      props.documentType === 'NORMAL_IN' ? api.get('/purchase-orders', { params: { order_status: 'CONFIRMED', page_size: 100 } }) : Promise.resolve({ data: { items: [] } }),
    ])
    rows.value = [...docs.data.items, ...outbounds.data.items]; total.value = docs.data.total; materials.value = options.data.materials; suppliers.value = options.data.suppliers; purchaseOrders.value = orders.data.items
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function resetForm() {
  Object.assign(form, blank(), { document_type: props.documentType })
  form.lines = props.documentType === 'RETURN_IN' ? [] : [blankLine()]
}
function openCreate() { editingId.value = null; resetForm(); dialog.value = true }
function openEdit(row: MaterialDocument) {
  editingId.value = row.id
  Object.assign(form, { document_type: row.document_type, business_date: row.business_date, supplier_id: row.supplier_id, purchase_order_id: row.purchase_order_id, related_outbound_id: row.related_outbound_id, inbound_mode: row.inbound_mode || (row.purchase_order_id ? 'PURCHASE_ORDER' : 'DIRECT'), inbound_category: row.inbound_category === 'SCRAP' ? 'SCRAP' : 'MATERIAL', outbound_category: row.outbound_category, is_paid: false, handler: row.handler, note: row.note || '' })
  form.lines = row.lines.map((line) => ({ material_id: line.material_id, quantity: Number(line.quantity), unit_price: Number(line.unit_price) }))
  dialog.value = true
}
function addLine() { form.lines.push(blankLine()) }
function removeLine(index: number) { if (form.lines.length > 1) form.lines.splice(index, 1) }
function materialChanged(line: any) { const item = materials.value.find((row) => row.id === line.material_id); if (item) line.unit_price = Number(item.price) }
function returnLimit(materialId: number) {
  const outbound = postedOutbounds.value.find((row) => row.id === form.related_outbound_id)
  const original = Number(outbound?.lines.find((line) => line.material_id === materialId)?.quantity || 0)
  const returned = rows.value
    .filter((row) => row.document_type === 'RETURN_IN' && row.status === 'POSTED' && row.related_outbound_id === form.related_outbound_id && row.id !== editingId.value)
    .flatMap((row) => row.lines)
    .filter((line) => line.material_id === materialId)
    .reduce((sum, line) => sum + Number(line.quantity), 0)
  return Math.max(Number((original - returned).toFixed(2)), 0)
}
function outboundChanged() {
  const outbound = postedOutbounds.value.find((row) => row.id === form.related_outbound_id)
  if (outbound) form.lines = outbound.lines.map((line) => ({ material_id: line.material_id, quantity: returnLimit(line.material_id), unit_price: Number(line.unit_price) })).filter((line) => line.quantity > 0)
}
function inboundModeChanged(value: 'DIRECT' | 'PURCHASE_ORDER') { form.purchase_order_id = undefined; form.supplier_id = undefined; form.inbound_category = 'MATERIAL'; form.lines = value === 'PURCHASE_ORDER' ? [] : [blankLine()] }
function inboundCategoryChanged(value: 'MATERIAL' | 'SCRAP') {
  const available = materials.value.filter((item) => item.is_active && item.material_type === value)
  form.lines = value === 'SCRAP' && available.length === 1
    ? [{ material_id: available[0].id, quantity: 1, unit_price: Number(available[0].price) }]
    : [blankLine()]
}
function purchaseOrderChanged() { const order = purchaseOrders.value.find((item) => item.id === form.purchase_order_id); if (order) { form.supplier_id = order.supplier_id; form.lines = order.lines.map((line) => ({ material_id: line.material_id, quantity: Number(line.quantity), unit_price: Number(line.unit_price) })) } }
async function submit() {
  await formRef.value?.validate()
  if (!form.lines.length || form.lines.some((line: any) => !line.material_id || !line.quantity)) return ElMessage.warning('请完整填写原材料明细')
  if (form.document_type === 'RETURN_IN' && form.lines.some((line: any) => Number(line.quantity) > returnLimit(line.material_id))) return ElMessage.warning('退料数量不能超过原出库单的剩余可退数量')
  try {
    if (editingId.value) await api.put(`/material-documents/${editingId.value}`, form)
    else await api.post('/material-documents', form)
    ElMessage.success('单据草稿已保存')
    dialog.value = false
    await load()
  } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function action(row: MaterialDocument, type: 'post' | 'void' | 'delete') {
  const prompts = { post: '确认单据后将立即改变库存，是否继续？', void: '作废或撤销将反向恢复库存，是否继续？', delete: '确认删除该草稿单据？' }
  try {
    await ElMessageBox.confirm(prompts[type], type === 'post' ? '确认入账' : type === 'void' ? '作废或撤销' : '删除草稿', { type: 'warning' })
    if (type === 'delete') await api.delete(`/material-documents/${row.id}`)
    else await api.post(`/material-documents/${row.id}/${type}`)
    ElMessage.success(type === 'post' ? '单据已生效' : type === 'void' ? '单据已作废' : '草稿已删除')
    await load()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
function search() { page.value = 1; load() }
function resetFilters() { dateRange.value = []; modeFilter.value = undefined; categoryFilter.value = undefined; materialFilter.value = undefined; search() }
function resetOutboundFilters() { dateRange.value = []; outboundCategoryFilter.value = undefined; search() }
function resetReturnFilters() { dateRange.value = []; search() }
function showDetail(row: MaterialDocument) { selected.value = row; detailDialog.value = true }
function docTotal(row: MaterialDocument) { return row.lines.reduce((sum, line) => sum + Number(line.amount), 0) }
function formatNumber(value: string | number) { return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function formatAuditTime(value?: string) {
  if (!value) return ''
  const source = value.endsWith('Z') ? value : `${value}Z`
  return new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(source))
}
function materialName(id: number) { return materials.value.find((row) => row.id === id)?.name || `原材料 #${id}` }
watch(() => props.documentType, () => {
  page.value = 1
  dateRange.value = []
  modeFilter.value = undefined
  categoryFilter.value = undefined
  materialFilter.value = undefined
  outboundCategoryFilter.value = undefined
  load()
}, { immediate: true })
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
</script>

<template>
  <div>
    <PageHeader :title="pageConfig.title" :description="pageConfig.description">
      <el-button v-if="can('create')" type="primary" @click="openCreate"><GameIcon name="plus" />{{ pageConfig.action }}</el-button>
    </PageHeader>
    <section class="surface">
      <div v-if="props.documentType === 'NORMAL_IN'" class="document-filters">
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" clearable unlink-panels range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
        <el-select v-model="modeFilter" clearable placeholder="全部入库方式"><el-option label="直接入库" value="DIRECT" /><el-option label="采购单入库" value="PURCHASE_ORDER" /></el-select>
        <el-select v-model="categoryFilter" clearable placeholder="全部物料类型"><el-option label="原料入库" value="MATERIAL" /><el-option label="废料入库" value="SCRAP" /></el-select>
        <el-select v-model="materialFilter" class="material-filter" filterable clearable placeholder="选择原材料档案"><el-option v-for="item in materials" :key="item.id" :label="`${item.name} / ${item.specification || '无规格'}`" :value="item.id" /></el-select>
        <el-button type="primary" @click="search"><GameIcon name="search" />查询</el-button><el-button @click="resetFilters">重置</el-button>
      </div>
      <div v-if="props.documentType === 'OUTBOUND'" class="outbound-filters">
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" clearable unlink-panels range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
        <el-select v-model="outboundCategoryFilter" clearable placeholder="全部出库类型"><el-option label="原材料出库" value="MATERIAL" /><el-option label="废料出库" value="SCRAP" /></el-select>
        <el-button type="primary" @click="search"><GameIcon name="search" />查询</el-button><el-button @click="resetOutboundFilters">重置</el-button>
      </div>
      <div v-if="props.documentType === 'RETURN_IN'" class="return-filters">
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" clearable unlink-panels range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
        <el-button type="primary" @click="search"><GameIcon name="search" />查询</el-button><el-button @click="resetReturnFilters">重置</el-button>
      </div>
      <div class="surface-header toolbar">
        <h2>{{ labels[props.documentType] }}记录</h2><span class="grow" /><span class="muted">共 {{ total }} 张</span><el-button @click="load"><GameIcon name="refresh" />刷新</el-button>
      </div>
      <el-table v-if="filtered.length" v-loading="loading" :data="filtered" stripe>
        <el-table-column prop="document_no" label="单据编号" min-width="190"><template #default="{ row }"><button class="table-link" @click="showDetail(row)">{{ row.document_no }}</button></template></el-table-column>
        <el-table-column prop="business_date" label="业务日期" width="115" />
        <el-table-column prop="handler" label="经办人" width="110" />
        <el-table-column label="操作记录" min-width="250"><template #default="{ row }">
          <div class="audit-stack">
            <span><b>创建</b>{{ row.created_by_name }}<time>{{ formatAuditTime(row.created_at) }}</time></span>
            <span v-if="row.updated_by_name"><b>编辑</b>{{ row.updated_by_name }}<time>{{ formatAuditTime(row.updated_at) }}</time></span>
            <span v-if="row.posted_by_name"><b>审批</b>{{ row.posted_by_name }}<time>{{ formatAuditTime(row.posted_at) }}</time></span>
            <span v-if="row.voided_by_name"><b>撤销</b>{{ row.voided_by_name }}<time>{{ formatAuditTime(row.voided_at) }}</time></span>
          </div>
        </template></el-table-column>
        <el-table-column label="明细" min-width="160"><template #default="{ row }">{{ row.lines.map((line: any) => `${line.material_name} ${formatNumber(line.quantity)} ${line.unit}`).join('；') }}</template></el-table-column>
        <el-table-column label="金额" width="120" align="right"><template #default="{ row }"><span class="numeric">¥{{ docTotal(row).toFixed(2) }}</span></template></el-table-column>
        <el-table-column v-if="props.documentType === 'NORMAL_IN'" label="入库方式" width="110"><template #default="{ row }">{{ row.inbound_mode === 'PURCHASE_ORDER' ? '采购单入库' : '直接入库' }}</template></el-table-column>
        <el-table-column v-if="props.documentType === 'NORMAL_IN'" label="物料类型" width="100"><template #default="{ row }"><el-tag :type="row.inbound_category === 'SCRAP' ? 'warning' : 'info'">{{ row.inbound_category === 'SCRAP' ? '废料' : '原料' }}</el-tag></template></el-table-column>
        <el-table-column v-if="props.documentType === 'NORMAL_IN'" label="来源采购单" min-width="160"><template #default="{ row }">{{ row.purchase_order_id ? purchaseOrders.find((item) => item.id === row.purchase_order_id)?.order_no || `采购单 #${row.purchase_order_id}` : '-' }}</template></el-table-column>
        <el-table-column v-if="props.documentType === 'OUTBOUND'" label="出库类型" width="120"><template #default="{ row }"><el-tag :type="row.outbound_category === 'SCRAP' ? 'warning' : 'info'" effect="light">{{ row.outbound_category === 'SCRAP' ? '废料出库' : '原材料出库' }}</el-tag></template></el-table-column>
        <el-table-column label="状态" width="90"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
        <el-table-column label="操作" width="230" fixed="right"><template #default="{ row }">
          <el-button link type="primary" @click="showDetail(row)">查看</el-button>
          <el-button v-if="row.status === 'DRAFT' && can('update')" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'DRAFT' && can('post')" link type="success" @click="action(row, 'post')">确认</el-button>
          <el-button v-if="row.status === 'DRAFT' && can('delete')" link type="danger" @click="action(row, 'delete')">删除</el-button>
          <el-button v-if="row.status === 'POSTED' && can('void')" link type="danger" @click="action(row, 'void')">作废</el-button>
        </template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : `还没有${labels[props.documentType]}`" description="创建草稿并确认后，库存才会发生变化。"><el-button v-if="can('create')" type="primary" @click="openCreate()"><GameIcon name="plus" />{{ pageConfig.action }}</el-button></EmptyState>
      <TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>

    <el-dialog v-model="dialog" :title="`${editingId ? '编辑' : '新建'}${labels[form.document_type]}`" width="820px" destroy-on-close>
      <el-form ref="formRef" :model="form" label-position="top" :rules="{ business_date: [{ required: true, message: '请选择日期' }], handler: [{ required: true, message: '请输入经办人' }], related_outbound_id: [{ required: form.document_type === 'RETURN_IN', message: '请选择原出库单' }] }">
        <div class="form-grid">
          <el-form-item label="业务日期" prop="business_date"><el-date-picker v-model="form.business_date" type="date" value-format="YYYY-MM-DD" class="w-full" /></el-form-item>
          <el-form-item v-if="form.document_type === 'NORMAL_IN'" class="span-2" label="入库方式"><el-radio-group v-model="form.inbound_mode" @change="inboundModeChanged"><el-radio-button value="DIRECT">直接入库</el-radio-button><el-radio-button value="PURCHASE_ORDER">采购单入库</el-radio-button></el-radio-group></el-form-item>
          <el-form-item v-if="form.document_type === 'NORMAL_IN' && form.inbound_mode === 'DIRECT'" class="span-2" label="物料类型"><el-radio-group v-model="form.inbound_category" @change="inboundCategoryChanged"><el-radio-button value="MATERIAL">原料入库</el-radio-button><el-radio-button value="SCRAP">废料入库</el-radio-button></el-radio-group></el-form-item>
          <el-form-item v-if="form.document_type === 'OUTBOUND'" label="出库类型"><el-radio-group v-model="form.outbound_category"><el-radio-button value="MATERIAL">原材料出库</el-radio-button><el-radio-button value="SCRAP">废料出库</el-radio-button></el-radio-group></el-form-item>
          <el-form-item v-if="form.document_type === 'NORMAL_IN' && form.inbound_mode === 'PURCHASE_ORDER'" class="span-2" label="来源采购单"><el-select v-model="form.purchase_order_id" filterable placeholder="请选择已确认且未入库的采购单" class="w-full" @change="purchaseOrderChanged"><el-option v-for="item in purchaseOrders.filter((order) => !order.inbound_document_id || order.id === form.purchase_order_id)" :key="item.id" :label="`${item.order_no} / ${item.supplier_name} / ¥${Number(item.total_amount).toFixed(2)}`" :value="item.id" /></el-select></el-form-item>
          <el-form-item v-if="form.document_type === 'RETURN_IN'" label="绑定原出库单" prop="related_outbound_id"><el-select v-model="form.related_outbound_id" filterable placeholder="请选择已生效出库单" @change="outboundChanged"><el-option v-for="item in postedOutbounds" :key="item.id" :label="`${item.document_no} / ${item.business_date}`" :value="item.id" /></el-select></el-form-item>
          <el-form-item label="经办人" prop="handler"><el-input v-model="form.handler" /></el-form-item>
          <el-form-item class="span-2" label="备注"><el-input v-model="form.note" type="textarea" :rows="2" placeholder="选填" /></el-form-item>
        </div>
        <div class="detail-heading"><strong>原材料明细</strong><el-button v-if="form.document_type !== 'RETURN_IN' && form.inbound_mode !== 'PURCHASE_ORDER'" link type="primary" @click="addLine"><GameIcon name="plus" />添加一行</el-button></div>
        <el-alert v-if="form.document_type === 'NORMAL_IN' && form.inbound_mode === 'PURCHASE_ORDER' && !form.purchase_order_id" title="请选择采购单，系统会自动带出对应供应商、原材料、数量和采购价格。" type="info" :closable="false" class="mb-16" />
        <el-alert v-if="form.document_type === 'RETURN_IN' && !form.related_outbound_id" title="请先选择原出库单，系统会自动带出可退原材料和剩余数量。" type="info" :closable="false" class="mb-16" />
        <el-alert v-else-if="form.document_type === 'RETURN_IN' && !form.lines.length" title="所选出库单已没有可退数量。" type="warning" :closable="false" class="mb-16" />
        <div v-for="(line, index) in form.lines" :key="index" class="line-editor">
          <div class="line-editor-grid">
            <div><label>原材料</label><el-select v-model="line.material_id" filterable :placeholder="form.inbound_category === 'SCRAP' ? '选择废料' : '选择原料'" :disabled="form.document_type === 'RETURN_IN' || form.inbound_mode === 'PURCHASE_ORDER'" @change="materialChanged(line)"><el-option v-for="item in selectableMaterials" :key="item.id" :label="`${item.name} / ${item.specification || '无规格'}`" :value="item.id" /></el-select></div>
            <div><label>{{ form.document_type === 'RETURN_IN' ? `退料数量（最多 ${formatNumber(returnLimit(line.material_id))}）` : '数量' }}</label><el-input-number v-model="line.quantity" :min="form.document_type === 'RETURN_IN' ? 0 : 0.01" :max="form.document_type === 'RETURN_IN' ? returnLimit(line.material_id) || undefined : undefined" :disabled="form.inbound_mode === 'PURCHASE_ORDER' || (form.document_type === 'RETURN_IN' && (!form.related_outbound_id || returnLimit(line.material_id) <= 0))" :precision="2" :controls="false" class="w-full" /></div>
            <div><label>{{ form.document_type === 'OUTBOUND' ? form.outbound_category === 'SCRAP' ? '销售单价（收入）' : '成本单价' : '单价' }}</label><el-input-number v-model="line.unit_price" :min="0" :precision="2" :controls="false" :disabled="form.inbound_mode === 'PURCHASE_ORDER'" class="w-full" /></div>
            <el-button circle text type="danger" aria-label="删除明细" :disabled="form.lines.length === 1 || form.document_type === 'RETURN_IN' || form.inbound_mode === 'PURCHASE_ORDER'" @click="removeLine(index)"><GameIcon name="trash" /></el-button>
          </div>
        </div>
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="submit">保存草稿</el-button></div></template>
    </el-dialog>

    <el-dialog v-model="detailDialog" title="单据详情" width="720px">
      <div v-if="selected" class="doc-detail">
        <dl><dt>单据编号</dt><dd class="numeric">{{ selected.document_no }}</dd><dt>类型</dt><dd>{{ labels[selected.document_type] }}</dd><dt>业务日期</dt><dd>{{ selected.business_date }}</dd><dt>经办人</dt><dd>{{ selected.handler }}</dd><template v-if="selected.document_type === 'NORMAL_IN'"><dt>入库方式</dt><dd>{{ selected.inbound_mode === 'PURCHASE_ORDER' ? '采购单入库' : '直接入库' }}</dd><dt>物料类型</dt><dd>{{ selected.inbound_category === 'SCRAP' ? '废料入库' : '原料入库' }}</dd><dt>来源采购单</dt><dd>{{ selected.purchase_order_id ? purchaseOrders.find((item) => item.id === selected?.purchase_order_id)?.order_no || `采购单 #${selected.purchase_order_id}` : '-' }}</dd></template><template v-if="selected.document_type === 'OUTBOUND'"><dt>出库类型</dt><dd>{{ selected.outbound_category === 'SCRAP' ? '废料出库（收入）' : '原材料出库' }}</dd></template><dt>状态</dt><dd><StatusTag :status="selected.status" /></dd><dt>关联出库单</dt><dd>{{ selected.related_outbound_id ? rows.find((x) => x.id === selected?.related_outbound_id)?.document_no : '-' }}</dd><dt>创建记录</dt><dd>{{ selected.created_by_name }} · {{ formatAuditTime(selected.created_at) }}</dd><dt>编辑记录</dt><dd>{{ selected.updated_by_name ? `${selected.updated_by_name} · ${formatAuditTime(selected.updated_at)}` : '-' }}</dd><dt>审批记录</dt><dd>{{ selected.posted_by_name ? `${selected.posted_by_name} · ${formatAuditTime(selected.posted_at)}` : '-' }}</dd><dt>撤销记录</dt><dd>{{ selected.voided_by_name ? `${selected.voided_by_name} · ${formatAuditTime(selected.voided_at)}` : '-' }}</dd></dl>
        <el-table :data="selected.lines" border><el-table-column prop="material_name" label="原材料" /><el-table-column prop="specification" label="规格" /><el-table-column label="数量" align="right"><template #default="{ row }">{{ formatNumber(row.quantity) }} {{ row.unit }}</template></el-table-column><el-table-column label="单价" align="right"><template #default="{ row }">¥{{ Number(row.unit_price).toFixed(2) }}</template></el-table-column><el-table-column label="金额" align="right"><template #default="{ row }">¥{{ Number(row.amount).toFixed(2) }}</template></el-table-column></el-table>
        <ReportActions class="detail-actions" :title="labels[selected.document_type]" :filename="`${labels[selected.document_type]}-${selected.document_no}`" :lines="materialReportLines" :show-copy="false" />
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.table-link { padding: 0; color: var(--ja-red); background: none; border: 0; font-family: monospace; }
.document-filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 16px 18px; border-bottom: 1px solid var(--ja-line); }
.document-filters :deep(.el-date-editor) { width: 320px; max-width: 100%; }
.document-filters .el-select { width: 160px; }
.document-filters .material-filter { width: 220px; }
.outbound-filters { display: grid; grid-template-columns: 320px 180px auto auto 1fr; gap: 10px; align-items: center; padding: 16px 18px; border-bottom: 1px solid var(--ja-line); }
.outbound-filters :deep(.el-date-editor) { width: 100%; }
.return-filters { display: grid; grid-template-columns: 320px auto auto 1fr; gap: 10px; align-items: center; padding: 16px 18px; border-bottom: 1px solid var(--ja-line); }
.return-filters :deep(.el-date-editor) { width: 100%; }
.detail-heading { display: flex; justify-content: space-between; align-items: center; margin: 4px 0 10px; }
.doc-detail dl { display: grid; grid-template-columns: 100px 1fr 100px 1fr; gap: 10px 16px; margin: 0 0 20px; }
.doc-detail dt { color: var(--ja-muted); }.doc-detail dd { margin: 0; }
.audit-stack { display: flex; flex-direction: column; gap: 3px; font-size: 11px; }
.audit-stack span { display: grid; grid-template-columns: 34px minmax(60px, 1fr) auto; align-items: center; gap: 6px; }
.audit-stack b { color: var(--ja-muted); font-weight: 500; }
.audit-stack time { color: #92969d; font-variant-numeric: tabular-nums; }
.detail-actions { margin-top: 18px; }
@media (max-width: 760px) { .document-filters { display: grid; grid-template-columns: 1fr; } .document-filters .el-select, .document-filters .material-filter, .document-filters :deep(.el-date-editor) { width: 100%; } .outbound-filters, .return-filters { grid-template-columns: 1fr; } .doc-detail dl { grid-template-columns: 90px 1fr; } }
</style>
