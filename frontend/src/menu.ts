import { reactive } from 'vue'
import api from './api'
export interface MenuItem { path: string; label: string; icon: string; permission?: string; permissions?: string[]; superadmin?: boolean; hidden?: boolean }
export interface MenuGroup { label: string; items: MenuItem[] }
export interface MenuSettings { groups: Array<{ label: string; items: Array<{ path: string; hidden: boolean; label?: string | null }> }>; version: number }

export const defaultMenuGroups: MenuGroup[] = [
  {
    label: '总览',
    items: [{ path: '/dashboard', label: '工作台', icon: 'grid', permission: 'dashboard:view' }],
  },
  {
    label: '基础信息',
    items: [
      { path: '/materials', label: '原材料档案', icon: 'chest', permission: 'materials:view' },
      { path: '/suppliers', label: '供应商', icon: 'truck', permission: 'suppliers:view' },
      { path: '/purchase-orders', label: '供应商采购单', icon: 'clipboard', permission: 'purchase_orders:view' },
      { path: '/bottle-sources', label: '供瓶单位', icon: 'user-group', permission: 'sources:view' },
      { path: '/bottle-specs', label: '瓶子规格', icon: 'adjustment', permission: 'specs:view' },
      { path: '/bottle-manufacturers', label: '钢瓶生产厂家', icon: 'a-bottle-of-water', permission: 'manufacturers:view' },
      { path: '/quick-configs', label: '抄码快捷配置', icon: 'settings', permission: 'quick_configs:view' },
      { path: '/profit-analysis', label: '盈利成本计算', icon: 'clipboard', permission: 'profit:view' },
    ],
  },
  {
    label: '原材料',
    items: [
      { path: '/material-daily', label: '原材料出入库管理', icon: 'clipboard', permission: 'material_daily:view' },
      { path: '/material-daily-logs', label: '出入库日志', icon: 'clipboard', permission: 'material_daily_logs:view' },
      { path: '/material-inbounds', label: '原材料入库', icon: 'plus', permission: 'material_inbound:view' },
      { path: '/material-outbounds', label: '材料出库', icon: 'door', permission: 'material_outbound:view' },
      { path: '/material-returns', label: '退料入库', icon: 'refresh', permission: 'material_return:view' },
    ],
  },
  {
    label: '钢瓶检测',
    items: [
      { path: '/quick-inbound', label: '快速入库', icon: 'user-add', permission: 'quick_inbound:view' },
      { path: '/quick-outbound', label: '快速出库', icon: 'door', permission: 'quick_outbound:view' },
      { path: '/bottle-lifecycle', label: '瓶子生命周期', icon: 'search', permission: 'bottle_lifecycle:view' },
      { path: '/quick-coding', label: '快捷抄码', icon: 'qr-code', permission: 'quick_entry:view' },
      { path: '/inspection-documents', label: '钢瓶检验单', icon: 'clipboard', permission: 'inspection_documents:view' },
      { path: '/unverified-bottles', label: '未经系统验证瓶子池', icon: 'exclamation', permission: 'unverified_bottles:view' },
      { path: '/bottle-inbounds', label: '出入库历史记录', icon: 'a-bottle-of-water', permissions: ['bottle_inbound:view', 'bottle_outbound:view'] },
      { path: '/coding-pool', label: '待抄码池', icon: 'chest', permission: 'coding_pool:view' },
      { path: '/coding', label: '抄码记录', icon: 'qr-code', permission: 'coding:view' },
      { path: '/bottle-quality', label: '质量分类库', icon: 'tick', permission: 'inspection:view' },
      { path: '/bottle-zones', label: '钢瓶库存', icon: 'chest', permission: 'bottle_zones:view' },
      { path: '/monthly-inventory', label: '月度盘点', icon: 'clipboard', permission: 'monthly_inventory:view' },
      { path: '/daily-inventory', label: '日度盘点', icon: 'clipboard', permission: 'daily_inventory:view' },
    ],
  },
  {
    label: '系统管理',
    items: [
      { path: '/menu-settings', label: '菜单设置', icon: 'settings', superadmin: true },
      { path: '/users', label: '人员与权限', icon: 'user-list', permission: 'users:view' },
      { path: '/inspection-word-codes', label: 'Word 报告编号', icon: 'clipboard', superadmin: true },
    ],
  },
]

export const menuSettings = reactive<MenuSettings>({ groups: [], version: 0 })
export function arrangedMenus(settings: MenuSettings = menuSettings): MenuGroup[] {
  const catalog = new Map(defaultMenuGroups.flatMap(group => group.items.map(item => [item.path, item] as const)))
  const used = new Set<string>()
  const result: MenuGroup[] = []
  for (const group of settings.groups) {
    const items: MenuItem[] = []
    for (const setting of group.items) {
      const item = catalog.get(setting.path)
      if (!item || used.has(item.path)) continue
      used.add(item.path)
      items.push({ ...item, label: setting.label?.trim() || item.label, hidden: item.path === '/menu-settings' ? false : setting.hidden })
    }
    result.push({ label: group.label, items })
  }
  for (const group of defaultMenuGroups) {
    let target = result.find(item => item.label === group.label)
    if (!target) { target = { label: group.label, items: [] }; result.push(target) }
    for (const item of group.items) if (!used.has(item.path)) target.items.push({ ...item, hidden: false })
  }
  return result
}
let loadId = 0
export async function loadMenuSettings() {
  const id = ++loadId
  const { data } = await api.get<MenuSettings>('/menu-settings')
  if (id === loadId) Object.assign(menuSettings, data)
}
export function applyMenuSettings(data: MenuSettings) { ++loadId; Object.assign(menuSettings, data) }
