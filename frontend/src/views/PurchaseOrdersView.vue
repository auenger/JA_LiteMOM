<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { auth, has } from '../auth'
import type { PurchaseOrder, Supplier } from '../types'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import TablePagination from '../components/TablePagination.vue'

const rows = ref<PurchaseOrder[]>([])
const suppliers = ref<Supplier[]>([])
const loading = ref(false)
const dialog = ref(false)
const detailDialog = ref(false)
const selected = ref<PurchaseOrder | null>(null)
const editingId = ref<number | null>(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dateRange = ref<string[]>([])
const supplierFilter = ref<number>()
const statusFilter = ref<string>()
const paidFilter = ref<boolean>()
const formRef = ref()
const today = () => { const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}` }
const blankLine = () => ({ material_id: undefined as number | undefined, quantity: 1 })
const blank = () => ({ order_date: today(), supplier_id: undefined as number | undefined, handler: auth.user?.name || '', note: '', lines: [blankLine()] })
const form = reactive<any>(blank())
const currentSupplier = computed(() => suppliers.value.find((item) => item.id === form.supplier_id))
const purchasablePrices = computed(() => (currentSupplier.value?.material_prices || []).filter((item) => item.material_type === 'MATERIAL'))

async function load() {
  loading.value = true
  try {
    const [orders, options] = await Promise.all([
      api.get('/purchase-orders', { params: { page: page.value, page_size: pageSize.value, date_from: dateRange.value[0], date_to: dateRange.value[1], supplier_id: supplierFilter.value, order_status: statusFilter.value, is_paid: paidFilter.value } }),
      api.get('/options'),
    ])
    rows.value = orders.data.items; total.value = orders.data.total; suppliers.value = options.data.suppliers
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function openCreate() { editingId.value = null; Object.assign(form, blank()); form.lines = [blankLine()]; dialog.value = true }
function openEdit(row: PurchaseOrder) { editingId.value = row.id; Object.assign(form, { order_date: row.order_date, supplier_id: row.supplier_id, handler: row.handler, note: row.note || '' }); form.lines = row.lines.map((line) => ({ material_id: line.material_id, quantity: Number(line.quantity) })); dialog.value = true }
function supplierChanged() { form.lines = [blankLine()] }
function addLine() { form.lines.push(blankLine()) }
function removeLine(index: number) { if (form.lines.length > 1) form.lines.splice(index, 1) }
function priceFor(materialId?: number) { return Number(currentSupplier.value?.material_prices.find((item) => item.material_id === materialId)?.purchase_price || 0) }
function materialLabel(materialId?: number) { const item = currentSupplier.value?.material_prices.find((row) => row.material_id === materialId); return item ? `${item.material_name} / ${item.specification || '无规格'}` : '-' }
function formTotal() { return form.lines.reduce((sum: number, line: any) => sum + Number(line.quantity || 0) * priceFor(line.material_id), 0) }
function search() { page.value = 1; load() }
function resetFilters() { dateRange.value = []; supplierFilter.value = undefined; statusFilter.value = undefined; paidFilter.value = undefined; search() }
async function submit() {
  await formRef.value?.validate()
  if (!form.lines.length || form.lines.some((line: any) => !line.material_id || Number(line.quantity) <= 0)) return ElMessage.warning('请完整填写采购明细')
  try {
    if (editingId.value) await api.put(`/purchase-orders/${editingId.value}`, form)
    else await api.post('/purchase-orders', form)
    ElMessage.success('采购单草稿已保存'); dialog.value = false; await load()
  } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function action(row: PurchaseOrder, type: 'confirm' | 'void' | 'delete') {
  const prompt = type === 'confirm' ? '确认后采购内容和价格将锁定，可用于采购单入库。' : type === 'void' ? '确认作废该采购单？' : '确认删除该采购单草稿？'
  try {
    await ElMessageBox.confirm(prompt, type === 'confirm' ? '确认采购单' : type === 'void' ? '作废采购单' : '删除草稿', { type: 'warning' })
    if (type === 'delete') await api.delete(`/purchase-orders/${row.id}`); else await api.post(`/purchase-orders/${row.id}/${type}`)
    ElMessage.success(type === 'confirm' ? '采购单已确认' : type === 'void' ? '采购单已作废' : '采购单已删除'); await load()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
async function changePayment(row: PurchaseOrder) {
  const next = !row.is_paid
  try {
    await ElMessageBox.confirm(`确认标记为“${next ? '已付款' : '未付款'}”？`, '采购单付款状态', { type: 'warning' })
    await api.put(`/purchase-orders/${row.id}/payment`, { is_paid: next }); ElMessage.success('付款状态已更新'); await load()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
function showDetail(row: PurchaseOrder) { selected.value = row; detailDialog.value = true }
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
function money(value: string | number) { return `¥${Number(value || 0).toFixed(2)}` }
onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="供应商采购单" description="按供应商专属原料采购价建立采购单；废料不进入采购单，需通过直接入库登记。"><el-button v-if="has('purchase_orders:create')" type="primary" @click="openCreate"><GameIcon name="plus" />新建采购单</el-button></PageHeader>
    <section class="surface">
      <div class="filters"><el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" clearable range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" /><el-select v-model="supplierFilter" clearable filterable placeholder="全部供应商"><el-option v-for="item in suppliers" :key="item.id" :label="item.name" :value="item.id" /></el-select><el-select v-model="statusFilter" clearable placeholder="全部状态"><el-option label="草稿" value="DRAFT" /><el-option label="已确认" value="CONFIRMED" /><el-option label="已作废" value="VOID" /></el-select><el-select v-model="paidFilter" clearable placeholder="全部付款状态"><el-option label="已付款" :value="true" /><el-option label="未付款" :value="false" /></el-select><el-button type="primary" @click="search"><GameIcon name="search" />查询</el-button><el-button @click="resetFilters">重置</el-button></div>
      <div class="surface-header"><h2>采购单记录</h2><span class="grow" /><span class="muted">共 {{ total }} 张</span><el-button @click="load"><GameIcon name="refresh" />刷新</el-button></div>
      <el-table v-if="rows.length" v-loading="loading" :data="rows" stripe>
        <el-table-column label="采购单号" min-width="180"><template #default="{ row }"><button class="table-link" @click="showDetail(row)">{{ row.order_no }}</button></template></el-table-column>
        <el-table-column prop="order_date" label="采购日期" width="115" /><el-table-column prop="supplier_name" label="供应商" min-width="150" /><el-table-column label="采购明细" min-width="220"><template #default="{ row }">{{ row.lines.map((line: any) => `${line.material_name} ${Number(line.quantity).toFixed(2)} ${line.unit}`).join('；') }}</template></el-table-column><el-table-column label="总金额" width="120" align="right"><template #default="{ row }"><strong>{{ money(row.total_amount) }}</strong></template></el-table-column><el-table-column label="付款状态" width="100"><template #default="{ row }"><el-tag :type="row.is_paid ? 'success' : 'warning'">{{ row.is_paid ? '已付款' : '未付款' }}</el-tag></template></el-table-column><el-table-column label="入库状态" width="100"><template #default="{ row }"><el-tag :type="row.inbound_document_id ? 'success' : 'info'">{{ row.inbound_document_id ? '已生成' : '未入库' }}</el-tag></template></el-table-column><el-table-column label="状态" width="90"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
        <el-table-column label="操作" width="300" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="showDetail(row)">查看</el-button><el-button v-if="row.status === 'DRAFT' && has('purchase_orders:update')" link type="primary" @click="openEdit(row)">编辑</el-button><el-button v-if="row.status === 'DRAFT' && has('purchase_orders:post')" link type="success" @click="action(row, 'confirm')">确认</el-button><el-button v-if="row.status === 'DRAFT' && has('purchase_orders:delete')" link type="danger" @click="action(row, 'delete')">删除</el-button><el-button v-if="row.status === 'CONFIRMED' && !row.inbound_document_id && has('purchase_orders:void')" link type="danger" @click="action(row, 'void')">作废</el-button><el-button v-if="row.status !== 'VOID' && has('purchase_orders:payment')" link type="primary" @click="changePayment(row)">{{ row.is_paid ? '改未付款' : '标记付款' }}</el-button></template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : '还没有供应商采购单'" /><TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>
    <el-dialog v-model="dialog" :title="editingId ? '编辑采购单' : '新建采购单'" width="820px" destroy-on-close><el-form ref="formRef" :model="form" label-position="top" :rules="{ order_date: [{ required: true, message: '请选择采购日期' }], supplier_id: [{ required: true, message: '请选择供应商' }], handler: [{ required: true, message: '请输入经办人' }] }"><div class="form-grid"><el-form-item label="采购日期" prop="order_date"><el-date-picker v-model="form.order_date" type="date" value-format="YYYY-MM-DD" class="w-full" /></el-form-item><el-form-item label="供应商" prop="supplier_id"><el-select v-model="form.supplier_id" filterable placeholder="请选择" class="w-full" @change="supplierChanged"><el-option v-for="item in suppliers.filter((x) => x.is_active)" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="经办人" prop="handler"><el-input v-model="form.handler" /></el-form-item><el-form-item class="span-2" label="备注"><el-input v-model="form.note" /></el-form-item></div><div class="section-heading"><strong>采购明细</strong><el-button type="primary" link :disabled="!form.supplier_id" @click="addLine"><GameIcon name="plus" />添加原材料</el-button></div><el-alert v-if="form.supplier_id && !purchasablePrices.length" title="该供应商尚未配置原料采购价，请先到供应商档案维护。" type="warning" :closable="false" class="mb-16" /><div v-for="(line, index) in form.lines" :key="index" class="line-row"><el-select v-model="line.material_id" filterable placeholder="选择该供应商的原料"><el-option v-for="item in purchasablePrices" :key="item.material_id" :label="`${item.material_name} / ${item.specification || '无规格'}`" :value="item.material_id" :disabled="form.lines.some((x: any, i: number) => i !== index && x.material_id === item.material_id)" /></el-select><el-input-number v-model="line.quantity" :min="0.01" :precision="2" :controls="false" class="w-full" /><span class="price">{{ money(priceFor(line.material_id)) }} / 单位</span><strong>{{ money(Number(line.quantity || 0) * priceFor(line.material_id)) }}</strong><el-button circle text type="danger" :disabled="form.lines.length === 1" @click="removeLine(index)"><GameIcon name="trash" /></el-button></div><div class="total">采购合计：<strong>{{ money(formTotal()) }}</strong></div></el-form><template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="submit">保存草稿</el-button></template></el-dialog>
    <el-dialog v-model="detailDialog" title="采购单详情" width="720px"><div v-if="selected" class="detail"><dl><dt>采购单号</dt><dd>{{ selected.order_no }}</dd><dt>采购日期</dt><dd>{{ selected.order_date }}</dd><dt>供应商</dt><dd>{{ selected.supplier_name }}</dd><dt>经办人</dt><dd>{{ selected.handler }}</dd><dt>付款状态</dt><dd>{{ selected.is_paid ? '已付款' : '未付款' }}</dd><dt>状态</dt><dd><StatusTag :status="selected.status" /></dd></dl><el-table :data="selected.lines" border><el-table-column prop="material_name" label="原材料" /><el-table-column prop="specification" label="规格" /><el-table-column label="数量"><template #default="{ row }">{{ Number(row.quantity).toFixed(2) }} {{ row.unit }}</template></el-table-column><el-table-column label="采购价"><template #default="{ row }">{{ money(row.unit_price) }}</template></el-table-column><el-table-column label="金额"><template #default="{ row }">{{ money(row.amount) }}</template></el-table-column></el-table><div class="total">合计：<strong>{{ money(selected.total_amount) }}</strong></div></div></el-dialog>
  </div>
</template>

<style scoped>
.filters{display:grid;grid-template-columns:300px 170px 130px 150px auto auto;gap:10px;padding:16px 18px;border-bottom:1px solid var(--ja-line)}.filters :deep(.el-date-editor){width:100%}.table-link{padding:0;border:0;background:none;color:var(--ja-red);font-family:monospace}.section-heading{display:flex;justify-content:space-between;align-items:center;margin:8px 0 12px}.line-row{display:grid;grid-template-columns:minmax(230px,1fr) 120px 130px 110px 36px;gap:10px;align-items:center;margin-bottom:10px}.price{color:var(--ja-muted)}.total{text-align:right;margin-top:16px;font-size:15px}.detail dl{display:grid;grid-template-columns:90px 1fr 90px 1fr;gap:10px 16px}.detail dt{color:var(--ja-muted)}.detail dd{margin:0}@media(max-width:900px){.filters{grid-template-columns:1fr 1fr}.line-row{grid-template-columns:1fr 110px}.detail dl{grid-template-columns:90px 1fr}}
</style>
