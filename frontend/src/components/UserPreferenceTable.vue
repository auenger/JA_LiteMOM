<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, onUpdated, reactive, ref, shallowRef, useAttrs, watch } from 'vue'
import { ElTable as ElementPlusTable } from 'element-plus'
import { useRoute } from 'vue-router'
import { auth } from '../auth'
import GameIcon from './GameIcon.vue'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  preferenceKey?: string
  defaultHidden?: string[]
}>(), {
  preferenceKey: '',
  defaultHidden: () => [],
})

type TableColumn = {
  id: string
  columnKey?: string
  property?: string
  label?: string
  type?: string
  fixed?: boolean | 'left' | 'right'
  getColumnIndex?: () => number
}

interface ColumnOption {
  id: string
  label: string
  column: TableColumn
  locked: boolean
  side: 'left' | 'right' | 'normal'
}

interface StoredPreference {
  version: 1
  order: string[]
  hidden: string[]
}

const attrs = useAttrs()
const route = useRoute()
const table = ref<any>()
const settingsVisible = ref(false)
const columns = shallowRef<ColumnOption[]>([])
const preference = reactive<StoredPreference>({ version: 1, order: [], hidden: [] })
const activeStorageKey = ref('')
const columnIds = new WeakMap<object, string>()
let observer: MutationObserver | undefined
let updateQueued = false

const defaultHiddenLabels = new Set(['入库编号', '出库单号'])
const lockedLabels = new Set(['操作', '管理', '单瓶报告'])

function hash(value: string) {
  let result = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    result ^= value.charCodeAt(index)
    result = Math.imul(result, 16777619)
  }
  return (result >>> 0).toString(36)
}

function columnBaseId(column: TableColumn, index: number) {
  return String(column.columnKey || column.property || column.label || column.type || `column-${index + 1}`)
}

function mountedColumns(): TableColumn[] {
  const registered = (table.value?.store?.states?._columns?.value || []) as TableColumn[]
  const known = columns.value.map(item => item.column)
  const merged = [...known, ...registered.filter(column => !known.includes(column))]
  return merged
    .filter(column => typeof column.getColumnIndex !== 'function' || column.getColumnIndex() >= 0)
    .sort((left, right) => (left.getColumnIndex?.() ?? 0) - (right.getColumnIndex?.() ?? 0))
}

function describeColumns(rawColumns: TableColumn[]) {
  const occurrences = new Map<string, number>()
  return rawColumns.map((column, index): ColumnOption => {
    const base = columnBaseId(column, index)
    const occurrence = (occurrences.get(base) || 0) + 1
    occurrences.set(base, occurrence)
    let id = columnIds.get(column as object)
    if (!id) {
      id = occurrence === 1 ? base : `${base}#${occurrence}`
      columnIds.set(column as object, id)
    }
    const label = String(column.label || (column.type === 'selection' ? '选择' : column.type === 'index' ? '序号' : column.property || '未命名字段'))
    const side = column.fixed === 'right' || lockedLabels.has(label)
      ? 'right'
      : column.fixed === true || column.fixed === 'left' || ['selection', 'index', 'expand'].includes(column.type || '')
        ? 'left'
        : 'normal'
    return { id, label, column, side, locked: side !== 'normal' }
  })
}

const configurableColumns = computed(() => columns.value.filter(item => !item.locked))
const hiddenIds = computed(() => new Set(preference.hidden))
const visibleConfigurableCount = computed(() => configurableColumns.value.filter(item => !hiddenIds.value.has(item.id)).length)
const orderedSettings = computed(() => {
  const orderIndex = new Map(preference.order.map((id, index) => [id, index]))
  return [...configurableColumns.value].sort((left, right) => {
    const leftIndex = orderIndex.get(left.id) ?? Number.MAX_SAFE_INTEGER
    const rightIndex = orderIndex.get(right.id) ?? Number.MAX_SAFE_INTEGER
    return leftIndex - rightIndex
  })
})

function tableIdentity() {
  if (props.preferenceKey) return props.preferenceKey
  const signature = columns.value.map(item => item.id).join('|')
  return `${String(route.name || route.path)}:${hash(signature)}`
}

function storageKey() {
  const user = auth.user?.id ?? auth.user?.username ?? 'anonymous'
  return `ailitewms:table-preference:v1:${user}:${tableIdentity()}`
}

