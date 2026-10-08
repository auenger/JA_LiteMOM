<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import PageHeader from '../components/PageHeader.vue'
import EmptyState from '../components/EmptyState.vue'

type RecordData = Record<string, any>
const code = ref('')
const loading = ref(false)
const searched = ref(false)
const saving = ref(false)
const nextZone = ref('')
const statusNote = ref('')
const result = ref<{ bottle: RecordData; inbound: RecordData | null; inspections: RecordData[]; unverified: RecordData[]; outbound: RecordData | null; correction_option: RecordData | null; corrections: RecordData[] } | null>(null)

function dateTime(value?: string | null) { return value ? new Date(`${value.replace('Z', '')}Z`).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '—' }
function value(value: unknown) { return value === null || value === undefined || value === '' ? '—' : String(value) }
const zoneNames: Record<string, string> = { PENDING: '待检', GOOD: '良品库', BAD: '不良品库', SCRAP: '报废', OUTBOUND: '已出库' }
const statusNames: Record<string, string> = { ACTIVE: '有效', VOID: '已作废', POSTED: '已生效', DRAFT: '草稿', PENDING: '待处理', RETRYING: '重检中', RESOLVED: '已处理' }
const resultNames: Record<string, string> = { GOOD: '合格', BAD: '不合格' }

async function search() {
  const bodyCode = code.value.trim()
  if (!bodyCode) return ElMessage.warning('请输入完整瓶身编号')
  loading.value = true
  searched.value = true
  result.value = null
  try {
    result.value = (await api.get('/bottles/lifecycle', { params: { body_code: bodyCode } })).data
    nextZone.value = result.value?.bottle.zone || ''
    statusNote.value = ''
  } catch (err) {
    if ((err as any)?.response?.status !== 404) ElMessage.error(errorMessage(err))
  } finally { loading.value = false }
}

