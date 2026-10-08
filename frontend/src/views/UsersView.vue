<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { auth, has } from '../auth'
import { arrangedMenus, loadMenuSettings } from '../menu'
import type { User } from '../types'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import GameIcon from '../components/GameIcon.vue'
import TablePagination from '../components/TablePagination.vue'

const rows = ref<User[]>([])
type PermissionGroup = { group: string; items: [string, string][] }
const catalog = ref<PermissionGroup[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const query = ref('')
const dialog = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const blank = () => ({ username: '', name: '', role_name: '业务人员', phone: '', remark: '', password: '', is_active: true, permissions: [] as string[] })
const form = reactive(blank())
const filtered = computed(() => rows.value.filter((row) => `${row.username} ${row.name} ${row.phone || ''}`.toLowerCase().includes(query.value.toLowerCase())))

const permissionSections = computed(() => {
  const used = new Set<string>()
  const sections = arrangedMenus().map(section => ({
    label: section.label,
    groups: section.items.map(menu => {
      const prefixes = (menu.permissions || (menu.permission ? [menu.permission] : [])).map(key => key.split(':')[0])
      const items: [string, string][] = catalog.value.flatMap(group => group.items.filter(([key]) => prefixes.includes(key.split(':')[0])))
        .map(([key, label]) => {
          used.add(key)
          const prefix = key.startsWith('bottle_inbound:') ? '入库 / ' : key.startsWith('bottle_outbound:') ? '出库 / ' : ''
          return [key, prefixes.length > 1 ? prefix + label : label]
        })
      return { key: menu.path, group: menu.label, items, superadmin: !!menu.superadmin, hidden: !!menu.hidden }
    }),
  }))
  const remaining = catalog.value.map(group => ({ ...group, key: group.group, superadmin: false, hidden: false, items: group.items.filter(([key]) => !used.has(key)) })).filter(group => group.items.length)
  if (remaining.length) sections.push({ label: '其他业务权限', groups: remaining })
  return sections
})

async function load() {
  loading.value = true
  try {
    const [users, permissions] = await Promise.all([api.get('/users', { params: { page: page.value, page_size: pageSize.value } }), api.get('/permissions/catalog'), loadMenuSettings()])
    rows.value = users.data.items; total.value = users.data.total
    catalog.value = permissions.data
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
function openCreate() { editingId.value = null; Object.assign(form, blank()); dialog.value = true }
function openEdit(row: User) {
  editingId.value = row.id
  Object.assign(form, { username: row.username, name: row.name, role_name: row.role_name, phone: row.phone || '', remark: row.remark || '', password: '', is_active: row.is_active, permissions: [...row.permissions] })
  dialog.value = true
}
function selectGroup(group: PermissionGroup) {
  const selected = new Set(form.permissions)
  for (const [key] of group.items) selected.add(key)
  form.permissions = [...selected]
}
function invertGroup(group: PermissionGroup) {
  const selected = new Set(form.permissions)
  for (const [key] of group.items) {
    if (selected.has(key)) selected.delete(key)
    else selected.add(key)
  }
  form.permissions = [...selected]
}
function selectedInGroup(group: PermissionGroup) {
  return group.items.filter(([key]) => form.permissions.includes(key)).length
}
async function submit() {
  await formRef.value?.validate()
  try {
    const payload: any = { ...form }
    if (editingId.value) {
      if (!auth.user?.is_superadmin) delete payload.username
      else payload.username = payload.username.trim()
      if (!payload.password) delete payload.password
      await api.put(`/users/${editingId.value}`, payload)
    } else await api.post('/users', payload)
    ElMessage.success('人员信息已保存')
    dialog.value = false
    await load()
  } catch (err) { ElMessage.error(errorMessage(err)) }
}
async function remove(row: User) {
  try {
    await ElMessageBox.confirm(`确认删除人员“${row.name}”？`, '删除人员', { type: 'warning' })
    await api.delete(`/users/${row.id}`)
    ElMessage.success('人员已删除')
    await load()
  } catch (err: any) { if (err !== 'cancel') ElMessage.error(errorMessage(err)) }
}
onMounted(load)
function pageChanged(nextPage: number, nextSize: number) { page.value = nextPage; pageSize.value = nextSize; load() }
</script>

<template>
  <div>
    <PageHeader title="人员与权限" description="维护登录人员，并按人员分配页面访问和新增、查询、编辑、删除权限。">
      <el-button v-if="has('users:create')" type="primary" @click="openCreate"><GameIcon name="user-add" />新增人员</el-button>
    </PageHeader>
    <section class="surface">
      <div class="surface-header toolbar"><el-input v-model="query" class="search-input" clearable placeholder="搜索姓名、账号或电话"><template #prefix><GameIcon name="search" /></template></el-input><span class="grow" /><span class="muted">共 {{ total }} 人</span></div>
      <el-table v-if="filtered.length" v-loading="loading" :data="filtered" stripe>
        <el-table-column prop="name" label="人员姓名" min-width="130" />
        <el-table-column prop="username" label="登录账号" min-width="130" />
        <el-table-column prop="phone" label="联系电话" min-width="140"><template #default="{ row }">{{ row.phone || '-' }}</template></el-table-column>
        <el-table-column label="角色/身份" min-width="130"><template #default="{ row }"><el-tag :type="row.is_superadmin ? 'danger' : 'info'" size="small">{{ row.role_name }}</el-tag></template></el-table-column>
        <el-table-column label="权限数量" width="100" align="right"><template #default="{ row }">{{ row.is_superadmin ? '全部' : row.permissions.length }}</template></el-table-column>
        <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }">
          <el-button v-if="has('users:update')" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="has('users:delete') && !row.is_superadmin" link type="danger" @click="remove(row)">删除</el-button>
        </template></el-table-column>
      </el-table>
      <EmptyState v-else :title="loading ? '正在加载' : '还没有人员信息'" />
      <TablePagination :page="page" :page-size="pageSize" :total="total" @change="pageChanged" />
    </section>

    <el-dialog v-model="dialog" :title="editingId ? '编辑人员与权限' : '新增人员'" width="760px" destroy-on-close>
      <el-form ref="formRef" :model="form" label-position="top" :rules="{ username: [{ required: true, whitespace: true, message: '请输入登录账号' }, { min: 2, max: 60, message: '登录账号长度为 2–60 个字符' }], name: [{ required: true, message: '请输入姓名' }], role_name: [{ required: true, message: '请输入角色/身份名称' }], password: [{ required: !editingId, message: '请输入至少 8 位密码', min: 8 }] }">
        <div class="form-grid">
          <el-form-item label="人员姓名" prop="name"><el-input v-model="form.name" placeholder="请输入人员姓名" /></el-form-item>
          <el-form-item label="登录账号" prop="username"><el-input v-model.trim="form.username" aria-label="登录账号" :disabled="Boolean(editingId) && !auth.user?.is_superadmin" placeholder="请输入唯一登录账号" /></el-form-item>
          <el-form-item label="角色/身份名称" prop="role_name"><el-input v-model="form.role_name" placeholder="例如：仓库管理员、质检员" /></el-form-item>
          <el-form-item label="联系电话"><el-input v-model="form.phone" placeholder="选填" /></el-form-item>
          <el-form-item :label="editingId ? '重置密码' : '初始密码'" prop="password"><el-input v-model="form.password" type="password" show-password :placeholder="editingId ? '留空表示不修改' : '至少 8 位'" /></el-form-item>
          <el-form-item label="账号状态"><el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" /></el-form-item>
          <el-form-item class="span-2" label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填" /></el-form-item>
        </div>
        <div v-if="!rows.find((row) => row.id === editingId)?.is_superadmin" class="permission-panel">
          <h4>页面及操作权限</h4>
          <section v-for="section in permissionSections" :key="section.label" class="permission-section">
            <h5>{{ section.label }}</h5>
            <div v-for="group in section.groups" :key="group.key" class="permission-group">
              <div class="permission-group-header"><strong>{{ group.group }}</strong><el-tag v-if="group.hidden" size="small" type="info">菜单已隐藏</el-tag>
                <template v-if="!group.superadmin"><span class="muted">{{ selectedInGroup(group) }}/{{ group.items.length }}</span><el-button link type="primary" size="small" @click="selectGroup(group)">全选</el-button><el-button link size="small" @click="invertGroup(group)">反选</el-button></template>
              </div>
              <p v-if="group.superadmin" class="muted admin-permission">仅超级管理员可用，无需分配权限。</p>
              <el-checkbox-group v-else v-model="form.permissions" class="permission-options">
                <el-checkbox v-for="item in group.items" :key="item[0]" :value="item[0]">{{ item[1] }}</el-checkbox>
              </el-checkbox-group>
            </div>
          </section>
        </div>
        <el-alert v-else title="默认超级管理员始终拥有全部权限，不能被停用或删除。" type="info" :closable="false" />
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="submit">保存</el-button></div></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.permission-panel { margin-top: 8px; padding: 4px 16px; border: 1px solid var(--ja-line); border-radius: var(--ja-radius); }
.permission-section { border-top: 1px solid var(--ja-line); padding: 8px 0 12px; }
.permission-section h5 { margin: 8px 0; font-size: 13px; color: var(--ja-muted); }
.admin-permission { margin: 4px 0 10px; font-size: 12px; }
.permission-panel h4 { margin: 13px 0 2px; }
.permission-group-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 10px 0 2px; }
.permission-group-header .muted { font-size: 12px; }
.permission-group-header :deep(.el-button + .el-button) { margin-left: 0; }
</style>
