<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { auth, has } from '../auth'
import type { BottleManufacturer, BottleSource, BottleSpec, QuickConfig } from '../types'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import ReportActions from '../components/ReportActions.vue'

const loading = ref(false)
const router = useRouter()
const saving = ref(false)
const bodyInput = ref()
const sources = ref<BottleSource[]>([])
const specs = ref<BottleSpec[]>([])
const manufacturers = ref<BottleManufacturer[]>([])
const prefixes = ref<QuickConfig[]>([])
const notes = ref<QuickConfig[]>([])
const datePresets = ref<QuickConfig[]>([])
const dailySummary = ref<any>({ total: 0, items: [] })
const recent = ref<any[]>([])
const selectedSourceId = ref<number | null>(null)
const form = reactive<any>({ spec_id: undefined, body_code: '', manufacture_date: '', note: '', manufacturer: '' })
const bodyCodeTooLong = computed(() => form.body_code.trim().length > 13)
const manufactureDateMissing = computed(() => manufactureDatePayload() === null)
watch(() => form.body_code, (value) => {
  const normalized = value.toUpperCase().replace(/\s+/g, '').replace(/[^0-9A-Z]/g, '')
  if (normalized !== value) form.body_code = normalized
})
watch(() => form.body_code, (value) => {
  // 瓶身编号清空时重置厂家；有编号时按前缀自动匹配（一个厂家可配多个逗号分隔前缀，长前缀优先），未匹配到则保留当前选择供手动调整。
  if (!value) { form.manufacturer = ''; return }
  const code = value.toUpperCase()
  const matched = manufacturers.value
    .filter((item) => item.is_active && item.code_prefix)
    .flatMap((item) => item.code_prefix.split(/[,，;；\s]+/).map((prefix) => ({ item, prefix: prefix.trim() })))
    .filter((entry) => entry.prefix && code.startsWith(entry.prefix.toUpperCase()))
    .sort((a, b) => b.prefix.length - a.prefix.length)[0]
  if (matched) form.manufacturer = matched.item.name
})
watch(() => form.manufacture_date, (value) => {
  const cleaned = value.replace(/[^0-9.]/g, '')
  const digits = cleaned.replace(/\D/g, '')
  const normalized = digits.length >= 6 ? `${digits.slice(0, 4)}.${digits.slice(4, 6)}` : cleaned
  if (normalized !== value) form.manufacture_date = normalized
})
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const availableSources = computed(() => sources.value.filter((item) => item.is_active).sort((a, b) => a.sort_order - b.sort_order))
const availableSpecs = computed(() => specs.value.filter((item) => item.is_active).sort((a, b) => a.sort_order - b.sort_order))
const selectedSourceName = computed(() => sources.value.find((item) => item.id === selectedSourceId.value)?.name || '未选择')
const ready = computed(() => Boolean(form.body_code.trim() && selectedSourceId.value && form.spec_id))
const reportLines = computed(() => [
  `日期：${today}`,
  `员工：${auth.user?.name || '-'}`,
  ...dailySummary.value.items.map((item: any) => `客户：${item.customer_name || selectedSourceName.value}，钢瓶规格：${item.spec_name}，抄码数量：${item.quantity} 只`),
  `当日抄码总量：${dailySummary.value.total} 只`,
])

