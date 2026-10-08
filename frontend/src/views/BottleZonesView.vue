<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { auth } from '../auth'
import type { Bottle, BottleSource, BottleSpec } from '../types'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import GameIcon from '../components/GameIcon.vue'
import TablePagination from '../components/TablePagination.vue'

const data = ref<any>({ zones: {}, bottles: { items: [], total: 0 }, stock_by_spec: [], adjustments: [], manual_good: 0, manual_bad: 0 })
const sources = ref<BottleSource[]>([])
const specs = ref<BottleSpec[]>([])
const loading = ref(false)
const zone = ref('GOOD')
const query = ref('')
const page = ref(1)
const pageSize = ref(20)
const adjustmentDialog = ref(false)
const adjustmentSaving = ref(false)
const adjustmentMode = ref<'ADD' | 'DEDUCT'>('ADD')
const today = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const adjustmentForm = reactive({ business_date: today(), spec_id: undefined as number | undefined, zone: 'GOOD', quantity: 1, note: '' })
const zoneRows = computed<Bottle[]>(() => data.value.bottles.items)
const zones = [
  { key: 'GOOD', countKey: 'good', label: '良品区' },
  { key: 'TEMPORARY', countKey: 'temporary', label: '暂存区' },
  { key: 'SCRAP', countKey: 'scrap', label: '报废区' },
  { key: 'BAD', countKey: 'bad', label: '不良品区' },
]
const selectedCount = computed(() => {
  const item = zones.find((entry) => entry.key === zone.value)
  return item ? data.value.zones[item.countKey] || 0 : 0
})
async function load() {
  loading.value = true
  try { const [zoneData, options] = await Promise.all([api.get('/bottle-zones', { params: { zone: zone.value, body_code: query.value || undefined, page: page.value, page_size: pageSize.value } }), api.get('/options')]); data.value = zoneData.data; sources.value = options.data.sources; specs.value = options.data.specs } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function sourceName(id: number) { return sources.value.find((item) => item.id === id)?.name || `单位 #${id}` }
function specName(id: number) { return specs.value.find((item) => item.id === id)?.name || `规格 #${id}` }
const zoneName = (value: string) => ({ GOOD: '良品', TEMPORARY: '暂存', SCRAP: '报废', BAD: '不良品' }[value] || value)
function openAdjustment(mode: 'ADD' | 'DEDUCT') {
  adjustmentMode.value = mode
  Object.assign(adjustmentForm, { business_date: today(), spec_id: specs.value.find((item) => item.is_default)?.id || specs.value[0]?.id, zone: 'GOOD', quantity: 1, note: '' })
  adjustmentDialog.value = true
}
async function submitAdjustment() {
  if (!adjustmentForm.business_date || !adjustmentForm.spec_id || adjustmentForm.quantity <= 0) return ElMessage.warning('请完整填写库存调整信息')
  adjustmentSaving.value = true
  try {
    await api.post('/bottle-inventory-adjustments', { ...adjustmentForm, quantity: adjustmentMode.value === 'DEDUCT' ? -adjustmentForm.quantity : adjustmentForm.quantity })
    ElMessage.success(`已${adjustmentMode.value === 'ADD' ? '增加' : '扣减'} ${zoneName(adjustmentForm.zone)}库存 ${adjustmentForm.quantity} 只`)
    adjustmentDialog.value = false
    await load()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { adjustmentSaving.value = false }
}
async function deleteAdjustment(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除这条${row.quantity > 0 ? '补录' : '扣减'}记录吗？删除后将重新计算库存。`, '删除库存调整记录', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await api.delete(`/bottle-inventory-adjustments/${row.id}`)
    ElMessage.success('库存调整记录已删除')
    await load()
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') ElMessage.error(errorMessage(err))
  }
}
onMounted(load)
function selectZone(value: string) { zone.value = value; page.value = 1; query.value = ''; load() }
function search() { page.value = 1; load() }
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
</script>

<template>
  <div>
    <PageHeader title="钢瓶库存" description="查看良品、暂存、报废和不良品库存；已进入检验单的良品仍可正常出库。"><el-button v-if="auth.user?.is_superadmin" type="primary" @click="openAdjustment('ADD')"><GameIcon name="plus" />库存补录</el-button><el-button v-if="auth.user?.is_superadmin" type="danger" plain @click="openAdjustment('DEDUCT')"><GameIcon name="minus" />库存扣减</el-button><el-button @click="load"><GameIcon name="refresh" />刷新</el-button></PageHeader>
    <div class="zone-strip zone-navigation">
      <button v-for="item in zones" :key="item.key" class="zone-cell" :class="{ active: zone === item.key }" @click="selectZone(item.key)">
        <span>{{ item.label }}</span><b>{{ data.zones[item.countKey] || 0 }}</b><small v-if="['TEMPORARY', 'SCRAP'].includes(item.key)">按数量记录</small><small v-else-if="item.key === 'GOOD' && data.manual_good">含补录 {{ data.manual_good }} 只</small><small v-else-if="item.key === 'BAD' && data.manual_bad">含补录 {{ data.manual_bad }} 只</small><small v-else>逐瓶明细</small>
      </button>
    </div>
    <section class="surface spec-stock"><div class="surface-header"><h2>按规格库存统计</h2><span class="muted">出库可用数量按规格独立计算</span></div><el-table :data="data.stock_by_spec" stripe><el-table-column prop="spec_name" label="钢瓶规格" min-width="150"><template #default="{ row }"><strong>{{ row.spec_name }}</strong></template></el-table-column><el-table-column prop="good" label="良品" min-width="90" align="right" /><el-table-column prop="temporary" label="暂存" min-width="90" align="right" /><el-table-column prop="scrap" label="报废" min-width="90" align="right" /><el-table-column prop="bad" label="不良品" min-width="90" align="right" /><el-table-column prop="total" label="库存合计" min-width="100" align="right"><template #default="{ row }"><strong>{{ row.total }}</strong></template></el-table-column></el-table></section>
    <section class="surface zone-detail">
      <div class="surface-header toolbar"><h2>{{ zones.find((item) => item.key === zone)?.label }}</h2><span class="grow" /><el-input v-if="!['TEMPORARY', 'SCRAP'].includes(zone)" v-model="query" class="search-input" clearable placeholder="搜索瓶身编号" @keyup.enter="search"><template #prefix><GameIcon name="search" /></template></el-input><el-button v-if="!['TEMPORARY', 'SCRAP'].includes(zone)" type="primary" @click="search">查询</el-button></div>
      <el-alert v-if="zone === 'GOOD' && data.manual_good" class="manual-good-alert" :title="`当前良品库存包含 ${data.manual_good} 只补录数量，补录部分无瓶身编号。`" type="info" :closable="false" />
      <el-alert v-if="zone === 'BAD' && data.manual_bad" class="manual-good-alert" :title="`当前不良品库存包含 ${data.manual_bad} 只补录数量，补录部分无瓶身编号；下方仅显示逐瓶记录。`" type="info" :closable="false" />
      <div v-if="['TEMPORARY', 'SCRAP'].includes(zone)" class="quantity-only"><strong>{{ selectedCount }}</strong><span>只</span><p>按有效入库、出库和库存补录记录汇总。</p></div>
      <el-table v-else-if="zoneRows.length" v-loading="loading" :data="zoneRows" stripe>
        <el-table-column prop="body_code" label="瓶身编号" min-width="160"><template #default="{ row }"><strong class="numeric">{{ row.body_code }}</strong></template></el-table-column>
        <el-table-column prop="manufacture_date" label="生产日期" width="115" />
        <el-table-column label="来源客户" min-width="170"><template #default="{ row }">{{ sourceName(row.source_id) }}</template></el-table-column>
        <el-table-column label="瓶子规格" width="140"><template #default="{ row }">{{ specName(row.spec_id) }}</template></el-table-column>
        <el-table-column label="工序状态" width="140"><template #default="{ row }"><StatusTag :status="row.process_status" /></template></el-table-column>
        <el-table-column label="当前区域" width="100"><template #default="{ row }"><StatusTag :status="row.zone" /></template></el-table-column>
        <el-table-column label="检验单状态" width="130"><template #default="{ row }"><el-tag v-if="row.inspection_document_status === 'INSPECTED'" type="success" size="small">已检验</el-tag><span v-else class="muted">未进检验单</span></template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : '当前区域没有逐瓶记录'" description="数据会随库存补录、入库、出库和检测工序自动更新。" />
      <TablePagination v-if="!['TEMPORARY', 'SCRAP'].includes(zone)" :page="page" :page-size="pageSize" :total="data.bottles.total" @change="pageChanged" />
    </section>
    <section v-if="data.adjustments?.length" class="surface adjustment-history"><div class="surface-header"><h2>库存调整记录</h2><span class="muted">最近 {{ data.adjustments.length }} 条</span></div><el-table :data="data.adjustments" stripe><el-table-column prop="business_date" label="调整日期" width="115" /><el-table-column prop="spec_name" label="钢瓶规格" min-width="140" /><el-table-column label="库存类型" width="100"><template #default="{ row }">{{ zoneName(row.zone) }}</template></el-table-column><el-table-column label="操作" width="90"><template #default="{ row }"><el-tag :type="row.quantity > 0 ? 'success' : 'danger'" effect="plain">{{ row.quantity > 0 ? '补录' : '扣减' }}</el-tag></template></el-table-column><el-table-column label="数量" width="90" align="right"><template #default="{ row }"><strong>{{ Math.abs(row.quantity) }}</strong></template></el-table-column><el-table-column prop="created_by_name" label="操作人" width="120" /><el-table-column prop="note" label="备注" min-width="160"><template #default="{ row }">{{ row.note || '-' }}</template></el-table-column><el-table-column v-if="auth.user?.is_superadmin" label="管理" width="80" fixed="right"><template #default="{ row }"><el-button link type="danger" @click="deleteAdjustment(row)">删除</el-button></template></el-table-column></el-table></section>

    <el-dialog v-model="adjustmentDialog" :title="adjustmentMode === 'ADD' ? '库存补录' : '库存扣减'" width="560px" destroy-on-close><el-form :model="adjustmentForm" label-position="top"><div class="form-grid"><el-form-item label="调整日期" required><el-date-picker v-model="adjustmentForm.business_date" type="date" value-format="YYYY-MM-DD" :clearable="false" class="w-full" /></el-form-item><el-form-item label="钢瓶规格" required><el-select v-model="adjustmentForm.spec_id" filterable placeholder="选择规格"><el-option v-for="item in specs" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item class="span-2" label="库存类型" required><el-radio-group v-model="adjustmentForm.zone"><el-radio-button value="GOOD">良品</el-radio-button><el-radio-button value="TEMPORARY">暂存</el-radio-button><el-radio-button value="SCRAP">报废</el-radio-button><el-radio-button value="BAD">不良品</el-radio-button></el-radio-group></el-form-item><el-form-item :label="adjustmentMode === 'ADD' ? '增加数量' : '扣减数量'" required><el-input-number v-model="adjustmentForm.quantity" :min="1" :precision="0" class="w-full" /></el-form-item><el-form-item class="span-2" label="调整说明"><el-input v-model="adjustmentForm.note" maxlength="200" show-word-limit :placeholder="`选填，说明${adjustmentMode === 'ADD' ? '补录' : '扣减'}原因`" /></el-form-item></div><el-alert :title="adjustmentForm.zone === 'BAD' ? (adjustmentMode === 'ADD' ? '不良品补录只增加无瓶身编号的数量，不会生成逐瓶记录。' : '不良品扣减仅限补录的无编号数量；有编号的不良品请通过质量状态流程处理。') : (adjustmentMode === 'ADD' ? '补录只增加库存，不会生成钢瓶入库单；操作完成后将保留调整记录。' : '扣减不会生成钢瓶出库单，且不能超过当前规格与库存类型的可用数量。')" :type="adjustmentMode === 'ADD' ? 'warning' : 'error'" :closable="false" /></el-form><template #footer><el-button @click="adjustmentDialog = false">取消</el-button><el-button :type="adjustmentMode === 'ADD' ? 'primary' : 'danger'" :loading="adjustmentSaving" @click="submitAdjustment">确认{{ adjustmentMode === 'ADD' ? '增加' : '扣减' }}</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.zone-navigation { overflow: hidden; grid-template-columns: repeat(4, minmax(0, 1fr)); }.zone-navigation button { text-align: left; color: var(--ja-text); background:#fff; border:0; }.zone-navigation button:hover { background:#fafafa; }.zone-navigation small { display:block; min-height:17px; color:#9a9da4; font-size:10px; margin-top:4px; }.spec-stock,.zone-detail { margin-top:16px; }.manual-good-alert{margin:12px 18px}.quantity-only { min-height:260px; display:flex; align-items:baseline; justify-content:center; padding-top:76px; }.quantity-only strong { font-size:54px; }.quantity-only span { color:var(--ja-muted); margin-left:8px; }.quantity-only p { position:absolute; margin-top:78px; color:var(--ja-muted); font-size:12px; }.adjustment-history{margin-top:16px}
</style>