async function restoreGood() {
  if (!result.value?.outbound || !result.value.correction_option) return
  const current = result.value
  const option = current.correction_option!
  const replacementText = option.anonymous_good > 0
    ? '先扣减 1 只未绑定瓶码的良品库存数量。'
    : `用最老的同供瓶单位、同规格已检验瓶 ${option.oldest_replacement_body_code} 替换出库。`
  if (!option.anonymous_good && !option.oldest_replacement_body_code) return ElMessage.warning('当前没有可用库存或符合条件的替换瓶')
  try {
    await ElMessageBox.confirm(`将 ${current.bottle.body_code} 改回良品库，原出库单数量保持不变。${replacementText}`, '确认纠正出库关联', { type: 'warning' })
  } catch { return }
  saving.value = true
  try {
    const response = await api.post('/bottles/lifecycle/restore-good', {
      body_code: current.bottle.body_code, outbound_id: current.outbound!.id,
    })
    ElMessage.success(response.data.replacement_type === 'ANONYMOUS'
      ? '已改回良品库，并扣减 1 只库存数量'
      : `已改回良品库，由 ${response.data.replacement_body_code} 替换出库`)
    await search()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { saving.value = false }
}

async function updateZone() {
  if (!result.value || nextZone.value === result.value.bottle.zone) return
  saving.value = true
  try {
    await api.put(`/bottles/${result.value.bottle.id}/status`, { zone: nextZone.value, note: statusNote.value.trim() || null })
    ElMessage.success('瓶子状态已更新')
    await search()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { saving.value = false }
}
</script>

<template>
  <div class="lifecycle-page">
    <PageHeader title="瓶子生命周期" description="按完整瓶身编号查询抄码、检验、入库和出库关联记录。" />
    <section class="surface search-card">
      <el-input v-model="code" size="large" clearable placeholder="输入完整瓶身编号，例如 003221596860" @keyup.enter="search" />
      <el-button type="primary" size="large" :loading="loading" @click="search">查询</el-button>
    </section>
    <div v-if="result" class="result">
      <el-alert v-if="result.outbound && result.bottle.coding_date && result.outbound.business_date < result.bottle.coding_date" title="出库单业务日期早于这只瓶的抄码日期" description="这是一条补录或自动分配记录，请结合实际交接单核实该瓶的实物出库日期。" type="warning" :closable="false" show-icon />
      <section class="surface section-card">
        <div class="section-heading"><div><small>瓶身编号</small><h2 class="numeric">{{ result.bottle.body_code }}</h2></div><el-tag :type="result.bottle.zone === 'OUTBOUND' ? 'warning' : 'success'">{{ zoneNames[result.bottle.zone] || result.bottle.zone }}</el-tag></div>
        <div class="detail-grid">
          <div><span>供瓶单位</span><strong>{{ value(result.bottle.source_name) }}</strong></div>
          <div><span>规格</span><strong>{{ value(result.bottle.spec_name) }}</strong></div>
          <div><span>生产日期</span><strong>{{ value(result.bottle.manufacture_date) }}</strong></div>
          <div><span>生产厂家</span><strong>{{ value(result.bottle.manufacturer) }}</strong></div>
          <div><span>工序状态</span><strong>{{ result.bottle.process_status === 'INSPECTED' ? '已检验' : '已抄码' }}</strong></div>
          <div><span>检验结果</span><strong>{{ resultNames[result.bottle.inspection_result] || value(result.bottle.inspection_result) }}</strong></div>
          <div><span>抄码日期 / 序号</span><strong>{{ value(result.bottle.coding_date) }} / {{ value(result.bottle.coding_sequence) }}</strong></div>
          <div><span>抄码人</span><strong>{{ value(result.bottle.coded_by_name) }}</strong></div>
          <div><span>抄码实际时间</span><strong>{{ dateTime(result.bottle.coded_at) }}</strong></div>
          <div><span>检验人 / 时间</span><strong>{{ value(result.bottle.inspected_by_name) }} / {{ dateTime(result.bottle.inspected_at) }}</strong></div>
          <div><span>进入良品库日期</span><strong>{{ value(result.bottle.good_entry_date) }}</strong></div>
          <div><span>原出库区域</span><strong>{{ zoneNames[result.bottle.outbound_origin_zone] || value(result.bottle.outbound_origin_zone) }}</strong></div>
          <div><span>抄码备注</span><strong>{{ value(result.bottle.coding_note) }}</strong></div>
          <div><span>检验备注</span><strong>{{ value(result.bottle.inspection_note) }}</strong></div>
          <div><span>检验价格</span><strong>{{ value(result.bottle.inspection_price) }}</strong></div>
          <div><span>系统建档 / 最近更新</span><strong>{{ dateTime(result.bottle.created_at) }} / {{ dateTime(result.bottle.updated_at) }}</strong></div>
        </div>
      </section>

      <section class="surface section-card"><h3>入库来源</h3>
        <div v-if="result.inbound" class="detail-grid"><div><span>单号</span><strong class="numeric">{{ result.inbound.document_no }}</strong></div><div><span>业务日期</span><strong>{{ result.inbound.business_date }}</strong></div><div><span>单据状态</span><strong>{{ statusNames[result.inbound.status] || result.inbound.status }}</strong></div><div><span>经办人</span><strong>{{ value(result.inbound.handler) }}</strong></div><div><span>生效时间</span><strong>{{ dateTime(result.inbound.posted_at) }}</strong></div><div><span>备注</span><strong>{{ value(result.inbound.note) }}</strong></div></div>
        <p v-else class="muted">没有关联的入库单；可能是快捷抄码或历史补录。</p>
      </section>

      <section class="surface section-card"><h3>检验单记录 <small>{{ result.inspections.length }} 条</small></h3>
        <div v-if="result.inspections.length" class="records"><div v-for="(item, index) in result.inspections" :key="index" class="record"><div class="record-title"><strong class="numeric">{{ item.document_no }}</strong><el-tag size="small" :type="item.document_status === 'ACTIVE' ? 'success' : 'info'">{{ statusNames[item.document_status] || item.document_status }}</el-tag><el-tag v-if="item.is_retry" size="small" type="warning">重检</el-tag><el-tag v-if="item.is_archived" size="small" type="info">历史归档</el-tag></div><div class="detail-grid"><div><span>检验日期</span><strong>{{ value(item.inspection_date) }}</strong></div><div><span>行号</span><strong>{{ item.sequence }}</strong></div><div><span>检验员</span><strong>{{ value(item.inspector_name) }}</strong></div><div><span>结果</span><strong>{{ resultNames[item.result] || value(item.result) }}</strong></div><div><span>下次检验日期</span><strong>{{ value(item.next_inspection_date) }}</strong></div><div><span>客户</span><strong>{{ value(item.customer_name) }}</strong></div><div><span>生产厂家 / 日期</span><strong>{{ value(item.manufacturer) }} / {{ value(item.manufacture_date) }}</strong></div><div><span>容积</span><strong>{{ value(item.volume) }}</strong></div><div><span>关联原检验行</span><strong>{{ value(item.source_line_id) }}</strong></div></div></div></div>
        <p v-else class="muted">未生成关联的检验单。</p>
        <div v-if="result.unverified.length" class="warning-note"><strong>上游驳回 / 未验证记录</strong><p v-for="(item, index) in result.unverified" :key="index">{{ item.document_no }} 第 {{ item.sequence }} 行：{{ item.error_message }}（{{ statusNames[item.status] || item.status }}）</p></div>
      </section>

      <section class="surface section-card"><h3>出库记录</h3>
        <div v-if="result.outbound" class="detail-grid"><div><span>单号</span><strong class="numeric">{{ result.outbound.document_no }}</strong></div><div><span>业务日期</span><strong>{{ result.outbound.business_date }}</strong></div><div><span>实际审批入账时间</span><strong>{{ dateTime(result.outbound.posted_at) }}</strong></div><div><span>出库对象</span><strong>{{ value(result.outbound.customer) }}</strong></div><div><span>状态</span><strong>{{ statusNames[result.outbound.status] || result.outbound.status }}</strong></div><div><span>经办人</span><strong>{{ value(result.outbound.handler) }}</strong></div><div><span>备注</span><strong>{{ value(result.outbound.note) }}</strong></div></div>
        <p v-else class="muted">没有关联的出库单。</p>
        <p class="date-note">业务日期可用于补录；实际审批入账时间反映系统处理时间。两者不同不代表该瓶在业务日期实际发出。</p>
      </section>
      <section v-if="result.bottle.zone === 'OUTBOUND' || ['GOOD', 'BAD'].includes(result.bottle.zone)" class="surface section-card"><h3>状态操作</h3>
        <template v-if="result.bottle.zone === 'OUTBOUND'">
          <p class="muted">纠正后原出库单数量不变。系统优先扣减未绑定瓶码的库存数量，数量不足时使用同供瓶单位、同规格且有有效检验单的最老瓶子替换。</p>
          <p v-if="result.correction_option" class="correction-plan">预计处理：<strong v-if="result.correction_option.anonymous_good > 0">扣减 1 只库存数量（当前可用 {{ result.correction_option.anonymous_good }} 只）</strong><strong v-else-if="result.correction_option.oldest_replacement_body_code">由 {{ result.correction_option.oldest_replacement_body_code }}（{{ result.correction_option.oldest_replacement_coding_date }} 抄码）替换出库</strong><strong v-else>没有可用库存或符合条件的替换瓶</strong></p>
          <el-button v-if="has('bottle_lifecycle:restore') && result.correction_option" type="primary" :loading="saving" :disabled="!result.correction_option.anonymous_good && !result.correction_option.oldest_replacement_body_code" @click="restoreGood">改回良品库并保持出库数量</el-button>
        </template>
        <template v-else-if="has('bottle_lifecycle:update') && !result.inspections.some((item) => item.document_status === 'ACTIVE')">
          <div class="status-form"><el-select v-model="nextZone" placeholder="选择状态"><el-option label="良品库" value="GOOD" /><el-option label="不良品库" value="BAD" /><el-option v-if="result.bottle.zone === 'BAD'" label="报废" value="SCRAP" /></el-select><el-input v-model="statusNote" placeholder="状态调整备注（选填）" /><el-button type="primary" :loading="saving" :disabled="nextZone === result.bottle.zone" @click="updateZone">保存状态</el-button></div>
        </template>
        <p v-else class="muted">此瓶已有有效检验单，质量状态需通过检验单流程处理。</p>
      </section>
      <section v-if="result.corrections.length" class="surface section-card"><h3>出库关联纠正记录</h3><div class="records"><div v-for="(item, index) in result.corrections" :key="index" class="record"><div class="record-title"><strong class="numeric">{{ item.outbound_document_no }}</strong><small>{{ dateTime(item.created_at) }} · {{ item.created_by_name }}</small></div><p>{{ item.original_body_code }} 改回良品库；{{ item.replacement_type === 'ANONYMOUS' ? '改扣 1 只未绑定瓶码库存数量' : `由 ${item.replacement_body_code} 替换出库` }}</p></div></div></section>
    </div>
    <EmptyState v-else-if="searched && !loading" title="没有找到这个瓶身编号" description="请核对完整编号，包含开头的 0。" />
  </div>
</template>

<style scoped>
.lifecycle-page{max-width:1050px;margin:0 auto}.search-card{display:flex;gap:12px;padding:18px;margin-bottom:18px}.search-card :deep(.el-input){max-width:520px}.result{display:grid;gap:16px}.section-card{padding:22px}.section-card h3{margin:0 0 16px;font-size:18px}.section-card h3 small{color:var(--ja-muted);font-size:12px;font-weight:400}.section-heading{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}.section-heading small,.detail-grid span{display:block;color:var(--ja-muted);font-size:12px;margin-bottom:5px}.section-heading h2{margin:0;font-size:25px}.detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 22px}.detail-grid strong{font-size:14px;overflow-wrap:anywhere}.records{display:grid;gap:12px}.record{border:1px solid var(--ja-line);border-radius:var(--ja-radius);padding:15px}.record-title{display:flex;gap:10px;align-items:center;margin-bottom:14px}.record-title small{color:var(--ja-muted)}.record p{margin:0}.muted,.date-note{color:var(--ja-muted);font-size:13px}.warning-note{margin-top:18px;padding:14px;border-radius:var(--ja-radius);background:#fff8e9}.warning-note p{margin:8px 0 0}.date-note{margin:20px 0 0}.correction-plan{padding:12px 14px;background:#f7f8f9;border-radius:var(--ja-radius);font-size:13px}.status-form{display:flex;gap:10px}.status-form :deep(.el-select){width:170px;flex:none}@media(max-width:680px){.search-card{padding:12px}.section-card{padding:16px}.detail-grid{grid-template-columns:1fr}.section-heading h2{font-size:20px}.status-form{flex-direction:column}.status-form :deep(.el-select){width:100%}}
</style>
