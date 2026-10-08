<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { errorMessage } from '../api'
import { auth, has, loadMe, logout } from '../auth'
import { updateSavedPassword } from '../loginCredentials'
import GameIcon from './GameIcon.vue'
import { arrangedMenus, loadMenuSettings } from '../menu'

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)
const mobileOpen = ref(false)
const passwordDialog = ref(false)
const passwordLoading = ref(false)
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' })
const viewRefreshKey = ref(0)

watch(() => route.fullPath, async () => {
  await nextTick()
  window.scrollTo({ top: 0, left: 0 })
}, { immediate: true })



function canViewItem(item: { permission?: string; permissions?: string[]; superadmin?: boolean }) {
  if (item.superadmin) return Boolean(auth.user?.is_superadmin)
  return item.permissions ? item.permissions.some((permission) => has(permission)) : has(item.permission)
}

const visibleGroups = computed(() => arrangedMenus()
  .map((group) => ({ ...group, items: group.items.filter(item => !item.hidden && canViewItem(item)) }))
  .filter((group) => group.items.length))

async function refreshMenus() {
  try { await loadMenuSettings() } catch { /* Keep usable navigation if settings cannot be loaded. */ }
}
onMounted(() => { refreshMenus(); window.addEventListener('focus', refreshMenus) })
onUnmounted(() => window.removeEventListener('focus', refreshMenus))

function navigate(path: string) {
  mobileOpen.value = false
  if (route.path === path) {
    viewRefreshKey.value += 1
    return
  }
  router.push(path)
}

function signOut() {
  logout()
  router.replace('/login')
}

async function changePassword() {
  if (passwordForm.value.new_password.length < 8) return ElMessage.warning('新密码至少 8 位')
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) return ElMessage.warning('两次输入的新密码不一致')
  passwordLoading.value = true
  try {
    await api.post('/auth/change-password', { old_password: passwordForm.value.old_password, new_password: passwordForm.value.new_password })
    if (auth.user) updateSavedPassword(auth.user.username, passwordForm.value.new_password)
    await loadMe()
    passwordDialog.value = false
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
    ElMessage.success('密码已修改')
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { passwordLoading.value = false }
}
</script>

<template>
  <div class="app-shell" :class="{ 'is-collapsed': collapsed, 'mobile-open': mobileOpen }">
    <header class="topbar">
      <button class="icon-button menu-toggle" aria-label="展开导航" @click="mobileOpen = !mobileOpen">
        <GameIcon name="menu" />
      </button>
      <div class="brand-block">
        <div class="brand-mark">锦</div>
        <div class="brand-copy">
          <strong>锦安特种设备检测</strong>
          <small>钢瓶检测与仓储管理</small>
        </div>
      </div>
      <div class="topbar-spacer" />
      <div class="topbar-watermark" aria-label="项目来源：苏州硅基源流，原舒雅FDE实验项目">
        <span>苏州硅基源流</span>
        <a href="https://siliroot.com/" target="_blank" rel="noopener noreferrer">https://siliroot.com/</a>
        <span>原舒雅FDE实验项目</span>
      </div>
      <button class="icon-button alert-button" aria-label="库存预警" @click="router.push('/dashboard')">
        <GameIcon name="notification" />
      </button>
      <button class="user-chip" title="修改密码" @click="passwordDialog = true">
        <span class="avatar">{{ auth.user?.name.slice(0, 1) }}</span>
        <span class="user-copy"><strong>{{ auth.user?.name }}</strong><small>{{ auth.user?.role_name || (auth.user?.is_superadmin ? '超级管理员' : '业务人员') }}</small></span>
      </button>
      <button class="topbar-logout" @click="signOut"><GameIcon name="door" /><span>退出</span></button>
    </header>

    <aside class="sidebar" :aria-hidden="!mobileOpen && undefined">
      <nav aria-label="系统导航">
        <section v-for="group in visibleGroups" :key="group.label" class="nav-group">
          <div class="nav-heading">{{ group.label }}</div>
          <el-tooltip
            v-for="item in group.items"
            :key="item.path"
            :content="item.label"
            placement="right"
            :disabled="!collapsed"
            :show-after="180"
          >
            <button
              class="nav-item"
              :class="{ active: route.path === item.path }"
              :aria-label="item.label"
              @click="navigate(item.path)"
            >
              <GameIcon :name="item.icon" />
              <span class="nav-label">{{ item.label }}</span>
            </button>
          </el-tooltip>
        </section>
      </nav>
      <el-tooltip content="展开导航" placement="right" :disabled="!collapsed" :show-after="180">
        <button class="collapse-button" :aria-label="collapsed ? '展开导航' : '收起导航'" @click="collapsed = !collapsed">
          <GameIcon name="menu" /><span class="collapse-label">{{ collapsed ? '展开导航' : '收起导航' }}</span>
        </button>
      </el-tooltip>
    </aside>
    <button v-if="mobileOpen" class="mobile-scrim" aria-label="关闭导航" @click="mobileOpen = false" />

    <main class="workspace">
      <el-alert
        v-if="auth.user?.must_change_password"
        class="password-alert"
        title="当前账号仍在使用初始密码，请联系超级管理员重置或尽快修改。"
        type="warning"
        :closable="false"
      />
      <router-view :key="`${route.fullPath}:${viewRefreshKey}`" />
    </main>

    <div v-if="!['/quick-inbound', '/quick-outbound', '/quick-coding'].includes(route.path)" class="mobile-quick-actions">
      <button v-if="has('quick_inbound:view') && route.path !== '/quick-inbound'" class="mobile-quick-entry secondary" aria-label="打开快速入库" @click="navigate('/quick-inbound')"><GameIcon name="user-add" :size="20" /><span>快速入库</span></button>
      <button v-if="has('quick_entry:view') && route.path !== '/quick-coding'" class="mobile-quick-entry" aria-label="打开快捷抄码" @click="navigate('/quick-coding')"><GameIcon name="qr-code" :size="20" /><span>快捷抄码</span></button>
    </div>

    <el-dialog v-model="passwordDialog" title="修改登录密码" width="460px">
      <el-form label-position="top">
        <el-form-item label="当前密码"><el-input v-model="passwordForm.old_password" type="password" show-password autocomplete="current-password" /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="passwordForm.new_password" type="password" show-password autocomplete="new-password" placeholder="至少 8 位" /></el-form-item>
        <el-form-item label="确认新密码"><el-input v-model="passwordForm.confirm_password" type="password" show-password autocomplete="new-password" /></el-form-item>
      </el-form>
      <template #footer><div class="dialog-footer"><el-button @click="passwordDialog = false">取消</el-button><el-button type="primary" :loading="passwordLoading" @click="changePassword">修改密码</el-button></div></template>
    </el-dialog>
  </div>
</template>
