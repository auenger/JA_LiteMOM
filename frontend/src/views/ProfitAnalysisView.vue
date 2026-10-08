<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api, { errorMessage } from '../api'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'

const loading = ref(false)
const data = ref<any>(null)

function currentMonthRange() {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  const prefix = `${year}-${String(month).padStart(2, '0')}`
  return [`${prefix}-01`, `${prefix}-${String(new Date(year, month, 0).getDate()).padStart(2, '0')}`]
}

const dateRange = ref(currentMonthRange())
const totals = computed(() => data.value?.totals || {})
const purchase = computed(() => data.value?.purchase || {})
const materials = computed(() => data.value?.materials || {})
const scrap = computed(() => data.value?.scrap || {})
const inspection = computed(() => data.value?.inspection || {})
const money = (value: string | number | null | undefined) => `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

async function load() {
  loading.value = true
  try {
    data.value = (await api.get('/profit-analysis', { params: { date_from: dateRange.value[0], date_to: dateRange.value[1] } })).data
  } catch (err) {
    ElMessage.error(errorMessage(err))
  } finally {
    loading.value = false
  }
}

function reset() {
  dateRange.value = currentMonthRange()
  load()
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <PageHeader title="盈利成本计算" description="汇总采购、材料耗用、废料出库收入和钢瓶检测费用，默认查看当前月份。">
      <el-button @click="load"><GameIcon name="refresh" />刷新</el-button>
    </PageHeader>

    <section class="surface analysis-filter">
      <label><span>统计日期</span><el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" :clearable="false" unlink-panels range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" /></label>
      <el-button type="primary" @click="load"><GameIcon name="search" />查询</el-button>
      <el-button @click="reset">本月</el-button>
    </section>

    <el-alert
      v-if="purchase.unpaid_count"
      :title="`当前区间有 ${purchase.unpaid_count} 张供应商采购单尚未付款，涉及 ${money(purchase.unpaid_amount)}，暂未计入采购成本。`"
      type="warning"
      :closable="false"
      show-icon
      class="mb-16"
    />

    <div class="metric-grid profit-metrics">
      <div class="metric"><span>总营收</span><strong>{{ money(totals.revenue) }}</strong><small>废料出库收入 + 良品检测营收</small></div>
      <div class="metric"><span>总成本</span><strong>{{ money(totals.cost) }}</strong><small>采购 + 净耗用，废料入库不计成本</small></div>
      <div class="metric" :class="{ loss: Number(totals.profit || 0) < 0, gain: Number(totals.profit || 0) >= 0 }"><span>区间盈利</span><strong>{{ money(totals.profit) }}</strong><small>总营收 − 总成本</small></div>
      <div class="metric"><span>未付款采购</span><strong>{{ purchase.unpaid_count || 0 }} 张</strong><small>{{ money(purchase.unpaid_amount) }}</small></div>
    </div>

    <section class="surface formula-note">
      <strong>计算方式</strong>
      <div class="formula-lines">
        <span>{{ data?.calculation?.cost }}</span>
        <span>{{ data?.calculation?.revenue }}</span>
        <span>{{ data?.calculation?.scrap }}</span>
        <span>{{ data?.calculation?.profit }}</span>
        <small>采购成本仅计入已确认且已付款的采购单；废料入库只记录库存，钢瓶检测营收仅计入已生效的良品出库。</small>
      </div>
    </section>

    <div class="summary-grid">
      <section class="surface summary-card">
        <div class="surface-header"><h2>采购成本</h2><span>{{ purchase.paid_count || 0 }} 张已付款</span></div>
        <dl><dt>已付款采购成本</dt><dd>{{ money(purchase.paid_amount) }}</dd><dt>未付款采购金额</dt><dd>{{ money(purchase.unpaid_amount) }}</dd><dt>未付款单据</dt><dd>{{ purchase.unpaid_count || 0 }} 张</dd></dl>
      </section>
      <section class="surface summary-card">
        <div class="surface-header"><h2>材料成本</h2><span>按出库与退料计算</span></div>
        <dl><dt>原材料出库成本</dt><dd>{{ money(materials.outbound_cost) }}</dd><dt>退料入库冲减</dt><dd>− {{ money(materials.return_amount) }}</dd><dt>净材料成本</dt><dd>{{ money(materials.net_cost) }}</dd></dl>
      </section>
      <section class="surface summary-card">
        <div class="surface-header"><h2>废料收益</h2><span>仅按废料出库计算</span></div>
        <dl><dt>废料入库</dt><dd>只记库存，不计成本</dd><dt>废料出库收入</dt><dd>{{ money(scrap.outbound_revenue) }}</dd><dt>废料收益</dt><dd :class="Number(scrap.profit || 0) < 0 ? 'negative' : 'positive'">{{ money(scrap.profit) }}</dd></dl>
      </section>
      <section class="surface summary-card">
        <div class="surface-header"><h2>钢瓶检测营收</h2><span>只计算良品出库</span></div>
        <dl><dt>良品出库数量</dt><dd>{{ inspection.quantity || 0 }} 只</dd><dt>检测营收</dt><dd>{{ money(inspection.revenue) }}</dd><dt>暂存/报废检测费</dt><dd>{{ money(0) }}</dd></dl>
      </section>
    </div>

    <section class="surface detail-section">
      <div class="surface-header"><h2>采购单明细</h2><span>共 {{ (purchase.items || []).length }} 张已确认采购单</span></div>
      <el-table v-if="purchase.items?.length" :data="purchase.items" stripe>
        <el-table-column prop="order_no" label="采购单号" min-width="180" />
        <el-table-column prop="order_date" label="采购日期" width="115" />
        <el-table-column prop="supplier_name" label="供应商" min-width="180" />
        <el-table-column label="付款状态" width="100"><template #default="{ row }"><el-tag :type="row.is_paid ? 'success' : 'warning'" effect="plain">{{ row.is_paid ? '已付款' : '未付款' }}</el-tag></template></el-table-column>
        <el-table-column label="采购金额" align="right"><template #default="{ row }"><strong>{{ money(row.amount) }}</strong></template></el-table-column>
      </el-table>
      <EmptyState v-else title="区间内没有已确认的采购单" />
    </section>

    <section class="surface detail-section">
      <div class="surface-header"><h2>原材料成本明细</h2><span>退料金额从对应期间材料成本中冲减</span></div>
      <el-table v-if="materials.items?.length" :data="materials.items" stripe>
        <el-table-column prop="material_name" label="原材料" min-width="180" />
        <el-table-column label="出库成本" align="right"><template #default="{ row }">{{ money(row.outbound_cost) }}</template></el-table-column>
        <el-table-column label="退料冲减" align="right"><template #default="{ row }">{{ money(row.return_amount) }}</template></el-table-column>
        <el-table-column label="净材料成本" align="right"><template #default="{ row }"><strong>{{ money(row.net_cost) }}</strong></template></el-table-column>
      </el-table>
      <EmptyState v-else title="区间内没有原材料出库或退料记录" />
    </section>

    <div class="detail-grid scrap-detail-grid">
      <section class="surface detail-section">
        <div class="surface-header"><h2>废料入库明细</h2><span>仅记录库存，不计成本</span></div>
        <el-table v-if="scrap.inbound_items?.length" :data="scrap.inbound_items" stripe>
          <el-table-column prop="material_name" label="废料" min-width="150" />
          <el-table-column label="入库数量" align="right"><template #default="{ row }">{{ row.quantity }} {{ row.unit }}</template></el-table-column>
        </el-table>
        <EmptyState v-else title="区间内没有已生效的废料入库记录" />
      </section>
      <section class="surface detail-section">
        <div class="surface-header"><h2>废料出库明细</h2><span>收入 {{ money(scrap.outbound_revenue) }}</span></div>
        <el-table v-if="scrap.outbound_items?.length" :data="scrap.outbound_items" stripe>
          <el-table-column prop="material_name" label="废料" min-width="150" />
          <el-table-column label="出库数量" align="right"><template #default="{ row }">{{ row.quantity }} {{ row.unit }}</template></el-table-column>
          <el-table-column label="销售收入" align="right"><template #default="{ row }"><strong>{{ money(row.revenue) }}</strong></template></el-table-column>
        </el-table>
        <EmptyState v-else title="区间内没有已生效的废料出库记录" />
      </section>
    </div>

    <div class="detail-grid">
      <section class="surface detail-section">
        <div class="surface-header"><h2>钢瓶检测营收明细</h2><span>良品出库 {{ inspection.quantity || 0 }} 只</span></div>
        <el-table v-if="inspection.items?.length" :data="inspection.items" stripe>
          <el-table-column prop="spec_name" label="钢瓶规格" min-width="120" />
          <el-table-column label="检测单价" align="right"><template #default="{ row }">{{ money(row.inspection_price) }}</template></el-table-column>
          <el-table-column prop="quantity" label="良品出库数量" align="right" />
          <el-table-column label="检测营收" align="right"><template #default="{ row }"><strong>{{ money(row.revenue) }}</strong></template></el-table-column>
        </el-table>
        <EmptyState v-else title="区间内没有已生效的良品出库记录" />
      </section>
      <section class="surface detail-section result-panel">
        <div class="surface-header"><h2>区间计算结果</h2><span>{{ dateRange[0] }} 至 {{ dateRange[1] }}</span></div>
        <dl><dt>总营收</dt><dd>{{ money(totals.revenue) }}</dd><dt>总成本</dt><dd>− {{ money(totals.cost) }}</dd><dt>区间盈利</dt><dd :class="Number(totals.profit || 0) < 0 ? 'negative' : 'positive'">{{ money(totals.profit) }}</dd></dl>
      </section>
    </div>
  </div>
</template>

<style scoped>
.analysis-filter { display: flex; align-items: flex-end; gap: 10px; padding: 16px 18px; margin-bottom: 16px; }
.analysis-filter label { display: grid; gap: 6px; color: var(--ja-muted); font-size: 11px; }
.analysis-filter :deep(.el-date-editor) { width: 340px; }
.profit-metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.profit-metrics .gain strong { color: #24754c; }
.profit-metrics .loss strong { color: var(--ja-red); }
.formula-note { display: flex; gap: 18px; align-items: flex-start; padding: 15px 18px; margin-bottom: 16px; border-left: 3px solid var(--ja-red); }
.formula-lines { display: grid; gap: 6px; }
.formula-lines span { color: var(--ja-text); font-size: 12px; }
.formula-lines small { color: var(--ja-muted); margin-top: 3px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); align-items: stretch; gap: 16px; margin-bottom: 16px; }
.summary-grid > .surface, .detail-grid > .surface { height: 100%; margin-top: 0; }
.summary-card .surface-header span, .detail-section .surface-header span { color: var(--ja-muted); font-size: 11px; }
.summary-card dl { display: grid; grid-template-columns: 1fr auto; gap: 12px; padding: 18px; margin: 0; }
.summary-card dt { color: var(--ja-muted); font-size: 12px; }
.summary-card dd { margin: 0; font-weight: 650; font-variant-numeric: tabular-nums; }
.positive { color: #24754c; }
.negative { color: var(--ja-red); }
.detail-section { margin-bottom: 16px; overflow: hidden; }
.detail-grid { display: grid; grid-template-columns: 1.35fr 1fr; align-items: stretch; gap: 16px; margin-bottom: 16px; }
.detail-grid .detail-section { display: flex; flex-direction: column; margin-bottom: 0; }
.scrap-detail-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.result-panel dl { display: grid; grid-template-columns: 1fr auto; gap: 16px; margin: 0; padding: 22px; }
.result-panel dd { margin: 0; font-size: 16px; font-weight: 700; }
@media (max-width: 1180px) { .summary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 1000px) { .profit-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } .detail-grid { grid-template-columns: 1fr; } }
@media (max-width: 760px) { .analysis-filter { align-items: stretch; flex-direction: column; } .analysis-filter :deep(.el-date-editor) { width: 100%; } .profit-metrics { grid-template-columns: 1fr; } .formula-note { align-items: flex-start; flex-direction: column; } }
</style>
