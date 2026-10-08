<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { auth, has } from '../auth'
import type { BottleOutbound, BottleSource, BottleSpec } from '../types'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import TablePagination from '../components/TablePagination.vue'

const props = withDefaults(defineProps<{
  embedded?: boolean
  selectable?: boolean
  dateRange?: string[]
  sourceId?: number
  searchVersion?: number
}>(), { embedded: false, dateRange: () => [], sourceId: undefined, searchVersion: 0 })

const emit = defineEmits<{ selectionChange: [rows: BottleOutbound[]] }>()
const table = ref()
defineExpose({ clearSelection: () => table.value?.clearSelection() })

const today = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const rows = ref<BottleOutbound[]>([])
const specs = ref<BottleSpec[]>([])
const sources = ref<BottleSource[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialog = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const blankLine = () => ({ spec_id: undefined as number | undefined, quantity: 0, good_quantity: 0, temporary_quantity: 0, scrap_quantity: 0, bad_quantity: 0 })
const blank = () => ({ business_date: today(), source_id: undefined as number | undefined, handler: auth.user?.name || '', note: '', lines: [blankLine()] })
const form = reactive<any>(blank())
async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value, date_from: props.dateRange?.[0] || undefined, date_to: props.dateRange?.[1] || undefined, source_id: props.sourceId }
    const [docs, options] = await Promise.all([api.get('/bottle-outbounds', { params }), api.get('/options')])
    rows.value = docs.data.items; total.value = docs.data.total; specs.value = options.data.specs; sources.value = options.data.sources
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function openCreate() { editingId.value = null; Object.assign(form, blank()); form.source_id = sources.value.find((item) => item.is_default)?.id || sources.value[0]?.id; form.lines = [blankLine()]; dialog.value = true }
function openEdit(row: BottleOutbound) { editingId.value = row.id; Object.assign(form, { business_date: row.business_date, source_id: row.source_id, handler: row.handler, note: row.note || '' }); form.lines = row.lines.map((line) => ({ spec_id: line.spec_id, quantity: line.quantity, good_quantity: line.good_quantity, temporary_quantity: line.temporary_quantity, scrap_quantity: line.scrap_quantity, bad_quantity: line.bad_quantity })); dialog.value = true }
function addLine() { form.lines.push(blankLine()) }
function removeLine(index: number) { if (form.lines.length > 1) form.lines.splice(index, 1) }
async function submit() { await formRef.value?.validate(); if (form.lines.some((item: any) => !item.spec_id || item.good_quantity + item.temporary_quantity + item.scrap_quantity + item.bad_quantity <= 0)) return ElMessage.warning('请完整填写规格及分类数量'); try { if (editingId.value) await api.put(`/bottle-outbounds/${editingId.value}`, form); else await api.post('/bottle-outbounds', form); ElMessage.success(editingId.value ? '出库历史记录已修改' : '出库草稿已保存'); dialog.value = false; await load() } catch (err) { ElMessage.error(errorMessage(err)) } }
async function action(row: BottleOutbound, type: 'post' | 'void' | 'delete' | 'purge') { try { const prompt = type === 'post' ? '审批后将按规格从良品库分配钢瓶并出库。' : type === 'void' ? '撤销后钢瓶将返回原库存区。' : type === 'purge' ? '此操作将彻底删除该条已作废出库记录，删除后无法恢复，是否继续？' : '确认删除该草稿？'; await ElMessageBox.confirm(prompt, type === 'purge' ? '彻底删除记录' : '操作确认', { type: type === 'purge' ? 'error' : 'warning', confirmButtonText: type === 'purge' ? '确认彻底删除' : '确定' }); if (type === 'delete' || type === 'purge') await api.delete(`/bottle-outbounds/${row.id}`); else await api.post(`/bottle-outbounds/${row.id}/${type}`); ElMessage.success(type === 'purge' ? '已彻底删除作废记录' : '操作成功'); await load() } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) } }
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
function audit(row: BottleOutbound) { return [`创建：${row.created_by_name}`, row.updated_by_name && `修改：${row.updated_by_name}`, row.posted_by_name && `审批：${row.posted_by_name}`, row.voided_by_name && `撤销：${row.voided_by_name}`].filter(Boolean).join('；') }
function boundBottles(row: BottleOutbound) {
  return row.lines.flatMap((line) => (line.selected_bottles || []).map((item) => ({
    ...item,
    spec_name: line.spec_name,
    zone_name: item.origin_zone === 'BAD' ? '不良品' : '报废',
  })))
}
function hasBoundBottles(row: BottleOutbound) { return boundBottles(row).length > 0 }
function outboundRowClassName({ row }: { row: BottleOutbound }) { return hasBoundBottles(row) ? 'has-bound-bottles' : 'no-bound-bottles' }
onMounted(load)
watch(() => props.searchVersion, () => { page.value = 1; load() })
</script>

