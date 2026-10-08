<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import PageHeader from '../components/PageHeader.vue'
import TablePagination from '../components/TablePagination.vue'
interface Log {
  id: number; business_date: string; material_name: string; unit: string; operator_name: string
  created_at: string; old_inbound: string; inbound: string; old_outbound: string; outbound: string; balance_after: string
}
const router = useRouter()
const filters = reactive({ date_from: '', date_to: '', query: '' })
let applied = { ...filters }
const rows = ref<Log[]>([]), loading = ref(false), failure = ref('')
const page = ref(1), pageSize = ref(20), total = ref(0)
const number = (value: string | number) => Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
const time = (value: string) => new Date(`${value}Z`).toLocaleString('zh-CN', { hour12: false })
let requestId = 0
async function load() {
  const id = ++requestId
  loading.value = true; failure.value = ''; rows.value = []
  try {
    const { data } = await api.get('/material-daily/logs/list', { params: {
      date_from: applied.date_from || undefined, date_to: applied.date_to || undefined,
      query: applied.query || undefined, page: page.value, page_size: pageSize.value,
    } })
    if (id !== requestId) return
    rows.value = data.items; total.value = data.total
  } catch (err) {
    if (id === requestId) { failure.value = errorMessage(err); total.value = 0 }
  } finally { if (id === requestId) loading.value = false }
}
function search() {
  if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) {
    ElMessage.warning('开始日期不能晚于结束日期'); return
  }
  applied = { ...filters }; page.value = 1; load()
}
function reset() { Object.assign(filters, { date_from: '', date_to: '', query: '' }); search() }
function pageChanged(next: number, size: number) { page.value = next; pageSize.value = size; load() }
onMounted(load)
</script>
<template>
  <div>
    <PageHeader title="出入库日志" description="查看所有日期的原材料出入库变更记录，按操作时间从新到旧排列。">
      <el-button v-if="has('material_daily:view')" @click="router.push('/material-daily')">返回出入库管理</el-button>
    </PageHeader>
    <section class="surface">
      <form class="surface-header log-filters" @submit.prevent="search">
        <label>业务日期从<el-date-picker v-model="filters.date_from" type="date" value-format="YYYY-MM-DD" placeholder="不限开始日期" :editable="false" /></label>
        <label>至<el-date-picker v-model="filters.date_to" type="date" value-format="YYYY-MM-DD" placeholder="不限结束日期" :editable="false" /></label>
        <el-input v-model="filters.query" class="search-input" placeholder="搜索原材料名称" clearable :maxlength="120" />
        <el-button type="primary" native-type="submit">查询</el-button><el-button @click="reset">重置</el-button>
      </form>
      <el-alert v-if="failure" :title="failure" type="error" show-icon :closable="false" />
      <el-table v-loading="loading" :data="rows" stripe row-key="id" empty-text="暂无符合条件的出入库变更记录">
        <el-table-column prop="business_date" label="业务日期" width="120" />
        <el-table-column label="操作时间" min-width="180"><template #default="{ row }">{{ time(row.created_at) }}</template></el-table-column>
        <el-table-column prop="operator_name" label="操作人" min-width="110" />
        <el-table-column prop="material_name" label="原材料" min-width="160" />
        <el-table-column label="入库（修改前 → 后）" min-width="185"><template #default="{ row }">{{ number(row.old_inbound) }} → {{ number(row.inbound) }} {{ row.unit }}</template></el-table-column>
        <el-table-column label="出库（修改前 → 后）" min-width="185"><template #default="{ row }">{{ number(row.old_outbound) }} → {{ number(row.outbound) }} {{ row.unit }}</template></el-table-column>
        <el-table-column label="操作后总库存" min-width="150" align="right"><template #default="{ row }">{{ number(row.balance_after) }} {{ row.unit }}</template></el-table-column>
      </el-table>
      <TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>
  </div>
</template>
<style scoped>
.log-filters { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
.log-filters label { display: flex; align-items: center; gap: 8px; color: var(--ja-muted); }
.log-filters :deep(.el-date-editor) { width: 170px; }
@media (max-width: 760px) {
  .log-filters label { width: 100%; justify-content: space-between; }
  .log-filters :deep(.el-date-editor) { flex: 1; max-width: 240px; }
}
</style>