async function load() {
  loading.value = true
  try {
    const [options, summaryData] = await Promise.all([api.get('/options'), api.get('/coding/summary', { params: { date_from: today, date_to: today, coded_by: auth.user?.id } })])
    sources.value = options.data.sources; specs.value = options.data.specs; manufacturers.value = options.data.manufacturers || []
    prefixes.value = options.data.code_prefixes; notes.value = options.data.inspection_notes; datePresets.value = options.data.date_presets; dailySummary.value = summaryData.data
    if (!availableSources.value.some((item) => item.id === selectedSourceId.value)) selectedSourceId.value = availableSources.value.find((item) => item.is_default)?.id ?? availableSources.value[0]?.id ?? null
    chooseDefaultSpec()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function chooseDefaultSpec() {
  const preferred = availableSpecs.value.find((item) => item.is_default)?.id
  if (!availableSpecs.value.some((item) => item.id === form.spec_id)) form.spec_id = preferred || availableSpecs.value[0]?.id
}
function changeSource(sourceId: number) { selectedSourceId.value = sourceId }
function focusBodyCode() { bodyInput.value?.focus(); bodyInput.value?.select() }
function selectBodyCodeOnFocus() {
  window.setTimeout(() => {
    const input = bodyInput.value?.input as HTMLInputElement | undefined
    if (input && document.activeElement === input) input.select()
  }, 0)
}
function insertPrefix(value: string) { form.body_code = value; nextTick(focusBodyCode) }
function insertNote(value: string) { form.note = value }
function insertDate(value: string) { form.manufacture_date = value }
function openInspectionDocument() { router.push({ path: '/inspection-documents', query: { date: today, generate: '1' } }) }
function manufactureDatePayload() {
  const digits = form.manufacture_date.replace(/\D/g, '')
  // 后端按完整日期存储，年月 6 位数字齐全时补 1 日提交，否则视为未填写。
  return digits.length >= 6 ? `${digits.slice(0, 4)}-${digits.slice(4, 6)}-01` : null
}
async function submit() {
  if (saving.value) return
  if (!ready.value) return ElMessage.warning('请选择供瓶单位、规格并填写瓶身编号')
  saving.value = true
  const code = form.body_code.trim()
  try {
    const { data } = await api.post('/quick-entry', { source_id: selectedSourceId.value, spec_id: form.spec_id, body_code: code, manufacture_date: manufactureDatePayload(), note: form.note.trim() || null, manufacturer: form.manufacturer || null })
    recent.value.unshift({ ...data, source_name: sources.value.find((x) => x.id === data.source_id)?.name, spec_name: specs.value.find((x) => x.id === data.spec_id)?.name })
    recent.value = recent.value.slice(0, 8)
    form.body_code = ''; form.manufacture_date = ''; form.note = ''; form.manufacturer = ''
    ElMessage.success(`今日序号 ${data.coding_sequence}，已进入良品库`)
    await load(); await nextTick(); focusBodyCode()
  } catch (err) { ElMessage.error(errorMessage(err)); await nextTick(); focusBodyCode() } finally { saving.value = false }
}
async function undoCoding(row: any) {
  try {
    await ElMessageBox.confirm(`确认撤销瓶身编号“${row.body_code}”的抄码？撤销后将从良品库移除${row.inbound_id ? '，对应入库单待抄码余量加回 1' : ''}。`, '撤销抄码', { type: 'warning' })
    await api.delete(`/bottles/${row.id}/coding`)
    recent.value = recent.value.filter((item) => item.id !== row.id)
    ElMessage.success('抄码已撤销，可以重新录入')
    await load(); await nextTick(); focusBodyCode()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
onMounted(async () => { await load(); if (window.matchMedia('(min-width: 761px)').matches) focusBodyCode() })
</script>

<template>
  <div v-loading="loading" class="quick-entry-page">
    <section class="surface quick-form">
      <div class="quick-section" role="group" aria-label="选择供瓶单位"><div class="choice-grid"><button v-for="item in availableSources" :key="item.id" class="choice-button" :class="{ selected: selectedSourceId === item.id }" type="button" @click="changeSource(item.id)"><GameIcon name="adjustment" /><span :title="item.name">{{ item.name }}</span></button></div><div v-if="!availableSources.length" class="config-warning">请先在基础资料中启用供瓶单位。</div></div>
      <div class="quick-section quick-fields" role="group" aria-label="录入钢瓶信息"><el-form label-position="top" @submit.prevent="submit">
        <el-form-item><div class="field-with-shortcuts"><div v-if="prefixes.length" class="shortcut-row"><button v-for="item in prefixes" :key="item.id" type="button" @click="insertPrefix(item.value)">{{ item.name }} · {{ item.value }}</button></div><el-input ref="bodyInput" v-model="form.body_code" size="large" clearable autocomplete="off" aria-label="瓶身编号" aria-required="true" placeholder="输入或扫描瓶身编号" @focus="selectBodyCodeOnFocus" @keyup.enter="submit"><template #prefix><GameIcon name="qr-code" /></template></el-input><div v-if="bodyCodeTooLong" class="code-length-warning"><el-tag type="warning" effect="light">编号超过 13 位，请核对；仍可正常保存</el-tag><span>当前 {{ form.body_code.trim().length }} 位</span></div></div></el-form-item>
        <el-form-item><el-select v-model="form.manufacturer" filterable clearable aria-label="生产厂家" placeholder="生产厂家（扫描后自动匹配，可手动修改）" class="w-full"><el-option v-for="item in manufacturers" :key="item.id" :label="item.code_prefix ? `${item.name}（${item.code_prefix}）` : item.name" :value="item.name" /></el-select></el-form-item>
        <el-form-item><div class="field-with-shortcuts"><div v-if="datePresets.length" class="shortcut-row"><button v-for="item in datePresets" :key="item.id" type="button" @click="insertDate(item.value)">{{ item.value }}</button></div><el-input v-model="form.manufacture_date" size="large" clearable autocomplete="off" aria-label="生产日期" placeholder="请选择或输入生产日期，如 2022.09" /><div v-if="manufactureDateMissing" class="date-missing-warning"><el-tag type="warning" effect="light">请选择对应的生产日期</el-tag><span>未填写仍可保存，今日抄码核对会标黄提醒</span></div></div></el-form-item>
        <el-form-item v-if="notes.length"><div class="field-with-shortcuts"><div class="shortcut-row"><button v-for="item in notes" :key="item.id" type="button" @click="insertNote(item.value)">{{ item.name }}</button></div></div></el-form-item>
        <button type="submit" class="quick-submit" :disabled="!ready || saving || !has('quick_entry:create')"><GameIcon :name="saving ? 'refresh' : 'save'" /><span>{{ saving ? '正在抄码' : '抄码并继续' }}</span></button>
      </el-form></div>
      <div class="quick-section" role="group" aria-label="选择钢瓶规格"><div class="choice-label">瓶子规格</div><div class="choice-grid"><button v-for="item in availableSpecs" :key="item.id" class="choice-button" :class="{ selected: form.spec_id === item.id }" type="button" @click="form.spec_id = item.id"><GameIcon name="adjustment" /><span :title="item.name">{{ item.name }}</span></button></div><div v-if="!availableSpecs.length" class="config-warning">请先在基础资料中启用瓶子规格。</div></div>
    </section>
    <PageHeader title="快捷抄码" description="选择供瓶单位和规格后连续录入；完成抄码即默认检测通过并进入良品库。"><el-button v-if="has('inspection_documents:create')" @click="openInspectionDocument">生成检验单</el-button><ReportActions title="当日抄码汇总" :filename="`抄码汇总-${today}-${auth.user?.name || '当前员工'}`" :lines="reportLines" /></PageHeader>
    <section class="surface quick-context"><div><span>抄码日期</span><strong class="numeric">{{ today }}</strong><small>每日序号从 1 开始</small></div><div><span>当前供瓶单位</span><strong class="source-name">{{ selectedSourceName }}</strong><small>按所选单位记录</small></div><div><span>本人今日已抄码</span><strong>{{ dailySummary.total }}</strong><small>{{ auth.user?.name || '当前员工' }}当日累计</small></div></section>
    <section v-if="recent.length" class="surface recent-section"><div class="surface-header"><h2>今日最近抄码</h2><span class="muted">当前页面会话</span></div><div class="recent-list"><div v-for="item in recent" :key="item.id" class="recent-item"><span class="sequence">{{ item.coding_sequence }}</span><div><strong class="numeric">{{ item.body_code }}</strong><small>{{ item.source_name }} · {{ item.spec_name }} · 已进入良品库</small></div><el-button v-if="has('coding:delete')" link type="danger" @click="undoCoding(item)">撤销</el-button></div></div></section>
  </div>
</template>

<style scoped>
.quick-entry-page{max-width:980px;margin:0 auto}
.quick-context{display:grid;grid-template-columns:repeat(3,1fr);margin-bottom:16px}
.quick-context>div{padding:18px 20px}
.quick-context>div+div{border-left:1px solid var(--ja-line)}
.quick-context span,.quick-context small,.quick-context strong{display:block}
.quick-context span,.quick-context small{color:var(--ja-muted);font-size:11px}
.quick-context strong{margin:4px 0;font-size:24px;white-space:nowrap}
.quick-context>div:nth-child(n+2) strong{color:var(--ja-red)}
.quick-context .source-name{font-size:18px;white-space:normal;overflow-wrap:anywhere}
.quick-form{overflow:hidden;margin-bottom:20px}
.quick-section{padding:20px;border-bottom:1px solid var(--ja-line)}
.quick-section:last-child{border:0}
.choice-label{margin-bottom:10px;color:var(--ja-muted);font-size:12px;font-weight:700}
.choice-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
.choice-button{display:grid;grid-template-columns:20px minmax(0,1fr) auto;align-items:center;gap:4px;min-height:44px;padding:4px 6px;color:var(--ja-text);background:#fff;border:1px solid var(--ja-line);border-radius:var(--ja-radius);text-align:left}
.choice-button.selected{color:var(--ja-red);background:var(--ja-red-soft);border-color:var(--ja-red)}
.choice-button>span:not(.game-icon){min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.choice-button small{font-size:10px;white-space:nowrap}
.quick-fields :deep(.el-form){max-width:640px}
.quick-fields :deep(.el-form-item){margin-bottom:8px}
.quick-fields :deep(.el-form-item.is-error){margin-bottom:26px}
.field-with-shortcuts{width:100%}
.code-length-warning{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px;color:var(--ja-warning);font-size:12px}
.date-missing-warning{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:6px;color:var(--ja-warning);font-size:12px}
.shortcut-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px}
.shortcut-row button{min-height:36px;padding:2px 6px;color:var(--ja-red);background:var(--ja-red-soft);border:1px solid #f4b8bd;border-radius:8px}
.quick-submit{width:100%;height:52px;display:flex;align-items:center;justify-content:center;gap:8px;color:#fff;background:var(--ja-red);border:0;border-radius:var(--ja-radius);font-weight:700}
.quick-submit:disabled{opacity:.45}
.config-warning{color:var(--ja-warning);font-size:12px}
.recent-section{margin-top:16px}
.recent-list{padding:0 18px}
.recent-item{display:grid;grid-template-columns:34px 1fr auto;gap:10px;align-items:center;padding:12px 0;border-bottom:1px solid var(--ja-line)}
.recent-item strong,.recent-item small{display:block}
.recent-item small{color:var(--ja-muted);font-size:11px}
.sequence{width:30px;height:30px;display:grid;place-items:center;color:#fff;background:var(--ja-success);border-radius:50%;font-weight:700}
@media(max-width:760px){.quick-context{grid-template-columns:1fr}.quick-context>div+div{border-left:0;border-top:1px solid var(--ja-line)}.quick-context strong{font-size:19px}.quick-section{padding:16px 14px}.choice-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
