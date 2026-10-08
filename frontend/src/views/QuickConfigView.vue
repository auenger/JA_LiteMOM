<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { has } from '../auth'
import type { QuickConfig } from '../types'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import TablePagination from '../components/TablePagination.vue'

const rows = ref<QuickConfig[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const tab = ref<'CODE_PREFIX' | 'INSPECTION_NOTE' | 'MANUFACTURE_DATE'>('CODE_PREFIX')
const dialog = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const form = reactive({ category: 'CODE_PREFIX', name: '', value: '', sort_order: 0, is_active: true })
const filtered = computed(() => rows.value.filter((item) => item.category === tab.value))
const titles = { CODE_PREFIX: '编码前缀', INSPECTION_NOTE: '检测备注', MANUFACTURE_DATE: '生产日期' } as const
const title = computed(() => titles[tab.value])

async function load() {
  loading.value = true
  try { const { data } = await api.get('/quick-configs', { params: { category: tab.value, page: page.value, page_size: pageSize.value } }); rows.value = data.items; total.value = data.total } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function openCreate() { editingId.value = null; Object.assign(form, { category: tab.value, name: '', value: '', sort_order: 0, is_active: true }); dialog.value = true }
function openEdit(row: QuickConfig) { editingId.value = row.id; Object.assign(form, row); dialog.value = true }
async function submit() {
  await formRef.value?.validate()
  try {
    if (editingId.value) await api.put(`/quick-configs/${editingId.value}`, form)
    else await api.post('/quick-configs', form)
    ElMessage.success('快捷配置已保存'); dialog.value = false; await load()
  } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function remove(row: QuickConfig) {
  try {
    await ElMessageBox.confirm(`确认删除“${row.name}”？`, '删除快捷配置', { type: 'warning' })
    await api.delete(`/quick-configs/${row.id}`); ElMessage.success('已删除'); await load()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
onMounted(load)
watch(tab, () => { page.value = 1; load() })
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
</script>

<template>
  <div>
    <PageHeader title="抄码快捷配置" description="维护快捷抄码使用的瓶身编码前缀、检测备注和生产日期快捷内容。">
      <el-button v-if="has('quick_configs:create')" type="primary" @click="openCreate"><GameIcon name="plus" />新增{{ title }}</el-button>
    </PageHeader>
    <section class="surface">
      <div class="surface-header toolbar"><el-radio-group v-model="tab" size="small"><el-radio-button value="CODE_PREFIX">编码前缀</el-radio-button><el-radio-button value="INSPECTION_NOTE">检测备注</el-radio-button><el-radio-button value="MANUFACTURE_DATE">生产日期</el-radio-button></el-radio-group><span class="grow" /><span class="muted">共 {{ total }} 项</span></div>
      <el-table v-if="filtered.length" v-loading="loading" :data="filtered" stripe>
        <el-table-column prop="name" label="按钮名称" min-width="150" />
        <el-table-column prop="value" :label="title + '内容'" min-width="260"><template #default="{ row }"><strong class="numeric">{{ row.value }}</strong></template></el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" align="right" />
        <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="150"><template #default="{ row }"><el-button v-if="has('quick_configs:update')" link type="primary" @click="openEdit(row)">编辑</el-button><el-button v-if="has('quick_configs:delete')" link type="danger" @click="remove(row)">删除</el-button></template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : `还没有${title}配置`" />
      <TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>
    <el-dialog v-model="dialog" :title="`${editingId ? '编辑' : '新增'}${title}`" width="560px">
      <el-form ref="formRef" :model="form" label-position="top" :rules="{ name: [{ required: true, message: '请输入按钮名称' }], value: [{ required: true, message: '请输入快捷内容' }] }">
        <el-form-item label="按钮名称" prop="name"><el-input v-model="form.name" placeholder="例如：济南瓶 / 外观划伤" /></el-form-item>
        <el-form-item :label="title + '内容'" prop="value"><el-input v-model="form.value" :type="tab === 'INSPECTION_NOTE' ? 'textarea' : 'text'" :rows="3" :placeholder="{ CODE_PREFIX: '例如：JN-', INSPECTION_NOTE: '例如：外观划伤，改判不良品', MANUFACTURE_DATE: '例如：2025.01' }[tab]" /></el-form-item>
        <div class="form-grid"><el-form-item label="显示顺序"><el-input-number v-model="form.sort_order" :min="0" :precision="0" class="w-full" /></el-form-item><el-form-item label="状态"><el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" /></el-form-item></div>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="submit">保存</el-button></template>
    </el-dialog>
  </div>
</template>