function defaultHiddenIds() {
  const configured = new Set(props.defaultHidden)
  return configurableColumns.value
    .filter(item => configured.has(item.id) || configured.has(item.label) || defaultHiddenLabels.has(item.label))
    .map(item => item.id)
}

function loadPreference(force = false) {
  const key = storageKey()
  if (!force && activeStorageKey.value === key) return
  activeStorageKey.value = key
  const defaultOrder = configurableColumns.value.map(item => item.id)
  try {
    const saved = JSON.parse(localStorage.getItem(key) || 'null') as Partial<StoredPreference> | null
    preference.order = Array.isArray(saved?.order) ? saved.order.filter(value => typeof value === 'string') : defaultOrder
    preference.hidden = Array.isArray(saved?.hidden) ? saved.hidden.filter(value => typeof value === 'string') : defaultHiddenIds()
  } catch {
    localStorage.removeItem(key)
    preference.order = defaultOrder
    preference.hidden = defaultHiddenIds()
  }
}

function savePreference() {
  if (!activeStorageKey.value) return
  const value: StoredPreference = { version: 1, order: [...preference.order], hidden: [...preference.hidden] }
  try { localStorage.setItem(activeStorageKey.value, JSON.stringify(value)) } catch { /* 浏览器禁用缓存时仍保持本次页面设置 */ }
}

function applyPreference() {
  const store = table.value?.store
  if (!store) return
  const rawColumns = mountedColumns()
  if (!rawColumns.length) return
  const described = describeColumns(rawColumns)
  const descriptionChanged = described.length !== columns.value.length || described.some((item, index) => {
    const current = columns.value[index]
    return !current || current.column !== item.column || current.id !== item.id || current.label !== item.label || current.side !== item.side
  })
  if (descriptionChanged) columns.value = described
  loadPreference()

  const byId = new Map(columns.value.map(item => [item.id, item]))
  const ordered = preference.order.map(id => byId.get(id)).filter((item): item is ColumnOption => Boolean(item))
  const remaining = columns.value.filter(item => !item.locked && !preference.order.includes(item.id))
  const visible = [...ordered, ...remaining].filter(item => !hiddenIds.value.has(item.id))
  const left = columns.value.filter(item => item.side === 'left')
  const right = columns.value.filter(item => item.side === 'right')
  const nextColumns = [...left, ...visible, ...right].map(item => item.column)
  const current = store.states._columns.value as TableColumn[]
  const unchanged = current.length === nextColumns.length && current.every((column, index) => column === nextColumns[index])
  if (!unchanged) {
    store.states._columns.value = nextColumns
    store.updateColumns()
    store.scheduleLayout()
  }
  nextTick(() => table.value?.doLayout?.())
}

function queueApply() {
  if (updateQueued) return
  updateQueued = true
  queueMicrotask(() => {
    updateQueued = false
    applyPreference()
  })
}

function toggleColumn(item: ColumnOption, visible: boolean) {
  const hidden = new Set(preference.hidden)
  if (visible) hidden.delete(item.id)
  else if (visibleConfigurableCount.value > 1) hidden.add(item.id)
  preference.hidden = [...hidden]
  savePreference()
  applyPreference()
}

function moveColumn(index: number, offset: number) {
  const items = orderedSettings.value
  const target = index + offset
  if (target < 0 || target >= items.length) return
  const order = items.map(item => item.id)
  ;[order[index], order[target]] = [order[target], order[index]]
  preference.order = order
  savePreference()
  applyPreference()
}

function resetPreference() {
  preference.order = configurableColumns.value.map(item => item.id)
  preference.hidden = defaultHiddenIds()
  try { localStorage.removeItem(activeStorageKey.value) } catch { /* ignore */ }
  applyPreference()
}

function callTableMethod(method: string, ...args: unknown[]) {
  return table.value?.[method]?.(...args)
}

defineExpose({
  clearSelection: () => callTableMethod('clearSelection'),
  getSelectionRows: () => callTableMethod('getSelectionRows'),
  toggleRowSelection: (...args: unknown[]) => callTableMethod('toggleRowSelection', ...args),
  toggleAllSelection: () => callTableMethod('toggleAllSelection'),
  setCurrentRow: (...args: unknown[]) => callTableMethod('setCurrentRow', ...args),
  clearSort: () => callTableMethod('clearSort'),
  clearFilter: (...args: unknown[]) => callTableMethod('clearFilter', ...args),
  doLayout: () => callTableMethod('doLayout'),
  scrollTo: (...args: unknown[]) => callTableMethod('scrollTo', ...args),
  setScrollTop: (...args: unknown[]) => callTableMethod('setScrollTop', ...args),
  setScrollLeft: (...args: unknown[]) => callTableMethod('setScrollLeft', ...args),
})