<template>
  <div>
    <PageHeader v-if="!embedded" title="良品库出库记录" description="按供瓶单位和钢瓶规格创建良品出库单，审批后自动占用对应规格的良品钢瓶。"><el-button v-if="has('bottle_outbound:create')" type="primary" @click="openCreate"><GameIcon name="plus" />新建出库单</el-button></PageHeader>
    <section :class="{ surface: !embedded }"><div class="surface-header"><h2>出库记录</h2><span class="muted">共 {{ total }} 条</span><el-button @click="load"><GameIcon name="refresh" />刷新</el-button></div>
      <el-table ref="table" v-show="rows.length" v-loading="loading" :data="rows" :row-class-name="outboundRowClassName" stripe row-key="id" @selection-change="emit('selectionChange', $event)"><el-table-column type="expand" width="44"><template #default="{ row }"><section v-if="hasBoundBottles(row)" class="bound-bottle-child"><header><strong>{{ row.document_no }} 的瓶号明细</strong><span>共 {{ boundBottles(row).length }} 只</span></header><table class="bound-bottle-table"><thead><tr><th>钢瓶规格</th><th>出库类别</th><th>瓶身编号</th><th>备注</th><th>绑定状态</th></tr></thead><tbody><tr v-for="bottle in boundBottles(row)" :key="bottle.id"><td>{{ bottle.spec_name }}</td><td>{{ bottle.zone_name }}</td><td><strong class="numeric" :class="{ voided: !bottle.is_active }">{{ bottle.body_code }}</strong></td><td>{{ bottle.inspection_note || '-' }}</td><td><el-tag :type="bottle.is_active ? 'success' : 'info'" effect="light">{{ bottle.is_active ? '有效' : '已撤销' }}</el-tag></td></tr></tbody></table></section></template></el-table-column><el-table-column v-if="selectable" type="selection" width="48" reserve-selection :selectable="(row: BottleOutbound) => row.status === 'POSTED'" /><el-table-column prop="document_no" label="出库单号" min-width="190" /><el-table-column prop="business_date" label="出库日期" width="115" /><el-table-column prop="customer" label="客户/供瓶单位" min-width="160" /><el-table-column label="规格数量" min-width="400"><template #default="{ row }"><table class="spec-detail-table"><thead><tr><th>规格</th><th>良品</th><th>暂存</th><th>报废</th><th>不良品</th></tr></thead><tbody><tr v-for="line in row.lines" :key="line.id"><td>{{ line.spec_name }}</td><td>{{ line.good_quantity }}</td><td>{{ line.temporary_quantity }}</td><td>{{ line.scrap_quantity }}</td><td>{{ line.bad_quantity || 0 }}</td></tr></tbody></table></template></el-table-column><el-table-column prop="total_quantity" label="总数量" width="90" align="right" /><el-table-column prop="handler" label="经办人" width="110" /><el-table-column label="操作记录" min-width="240"><template #default="{ row }">{{ audit(row) }}</template></el-table-column><el-table-column label="状态" width="90"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column><el-table-column label="操作" width="220" fixed="right"><template #default="{ row }"><el-button v-if="has('bottle_outbound:update')" link type="primary" @click="openEdit(row)">编辑</el-button><el-button v-if="row.status === 'DRAFT' && has('bottle_outbound:post')" link type="success" @click="action(row,'post')">审批</el-button><el-button v-if="row.status === 'DRAFT' && has('bottle_outbound:delete')" link type="danger" @click="action(row,'delete')">删除</el-button><el-button v-if="row.status === 'POSTED' && has('bottle_outbound:void')" link type="danger" @click="action(row,'void')">撤销</el-button><el-button v-if="row.status === 'VOID' && auth.user?.is_superadmin" link type="danger" @click="action(row,'purge')">彻底删除</el-button></template></el-table-column></el-table>
      <EmptyState v-if="!rows.length" :title="loading ? '正在加载' : '还没有良品出库单'" /><TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>
    <el-dialog v-model="dialog" :title="editingId ? '编辑出库历史记录' : '新建出库单'" width="920px"><el-form ref="formRef" :model="form" label-position="top" :rules="{ business_date:[{required:true,message:'请选择日期'}],source_id:[{required:true,message:'请选择客户/供瓶单位'}],handler:[{required:true,message:'请输入经办人'}] }"><div class="form-grid"><el-form-item label="出库日期" prop="business_date"><el-date-picker v-model="form.business_date" type="date" value-format="YYYY-MM-DD" class="w-full" /></el-form-item><el-form-item label="客户/供瓶单位" prop="source_id"><el-select v-model="form.source_id" filterable placeholder="请选择供瓶单位"><el-option v-for="item in sources" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="经办人" prop="handler"><el-input v-model="form.handler" /></el-form-item><el-form-item class="span-2" label="备注"><el-input v-model="form.note" type="textarea" :rows="2" /></el-form-item></div><div class="line-title"><strong>按规格和类别填写出库数量</strong><el-button link type="primary" @click="addLine"><GameIcon name="plus" />添加规格</el-button></div><div v-for="(line,index) in form.lines" :key="index" class="out-line"><el-select v-model="line.spec_id" filterable placeholder="选择钢瓶规格"><el-option v-for="item in specs" :key="item.id" :label="item.name" :value="item.id" /></el-select><label>良品<el-input-number v-model="line.good_quantity" :min="0" :precision="0" :controls="false" /></label><label>暂存<el-input-number v-model="line.temporary_quantity" :min="0" :precision="0" :controls="false" /></label><label>报废<el-input-number v-model="line.scrap_quantity" :min="0" :precision="0" :controls="false" /></label><label>不良品<el-input-number v-model="line.bad_quantity" :min="0" :precision="0" :controls="false" /></label><el-button circle text type="danger" :disabled="form.lines.length===1" @click="removeLine(index)"><GameIcon name="trash" /></el-button></div></el-form><template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" @click="submit">{{ editingId ? '保存修改' : '保存草稿' }}</el-button></template></el-dialog>
  </div>
