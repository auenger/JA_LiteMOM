<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import type { Bottle, BottleSource, BottleSpec } from '../types'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import TablePagination from '../components/TablePagination.vue'

const rows = ref<Bottle[]>([])
const sources = ref<BottleSource[]>([])
const specs = ref<BottleSpec[]>([])
const loading = ref(false)
const zone = ref<'GOOD' | 'BAD' | 'SCRAP'>('GOOD')
const query = ref('')
const returnedFilter = ref<string>('')
const dateRange = ref<[string, string] | null>(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialog = ref(false)
const selected = ref<Bottle | null>(null)
const form = reactive({ zone: 'BAD' as 'GOOD' | 'BAD' | 'SCRAP', note: '', returned_to_customer: true })

async function load() {
  loading.value = true
  try {
    const [records, options] = await Promise.all([api.get('/bottles', { params: { zone: zone.value, returned_to_customer: returnedFilter.value ? returnedFilter.value === 'yes' : undefined, body_code: query.value || undefined, date_from: dateRange.value?.[0], date_to: dateRange.value?.[1], page: page.value, page_size: pageSize.value } }), api.get('/options')])
    rows.value = records.data.items; total.value = records.data.total; sources.value = options.data.sources; specs.value = options.data.specs
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function search() { page.value = 1; load() }
function resetFilters() { dateRange.value = null; returnedFilter.value = ''; query.value = ''; search() }
function changeZone(value: 'GOOD' | 'BAD' | 'SCRAP') { zone.value = value; returnedFilter.value = ''; search() }
function openChange(row: Bottle, target: 'GOOD' | 'BAD' | 'SCRAP') { selected.value = row; form.zone = target; form.note = ''; form.returned_to_customer = target === 'BAD'; dialog.value = true }
function targetName() { return form.zone === 'GOOD' ? '良品' : form.zone === 'BAD' ? '不良品' : '报废' }
async function submit() {
  if (!selected.value) return
  try { await api.put(`/bottles/${selected.value.id}/status`, form); ElMessage.success(form.zone === 'SCRAP' ? '已转为报废，报废库存增加 1' : `已转入${targetName()}库`); dialog.value = false; await load() } catch (err) { ElMessage.error(errorMessage(err)) }
}
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
function sourceName(id: number) { return sources.value.find((item) => item.id === id)?.name || `单位 #${id}` }
function specName(id: number) { return specs.value.find((item) => item.id === id)?.name || `规格 #${id}` }
async function undoCoding(row: Bottle) {
  try {
    await ElMessageBox.confirm(`确认撤销瓶身编号“${row.body_code}”的抄码？该瓶会从良品库和抄码记录中移除，待抄码余量加回 1。`, '撤销抄码', { type: 'warning' })
    await api.delete(`/bottles/${row.id}/coding`)
    ElMessage.success('抄码已撤销，待抄码余量已恢复')
    await load()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
onMounted(load)
</script>

<template>
  <div class="quality-page">
    <PageHeader title="质量分类库" description="集中查看良品、不良品和报废瓶；良品可快捷转为不良品或报废。"><el-button @click="load"><GameIcon name="refresh" />刷新</el-button></PageHeader>
    <section class="surface quality-surface">
      <form class="inventory-filters" @submit.prevent="search">
        <div class="filter-mode-row">
          <div class="filter-mode-field">
            <span class="filter-label">库存类型</span>
            <el-radio-group :model-value="zone" aria-label="库存类型" @change="changeZone">
              <el-radio-button value="GOOD">良品库</el-radio-button>
              <el-radio-button value="BAD">不良品库</el-radio-button>
              <el-radio-button value="SCRAP">报废库</el-radio-button>
            </el-radio-group>
          </div>
          <span class="filter-total">共 <strong>{{ total }}</strong> 条记录</span>
        </div>
        <div class="filter-grid" :class="{ 'has-returned-filter': zone === 'BAD' }">
          <label class="filter-field date-filter">
            <span class="filter-label">抄码日期</span>
            <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" clearable />
          </label>
          <label v-if="zone === 'BAD'" class="filter-field returned-filter">
            <span class="filter-label">退还客户</span>
            <el-select v-model="returnedFilter" clearable placeholder="全部状态" @change="search">
              <el-option label="退还客户：是" value="yes" />
              <el-option label="退还客户：否" value="no" />
            </el-select>
          </label>
          <label class="filter-field code-filter">
            <span class="filter-label">瓶身编号</span>
            <el-input v-model="query" clearable placeholder="输入瓶身编号" @keyup.enter="search"><template #prefix><GameIcon name="search" /></template></el-input>
          </label>
          <div class="filter-actions">
            <el-button type="primary" native-type="submit"><GameIcon name="search" />查询</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </div>
        </div>
      </form>
      <div v-if="zone === 'BAD'" class="return-summary">当前条件共 {{ total }} 只；退还客户标识仅用于统计。历史未标记记录不会计入“是 / 否”筛选。</div>
      <el-table v-if="rows.length" v-loading="loading" class="desktop-quality-table" :data="rows" stripe>
        <el-table-column prop="body_code" label="瓶身编号" min-width="170"><template #default="{ row }"><strong class="numeric">{{ row.body_code }}</strong></template></el-table-column>
        <el-table-column prop="coding_date" label="抄码日期" width="115" />
        <el-table-column prop="manufacture_date" label="生产日期" width="115"><template #default="{ row }">{{ row.manufacture_date || '-' }}</template></el-table-column>
        <el-table-column label="供瓶单位" min-width="160"><template #default="{ row }">{{ sourceName(row.source_id) }}</template></el-table-column>
        <el-table-column label="瓶子规格" width="130"><template #default="{ row }">{{ specName(row.spec_id) }}</template></el-table-column>
        <el-table-column prop="coded_by_name" label="抄码人员" width="120" />
        <el-table-column label="状态" width="95"><template #default="{ row }"><StatusTag :status="row.zone" /></template></el-table-column>
        <el-table-column label="检验单" width="135"><template #default="{ row }"><el-tag v-if="row.inspection_document_status === 'INSPECTED'" type="success" size="small">已检验</el-tag><span v-else class="muted">未生成</span></template></el-table-column>
        <el-table-column v-if="zone === 'BAD'" label="退还客户" width="110"><template #default="{ row }"><el-tag v-if="row.returned_to_customer === true" type="warning">是</el-tag><span v-else>{{ row.returned_to_customer === false ? '否' : '未标记' }}</span></template></el-table-column>
        <el-table-column prop="inspection_note" label="状态备注" min-width="160"><template #default="{ row }">{{ row.inspection_note || '-' }}</template></el-table-column>
        <el-table-column label="操作" width="270" fixed="right"><template #default="{ row }"><span v-if="row.inspection_document_status === 'INSPECTED' && row.zone !== 'SCRAP'" class="muted">检验资料已锁定</span><template v-else><template v-if="row.zone === 'GOOD' && has('inspection:create')"><el-button link type="danger" @click="openChange(row, 'BAD')">转为不良品</el-button><el-button link type="danger" @click="openChange(row, 'SCRAP')">转为报废</el-button></template><template v-if="row.zone === 'BAD' && has('inspection:create')"><el-button link type="success" @click="openChange(row, 'GOOD')">转为良品</el-button><el-button link type="danger" @click="openChange(row, 'SCRAP')">转为报废</el-button></template><el-button v-if="row.zone === 'GOOD' && has('coding:delete')" link type="danger" @click="undoCoding(row)">撤销抄码</el-button><span v-if="row.zone === 'SCRAP'" class="muted">已报废</span></template></template></el-table-column>
      </el-table>
      <div v-if="rows.length" v-loading="loading" class="mobile-quality-list">
        <article v-for="row in rows" :key="row.id" class="quality-record">
          <div class="quality-record-heading">
            <div><span>瓶身编号</span><strong class="numeric">{{ row.body_code }}</strong></div>
            <StatusTag :status="row.zone" />
          </div>
          <dl class="quality-record-details">
            <div><dt>抄码日期</dt><dd>{{ row.coding_date }}</dd></div>
            <div><dt>生产日期</dt><dd>{{ row.manufacture_date || '-' }}</dd></div>
            <div><dt>供瓶单位</dt><dd>{{ sourceName(row.source_id) }}</dd></div>
            <div><dt>瓶子规格</dt><dd>{{ specName(row.spec_id) }}</dd></div>
            <div><dt>抄码人员</dt><dd>{{ row.coded_by_name }}</dd></div>
            <div><dt>检验单</dt><dd><el-tag v-if="row.inspection_document_status === 'INSPECTED'" type="success" size="small">已检验</el-tag><span v-else>未生成</span></dd></div>
            <div v-if="zone === 'BAD'"><dt>退还客户</dt><dd>{{ row.returned_to_customer === true ? '是' : row.returned_to_customer === false ? '否' : '未标记' }}</dd></div>
            <div v-if="row.inspection_note" class="record-note"><dt>状态备注</dt><dd>{{ row.inspection_note }}</dd></div>
          </dl>
          <div class="mobile-record-actions">
            <span v-if="row.inspection_document_status === 'INSPECTED' && row.zone !== 'SCRAP'" class="muted">检验资料已锁定</span>
            <template v-else-if="row.zone !== 'SCRAP'">
              <el-button v-if="row.zone === 'GOOD' && has('inspection:create')" plain type="danger" @click="openChange(row, 'BAD')">转为不良品</el-button>
              <el-button v-if="row.zone === 'GOOD' && has('inspection:create')" plain type="danger" @click="openChange(row, 'SCRAP')">转为报废</el-button>
              <template v-if="row.zone === 'BAD' && has('inspection:create')">
                <el-button plain type="success" @click="openChange(row, 'GOOD')">转为良品</el-button>
                <el-button plain type="danger" @click="openChange(row, 'SCRAP')">转为报废</el-button>
              </template>
              <el-button v-if="row.zone === 'GOOD' && row.inspection_document_status !== 'INSPECTED' && has('coding:delete')" plain type="danger" @click="undoCoding(row)">撤销抄码</el-button>
            </template>
            <span v-else class="muted">已报废</span>
          </div>
        </article>
      </div>
      <EmptyState v-else :title="loading ? '正在加载' : `当前${zone === 'GOOD' ? '良品库' : zone === 'BAD' ? '不良品库' : '报废库'}没有记录`" />
      <TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>
    <el-dialog v-model="dialog" :title="`转为${targetName()}`" width="520px"><div v-if="selected" class="change-summary"><strong class="numeric">{{ selected.body_code }}</strong><StatusTag :status="selected.zone" /></div><el-form label-position="top"><el-form-item v-if="form.zone === 'BAD'" label="是否退还客户"><el-radio-group v-model="form.returned_to_customer"><el-radio :value="false">否</el-radio><el-radio :value="true">是</el-radio></el-radio-group><div class="return-help">仅记录标识，不办理出库或扣减库存。</div></el-form-item><el-form-item label="状态备注"><el-input v-model="form.note" type="textarea" :rows="3" placeholder="选填，记录本次状态调整原因" /></el-form-item><el-alert :title="form.zone === 'SCRAP' ? '确认后该钢瓶将退出不良品库，对应规格的报废库存增加 1。' : `确认后该钢瓶将进入${targetName()}库。`" type="warning" :closable="false" /></el-form><template #footer><el-button @click="dialog = false">取消</el-button><el-button :type="form.zone === 'SCRAP' ? 'danger' : 'primary'" @click="submit">确认调整</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.quality-surface{overflow:hidden}
.inventory-filters{padding:16px 18px;border-bottom:1px solid var(--ja-line);background:#fbfbfc}
.filter-mode-row{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #eceef1}
.filter-mode-field,.filter-field{display:grid;gap:7px;min-width:0}
.filter-mode-field :deep(.el-radio-group){width:max-content}
.filter-label{color:#565b64;font-size:12px;font-weight:600;line-height:1.35}
.filter-total{padding-bottom:7px;color:var(--ja-muted);font-size:12px;white-space:nowrap}
.filter-total strong{color:var(--ja-text);font-size:14px;font-variant-numeric:tabular-nums}
.filter-grid{display:grid;grid-template-columns:minmax(260px,320px) minmax(240px,1fr) auto;gap:12px;align-items:end}
.filter-grid.has-returned-filter{grid-template-columns:minmax(260px,320px) minmax(150px,200px) minmax(220px,1fr) auto}
.filter-grid :deep(.el-date-editor),.filter-grid :deep(.el-select),.filter-grid :deep(.el-input){width:100%;min-width:0}
.filter-grid :deep(.el-input__wrapper),.filter-grid :deep(.el-select__wrapper),.filter-grid :deep(.el-date-editor){min-height:38px}
.filter-actions{display:flex;align-items:center;gap:8px}
.filter-actions :deep(.el-button){min-width:76px;min-height:38px;margin-left:0;white-space:nowrap}
.return-summary{margin:14px 18px;padding:10px 12px;color:#606266;background:#f6f7f8;border-radius:var(--ja-control-radius);font-size:12px;line-height:1.6}
.return-help{width:100%;font-size:12px;color:#909399}
.change-summary{display:flex;justify-content:space-between;padding:12px 14px;margin-bottom:14px;background:#f6f7f8;border-radius:var(--ja-radius)}
.mobile-quality-list{display:none}
@media(max-width:1100px){
  .filter-grid,.filter-grid.has-returned-filter{grid-template-columns:repeat(2,minmax(0,1fr))}
  .filter-actions{justify-content:flex-end}
}
@media(max-width:760px){
  .desktop-quality-table{display:none}
  .mobile-quality-list{display:grid;padding:0 14px 14px;background:#f6f7f8}
  .quality-record{overflow:hidden;margin-top:12px;background:#fff;border:1px solid var(--ja-line);border-radius:var(--ja-control-radius);box-shadow:0 1px 3px rgba(19,23,31,.04)}
  .quality-record-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:14px;border-bottom:1px solid var(--ja-line)}
  .quality-record-heading>div{display:grid;gap:4px;min-width:0}
  .quality-record-heading span,.quality-record-details dt{color:var(--ja-muted);font-size:11px}
  .quality-record-heading strong{overflow-wrap:anywhere;color:var(--ja-ink);font-size:15px}
  .quality-record-details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 16px;margin:0;padding:14px}
  .quality-record-details>div{min-width:0}
  .quality-record-details dt{margin-bottom:3px}
  .quality-record-details dd{margin:0;overflow-wrap:anywhere;color:var(--ja-text);font-size:13px}
  .quality-record-details .record-note{grid-column:1/-1}
  .mobile-record-actions{display:flex;gap:8px;padding:12px 14px;border-top:1px solid var(--ja-line)}
  .mobile-record-actions :deep(.el-button){flex:1;min-height:38px;margin:0}
  .mobile-record-actions>.muted{padding:5px 0;font-size:12px}
}
@media(max-width:620px){
  .inventory-filters{padding:14px}
  .filter-mode-row{align-items:stretch;flex-direction:column;margin-bottom:14px;padding-bottom:14px}
  .filter-mode-field :deep(.el-radio-group){display:grid;grid-template-columns:1fr 1fr;width:100%}
  .filter-mode-field :deep(.el-radio-button),.filter-mode-field :deep(.el-radio-button__inner){width:100%}
  .filter-mode-field :deep(.el-radio-button__inner){display:flex;align-items:center;justify-content:center;min-height:40px}
  .filter-total{align-self:flex-end;padding:0}
  .filter-grid,.filter-grid.has-returned-filter{grid-template-columns:1fr;gap:13px}
  .filter-grid :deep(.el-input__wrapper),.filter-grid :deep(.el-select__wrapper),.filter-grid :deep(.el-date-editor){min-height:44px}
  .filter-actions{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);width:100%;padding-top:2px}
  .filter-actions :deep(.el-button){width:100%;min-height:44px}
  .return-summary{margin:12px 14px}
}
</style>
