<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import GameIcon from '../components/GameIcon.vue'
import TablePagination from '../components/TablePagination.vue'
import type { Material } from '../types'

const props = defineProps<{ kind: 'suppliers' | 'sources' | 'specs' | 'manufacturers' }>()
const config = computed(() => ({
  suppliers: { title: '供应商', desc: '维护原材料入库业务使用的供应商信息。', endpoint: '/suppliers', permission: 'suppliers' },
  sources: { title: '供瓶单位', desc: '维护钢瓶来源客户、默认项与显示顺序。', endpoint: '/bottle-sources', permission: 'sources' },
  specs: { title: '瓶子规格', desc: '维护可选规格、容积、瓶壁厚度、检测价格与显示顺序。', endpoint: '/bottle-specs', permission: 'specs' },
  manufacturers: { title: '钢瓶生产厂家', desc: '维护钢瓶生产厂家及瓶身编号前缀，快捷抄码时按前缀自动匹配生产厂家。', endpoint: '/bottle-manufacturers', permission: 'manufacturers' },
}[props.kind]))
const rows = ref<any[]>([])
const materials = ref<Material[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const query = ref('')
const dialog = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const splitCodePrefixes = (value = '') => value.split(/[,，;；\s]+/).map((item: string) => item.trim()).filter(Boolean)
const blank = () => props.kind === 'specs'
  ? { name: '', inspection_price: 0, volume: 0, wall_thickness: 0, is_default: false, sort_order: 0, is_active: true, remark: '' }
  : props.kind === 'manufacturers'
    ? { name: '', code_prefix: '', code_prefixes: [], sort_order: 0, is_active: true, remark: '' }
    : { name: '', contact: '', phone: '', address: '', remark: '', is_active: true, ...(props.kind === 'sources' ? { is_default: false, sort_order: 0 } : { material_prices: [] }) }
const form = reactive<any>(blank())
const filtered = computed(() => rows.value.filter((row) => `${row.name} ${row.contact || ''} ${row.phone || ''} ${row.code_prefix || ''}`.toLowerCase().includes(query.value.toLowerCase())))

async function load() {
  loading.value = true
  try {
    const [records, options] = await Promise.all([
      api.get(config.value.endpoint, { params: { page: page.value, page_size: pageSize.value } }),
      props.kind === 'suppliers' ? api.get('/options') : Promise.resolve({ data: { materials: [] } }),
    ])
    rows.value = records.data.items; total.value = records.data.total; materials.value = options.data.materials
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function openCreate() { editingId.value = null; Object.keys(form).forEach((key) => delete form[key]); Object.assign(form, blank()); dialog.value = true }
function openEdit(row: any) { editingId.value = row.id; Object.keys(form).forEach((key) => delete form[key]); Object.assign(form, { ...row, code_prefixes: splitCodePrefixes(row.code_prefix), inspection_price: row.inspection_price == null ? 0 : Number(row.inspection_price), volume: row.volume == null ? 0 : Number(row.volume), wall_thickness: row.wall_thickness == null ? 0 : Number(row.wall_thickness), material_prices: (row.material_prices || []).map((item: any) => ({ material_id: item.material_id, purchase_price: Number(item.purchase_price) })) }); dialog.value = true }
function addMaterialPrice() { form.material_prices.push({ material_id: undefined, purchase_price: 0 }) }
function removeMaterialPrice(index: number) { form.material_prices.splice(index, 1) }
function materialLabel(id: number) { const item = materials.value.find((row) => row.id === id); return item ? `${item.name} / ${item.specification || '无规格'}` : `原材料 #${id}` }
async function submit() {
  await formRef.value?.validate()
  try {
    const url = editingId.value ? `${config.value.endpoint}/${editingId.value}` : config.value.endpoint
    const payload = { ...form }
    if (props.kind === 'manufacturers') {
      payload.code_prefix = (form.code_prefixes || []).join(',')
      delete payload.code_prefixes
    }
    if (editingId.value) await api.put(url, payload); else await api.post(url, payload)
    ElMessage.success(`${config.value.title}已保存`)
    dialog.value = false
    await load()
  } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function remove(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除“${row.name}”？已有业务引用时将无法删除。`, `删除${config.value.title}`, { type: 'warning' })
    await api.delete(`${config.value.endpoint}/${row.id}`)
    ElMessage.success('已删除')
    await load()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
watch(() => props.kind, () => { query.value = ''; page.value = 1; load() })
onMounted(load)
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
</script>

<template>
  <div>
    <PageHeader :title="config.title" :description="config.desc">
      <el-button v-if="has(`${config.permission}:create`)" type="primary" @click="openCreate"><GameIcon name="plus" />新增{{ config.title }}</el-button>
    </PageHeader>
    <section class="surface">
      <div class="surface-header toolbar"><el-input v-model="query" class="search-input" clearable :placeholder="kind === 'manufacturers' ? '搜索厂家名称或编号前缀' : '搜索名称或联系方式'"><template #prefix><GameIcon name="search" /></template></el-input><span class="grow" /><span class="muted">共 {{ total }} 项</span></div>
      <el-table v-if="filtered.length" v-loading="loading" :data="filtered" stripe>
        <el-table-column prop="name" label="名称" min-width="170" />
        <template v-if="kind === 'suppliers' || kind === 'sources'">
          <el-table-column prop="contact" label="联系人" width="120"><template #default="{ row }">{{ row.contact || '-' }}</template></el-table-column>
          <el-table-column prop="phone" label="联系电话" width="145"><template #default="{ row }">{{ row.phone || '-' }}</template></el-table-column>
          <el-table-column prop="address" label="地址" min-width="180"><template #default="{ row }">{{ row.address || '-' }}</template></el-table-column>
        </template>
        <el-table-column v-if="kind === 'manufacturers'" prop="code_prefix" label="编号前缀" min-width="220"><template #default="{ row }"><div v-if="row.code_prefix" class="prefix-tags"><el-tag v-for="prefix in splitCodePrefixes(row.code_prefix)" :key="prefix" size="small" effect="plain">{{ prefix }}</el-tag></div><span v-else class="muted">不参与匹配</span></template></el-table-column>
        <el-table-column v-if="kind === 'suppliers'" label="供应原材料及采购价" min-width="260"><template #default="{ row }"><div v-if="row.material_prices?.length" class="price-list"><span v-for="item in row.material_prices" :key="item.id">{{ item.material_name }}：¥{{ Number(item.purchase_price).toFixed(2) }}/{{ item.unit }}</span></div><span v-else class="muted">未配置</span></template></el-table-column>
        <el-table-column v-if="kind === 'specs'" label="检测价格" width="130" align="right"><template #default="{ row }"><span class="numeric">¥{{ Number(row.inspection_price).toFixed(2) }}</span></template></el-table-column>
        <el-table-column v-if="kind === 'specs'" label="容积" width="110" align="right"><template #default="{ row }"><span class="numeric">{{ Number(row.volume ?? 0).toFixed(2) }}</span></template></el-table-column>
        <el-table-column v-if="kind === 'specs'" label="瓶壁厚度" width="130" align="right"><template #default="{ row }"><span class="numeric">{{ Number(row.wall_thickness ?? 0).toFixed(2) }} mm</span></template></el-table-column>
        <el-table-column v-if="kind !== 'suppliers'" prop="sort_order" label="排序" width="80" align="right" />
        <el-table-column v-if="kind === 'sources' || kind === 'specs'" label="默认项" width="90"><template #default="{ row }"><el-tag v-if="row.is_default" type="danger" size="small">默认</el-tag><span v-else>-</span></template></el-table-column>
        <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }">
          <el-button v-if="has(`${config.permission}:update`)" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="has(`${config.permission}:delete`)" link type="danger" @click="remove(row)">删除</el-button>
        </template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : `还没有${config.title}`"><el-button v-if="has(`${config.permission}:create`)" type="primary" @click="openCreate">新增{{ config.title }}</el-button></EmptyState>
      <TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>

    <el-dialog v-model="dialog" :title="`${editingId ? '编辑' : '新增'}${config.title}`" width="640px" destroy-on-close>
      <el-form ref="formRef" :model="form" label-position="top" :rules="{ name: [{ required: true, message: '请输入名称' }] }">
        <div class="form-grid">
          <el-form-item label="名称" prop="name"><el-input v-model="form.name" :placeholder="kind === 'specs' ? '例如：15kg 钢瓶' : kind === 'manufacturers' ? '请输入生产厂家名称' : '请输入单位名称'" /></el-form-item>
          <el-form-item v-if="kind === 'manufacturers'" class="span-2" label="编号前缀（可多个）">
            <el-select v-model="form.code_prefixes" multiple filterable allow-create default-first-option :reserve-keyword="false" placeholder="输入一个前缀后按回车，再继续添加，例如 JN-、YN">
              <el-option v-for="prefix in form.code_prefixes" :key="prefix" :label="prefix" :value="prefix" />
            </el-select>
            <div class="field-help">快捷抄码时，瓶身编号只要匹配其中任意一个前缀，就会自动选择该生产厂家。</div>
          </el-form-item>
          <el-form-item v-if="kind === 'specs'" label="检测价格"><el-input-number v-model="form.inspection_price" :min="0" :precision="2" :controls="false" class="w-full" /></el-form-item>
          <el-form-item v-if="kind === 'specs'" label="容积"><el-input-number v-model="form.volume" :min="0" :precision="2" :controls="false" class="w-full" placeholder="选填，默认 0.00" /></el-form-item>
          <el-form-item v-if="kind === 'specs'" label="瓶壁厚度"><div class="value-with-unit"><el-input-number v-model="form.wall_thickness" :min="0" :precision="2" :controls="false" placeholder="0.00" /><span>mm</span></div></el-form-item>
          <template v-if="kind === 'suppliers' || kind === 'sources'">
            <el-form-item label="联系人"><el-input v-model="form.contact" placeholder="选填" /></el-form-item>
            <el-form-item label="联系电话"><el-input v-model="form.phone" placeholder="选填" /></el-form-item>
            <el-form-item class="span-2" label="地址"><el-input v-model="form.address" placeholder="选填" /></el-form-item>
          </template>
          <el-form-item v-if="kind !== 'suppliers'" label="显示顺序"><el-input-number v-model="form.sort_order" :min="0" :precision="0" class="w-full" /></el-form-item>
          <el-form-item v-if="kind === 'sources' || kind === 'specs'" label="默认项"><el-switch v-model="form.is_default" active-text="设为默认" /></el-form-item>
          <div v-if="kind === 'suppliers'" class="span-2 supplier-materials">
            <div class="section-heading"><strong>供应原材料与采购价</strong><el-button type="primary" link @click="addMaterialPrice"><GameIcon name="plus" />添加原材料</el-button></div>
            <el-alert v-if="!form.material_prices.length" title="请为该供应商配置可采购的原材料及专属采购价格。" type="info" :closable="false" />
            <div v-for="(item, index) in form.material_prices" :key="index" class="price-row">
              <el-select v-model="item.material_id" filterable placeholder="选择原材料"><el-option v-for="material in materials.filter((x) => x.is_active)" :key="material.id" :label="materialLabel(material.id)" :value="material.id" :disabled="form.material_prices.some((x: any, i: number) => i !== index && x.material_id === material.id)" /></el-select>
              <el-input-number v-model="item.purchase_price" :min="0" :precision="2" :controls="false" placeholder="采购价" class="w-full" />
              <el-button circle text type="danger" @click="removeMaterialPrice(index)"><GameIcon name="trash" /></el-button>
            </div>
          </div>
          <el-form-item label="档案状态"><el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" /></el-form-item>
          <el-form-item class="span-2" label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填" /></el-form-item>
        </div>
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="submit">保存</el-button></div></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.price-list{display:flex;flex-direction:column;gap:3px}.prefix-tags{display:flex;flex-wrap:wrap;gap:6px}.field-help{width:100%;margin-top:6px;color:var(--el-text-color-secondary);font-size:12px;line-height:1.5}.value-with-unit{display:flex;align-items:center;gap:8px;width:100%}.value-with-unit .el-input-number{flex:1;min-width:0}.value-with-unit span{color:var(--el-text-color-secondary)}.supplier-materials{margin-bottom:14px}.section-heading{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}.price-row{display:grid;grid-template-columns:minmax(260px,1fr) 160px 36px;gap:10px;align-items:center;margin-bottom:10px}@media(max-width:680px){.price-row{grid-template-columns:1fr 120px 36px}}
</style>
