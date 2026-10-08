import { createRouter, createWebHistory } from 'vue-router'
import { auth, has, loadMe } from './auth'
const AppShell = () => import('./components/AppShell.vue')
const LoginView = () => import('./views/LoginView.vue')
const DashboardView = () => import('./views/DashboardView.vue')
const UsersView = () => import('./views/UsersView.vue')
const MenuSettingsView = () => import('./views/MenuSettingsView.vue')
const MaterialDailyLogsView = () => import('./views/MaterialDailyLogsView.vue')
const MaterialDailyView = () => import('./views/MaterialDailyView.vue')
const MaterialsView = () => import('./views/MaterialsView.vue')
const MasterDataView = () => import('./views/MasterDataView.vue')
const MaterialDocumentsView = () => import('./views/MaterialDocumentsView.vue')
const BottleInboundView = () => import('./views/BottleInboundView.vue')
const CodingView = () => import('./views/CodingView.vue')
const InspectionView = () => import('./views/InspectionView.vue')
const InspectionDocumentsView = () => import('./views/InspectionDocumentsView.vue')
const InspectionWordCodesView = () => import('./views/InspectionWordCodesView.vue')
const UnverifiedBottlesView = () => import('./views/UnverifiedBottlesView.vue')
const BottleZonesView = () => import('./views/BottleZonesView.vue')
const QuickEntryView = () => import('./views/QuickEntryView.vue')
const QuickInboundView = () => import('./views/QuickInboundView.vue')
const QuickOutboundView = () => import('./views/QuickOutboundView.vue')
const CodingPoolView = () => import('./views/CodingPoolView.vue')
const QuickConfigView = () => import('./views/QuickConfigView.vue')
const ProfitAnalysisView = () => import('./views/ProfitAnalysisView.vue')
const PurchaseOrdersView = () => import('./views/PurchaseOrdersView.vue')
const MonthlyInventoryView = () => import('./views/MonthlyInventoryView.vue')
const DailyInventoryView = () => import('./views/DailyInventoryView.vue')
const BottleLifecycleView = () => import('./views/BottleLifecycleView.vue')

