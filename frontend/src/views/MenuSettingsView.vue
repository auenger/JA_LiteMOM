<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errorMessage } from '../api'
import { applyMenuSettings, arrangedMenus, type MenuGroup, type MenuSettings } from '../menu'
import PageHeader from '../components/PageHeader.vue'
const groups = ref<MenuGroup[]>([]), loading = ref(false), saving = ref(false), loaded = ref(false), dirty = ref(false)
const version = ref(0), failure = ref('')
async function load() {
  loading.value = true; failure.value = ''; loaded.value = false
  try {
    const { data } = await api.get<MenuSettings>('/menu-settings')
    groups.value = arrangedMenus(data); version.value = data.version; applyMenuSettings(data)
    loaded.value = true; dirty.value = false
  } catch (err) { failure.value = errorMessage(err) } finally { loading.value = false }
}
function move<T>(items: T[], index: number, offset: number) {
  const target = index + offset
  if (target < 0 || target >= items.length) return
  const [item] = items.splice(index, 1); items.splice(target, 0, item); dirty.value = true
}
function reset() { groups.value = arrangedMenus({ groups: [], version: 0 }); dirty.value = true }
function changeGroup(groupIndex: number, itemIndex: number, label: string) {
  const destination = groups.value.find(group => group.label === label)
  if (!destination || destination === groups.value[groupIndex]) return
  const [item] = groups.value[groupIndex].items.splice(itemIndex, 1)
  destination.items.push(item); dirty.value = true
}
async function addGroup() {
  try {
    const { value } = await ElMessageBox.prompt('输入新分组名称，创建后可通过“所属分组”把菜单移入。', '新增分组', {
      confirmButtonText: '新增', cancelButtonText: '取消',
      inputValidator: (value: string) => {
        const name = value?.trim() || ''
        if (!name || name.length > 40) return '请输入 1–40 个字符的分组名称'
        if (groups.value.some(group => group.label === name)) return '该分组名称已存在'
        return true
      },
    })
    groups.value.push({ label: value.trim(), items: [] }); dirty.value = true
    ElMessage.success('分组已添加，请移动菜单后保存设置')
  } catch { /* Canceling the dialog leaves the current settings unchanged. */ }
}
async function save() {
  if (groups.value.some(group => group.items.some(item => !item.label.trim()))) {
    ElMessage.warning('菜单名称不能为空'); return
  }
  saving.value = true
  try {
    const { data } = await api.put<MenuSettings>('/menu-settings', {
      version: version.value,
      groups: groups.value.map(group => ({ label: group.label, items: group.items.map(item => ({ path: item.path, label: item.label.trim(), hidden: !!item.hidden })) })),
    })
    version.value = data.version; groups.value = arrangedMenus(data); applyMenuSettings(data); dirty.value = false
    ElMessage.success('菜单设置已保存，对所有用户生效')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { saving.value = false }
}
onMounted(load)
</script>
<template>
  <div v-loading="loading">
    <PageHeader title="菜单设置" description="仅超级管理员可修改。编辑菜单名称、新增分组、调整菜单位置与显示状态，保存后对所有用户生效；各用户仍只能看到有权限的菜单。">
      <el-button :disabled="!loaded || saving || loading || groups.length >= 20" @click="addGroup">新增分组</el-button>
      <el-button :disabled="saving || loading" @click="load">重新加载</el-button>
      <el-button :disabled="!loaded || saving || loading" @click="reset">恢复默认</el-button>
      <el-button type="primary" :loading="saving" :disabled="!loaded || !dirty || loading" @click="save">保存设置</el-button>
    </PageHeader>
    <el-alert v-if="failure" :title="failure" type="error" show-icon :closable="false" />
    <p v-if="loaded" class="muted" role="status">{{ dirty ? '有未保存的修改，请点击“保存设置”生效。' : '当前菜单设置已保存。' }} “菜单设置”入口始终保留，方便恢复隐藏菜单。</p>
    <section v-for="(group, groupIndex) in groups" :key="group.label" class="surface menu-group">
      <div class="surface-header group-heading"><strong>{{ group.label }}</strong><span class="grow" />
        <el-button :aria-label="`${group.label}分组上移`" :disabled="saving || loading || groupIndex === 0" @click="move(groups, groupIndex, -1)">分组上移</el-button>
        <el-button :aria-label="`${group.label}分组下移`" :disabled="saving || loading || groupIndex === groups.length - 1" @click="move(groups, groupIndex, 1)">分组下移</el-button>
      </div>
      <el-table :data="group.items" row-key="path" stripe empty-text="此分组暂无菜单">
        <el-table-column label="顺序" type="index" width="65" />
        <el-table-column label="菜单名称" min-width="220"><template #default="{ row }"><el-input v-model="row.label" :aria-label="`${row.path}菜单名称`" :maxlength="60" :disabled="saving || loading" placeholder="请输入菜单名称" @input="dirty = true" /></template></el-table-column>
        <el-table-column label="是否显示" width="130"><template #default="{ row }"><el-switch :model-value="!row.hidden" :aria-label="`${row.label}是否显示`" :disabled="saving || loading || row.path === '/menu-settings'" @update:model-value="row.hidden = !$event; dirty = true" /></template></el-table-column>
        <el-table-column label="所属分组" min-width="150"><template #default="{ $index }"><el-select :model-value="group.label" :disabled="saving || loading" @change="changeGroup(groupIndex, $index, $event)"><el-option v-for="target in groups" :key="target.label" :label="target.label" :value="target.label" /></el-select></template></el-table-column>
        <el-table-column label="调整位置" width="155"><template #default="{ row, $index }"><el-button link type="primary" :aria-label="`${row.label}上移`" :disabled="saving || loading || $index === 0" @click="move(group.items, $index, -1)">上移</el-button><el-button link type="primary" :aria-label="`${row.label}下移`" :disabled="saving || loading || $index === group.items.length - 1" @click="move(group.items, $index, 1)">下移</el-button></template></el-table-column>
      </el-table>
    </section>
  </div>
</template>
<style scoped>
.menu-group { margin-bottom: 18px; }
.group-heading { display: flex; align-items: center; gap: 8px; }
@media (max-width: 760px) { .group-heading { flex-wrap: wrap; } }
</style>
