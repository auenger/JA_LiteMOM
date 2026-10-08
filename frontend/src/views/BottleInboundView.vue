<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import api, { errorMessage } from '../api'
import { auth, has } from '../auth'
import type { BottleInbound, BottleOutbound, BottleSource, BottleSpec } from '../types'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import GameIcon from '../components/GameIcon.vue'
import TablePagination from '../components/TablePagination.vue'
import BottleOutboundView from './BottleOutboundView.vue'
import ReceiptWordExport from '../components/ReceiptWordExport.vue'

const route = useRoute()

const rows = ref<BottleInbound[]>([])
const inboundTable = ref(), outboundTable = ref()
const selectedInbounds = ref<BottleInbound[]>([]), selectedOutbounds = ref<BottleOutbound[]>([])
function clearReceiptSelection() {
  inboundTable.value?.clearSelection(); outboundTable.value?.clearSelection()
  selectedInbounds.value = []; selectedOutbounds.value = []
}
const sources = ref<BottleSource[]>([])
const specs = ref<BottleSpec[]>([])
const users = ref<{ id: number; name: string; username: string }[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filters = reactive({ business_date_range: [] as string[], source_id: undefined as number | undefined })
const activeTab = ref<'inbound' | 'outbound'>(route.query.tab === 'outbound' || (!has('bottle_inbound:view') && has('bottle_outbound:view')) ? 'outbound' : 'inbound')
const outboundSearchVersion = ref(0)
const dialog = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const today = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}
const blank = () => ({ business_date: today(), source_id: undefined as number | undefined, pending_quantity: 0, temporary_quantity: 0, scrap_quantity: 0, handler: auth.user?.name || '', note: '', lines: [] as any[] })
const form = reactive(blank())
const formTotal = computed(() => form.lines.reduce((sum, line) => sum + line.pending_quantity + line.temporary_quantity + line.scrap_quantity, 0))

