<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { auth, has } from '../auth'
import type { Bottle, BottleSource, BottleSpec } from '../types'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import TablePagination from '../components/TablePagination.vue'
import { quantityText, selectQuantity } from '../quantityInput'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const sources = ref<BottleSource[]>([])
const specs = ref<BottleSpec[]>([])
type StockType = 'good' | 'temporary' | 'scrap' | 'bad'
type AvailabilityType = StockType | 'anonymous_good' | 'verified_good' | 'anonymous_bad' | 'verified_bad' | 'selectable_bad' | 'selectable_scrap'
const availability = ref<Record<string, Record<AvailabilityType, number>>>({})
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const form = reactive<any>({ business_date: today, source_id: undefined, handler: auth.user?.name || '', note: '', lines: [] })
const total = computed(() => form.lines.reduce((sum: number, line: any) => sum + line.good_quantity + line.temporary_quantity + line.scrap_quantity + line.bad_quantity, 0))
const selectionDialog = ref(false)
const candidateLoading = ref(false)
const candidateRows = ref<Bottle[]>([])
const candidateTotal = ref(0)
const candidatePage = ref(1)
const candidatePageSize = ref(20)
const candidateDateRange = ref<[string, string] | null>(null)
const candidateCode = ref('')
const selectionContext = reactive<any>({ line: null, zone: 'BAD', selected: new Map<number, Bottle>() })

function available(specId: number, type: AvailabilityType) { return Number(availability.value[String(specId)]?.[type] || 0) }
const candidateSelectable = computed(() => selectionContext.line ? available(selectionContext.line.spec_id, selectionContext.zone === 'BAD' ? 'selectable_bad' : 'selectable_scrap') : 0)

