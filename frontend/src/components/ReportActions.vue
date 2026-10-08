<script setup lang="ts">
import { ElMessage } from 'element-plus'
import GameIcon from './GameIcon.vue'

const props = withDefaults(defineProps<{
  title: string
  lines: string[]
  filename?: string
  showPrint?: boolean
  showCopy?: boolean
  showImage?: boolean
}>(), { filename: '业务报表', showPrint: true, showCopy: true, showImage: true })

const reportText = () => [props.title, ...props.lines].join('\n')
const escapeHtml = (value: string) => value.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char] || char)

function printReport() {
  const popup = window.open('', '_blank', 'width=900,height=720')
  if (!popup) return ElMessage.warning('浏览器阻止了打印窗口，请允许弹出窗口后重试')
  popup.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(props.title)}</title><style>@page{margin:16mm}body{font-family:"PingFang SC","Microsoft YaHei",sans-serif;color:#181b21;margin:0}h1{font-size:22px;margin:0 0 22px;padding-bottom:12px;border-bottom:2px solid #e82127}.line{padding:7px 0;border-bottom:1px solid #e5e7eb;white-space:pre-wrap;font-size:14px}.foot{margin-top:22px;color:#73777f;font-size:11px}@media print{button{display:none}}</style></head><body><h1>${escapeHtml(props.title)}</h1>${props.lines.map((line) => `<div class="line">${escapeHtml(line)}</div>`).join('')}<div class="foot">锦安特种设备检测 · ${new Date().toLocaleString('zh-CN')}</div><script>window.onload=()=>{window.print()}<\/script></body></html>`)
  popup.document.close()
}

async function copyReport() {
  try {
    await navigator.clipboard.writeText(reportText())
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = reportText(); document.body.appendChild(textarea); textarea.select(); document.execCommand('copy'); textarea.remove()
  }
  ElMessage.success('报表文字已复制')
}

function wrappedLines(ctx: CanvasRenderingContext2D, text: string, maxWidth: number) {
  const output: string[] = []
  let current = ''
  for (const char of text) {
    if (ctx.measureText(current + char).width > maxWidth && current) { output.push(current); current = char } else current += char
  }
  if (current) output.push(current)
  return output.length ? output : ['']
}

function downloadImage() {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const width = 1000; const padding = 60; const contentWidth = width - padding * 2
  ctx.font = '28px "PingFang SC", "Microsoft YaHei", sans-serif'
  const bodyLines = props.lines.flatMap((line) => wrappedLines(ctx, line, contentWidth))
  canvas.width = width; canvas.height = Math.max(360, 155 + bodyLines.length * 46 + 70)
  ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.fillStyle = '#e82127'; ctx.fillRect(0, 0, 12, canvas.height)
  ctx.fillStyle = '#181b21'; ctx.font = 'bold 38px "PingFang SC", "Microsoft YaHei", sans-serif'; ctx.fillText(props.title, padding, 72)
  ctx.strokeStyle = '#e3e5e8'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(padding, 105); ctx.lineTo(width - padding, 105); ctx.stroke()
  ctx.font = '28px "PingFang SC", "Microsoft YaHei", sans-serif'
  let y = 150
  for (const line of bodyLines) { ctx.fillStyle = '#2e3033'; ctx.fillText(line, padding, y); y += 46 }
  ctx.fillStyle = '#73777f'; ctx.font = '20px "PingFang SC", sans-serif'; ctx.fillText(`锦安特种设备检测 · ${new Date().toLocaleString('zh-CN')}`, padding, canvas.height - 35)
  const anchor = document.createElement('a'); anchor.download = `${props.filename}.png`; anchor.href = canvas.toDataURL('image/png'); anchor.click()
}
</script>

<template>
  <div class="report-actions">
    <el-button v-if="showPrint" @click="printReport"><GameIcon name="clipboard" />打印</el-button>
    <el-button v-if="showCopy" @click="copyReport"><GameIcon name="clipboard" />复制文字</el-button>
    <el-button v-if="showImage" @click="downloadImage"><GameIcon name="save" />下载图片</el-button>
  </div>
</template>

<style scoped>.report-actions{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap}@media(max-width:600px){.report-actions{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));width:100%}.report-actions :deep(.el-button){width:100%;margin:0;padding-left:8px;padding-right:8px}}</style>