async function load() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
      date_from: filters.business_date_range?.[0] || undefined,
      date_to: filters.business_date_range?.[1] || undefined,
      source_id: filters.source_id,
    }
    const [docs, options] = await Promise.all([has('bottle_inbound:view') ? api.get('/bottle-inbounds', { params }) : Promise.resolve({ data: { items: [], total: 0 } }), api.get('/options')])
    rows.value = docs.data.items; total.value = docs.data.total; sources.value = options.data.sources; specs.value = options.data.specs; users.value = options.data.users
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function openEdit(row: BottleInbound) { editingId.value = row.id; Object.assign(form, { business_date: row.business_date, source_id: row.source_id, handler: row.handler, note: row.note || '', lines: specs.value.map((spec) => { const line = row.lines.find((item) => item.spec_id === spec.id); return { spec_id: spec.id, spec_name: spec.name, pending_quantity: line?.pending_quantity || 0, temporary_quantity: line?.temporary_quantity || 0, scrap_quantity: line?.scrap_quantity || 0 } }) }); dialog.value = true }
async function submit() {
  await formRef.value?.validate()
  if (formTotal.value <= 0) return ElMessage.warning('本批入库总量必须大于零')
  try {
    const payload = { ...form, lines: form.lines.filter((line) => line.pending_quantity + line.temporary_quantity + line.scrap_quantity > 0) }
    if (!editingId.value) return
    await api.put(`/bottle-inbounds/${editingId.value}`, payload)
    ElMessage.success('入库历史记录已修改'); dialog.value = false; await load()
  } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function action(row: BottleInbound, type: 'post' | 'void' | 'delete' | 'purge') {
  const prompt = type === 'post' ? '确认后将计入对应业务状态区和当日入库总量。' : type === 'void' ? '作废后将从状态区数量和当日汇总中扣除；已有抄码记录会保留。' : type === 'purge' ? '此操作将彻底删除该条已作废记录，删除后无法恢复，是否继续？' : '确认删除该草稿？'
  try {
    await ElMessageBox.confirm(prompt, type === 'post' ? '确认入库' : type === 'void' ? '作废入库' : type === 'purge' ? '彻底删除记录' : '删除草稿', { type: type === 'purge' ? 'error' : 'warning', confirmButtonText: type === 'purge' ? '确认彻底删除' : '确定' })
    if (type === 'delete' || type === 'purge') await api.delete(`/bottle-inbounds/${row.id}`); else await api.post(`/bottle-inbounds/${row.id}/${type}`)
    ElMessage.success(type === 'post' ? '入库已生效' : type === 'void' ? '入库已作废' : type === 'purge' ? '已彻底删除作废记录' : '草稿已删除'); await load()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
function sourceName(id: number) { return sources.value.find((item) => item.id === id)?.name || `单位 #${id}` }
function search() { page.value = 1; load(); outboundSearchVersion.value += 1 }
function resetFilters() { Object.assign(filters, { business_date_range: [], source_id: undefined }); search() }
onMounted(load)
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
</script>

<template>
  <div>
    <PageHeader title="出入库历史记录" description="集中查询钢瓶入库与出库记录。" />
    <section class="surface history-shell">
      <div class="inbound-filters">
        <el-date-picker v-model="filters.business_date_range" type="daterange" value-format="YYYY-MM-DD" clearable unlink-panels range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
        <el-select v-model="filters.source_id" filterable clearable placeholder="选择客户">
          <el-option v-for="item in sources" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-button type="primary" @click="search"><GameIcon name="search" />查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
      <ReceiptWordExport v-if="has('bottle_inbound:export')" :inbound-ids="selectedInbounds.map(row => row.id)" :outbound-ids="selectedOutbounds.map(row => row.id)" @clear="clearReceiptSelection" />
      <el-tabs v-model="activeTab" class="history-tabs">
        <el-tab-pane label="入库" name="inbound">
          <div class="surface-header"><h2>入库记录</h2><span class="muted">共 {{ total }} 条</span><el-button @click="load"><GameIcon name="refresh" />刷新</el-button></div>
          <el-table ref="inboundTable" v-show="has('bottle_inbound:view') && rows.length" v-loading="loading" :data="rows" row-key="id" stripe @selection-change="selectedInbounds = $event">
        <el-table-column v-if="has('bottle_inbound:export')" type="selection" width="48" reserve-selection :selectable="(row: BottleInbound) => row.status === 'POSTED'" />
        <el-table-column prop="document_no" label="入库编号" min-width="190"><template #default="{ row }"><span class="numeric">{{ row.document_no }}</span></template></el-table-column>
        <el-table-column prop="business_date" label="入库日期" width="115" />
        <el-table-column label="来源客户" min-width="150"><template #default="{ row }">{{ sourceName(row.source_id) }}</template></el-table-column>
        <el-table-column label="规格数量明细" min-width="360"><template #default="{ row }">
          <table class="spec-detail-table">
            <thead><tr><th>规格</th><th>待检</th><th>暂存</th><th>报废</th></tr></thead>
            <tbody><tr v-for="line in row.lines" :key="line.id"><td>{{ line.spec_name }}</td><td>{{ line.pending_quantity }}</td><td>{{ line.temporary_quantity }}</td><td>{{ line.scrap_quantity }}</td></tr></tbody>
          </table>
        </template></el-table-column>
        <el-table-column prop="pending_quantity" label="待检测" width="90" align="right" />
        <el-table-column prop="temporary_quantity" label="暂存" width="80" align="right" />
        <el-table-column prop="scrap_quantity" label="报废" width="80" align="right" />
        <el-table-column prop="total_quantity" label="本批总量" width="100" align="right"><template #default="{ row }"><strong>{{ row.total_quantity }}</strong></template></el-table-column>
        <el-table-column prop="handler" label="经办人" width="110" />
        <el-table-column label="状态" width="90"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
        <el-table-column label="操作" width="220" fixed="right"><template #default="{ row }">
          <el-button v-if="has('bottle_inbound:update')" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'DRAFT' && has('bottle_inbound:post')" link type="success" @click="action(row, 'post')">确认</el-button>
          <el-button v-if="row.status === 'DRAFT' && has('bottle_inbound:delete')" link type="danger" @click="action(row, 'delete')">删除</el-button>
          <el-button v-if="row.status === 'POSTED' && has('bottle_inbound:void')" link type="danger" @click="action(row, 'void')">作废</el-button>
          <el-button v-if="row.status === 'VOID' && auth.user?.is_superadmin" link type="danger" @click="action(row, 'purge')">彻底删除</el-button>
        </template></el-table-column>
          </el-table>
          <EmptyState v-if="!has('bottle_inbound:view') || !rows.length" :title="!has('bottle_inbound:view') ? '暂无入库记录查看权限' : loading ? '正在加载' : '没有符合条件的钢瓶入库记录'" :description="has('bottle_inbound:view') ? '请调整日期区间或客户后重新查询。' : ''" />
          <TablePagination v-if="has('bottle_inbound:view')" :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
        </el-tab-pane>
        <el-tab-pane label="出库" name="outbound" lazy>
          <BottleOutboundView ref="outboundTable" v-if="has('bottle_outbound:view')" embedded :selectable="has('bottle_inbound:export')" @selection-change="selectedOutbounds = $event" :date-range="filters.business_date_range" :source-id="filters.source_id" :search-version="outboundSearchVersion" />
          <EmptyState v-else title="暂无出库记录查看权限" />
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="dialog" title="编辑钢瓶入库" width="680px" destroy-on-close>
      <el-form ref="formRef" :model="form" label-position="top" :rules="{ business_date: [{ required: true, message: '请选择入库日期' }], source_id: [{ required: true, message: '请选择来源客户' }], handler: [{ required: true, message: '请输入经办人' }] }">
        <div class="form-grid">
          <el-form-item label="入库日期" prop="business_date"><el-date-picker v-model="form.business_date" type="date" value-format="YYYY-MM-DD" class="w-full" /></el-form-item>
          <el-form-item label="来源客户/供瓶单位" prop="source_id"><el-select v-model="form.source_id" filterable placeholder="请选择"><el-option v-for="item in sources" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
          <el-form-item label="经办人" prop="handler"><el-select v-model="form.handler" filterable placeholder="请选择"><el-option v-for="item in users" :key="item.id" :label="`${item.name}（${item.username}）`" :value="item.name" /></el-select></el-form-item>
          <el-form-item class="span-2" label="备注"><el-input v-model="form.note" type="textarea" :rows="2" placeholder="选填" /></el-form-item>
        </div>
        <div class="spec-editor-title"><strong>按规格填写入库数量</strong><span>本批合计 {{ formTotal }} 只</span></div>
        <div class="spec-edit-list"><div v-for="line in form.lines" :key="line.spec_id" class="spec-edit-row"><strong>{{ line.spec_name }}</strong><label>待检测<el-input-number v-model="line.pending_quantity" :min="0" :precision="0" :controls="false" /></label><label>暂存<el-input-number v-model="line.temporary_quantity" :min="0" :precision="0" :controls="false" /></label><label>报废<el-input-number v-model="line.scrap_quantity" :min="0" :precision="0" :controls="false" /></label></div></div>
        <el-alert title="良品和不良品不能直接入库；完成抄码后自动进入良品库，后续可调整良品/不良品状态。" type="info" :closable="false" />
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="submit">保存修改</el-button></div></template>
    </el-dialog>
  </div>
</template>

<style scoped>.history-shell{overflow:hidden}.inbound-filters{display:grid;grid-template-columns:minmax(260px,380px) minmax(160px,240px) 92px 72px;gap:10px;align-items:center;padding:16px;border-bottom:1px solid var(--ja-border)}.inbound-filters :deep(.el-date-editor){width:100%;min-width:0}.history-tabs{padding:0 16px 16px}.history-tabs :deep(.el-tabs__header){margin:0 0 4px}.history-tabs :deep(.el-tabs__nav-wrap){padding-top:10px}.spec-detail-table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;font-size:12px;border:1px solid #e3e7eb;border-radius:8px;background:#fff}.spec-detail-table th,.spec-detail-table td{padding:6px 10px;text-align:right;border-right:1px solid #edf0f2;border-bottom:1px solid #edf0f2;white-space:nowrap}.spec-detail-table th:first-child,.spec-detail-table td:first-child{text-align:left}.spec-detail-table th{color:var(--ja-muted);font-size:11px;font-weight:600;background:#f5f7f8}.spec-detail-table th:last-child,.spec-detail-table td:last-child{border-right:0}.spec-detail-table tbody tr:last-child td{border-bottom:0}.spec-editor-title{display:flex;justify-content:space-between;margin:8px 0 10px}.spec-editor-title span{color:var(--ja-muted)}.spec-edit-list{display:grid;gap:9px;margin-bottom:14px}.spec-edit-row{display:grid;grid-template-columns:minmax(110px,1fr) repeat(3,120px);gap:10px;align-items:end;padding:12px;background:#f7f8f9;border-radius:var(--ja-radius)}.spec-edit-row label{color:var(--ja-muted);font-size:11px}.spec-edit-row :deep(.el-input-number){width:100%;margin-top:4px}@media(max-width:760px){.inbound-filters{grid-template-columns:1fr 1fr}.inbound-filters .el-button{margin-left:0}.history-tabs{padding:0 10px 12px}.spec-edit-row{grid-template-columns:1fr 1fr}.spec-edit-row>strong{grid-column:1/-1}}</style>
