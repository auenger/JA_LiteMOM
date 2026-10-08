<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { errorMessage } from '../api'
import { auth, has } from '../auth'
import type { BottleSource, BottleSpec } from '../types'
import EmptyState from '../components/EmptyState.vue'
import GameIcon from '../components/GameIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import { quantityText, selectQuantity } from '../quantityInput'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const sources = ref<BottleSource[]>([])
const specs = ref<BottleSpec[]>([])
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const form = reactive<any>({ business_date: today, source_id: undefined, handler: auth.user?.name || '', note: '', lines: [] })
const total = computed(() => form.lines.reduce((sum: number, line: any) => sum + line.pending_quantity + line.temporary_quantity + line.scrap_quantity, 0))

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/options')
    sources.value = data.sources; specs.value = data.specs
    form.source_id = sources.value.find((item) => item.is_default)?.id || sources.value[0]?.id
    form.lines = specs.value.map((item) => ({ spec_id: item.id, spec_name: item.name, pending_quantity: 0, temporary_quantity: 0, scrap_quantity: 0 }))
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { loading.value = false }
}
async function submit() {
  if (!form.business_date || !form.source_id || total.value <= 0) return ElMessage.warning('请选择入库日期、供瓶单位并填写至少一项入库数量')
  saving.value = true
  try {
    await api.post('/quick-inbound', { ...form, lines: form.lines.filter((line: any) => line.pending_quantity + line.temporary_quantity + line.scrap_quantity > 0) })
    ElMessage.success(`快速入库成功，共 ${total.value} 只`)
    form.note = ''; form.lines.forEach((line: any) => Object.assign(line, { pending_quantity: 0, temporary_quantity: 0, scrap_quantity: 0 }))
  } catch (err) { ElMessage.error(errorMessage(err)) } finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <div v-loading="loading" class="quick-inbound-page">
    <PageHeader title="快速入库" description="按钢瓶规格登记待检测、暂存和报废数量，保存后直接形成有效入库单。"><el-button v-if="has('quick_outbound:view')" @click="router.push('/quick-outbound')"><GameIcon name="door" />去快速出库</el-button></PageHeader>
    <section class="surface context-card"><div><label for="quick-inbound-date">入库日期</label><el-date-picker id="quick-inbound-date" v-model="form.business_date" type="date" value-format="YYYY-MM-DD" :clearable="false" placeholder="选择入库日期" /></div><div><span>本次总量</span><strong>{{ total }}</strong></div></section>
    <section class="surface quick-inbound-form">
      <div class="quick-block"><label>供瓶单位</label><div class="choice-grid"><button v-for="item in sources" :key="item.id" class="choice" :class="{ selected: form.source_id === item.id }" @click="form.source_id = item.id"><GameIcon name="user-group" /><strong>{{ item.name }}</strong><small v-if="item.is_default">默认</small></button></div></div>
      <div class="quick-block"><div class="block-title"><strong>按规格填写数量</strong><small>待检测数量将进入待抄码池</small></div><div v-if="specs.length" class="spec-lines" @focusin="selectQuantity"><div v-for="line in form.lines" :key="line.spec_id" class="spec-line"><strong>{{ line.spec_name }}</strong><label>待检测<el-input-number v-model="line.pending_quantity" :min="0" :precision="0" :controls="false" :formatter="quantityText" inputmode="numeric" /></label><label>暂存<el-input-number v-model="line.temporary_quantity" :min="0" :precision="0" :controls="false" :formatter="quantityText" inputmode="numeric" /></label><label>报废<el-input-number v-model="line.scrap_quantity" :min="0" :precision="0" :controls="false" :formatter="quantityText" inputmode="numeric" /></label></div></div><EmptyState v-else title="请先配置钢瓶规格" /></div>
      <div class="quick-block"><label>备注（选填）</label><el-input v-model="form.note" maxlength="200" show-word-limit placeholder="本批钢瓶的补充说明" /></div>
      <button class="quick-action" :disabled="saving || !has('quick_inbound:create') || total <= 0" @click="submit"><GameIcon :name="saving ? 'refresh' : 'save'" /><span>{{ saving ? '正在入库' : '确认快速入库' }}</span></button>
    </section>
  </div>
</template>

<style scoped>
.quick-inbound-page{max-width:900px;margin:0 auto}.context-card{display:grid;grid-template-columns:1fr 1fr;margin-bottom:16px}.context-card>div{padding:17px 20px}.context-card>div+div{border-left:1px solid var(--ja-line)}.context-card label,.context-card span,.context-card strong{display:block}.context-card label,.context-card span{margin-bottom:6px;color:var(--ja-muted);font-size:11px}.context-card strong{margin-top:4px;font-size:23px}.context-card :deep(.el-date-editor){width:180px}.quick-inbound-form{padding:20px}.quick-block{margin-bottom:22px}.quick-block>label,.block-title strong{display:block;margin-bottom:10px;font-weight:700}.block-title{display:flex;justify-content:space-between}.block-title small{color:var(--ja-muted)}.choice-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.choice{display:grid;grid-template-columns:24px 1fr auto;align-items:center;gap:8px;padding:13px;color:var(--ja-text);background:#fff;border:1px solid var(--ja-line);border-radius:var(--ja-radius);text-align:left}.choice.selected{color:var(--ja-red);background:var(--ja-red-soft);border-color:var(--ja-red)}.spec-lines{display:grid;gap:10px}.spec-line{display:grid;grid-template-columns:minmax(110px,1fr) repeat(3,minmax(90px,130px));gap:10px;align-items:end;padding:13px;background:#f7f8f9;border-radius:var(--ja-radius)}.spec-line label{color:var(--ja-muted);font-size:11px}.spec-line :deep(.el-input-number){width:100%;margin-top:5px}.quick-action{width:100%;height:52px;display:flex;justify-content:center;align-items:center;gap:8px;color:#fff;background:var(--ja-red);border:0;border-radius:var(--ja-radius);font-weight:700}.quick-action:disabled{opacity:.45}@media(max-width:760px){.quick-inbound-form{padding:14px}.choice-grid{grid-template-columns:repeat(2,1fr)}.spec-line{grid-template-columns:1fr 1fr}.spec-line>strong{grid-column:1/-1}.block-title{display:block}.block-title small{display:block;margin-top:-5px;margin-bottom:10px}}
</style>
