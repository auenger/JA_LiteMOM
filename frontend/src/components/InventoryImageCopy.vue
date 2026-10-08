<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { renderInventoryImage, type InventoryImageReport } from '../inventoryImage'
const props = defineProps<InventoryImageReport & { disabled?: boolean }>()
const copying = ref(false), preview = ref(false), imageUrl = ref(''), filename = ref('盘点结果.png')
let disposed = false
onUnmounted(() => { disposed = true; if (imageUrl.value) URL.revokeObjectURL(imageUrl.value) })
async function copy() {
  if (props.disabled || copying.value) return
  copying.value = true
  const snapshot: InventoryImageReport = JSON.parse(JSON.stringify({ title: props.title, source: props.source, columns: props.columns, cards: props.cards }))
  filename.value = `${snapshot.title}-${snapshot.columns[0]?.key || ''}-${snapshot.columns.at(-1)?.key || ''}.png`
  const image = renderInventoryImage(snapshot)
  // Handle rejection immediately, including when ClipboardItem is unsupported.
  void image.catch(() => {})
  try {
    if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') throw new Error('图片剪贴板不可用')
    // Pass the promise while the click still has user activation (Safari).
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': image })])
    if (!disposed) ElMessage.success('完整盘点图片已复制，可直接粘贴')
  } catch {
    try {
      const blob = await image
      if (disposed) return
      if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
      imageUrl.value = URL.createObjectURL(blob); preview.value = true
    } catch (err) { if (!disposed) ElMessage.error(err instanceof Error ? err.message : '图片生成失败') }
  } finally { copying.value = false }
}
function download() { const link = document.createElement('a'); link.href = imageUrl.value; link.download = filename.value; link.click() }
</script>
<template>
  <el-button :disabled="disabled" :loading="copying" :aria-label="`${title}复制结果`" @click="copy">复制结果</el-button>
  <el-dialog v-model="preview" title="盘点结果图片" width="min(1100px, 94vw)" append-to-body>
    <el-alert title="当前浏览器无法直接复制图片。完整图片已生成，可右键或长按图片复制，也可下载保存。" type="info" :closable="false" />
    <div class="image-preview"><img :src="imageUrl" :alt="title" /></div>
    <template #footer><el-button @click="preview = false">关闭</el-button><el-button type="primary" @click="download">下载图片</el-button></template>
  </el-dialog>
</template>
<style scoped>
.image-preview { margin-top: 16px; max-height: 65vh; overflow: auto; background: #f3f4f6; }
.image-preview img { display: block; max-width: none; }
</style>
