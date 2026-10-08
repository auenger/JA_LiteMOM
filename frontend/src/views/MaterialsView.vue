<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import type { Material } from '../types'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import StatusTag from '../components/StatusTag.vue'
import GameIcon from '../components/GameIcon.vue'
import TablePagination from '../components/TablePagination.vue'

const loading = ref(false)
const rows = ref<Material[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const query = ref('')
const dialog = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const fileInput = ref<HTMLInputElement>()
const importing = ref(false)
const blank = () => ({ name: '', material_type: 'MATERIAL' as 'MATERIAL' | 'SCRAP', specification: '', material_unit: '个', conversion_enabled: false, stock_unit: '', conversion_ratio: 1, price: 0, warning_enabled: false, safety_threshold: null as number | null, is_active: true, remark: '' })
const form = reactive(blank())
const filtered = computed(() => rows.value.filter((item) => `${item.name} ${item.specification}`.toLowerCase().includes(query.value.toLowerCase())))
const formatQuantity = (value: string | number | null | undefined) => Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

async function load() {
  loading.value = true
  try { const { data } = await api.get('/materials', { params: { page: page.value, page_size: pageSize.value } }); rows.value = data.items; total.value = data.total } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function openCreate() { editingId.value = null; Object.assign(form, blank()); dialog.value = true }
function openEdit(row: Material) {
  editingId.value = row.id
  Object.assign(form, { ...row, price: Number(row.price), conversion_ratio: Number(row.conversion_ratio), safety_threshold: row.safety_threshold == null ? null : Number(row.safety_threshold) })
  dialog.value = true
}
async function submit() {
  await formRef.value?.validate()
  try {
    if (editingId.value) await api.put(`/materials/${editingId.value}`, form)
    else await api.post('/materials', form)
    ElMessage.success(editingId.value ? '原材料已更新' : '原材料已新增')
    dialog.value = false
    await load()
  } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function remove(row: Material) {
  try {
    await ElMessageBox.confirm(`确认删除原材料“${row.name}”？已有单据引用时将无法删除。`, '删除原材料', { type: 'warning' })
    await api.delete(`/materials/${row.id}`)
    ElMessage.success('原材料已删除')
    await load()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
async function exportMaterials() {
  try {
    const response = await api.get('/materials/export', { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `原材料档案-${new Date().toISOString().slice(0, 10)}.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function importMaterials(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  importing.value = true
  try {
    const payload = new FormData()
    payload.append('file', file)
    const { data } = await api.post('/materials/import', payload)
    ElMessage.success(`导入完成，新增 ${data.created} 项，更新 ${data.updated} 项`)
    await load()
  } catch (err) { ElMessage.error(errorMessage(err)) } finally {
    importing.value = false
    input.value = ''
  }
}
onMounted(load)
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
</script>

<template>
  <div>
    <PageHeader title="原材料档案" description="维护原材料基础信息，并查看各供应商对应的采购价格。">
      <input ref="fileInput" class="file-input" type="file" accept=".csv,text/csv" @change="importMaterials" />
      <el-button v-if="has('materials:import')" :loading="importing" @click="fileInput?.click()"><GameIcon name="clipboard" />导入 CSV</el-button>
      <el-button v-if="has('materials:export')" @click="exportMaterials"><GameIcon name="save" />导出 CSV</el-button>
      <el-button v-if="has('materials:create')" type="primary" @click="openCreate"><GameIcon name="plus" />新增原材料</el-button>
    </PageHeader>
    <section class="surface">
      <div class="surface-header toolbar">
        <el-input v-model="query" class="search-input" clearable placeholder="搜索名称或规格"><template #prefix><GameIcon name="search" /></template></el-input>
        <span class="grow" /><span class="muted">共 {{ total }} 项</span>
      </div>
      <el-table v-if="filtered.length" v-loading="loading" :data="filtered" stripe>
        <el-table-column prop="name" label="原材料名称" min-width="150" />
        <el-table-column label="类型" width="90"><template #default="{ row }"><el-tag :type="row.material_type === 'SCRAP' ? 'warning' : 'info'">{{ row.material_type === 'SCRAP' ? '废料' : '原料' }}</el-tag></template></el-table-column>
        <el-table-column prop="specification" label="规格" min-width="140"><template #default="{ row }">{{ row.specification || '-' }}</template></el-table-column>
        <el-table-column label="单位换算" min-width="180"><template #default="{ row }"><span v-if="row.conversion_enabled" class="conversion">1 {{ row.material_unit }} = {{ formatQuantity(row.conversion_ratio) }} {{ row.stock_unit }}</span><span v-else class="muted">未启用</span></template></el-table-column>
        <el-table-column label="默认参考价" width="120" align="right"><template #default="{ row }"><span class="numeric">¥{{ Number(row.price).toFixed(2) }}</span></template></el-table-column>
        <el-table-column label="供应商采购价" min-width="220"><template #default="{ row }"><div v-if="row.supplier_prices?.length" class="supplier-prices"><span v-for="item in row.supplier_prices" :key="item.id">{{ item.supplier_name }}：¥{{ Number(item.purchase_price).toFixed(2) }}</span></div><span v-else class="muted">未匹配供应商</span></template></el-table-column>
        <el-table-column label="实际物料库存" width="150" align="right"><template #default="{ row }"><strong class="numeric">{{ formatQuantity(row.stock) }} {{ row.material_unit }}</strong></template></el-table-column>
        <el-table-column label="换算库存" width="150" align="right"><template #default="{ row }"><strong v-if="row.conversion_enabled" class="numeric converted-stock">{{ formatQuantity(row.converted_stock) }} {{ row.stock_unit }}</strong><span v-else class="muted">-</span></template></el-table-column>
        <el-table-column label="安全阈值" width="130" align="right"><template #default="{ row }">{{ row.warning_enabled ? `${formatQuantity(row.safety_threshold)} ${row.conversion_enabled ? row.stock_unit : row.material_unit}` : '-' }}</template></el-table-column>
        <el-table-column label="预警状态" width="110"><template #default="{ row }"><StatusTag :status="row.warning_status" /></template></el-table-column>
        <el-table-column label="档案状态" width="90"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }">
          <el-button v-if="has('materials:update')" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="has('materials:delete')" link type="danger" @click="remove(row)">删除</el-button>
        </template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : '还没有原材料'" description="新增原材料后，可通过入库单建立库存。"><el-button v-if="has('materials:create')" type="primary" @click="openCreate">新增原材料</el-button></EmptyState>
      <TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>

    <el-dialog v-model="dialog" :title="editingId ? '编辑原材料' : '新增原材料'" width="620px" destroy-on-close>
      <el-form ref="formRef" :model="form" label-position="top" :rules="{ name: [{ required: true, message: '请输入名称' }], material_unit: [{ required: true, message: '请输入物料单位' }] }">
        <div class="form-grid">
          <el-form-item label="原材料名称" prop="name"><el-input v-model="form.name" placeholder="例如：银灰粉末" /></el-form-item>
          <el-form-item label="类型"><el-radio-group v-model="form.material_type"><el-radio-button value="MATERIAL">原料</el-radio-button><el-radio-button value="SCRAP">废料</el-radio-button></el-radio-group></el-form-item>
          <el-form-item label="规格"><el-input v-model="form.specification" placeholder="例如：银灰色" /></el-form-item>
          <el-form-item label="物料单位" prop="material_unit"><el-input v-model="form.material_unit" placeholder="例如：瓶、桶、袋" /></el-form-item>
          <el-form-item label="参考价格（每物料单位）"><el-input-number v-model="form.price" :min="0" :precision="2" :controls="false" class="w-full" /></el-form-item>
          <el-form-item class="span-2" label="单位换算"><el-switch v-model="form.conversion_enabled" active-text="启用换算库存" inactive-text="仅使用物料单位" /></el-form-item>
          <template v-if="form.conversion_enabled">
            <el-form-item label="库存展示单位" prop="stock_unit"><el-input v-model="form.stock_unit" placeholder="例如：kg、L、ml" /></el-form-item>
            <el-form-item label="固定换算比例" prop="conversion_ratio"><el-input-number v-model="form.conversion_ratio" :min="0.01" :precision="2" :controls="false" class="w-full" /></el-form-item>
            <div class="conversion-preview span-2">换算预览：1 {{ form.material_unit || '物料单位' }} = {{ form.conversion_ratio || 0 }} {{ form.stock_unit || '库存单位' }}</div>
          </template>
          <el-form-item label="库存预警"><el-switch v-model="form.warning_enabled" active-text="启用" inactive-text="不启用" /></el-form-item>
          <el-form-item label="安全库存阈值"><el-input-number v-model="form.safety_threshold" :disabled="!form.warning_enabled" :min="0" :precision="2" :controls="false" class="w-full" /></el-form-item>
          <el-form-item label="档案状态"><el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" /></el-form-item>
          <el-form-item class="span-2" label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填" /></el-form-item>
        </div>
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="submit">保存</el-button></div></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.file-input { display: none; }
.conversion { color: var(--ja-muted); font-variant-numeric: tabular-nums; }
.converted-stock { color: var(--ja-red); }
.conversion-preview { margin: -2px 0 16px; padding: 10px 12px; color: var(--ja-muted); background: #f6f7f8; border-radius: var(--ja-radius); font-size: 12px; }
.supplier-prices { display: flex; flex-direction: column; gap: 3px; }
</style>
