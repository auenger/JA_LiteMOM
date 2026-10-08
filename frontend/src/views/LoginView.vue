<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api, { errorMessage } from '../api'
import { setSession } from '../auth'
import { clearLoginCredentials, readLoginCredentials, readRememberPreference, saveLoginCredentials, saveRememberPreference } from '../loginCredentials'
import GameIcon from '../components/GameIcon.vue'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const savedCredentials = readLoginCredentials()
const form = reactive({ username: savedCredentials?.username || '', password: savedCredentials?.password || '' })
const rememberCredentials = ref(readRememberPreference())

async function submit() {
  if (loading.value) return
  error.value = ''
  if (!form.username.trim() || !form.password) {
    error.value = '请输入登录账号和密码'
    return
  }
  loading.value = true
  try {
    const username = form.username.trim()
    const { data } = await api.post('/auth/login', { username, password: form.password })
    setSession(data.access_token, data.user)
    saveRememberPreference(rememberCredentials.value)
    if (rememberCredentials.value) saveLoginCredentials({ username, password: form.password })
    else clearLoginCredentials()
    await router.replace('/dashboard')
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-shell">
      <div class="login-brand">
        <div class="brand-mark">锦</div>
        <h1>锦安特种设备检测</h1>
        <h2>钢瓶检测与仓储协同平台</h2>
        <p>覆盖钢瓶入库、抄码、检验、出库和原材料管理，全程留痕。</p>
        <div class="login-features">
          <div class="login-feature"><strong>钢瓶流转</strong><span>五区库存、良品出库与快捷抄码</span></div>
          <div class="login-feature"><strong>检验业务</strong><span>每日检验单与单瓶检测报告</span></div>
          <div class="login-feature"><strong>上游核验</strong><span>驳回标注、未验证瓶子池与历史归档</span></div>
          <div class="login-feature"><strong>物料管理</strong><span>采购、库存预警与出入库记录</span></div>
        </div>
        <div class="login-watermark" aria-label="项目来源：苏州硅基源流，原舒雅FDE实验项目">
          <span>苏州硅基源流</span>
          <a href="https://siliroot.com/" target="_blank" rel="noopener noreferrer">https://siliroot.com/</a>
          <span>原舒雅FDE实验项目</span>
        </div>
      </div>
      <div class="login-form-panel">
        <h3>欢迎登录</h3>
        <p>使用管理员分配的账号进入工作台。</p>
        <el-form label-position="top" @submit.prevent="submit">
          <el-form-item label="登录账号">
            <el-input v-model="form.username" name="username" size="large" autocomplete="username" placeholder="请输入登录账号"><template #prefix><GameIcon name="user" /></template></el-input>
          </el-form-item>
          <el-form-item label="登录密码">
            <el-input v-model="form.password" name="password" size="large" type="password" show-password autocomplete="current-password" placeholder="请输入登录密码"><template #prefix><GameIcon name="lock" /></template></el-input>
          </el-form-item>
          <div class="login-remember"><el-checkbox v-model="rememberCredentials">记住账号和密码</el-checkbox><span>仅限可信设备</span></div>
          <el-alert v-if="error" class="login-error" :title="error" type="error" :closable="false" />
          <el-button class="w-full login-submit" type="primary" size="large" native-type="submit" :loading="loading">登录系统</el-button>
        </el-form>
        <div class="login-footnote">登录成功后，勾选的账号和密码会保存在当前浏览器。共用电脑请取消勾选；首次登录后请及时修改初始密码。</div>
      </div>
    </section>
  </main>
</template>
