<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusTag from '../components/StatusTag.vue'

const router = useRouter()
const loading = ref(true)
const error = ref('')
const data = ref<any>(null)
const today = () => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
}
const currentMonth = () => today().slice(0, 7)
const currentYear = () => today().slice(0, 4)
const dailyRange = ref([today(), today()])
const monthlyRange = ref([currentMonth(), currentMonth()])
const yearlyRange = ref([currentYear(), currentYear()])
const zones = computed(() => data.value?.zones || {})
const daily = computed(() => data.value?.daily_summary || {})
const monthly = computed(() => data.value?.monthly_summary || {})
const yearly = computed(() => data.value?.yearly_summary || {})
const formatQuantity = (value: string | number | null | undefined) => Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const monthFirstDay = (value: string) => `${value}-01`
function monthLastDay(value: string) {
  const [year, month] = value.split('-').map(Number)
  return `${value}-${String(new Date(year, month, 0).getDate()).padStart(2, '0')}`
}
const rangeLabel = (range: string[], suffix = '') => range[0] === range[1] ? `${range[0]}${suffix}` : `${range[0]} 至 ${range[1]}${suffix}`

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = (await api.get('/dashboard', { params: {
      daily_from: dailyRange.value[0], daily_to: dailyRange.value[1],
      monthly_from: monthFirstDay(monthlyRange.value[0]), monthly_to: monthLastDay(monthlyRange.value[1]),
      yearly_from: `${yearlyRange.value[0]}-01-01`, yearly_to: `${yearlyRange.value[1]}-12-31`,
    } })).data
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading">
    <PageHeader title="工作台" description="查看钢瓶实时状态和指定日期的入库、出库及检测汇总。">
      <el-button v-if="has('quick_inbound:view')" @click="router.push('/quick-inbound')"><GameIcon name="user-add" />快速入库</el-button>
      <el-button v-if="has('quick_outbound:view')" @click="router.push('/quick-outbound')"><GameIcon name="door" />快速出库</el-button>
      <el-button v-if="has('quick_entry:view')" type="primary" @click="router.push('/quick-coding')"><GameIcon name="qr-code" />快捷抄码</el-button>
    </PageHeader>
    <el-alert v-if="error" :title="error" type="error" :closable="false" class="mb-16" />

    <div class="metric-grid dashboard-metrics">
      <div class="metric"><span>当日入库（{{ data?.target_date || today() }}）</span><strong>{{ data?.today_inbound_total || 0 }}</strong><small>{{ data?.today_batch_count || 0 }} 个有效批次</small></div>
      <div class="metric"><span>待检测区</span><strong>{{ zones.pending || 0 }}</strong><small>含待抄码和已抄码</small></div>
      <div class="metric"><span>暂存区</span><strong>{{ zones.temporary || 0 }}</strong><small>暂存钢瓶数量</small></div>
      <div class="metric"><span>报废区</span><strong>{{ zones.scrap || 0 }}</strong><small>报废钢瓶数量</small></div>
      <div class="metric"><span>良品区</span><strong>{{ zones.good || 0 }}</strong><small>仅由检测转入</small></div>
      <div class="metric"><span>不良品区</span><strong>{{ zones.bad || 0 }}</strong><small>仅由检测转入</small></div>
    </div>

    <section class="surface business-summary-panel">
        <div class="surface-header daily-header"><div><h2>钢瓶业务汇总</h2><span>日、月、年分别选择统计区间</span></div></div>
        <div class="period-grid">
          <article class="period-card"><header><strong>每日汇总</strong><el-date-picker v-model="dailyRange" type="daterange" value-format="YYYY-MM-DD" :clearable="false" unlink-panels range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" @change="load" /></header><span class="period-range">{{ rangeLabel(dailyRange) }}</span><div class="period-values"><div><span>总入库</span><b>{{ daily.inbound || 0 }}</b></div><div><span>总出库</span><b>{{ daily.outbound || 0 }}</b></div><div><span>已检</span><b>{{ daily.inspected || 0 }}</b></div><div><span>未检</span><b>{{ daily.uninspected || 0 }}</b></div><div><span>暂存</span><b>{{ daily.temporary || 0 }}</b></div><div><span>报废</span><b>{{ daily.scrap || 0 }}</b></div></div><small>共 {{ daily.batch_count || 0 }} 个有效入库批次</small></article>
          <article class="period-card"><header><strong>月度汇总</strong><el-date-picker v-model="monthlyRange" type="monthrange" value-format="YYYY-MM" format="YYYY年MM月" :clearable="false" unlink-panels range-separator="至" start-placeholder="开始月份" end-placeholder="结束月份" @change="load" /></header><span class="period-range">{{ rangeLabel(monthlyRange) }}</span><div class="period-values"><div><span>总入库</span><b>{{ monthly.inbound || 0 }}</b></div><div><span>总出库</span><b>{{ monthly.outbound || 0 }}</b></div><div><span>已检</span><b>{{ monthly.inspected || 0 }}</b></div><div><span>未检</span><b>{{ monthly.uninspected || 0 }}</b></div><div><span>暂存</span><b>{{ monthly.temporary || 0 }}</b></div><div><span>报废</span><b>{{ monthly.scrap || 0 }}</b></div></div><small>共 {{ monthly.batch_count || 0 }} 个有效入库批次</small></article>
          <article class="period-card"><header><strong>年度汇总</strong><el-date-picker v-model="yearlyRange" type="yearrange" value-format="YYYY" format="YYYY年" :clearable="false" unlink-panels range-separator="至" start-placeholder="开始年份" end-placeholder="结束年份" @change="load" /></header><span class="period-range">{{ rangeLabel(yearlyRange, ' 年') }}</span><div class="period-values"><div><span>总入库</span><b>{{ yearly.inbound || 0 }}</b></div><div><span>总出库</span><b>{{ yearly.outbound || 0 }}</b></div><div><span>已检</span><b>{{ yearly.inspected || 0 }}</b></div><div><span>未检</span><b>{{ yearly.uninspected || 0 }}</b></div><div><span>暂存</span><b>{{ yearly.temporary || 0 }}</b></div><div><span>报废</span><b>{{ yearly.scrap || 0 }}</b></div></div><small>共 {{ yearly.batch_count || 0 }} 个有效入库批次</small></article>
        </div>
    </section>

    <div class="content-grid single-column">
      <section class="surface">
        <div class="surface-header"><h2>原材料安全预警</h2><GameIcon class="danger-text" name="exclamation" /></div>
        <div v-if="data?.low_materials?.length" class="warning-list">
          <div v-for="item in data.low_materials" :key="item.id" class="warning-row">
            <div><strong>{{ item.name }}</strong><span>{{ item.specification || '未填写规格' }}</span></div>
            <div class="warning-stock"><span>{{ formatQuantity(item.conversion_enabled ? item.converted_stock : item.stock) }} {{ item.conversion_enabled ? item.stock_unit : item.material_unit }}</span><StatusTag status="LOW" /></div>
          </div>
        </div>
        <EmptyState v-else title="库存状态正常" description="当前没有低于安全阈值的原材料。" />
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard-metrics { grid-template-columns: repeat(6, minmax(0, 1fr)); }
.business-summary-panel { margin-bottom: 16px; }
.daily-header > div:first-child span { display: block; color: var(--ja-muted); font-size: 11px; margin-top: 3px; }
.period-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; padding: 18px; }
.period-card { padding: 15px; border: 1px solid var(--ja-line); border-radius: var(--ja-radius); background: #f8fafb; }
.period-card header { display: grid; gap: 8px; margin-bottom: 6px; }
.period-card header :deep(.el-date-editor) { width: 100%; }
.period-card header span,.period-card > small { color: var(--ja-muted); font-size: 11px; }
.period-range { display: block; min-height: 17px; margin-bottom: 9px; color: var(--ja-muted); font-size: 11px; }
.period-values { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
.period-values > div { padding: 10px; background: #fff; border-radius: 7px; }
.period-values span { display: block; color: var(--ja-muted); font-size: 11px; }
.period-values b { display: block; margin-top: 4px; font-size: 21px; }
.single-column { grid-template-columns: 1fr; }
.warning-list { padding: 4px 18px; }
.warning-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--ja-line); }
.warning-row:last-child { border-bottom: 0; }
.warning-row strong, .warning-row span { display: block; }
.warning-row span { color: var(--ja-muted); font-size: 11px; margin-top: 3px; }
.warning-stock { text-align: right; }
.warning-stock > span { color: var(--ja-text); font-family: monospace; margin-bottom: 4px; }
@media (max-width: 1100px) { .dashboard-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); } .dashboard-metrics .metric:nth-child(3) { border-right: 0; } }
@media (max-width: 900px) { .period-grid { grid-template-columns: 1fr; } }
@media (max-width: 760px) { .dashboard-metrics { grid-template-columns: 1fr 1fr; } .dashboard-metrics .metric:nth-child(3) { border-right: 1px solid var(--ja-line); } .daily-header { align-items: stretch; flex-direction: column; } }
</style>
