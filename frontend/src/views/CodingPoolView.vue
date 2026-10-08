<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api, { errorMessage } from '../api'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import TablePagination from '../components/TablePagination.vue'

const loading = ref(false)
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const start = new Date(`${today}T00:00:00`); start.setDate(start.getDate() - 9)
const startText = new Intl.DateTimeFormat('sv-SE', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(start)
const dateRange = ref<[string, string]>([startText, today])
const pageSize = ref(10)
const dailyPage = ref(1)
const codingPage = ref(1)
const batchPage = ref(1)
const pool = ref<any>({ total_remaining: 0, daily: { items: [], total: 0 }, coding_daily: { items: [], total: 0 }, batches: { items: [], total: 0 } })

async function load() {
  loading.value = true
  try { pool.value = (await api.get('/coding/pool', { params: { date_from: dateRange.value[0], date_to: dateRange.value[1], daily_page: dailyPage.value, coding_page: codingPage.value, batch_page: batchPage.value, page_size: pageSize.value } })).data } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function search() { dailyPage.value = 1; codingPage.value = 1; batchPage.value = 1; load() }
function changeSection(section: 'daily' | 'coding' | 'batch', page: number, size: number) { pageSize.value = size; if (section === 'daily') dailyPage.value = page; if (section === 'coding') codingPage.value = page; if (section === 'batch') batchPage.value = page; load() }
onMounted(load)
</script>

<template>
  <div>
    <PageHeader title="待抄码池" description="默认查看最近 10 天，支持按入库日期查询待抄码余量和按抄码日期查询人员工作量。"><el-button @click="load"><GameIcon name="refresh" />刷新</el-button></PageHeader>
    <div class="metric-grid pool-metrics"><div class="metric"><span>当前待抄码总量</span><strong>{{ pool.total_remaining }}</strong><small>全部日期有效入库单余量</small></div><div class="metric"><span>当前查询区间</span><strong class="range-value">{{ dateRange[0] }}</strong><small>至 {{ dateRange[1] }}</small></div></div>
    <section class="surface filter-surface"><el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" :clearable="false" /><el-button type="primary" @click="search"><GameIcon name="search" />查询</el-button></section>
    <section class="surface pool-section"><div class="surface-header"><h2>每日待抄码余量</h2><span class="muted">按原入库日期统计</span></div><el-table v-if="pool.daily.items.length" v-loading="loading" :data="pool.daily.items" stripe><el-table-column prop="business_date" label="入库日期" /><el-table-column prop="pending_quantity" label="待检测入库" align="right" /><el-table-column prop="coded_quantity" label="已抄码" align="right" /><el-table-column prop="remaining" label="剩余待抄码" align="right"><template #default="{ row }"><strong>{{ row.remaining }}</strong></template></el-table-column></el-table><EmptyState v-else title="查询区间暂无待抄码统计" /><TablePagination :page="dailyPage" :page-size="pageSize" :total="pool.daily.total" @change="(p, s) => changeSection('daily', p, s)" /></section>
    <section class="surface pool-section"><div class="surface-header"><h2>每日抄码总量</h2><span class="muted">按日期和抄码人员统计</span></div><el-table v-if="pool.coding_daily.items.length" :data="pool.coding_daily.items" stripe><el-table-column prop="coding_date" label="抄码日期" /><el-table-column prop="coded_by_name" label="抄码人员" /><el-table-column prop="coded_quantity" label="当日抄码数量" align="right"><template #default="{ row }"><strong>{{ row.coded_quantity }}</strong></template></el-table-column></el-table><EmptyState v-else title="查询区间还没有抄码记录" /><TablePagination :page="codingPage" :page-size="pageSize" :total="pool.coding_daily.total" @change="(p, s) => changeSection('coding', p, s)" /></section>
    <section class="surface"><div class="surface-header"><h2>入库单余量明细</h2><span class="muted">仅加载查询日期内批次</span></div><el-table v-if="pool.batches.items.length" :data="pool.batches.items" stripe><el-table-column prop="document_no" label="入库单" min-width="190" /><el-table-column prop="business_date" label="日期" width="115" /><el-table-column prop="source_name" label="供瓶单位" min-width="150" /><el-table-column label="规格余量" min-width="220"><template #default="{ row }">{{ row.specs.map((x: any) => `${x.spec_name} ${x.remaining}/${x.pending_quantity}`).join('；') || '-' }}</template></el-table-column><el-table-column prop="remaining" label="剩余总量" width="110" align="right" /></el-table><EmptyState v-else title="查询区间没有待抄码入库单" /><TablePagination :page="batchPage" :page-size="pageSize" :total="pool.batches.total" @change="(p, s) => changeSection('batch', p, s)" /></section>
  </div>
</template>

<style scoped>.pool-metrics{grid-template-columns:repeat(2,1fr)}.range-value{font-size:18px!important}.filter-surface{display:flex;gap:10px;padding:16px;margin-bottom:16px}.pool-section{margin-bottom:16px}@media(max-width:760px){.pool-metrics{grid-template-columns:1fr 1fr}.filter-surface{align-items:stretch;flex-direction:column}.filter-surface>*{width:100%!important}}</style>