function blankLine(item: BottleSpec) { return { spec_id: item.id, spec_name: item.name, good_quantity: 0, temporary_quantity: 0, scrap_quantity: 0, bad_quantity: 0, bad_bottle_ids: [], scrap_bottle_ids: [], bad_selection_mode: '', scrap_selection_mode: '', selected_bad_bottles: [], selected_scrap_bottles: [] } }
async function loadStock() {
  if (!form.source_id) { availability.value = {}; return }
  availability.value = (await api.get('/quick-outbound/availability', { params: { source_id: form.source_id } })).data
}
async function chooseSource(sourceId: number) {
  if (form.source_id === sourceId) return
  form.source_id = sourceId
  form.lines.forEach((line: any) => Object.assign(line, { good_quantity: 0, temporary_quantity: 0, scrap_quantity: 0, bad_quantity: 0, bad_bottle_ids: [], scrap_bottle_ids: [], bad_selection_mode: '', scrap_selection_mode: '', selected_bad_bottles: [], selected_scrap_bottles: [] }))
  try { await loadStock() } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function load() {
  loading.value = true
  try {
    const options = await api.get('/options')
    sources.value = options.data.sources
    specs.value = options.data.specs
    form.source_id = sources.value.find((item) => item.is_default)?.id || sources.value[0]?.id
    form.lines = specs.value.map(blankLine)
    await loadStock()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}

async function askBottleSelection(line: any, zone: 'BAD' | 'SCRAP') {
  const modeKey = `${zone.toLowerCase()}_selection_mode`
  if (line[modeKey] === 'SELECTED') return openBottleSelection(line, zone)
  if (line[modeKey] === 'QUANTITY' || line[modeKey] === 'PENDING') return
  try {
    await ElMessageBox.confirm(`本次${zone === 'BAD' ? '不良品' : '报废'}出库是否需要选择对应瓶子？`, '出库方式', { confirmButtonText: '选择瓶子', cancelButtonText: '仅填写数量', distinguishCancelAndClose: true, type: 'info' })
    line[modeKey] = 'PENDING'
    ElMessageBox.close()
    await nextTick()
    await new Promise((resolve) => window.setTimeout(resolve, 220))
    await openBottleSelection(line, zone)
  } catch { line[modeKey] = 'QUANTITY' }
}
async function openBottleSelection(line: any, zone: 'BAD' | 'SCRAP') {
  if (!form.source_id) return ElMessage.warning('请先选择客户 / 供瓶单位')
  selectionContext.line = line; selectionContext.zone = zone
  const bottleKey = zone === 'BAD' ? 'selected_bad_bottles' : 'selected_scrap_bottles'
  selectionContext.selected = new Map((line[bottleKey] || []).map((item: Bottle) => [item.id, item]))
  candidateDateRange.value = null; candidateCode.value = ''; candidatePage.value = 1; selectionDialog.value = true
  await loadCandidates()
}
async function loadCandidates() {
  if (!selectionContext.line) return
  candidateLoading.value = true
  try {
    const { data } = await api.get('/quick-outbound/bottle-candidates', { params: { source_id: form.source_id, spec_id: selectionContext.line.spec_id, zone: selectionContext.zone, body_code: candidateCode.value || undefined, date_from: candidateDateRange.value?.[0], date_to: candidateDateRange.value?.[1], page: candidatePage.value, page_size: candidatePageSize.value } })
    candidateRows.value = data.items; candidateTotal.value = data.total
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { candidateLoading.value = false }
}
function candidateSelected(id: number) { return selectionContext.selected.has(id) }
function toggleCandidate(row: Bottle, checked: boolean) { checked ? selectionContext.selected.set(row.id, row) : selectionContext.selected.delete(row.id) }
function confirmCandidates() {
  const line = selectionContext.line; if (!line) return
  const zone: 'BAD' | 'SCRAP' = selectionContext.zone
  const bottles = Array.from(selectionContext.selected.values()) as Bottle[]
  if (!bottles.length) return ElMessage.warning('请至少选择一只瓶子')
  const prefix = zone.toLowerCase()
  line[`${prefix}_bottle_ids`] = bottles.map((item) => item.id)
  line[`selected_${prefix}_bottles`] = bottles
  line[`${prefix}_quantity`] = bottles.length
  line[`${prefix}_selection_mode`] = 'SELECTED'
  selectionDialog.value = false
}
function resetPendingSelection() {
  const line = selectionContext.line
  if (!line) return
  const modeKey = `${selectionContext.zone.toLowerCase()}_selection_mode`
  if (line[modeKey] === 'PENDING') line[modeKey] = ''
}
function clearBottleSelection(line: any, zone: 'BAD' | 'SCRAP') {
  const prefix = zone.toLowerCase(); line[`${prefix}_bottle_ids`] = []; line[`selected_${prefix}_bottles`] = []; line[`${prefix}_quantity`] = 0; line[`${prefix}_selection_mode`] = ''
  nextTick(() => askBottleSelection(line, zone))
}

async function submit() {
  const selectedLines = form.lines.filter((line: any) => line.good_quantity + line.temporary_quantity + line.scrap_quantity + line.bad_quantity > 0)
  if (!form.business_date || !form.source_id || !selectedLines.length) return ElMessage.warning('请选择出库日期、客户并填写至少一项出库数量')
  const stockLabels: Record<StockType, string> = { good: '良品', temporary: '暂存', scrap: '报废', bad: '不良品' }
  for (const line of selectedLines) {
    for (const type of Object.keys(stockLabels) as StockType[]) {
      const quantity = line[`${type}_quantity`]
      if (quantity > available(line.spec_id, type)) return ElMessage.warning(`${line.spec_name} ${stockLabels[type]}库存不足，当前可用 ${available(line.spec_id, type)} 只`)
    }
  }
  saving.value = true
  try {
    await api.post('/quick-outbound', { ...form, lines: selectedLines })
    ElMessage.success(`快速出库成功，共 ${total.value} 只`)
    form.note = ''
    form.lines = specs.value.map(blankLine)
    await loadStock()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { saving.value = false }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="quick-outbound-page">
    <PageHeader title="快速出库" description="库存按客户独立展示；不良品和报废可选择具体瓶子，也可仅按数量扣减。"><el-button v-if="has('quick_inbound:view')" @click="router.push('/quick-inbound')"><GameIcon name="user-add" />去快速入库</el-button></PageHeader>
    <section class="surface context-card"><div><label for="quick-outbound-date">出库日期</label><el-date-picker id="quick-outbound-date" v-model="form.business_date" type="date" value-format="YYYY-MM-DD" :clearable="false" placeholder="选择出库日期" /></div><div><span>本次总量</span><strong>{{ total }}</strong></div></section>
    <section class="surface quick-outbound-form">
      <div class="quick-block"><label>客户 / 供瓶单位</label><div class="choice-grid"><button v-for="item in sources" :key="item.id" class="choice" :class="{ selected: form.source_id === item.id }" @click="chooseSource(item.id)"><GameIcon name="user-group" /><strong>{{ item.name }}</strong><small v-if="item.is_default">默认</small></button></div></div>
      <div class="quick-block"><div class="block-title"><strong>按规格填写出库数量</strong><small>以下均为当前客户的可用库存</small></div><div v-if="specs.length" class="spec-lines" @focusin="selectQuantity"><div v-for="line in form.lines" :key="line.spec_id" class="spec-line"><strong>{{ line.spec_name }}</strong><label>良品 <small>可用 {{ available(line.spec_id, 'good') }}（数量 {{ available(line.spec_id, 'anonymous_good') }} + 有检验单 {{ available(line.spec_id, 'verified_good') }}）</small><el-input-number v-model="line.good_quantity" :min="0" :max="available(line.spec_id, 'good')" :precision="0" :controls="false" :formatter="quantityText" inputmode="numeric" :disabled="available(line.spec_id, 'good') <= 0" /></label><label>暂存 <small>可用 {{ available(line.spec_id, 'temporary') }}</small><el-input-number v-model="line.temporary_quantity" :min="0" :max="available(line.spec_id, 'temporary')" :precision="0" :controls="false" :formatter="quantityText" inputmode="numeric" :disabled="available(line.spec_id, 'temporary') <= 0" /></label><label>报废 <small>可用 {{ available(line.spec_id, 'scrap') }}</small><el-input-number v-model="line.scrap_quantity" :min="0" :max="available(line.spec_id, 'scrap')" :precision="0" :controls="false" :formatter="quantityText" inputmode="numeric" :disabled="available(line.spec_id, 'scrap') <= 0 || line.scrap_selection_mode === 'SELECTED'" @focus="askBottleSelection(line, 'SCRAP')" /><button v-if="line.scrap_selection_mode === 'SELECTED'" type="button" class="selection-link" @click="openBottleSelection(line, 'SCRAP')">已选 {{ line.scrap_bottle_ids.length }} 只，修改</button><button v-else-if="line.scrap_selection_mode === 'QUANTITY'" type="button" class="selection-link" @click="clearBottleSelection(line, 'SCRAP')">改为选择瓶子</button></label><label>不良品 <small>可用 {{ available(line.spec_id, 'bad') }}</small><el-input-number v-model="line.bad_quantity" :min="0" :max="available(line.spec_id, 'bad')" :precision="0" :controls="false" :formatter="quantityText" inputmode="numeric" :disabled="available(line.spec_id, 'bad') <= 0 || line.bad_selection_mode === 'SELECTED'" @focus="askBottleSelection(line, 'BAD')" /><button v-if="line.bad_selection_mode === 'SELECTED'" type="button" class="selection-link" @click="openBottleSelection(line, 'BAD')">已选 {{ line.bad_bottle_ids.length }} 只，修改</button><button v-else-if="line.bad_selection_mode === 'QUANTITY'" type="button" class="selection-link" @click="clearBottleSelection(line, 'BAD')">改为选择瓶子</button></label></div></div><EmptyState v-else title="请先配置钢瓶规格" /></div>
      <div class="quick-block"><label>备注（选填）</label><el-input v-model="form.note" maxlength="200" show-word-limit placeholder="本次出库的补充说明" /></div>
      <button class="quick-action" :disabled="saving || !has('quick_outbound:create') || total <= 0" @click="submit"><GameIcon :name="saving ? 'refresh' : 'door'" /><span>{{ saving ? '正在出库' : '确认快速出库' }}</span></button>
    </section>
    <el-dialog v-model="selectionDialog" :title="`选择${selectionContext.zone === 'BAD' ? '不良品' : '报废'}瓶子 · ${selectionContext.line?.spec_name || ''}`" width="860px" destroy-on-close @closed="resetPendingSelection">
      <div class="candidate-context"><div>当前客户：<strong>{{ sources.find(item => item.id === form.source_id)?.name }}</strong><small>{{ selectionContext.zone === 'BAD' ? '不良品库' : '报废库' }} · 库存 {{ available(selectionContext.line?.spec_id, selectionContext.zone === 'BAD' ? 'bad' : 'scrap') }} 只，其中有编号可选 {{ candidateSelectable }} 只</small></div><span>已选择 {{ selectionContext.selected.size }} 只</span></div>
      <div class="candidate-filters"><el-date-picker v-model="candidateDateRange" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="抄码开始日期" end-placeholder="抄码结束日期" clearable /><el-input v-model="candidateCode" clearable placeholder="输入瓶身编号快捷搜索" @keyup.enter="candidatePage = 1; loadCandidates()" /><el-button type="primary" @click="candidatePage = 1; loadCandidates()">查询</el-button></div>
      <el-table v-loading="candidateLoading" :data="candidateRows" row-key="id" stripe><el-table-column label="选择" width="70"><template #default="{ row }"><el-checkbox :model-value="candidateSelected(row.id)" @change="toggleCandidate(row, Boolean($event))" /></template></el-table-column><el-table-column prop="body_code" label="瓶身编号" min-width="180"><template #default="{ row }"><strong class="numeric">{{ row.body_code }}</strong></template></el-table-column><el-table-column prop="coding_date" label="抄码日期" width="120" /><el-table-column prop="manufacture_date" label="生产日期" width="120"><template #default="{ row }">{{ row.manufacture_date || '-' }}</template></el-table-column><el-table-column prop="inspection_note" label="状态备注" min-width="180"><template #default="{ row }">{{ row.inspection_note || '-' }}</template></el-table-column></el-table>
      <EmptyState v-if="!candidateLoading && !candidateRows.length" title="没有可选择的有编号瓶子" description="该仓库的剩余库存没有可关联的瓶身编号，可返回选择“仅填写数量”出库。" />
      <TablePagination :page="candidatePage" :page-size="candidatePageSize" :total="candidateTotal" @change="(p, s) => { candidatePage = p; candidatePageSize = s; loadCandidates() }" />
      <template #footer><el-button @click="selectionDialog = false">取消</el-button><el-button type="primary" @click="confirmCandidates">确认选择（{{ selectionContext.selected.size }}）</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.candidate-context small{display:block;margin-top:4px;color:var(--ja-muted)}
.quick-outbound-page{max-width:900px;margin:0 auto}.context-card{display:grid;grid-template-columns:1fr 1fr;margin-bottom:16px}.context-card>div{padding:17px 20px}.context-card>div+div{border-left:1px solid var(--ja-line)}.context-card label,.context-card span,.context-card strong{display:block}.context-card label,.context-card span{margin-bottom:6px;color:var(--ja-muted);font-size:11px}.context-card strong{margin-top:4px;font-size:23px}.context-card :deep(.el-date-editor){width:180px}.quick-outbound-form{padding:20px}.quick-block{margin-bottom:22px}.quick-block>label,.block-title strong{display:block;margin-bottom:10px;font-weight:700}.block-title{display:flex;justify-content:space-between}.block-title small{color:var(--ja-muted)}.choice-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.choice{display:grid;grid-template-columns:24px 1fr auto;align-items:center;gap:8px;padding:13px;color:var(--ja-text);background:#fff;border:1px solid var(--ja-line);border-radius:var(--ja-radius);text-align:left}.choice.selected{color:var(--ja-red);background:var(--ja-red-soft);border-color:var(--ja-red)}.spec-lines{display:grid;gap:10px}.spec-line{display:grid;grid-template-columns:minmax(110px,1fr) repeat(4,minmax(90px,130px));gap:10px;align-items:end;padding:13px;background:#f7f8f9;border-radius:var(--ja-radius)}.spec-line label{color:var(--ja-muted);font-size:11px}.spec-line label small{display:inline;color:var(--ja-muted);font-size:11px}.spec-line :deep(.el-input-number){width:100%;margin-top:5px}.selection-link{display:block;margin-top:5px;padding:0;color:var(--el-color-primary);background:none;border:0;font-size:11px;cursor:pointer}.candidate-context{display:flex;justify-content:space-between;margin-bottom:12px;padding:10px 12px;background:#f6f7f8;border-radius:8px}.candidate-context strong{display:inline}.candidate-context span{color:var(--ja-red)}.candidate-filters{display:grid;grid-template-columns:320px 1fr auto;gap:10px;margin-bottom:12px}.candidate-filters :deep(.el-date-editor){width:100%}.quick-action{width:100%;height:52px;display:flex;justify-content:center;align-items:center;gap:8px;color:#fff;background:var(--ja-red);border:0;border-radius:var(--ja-radius);font-weight:700}.quick-action:disabled{opacity:.45}@media(max-width:760px){.quick-outbound-form{padding:14px}.choice-grid{grid-template-columns:repeat(2,1fr)}.spec-line{grid-template-columns:1fr 1fr}.spec-line>strong{grid-column:1/-1}.block-title{display:block}.block-title small{display:block;margin-top:-5px;margin-bottom:10px}.candidate-filters{grid-template-columns:1fr}.candidate-context{display:block}.candidate-context span{margin-top:6px}}
</style>