onMounted(async () => {
  await nextTick()
  await nextTick()
  applyPreference()
  const hiddenColumns = table.value?.$el?.querySelector?.('.el-table__hidden-columns')
  if (hiddenColumns) {
    observer = new MutationObserver(queueApply)
    observer.observe(hiddenColumns, { childList: true, subtree: true })
  }
})
onUpdated(queueApply)
onBeforeUnmount(() => observer?.disconnect())
watch(() => [route.path, auth.user?.id, props.preferenceKey], () => {
  activeStorageKey.value = ''
  nextTick(applyPreference)
})
</script>

<template>
  <div class="user-preference-table">
    <div v-if="configurableColumns.length > 1" class="user-preference-table__toolbar">
      <el-popover v-model:visible="settingsVisible" placement="bottom-end" :width="340" trigger="click" popper-class="table-preference-popover">
        <template #reference>
          <el-button class="user-preference-table__trigger" :class="{ 'is-active': settingsVisible }" circle text title="字段设置" aria-label="字段设置"><GameIcon name="settings" /></el-button>
        </template>
        <div class="table-preference-panel">
          <div class="table-preference-panel__header">
            <strong>字段显示与顺序</strong>
            <el-button link type="primary" @click="resetPreference">恢复默认</el-button>
          </div>
          <p>设置仅保存在当前浏览器，不影响数据和导出文件。</p>
          <div class="table-preference-panel__list">
            <div v-for="(item, index) in orderedSettings" :key="item.id" class="table-preference-panel__item">
              <el-checkbox
                :model-value="!hiddenIds.has(item.id)"
                :disabled="!hiddenIds.has(item.id) && visibleConfigurableCount <= 1"
                @update:model-value="toggleColumn(item, Boolean($event))"
              >{{ item.label }}</el-checkbox>
              <span class="table-preference-panel__moves">
                <el-button text size="small" :disabled="index === 0" :aria-label="`${item.label}上移`" @click="moveColumn(index, -1)">↑</el-button>
                <el-button text size="small" :disabled="index === orderedSettings.length - 1" :aria-label="`${item.label}下移`" @click="moveColumn(index, 1)">↓</el-button>
              </span>
            </div>
          </div>
        </div>
      </el-popover>
    </div>
    <ElementPlusTable ref="table" v-bind="attrs">
      <slot />
      <template v-if="$slots.empty" #empty><slot name="empty" /></template>
      <template v-if="$slots.append" #append><slot name="append" /></template>
    </ElementPlusTable>
  </div>
</template>

<style scoped>
.user-preference-table{position:relative;min-width:0}.user-preference-table__toolbar{position:absolute;top:7px;right:7px;z-index:4}.user-preference-table__trigger{width:28px;height:28px;color:var(--ja-muted);background:rgba(255,255,255,.88);border:1px solid var(--ja-border);box-shadow:0 2px 8px rgba(21,30,40,.1);backdrop-filter:blur(5px);opacity:.2;transition:opacity .16s ease,color .16s ease,background-color .16s ease}.user-preference-table__trigger:hover,.user-preference-table__trigger:focus-visible,.user-preference-table__trigger:active,.user-preference-table__trigger.is-active{color:var(--el-color-primary);background:#fff;opacity:1}.table-preference-panel__header{display:flex;align-items:center;justify-content:space-between;gap:12px}.table-preference-panel p{margin:4px 0 10px;color:var(--ja-muted);font-size:12px}.table-preference-panel__list{max-height:360px;overflow:auto;border:1px solid var(--ja-border);border-radius:8px}.table-preference-panel__item{display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:38px;padding:2px 8px 2px 12px;border-bottom:1px solid var(--ja-border)}.table-preference-panel__item:last-child{border-bottom:0}.table-preference-panel__moves{display:flex;flex:none}.table-preference-panel__moves .el-button+.el-button{margin-left:0}
</style>