declare module 'vue-router' {
  interface RouteMeta {
    permission?: string
    permissionAny?: string[]
    superadmin?: boolean
    title?: string
  }
}

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', component: DashboardView, meta: { permission: 'dashboard:view', title: '工作台' } },
        { path: 'menu-settings', component: MenuSettingsView, meta: { superadmin: true, title: '菜单设置' } },
        { path: 'material-daily-logs', component: MaterialDailyLogsView, meta: { permission: 'material_daily_logs:view', title: '出入库日志' } },
        { path: 'material-daily', component: MaterialDailyView, meta: { permission: 'material_daily:view', title: '原材料出入库管理' } },
        { path: 'materials', component: MaterialsView, meta: { permission: 'materials:view', title: '原材料档案' } },
        { path: 'suppliers', component: MasterDataView, props: { kind: 'suppliers' }, meta: { permission: 'suppliers:view', title: '供应商' } },
        { path: 'purchase-orders', component: PurchaseOrdersView, meta: { permission: 'purchase_orders:view', title: '供应商采购单' } },
        { path: 'bottle-sources', component: MasterDataView, props: { kind: 'sources' }, meta: { permission: 'sources:view', title: '供瓶单位' } },
        { path: 'bottle-specs', component: MasterDataView, props: { kind: 'specs' }, meta: { permission: 'specs:view', title: '瓶子规格' } },
        { path: 'bottle-manufacturers', component: MasterDataView, props: { kind: 'manufacturers' }, meta: { permission: 'manufacturers:view', title: '钢瓶生产厂家' } },
        { path: 'material-documents', redirect: '/material-inbounds' },
        { path: 'material-inbounds', component: MaterialDocumentsView, props: { documentType: 'NORMAL_IN' }, meta: { permission: 'material_inbound:view', title: '原材料入库管理' } },
        { path: 'material-outbounds', component: MaterialDocumentsView, props: { documentType: 'OUTBOUND' }, meta: { permission: 'material_outbound:view', title: '材料出库管理' } },
        { path: 'material-returns', component: MaterialDocumentsView, props: { documentType: 'RETURN_IN' }, meta: { permission: 'material_return:view', title: '退料入库管理' } },
        { path: 'bottle-inbounds', component: BottleInboundView, meta: { permissionAny: ['bottle_inbound:view', 'bottle_outbound:view'], title: '出入库历史记录' } },
        { path: 'quick-entry', redirect: '/quick-coding' },
        { path: 'quick-inbound', component: QuickInboundView, meta: { permission: 'quick_inbound:view', title: '快速入库' } },
        { path: 'quick-outbound', component: QuickOutboundView, meta: { permission: 'quick_outbound:view', title: '快速出库' } },
        { path: 'bottle-lifecycle', component: BottleLifecycleView, meta: { permission: 'bottle_lifecycle:view', title: '瓶子生命周期' } },
        { path: 'quick-coding', component: QuickEntryView, meta: { permission: 'quick_entry:view', title: '快捷抄码' } },
        { path: 'inspection-documents', component: InspectionDocumentsView, meta: { permission: 'inspection_documents:view', title: '钢瓶检验单' } },
        { path: 'inspection-word-codes', component: InspectionWordCodesView, meta: { superadmin: true, title: 'Word 报告编号管理' } },
        { path: 'unverified-bottles', component: UnverifiedBottlesView, meta: { permission: 'unverified_bottles:view', title: '未经系统验证瓶子池' } },
        { path: 'coding-pool', component: CodingPoolView, meta: { permission: 'coding_pool:view', title: '待抄码池' } },
        { path: 'quick-configs', component: QuickConfigView, meta: { permission: 'quick_configs:view', title: '抄码快捷配置' } },
        { path: 'profit-analysis', component: ProfitAnalysisView, meta: { permission: 'profit:view', title: '盈利成本计算' } },
        { path: 'coding', component: CodingView, meta: { permission: 'coding:view', title: '抄码记录' } },
        { path: 'inspection', redirect: '/bottle-quality' },
        { path: 'bottle-quality', component: InspectionView, meta: { permission: 'inspection:view', title: '质量分类库' } },
        { path: 'bottle-outbounds', redirect: '/bottle-inbounds?tab=outbound' },
        { path: 'bottle-zones', component: BottleZonesView, meta: { permission: 'bottle_zones:view', title: '钢瓶库存' } },
        { path: 'monthly-inventory', component: MonthlyInventoryView, meta: { permission: 'monthly_inventory:view', title: '月度盘点' } },
        { path: 'daily-inventory', component: DailyInventoryView, meta: { permission: 'daily_inventory:view', title: '日度盘点' } },
        { path: 'users', component: UsersView, meta: { permission: 'users:view', title: '人员与权限' } },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  if (to.path === '/login') {
    if (localStorage.getItem('wms_token')) {
      try {
        await loadMe()
        return '/dashboard'
      } catch {
        return true
      }
    }
    return true
  }
  if (!localStorage.getItem('wms_token')) return '/login'
  if (!auth.ready || !auth.user) {
    try {
      await loadMe()
    } catch {
      return '/login'
    }
  }
  if (to.meta.superadmin && !auth.user?.is_superadmin) return '/inspection-documents'
  const canAccess = to.meta.permissionAny ? to.meta.permissionAny.some((permission) => has(permission)) : has(to.meta.permission)
  if (!canAccess) {
    const fallbacks = [
      ['/material-daily', 'material_daily:view'], ['/dashboard', 'dashboard:view'], ['/materials', 'materials:view'], ['/purchase-orders', 'purchase_orders:view'], ['/material-inbounds', 'material_inbound:view'], ['/material-outbounds', 'material_outbound:view'], ['/material-returns', 'material_return:view'], ['/material-daily-logs', 'material_daily_logs:view'],
      ['/bottle-inbounds', 'bottle_inbound:view'], ['/bottle-inbounds?tab=outbound', 'bottle_outbound:view'], ['/coding', 'coding:view'], ['/bottle-quality', 'inspection:view'],
      ['/quick-inbound', 'quick_inbound:view'], ['/quick-outbound', 'quick_outbound:view'], ['/quick-coding', 'quick_entry:view'], ['/coding-pool', 'coding_pool:view'],
      ['/inspection-documents', 'inspection_documents:view'],
      ['/bottle-lifecycle', 'bottle_lifecycle:view'],
      ['/unverified-bottles', 'unverified_bottles:view'],
      ['/bottle-zones', 'bottle_zones:view'], ['/suppliers', 'suppliers:view'], ['/bottle-sources', 'sources:view'],
      ['/monthly-inventory', 'monthly_inventory:view'], ['/daily-inventory', 'daily_inventory:view'],
      ['/bottle-specs', 'specs:view'], ['/bottle-manufacturers', 'manufacturers:view'], ['/users', 'users:view'],
      ['/profit-analysis', 'profit:view'],
    ]
    const target = fallbacks.find(([, permission]) => has(permission))?.[0]
    if (target && target !== to.path) return target
    if (!target) {
      localStorage.removeItem('wms_token')
      localStorage.removeItem('wms_user')
      return '/login'
    }
  }
  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '登录'} | 锦安特种设备检测`
})

export default router