</template>

<style scoped>.bound-bottle-child{padding:6px 16px 14px 58px}.bound-bottle-child header{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}.bound-bottle-child header span{color:var(--ja-muted);font-size:12px}.bound-bottle-child .voided{text-decoration:line-through;opacity:.55}.bound-bottle-table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;border:1px solid var(--ja-line);border-radius:8px;background:#fff;font-size:12px}.bound-bottle-table th,.bound-bottle-table td{padding:9px 12px;border-right:1px solid var(--ja-line);border-bottom:1px solid var(--ja-line);text-align:left}.bound-bottle-table th{color:var(--ja-muted);background:#f5f7f8;font-size:11px;font-weight:600}.bound-bottle-table th:last-child,.bound-bottle-table td:last-child{border-right:0}.bound-bottle-table tbody tr:last-child td{border-bottom:0}:deep(.no-bound-bottles .el-table__expand-icon){visibility:hidden}</style>

<style scoped>.line-title{display:flex;justify-content:space-between;align-items:center;margin:4px 0 10px}.out-line{display:grid;grid-template-columns:minmax(150px,1.2fr) repeat(4,minmax(92px,1fr)) 40px;gap:10px;align-items:end;margin-bottom:10px;padding:12px;background:#f7f8f9;border-radius:var(--ja-radius)}.out-line label{color:var(--ja-muted);font-size:11px}.out-line :deep(.el-input-number){width:100%;margin-top:4px}.spec-detail-table{width:100%;border-collapse:separate;border-spacing:0;overflow:hidden;font-size:12px;border:1px solid #e3e7eb;border-radius:8px;background:#fff}.spec-detail-table th,.spec-detail-table td{padding:6px 10px;text-align:right;border-right:1px solid #edf0f2;border-bottom:1px solid #edf0f2;white-space:nowrap}.spec-detail-table th:first-child,.spec-detail-table td:first-child{text-align:left}.spec-detail-table th{color:var(--ja-muted);font-size:11px;font-weight:600;background:#f5f7f8}.spec-detail-table th:last-child,.spec-detail-table td:last-child{border-right:0}.spec-detail-table tbody tr:last-child td{border-bottom:0}@media(max-width:760px){.out-line{grid-template-columns:1fr 1fr}.out-line>.el-select{grid-column:1/-1}.out-line>.el-button{justify-self:end}}</style>
