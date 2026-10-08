export interface InventoryImageRow {
  category_label: string
  category_first: boolean
  category_rowspan: number
  spec_name: string
  values: Record<string, number>
  modified_months: string[]
  summary: number
}
export interface InventoryImageCard {
  title: string
  summaryLabel: string
  rows: InventoryImageRow[]
  totals: Record<string, number>
  summary: number
}
export interface InventoryImageReport {
  title: string
  source: string
  columns: Array<{ key: string; label: string }>
  cards: InventoryImageCard[]
}

/** Render every row and column, independent of viewport size and scroll position. */
export async function renderInventoryImage(report: InventoryImageReport): Promise<Blob> {
  await document.fonts.ready
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('无法生成图片，请更换浏览器重试')
  const font = '"PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.font = `16px ${font}`
  const measure = (texts: string[], minimum: number) => Math.ceil(Math.max(minimum, ...texts.map(text => ctx.measureText(text).width + 28)))
  const allRows = report.cards.flatMap(card => card.rows)
  const widths = [
    measure(['状态', '合计', ...allRows.map(row => row.category_label)], 90),
    measure(['钢瓶规格', '全部状态', ...allRows.map(row => row.spec_name)], 130),
    ...report.columns.map(column => measure([column.label,
      ...allRows.map(row => String(row.values[column.key] ?? 0)),
      ...report.cards.map(card => String(card.totals[column.key] ?? 0))], 112)),
    measure(report.cards.flatMap(card => [card.summaryLabel, String(card.summary), ...card.rows.map(row => String(row.summary))]), 130),
  ]
  const padding = 28, rowHeight = 44, headerHeight = 48, cardHeader = 54, gap = 24
  const tableWidth = widths.reduce((sum, width) => sum + width, 0)
  const width = Math.max(800, tableWidth + padding * 2)
  const wrap = (text: string, maxWidth: number) => {
    const lines: string[] = []; let line = ''
    for (const char of text) {
      if (line && ctx.measureText(line + char).width > maxWidth) { lines.push(line); line = char }
      else line += char
    }
    lines.push(line); return lines
  }
  const sourceLines = wrap(`公司：${report.source}`, width - padding * 2)
  const headingHeight = 96 + sourceLines.length * 24
  const height = headingHeight + report.cards.reduce((sum, card) => sum + cardHeader + headerHeight + (card.rows.length + 1) * rowHeight + gap, 0) + 38
  const scale = Math.min(2, 16000 / Math.max(width, height), Math.sqrt(24000000 / (width * height)))
  if (scale < 0.65) throw new Error('数据较多，请按卡片复制或缩小查询区间后重试')
  canvas.width = Math.ceil(width * scale); canvas.height = Math.ceil(height * scale)
  ctx.scale(scale, scale)
  ctx.fillStyle = '#f3f4f6'; ctx.fillRect(0, 0, width, height)
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#202329'; ctx.font = `bold 26px ${font}`
  ctx.fillText(report.title, padding, 34)
  ctx.font = `16px ${font}`; ctx.fillStyle = '#555b63'
  sourceLines.forEach((line, index) => ctx.fillText(line, padding, 70 + index * 24))
  const first = report.columns[0]?.key || '—', last = report.columns.at(-1)?.key || '—'
  ctx.fillText(`查询区间：${first} 至 ${last}`, padding, 70 + sourceLines.length * 24)
  const cell = (text: string, x: number, y: number, w: number, h: number, bg: string, bold = false, left = false) => {
    ctx.fillStyle = bg; ctx.fillRect(x, y, w, h)
    ctx.strokeStyle = '#dfe2e6'; ctx.lineWidth = 1; ctx.strokeRect(x + 0.5, y + 0.5, w, h)
    ctx.fillStyle = '#252a32'; ctx.font = `${bold ? 'bold ' : ''}16px ${font}`
    ctx.textAlign = left ? 'left' : 'right'
    ctx.fillText(text, left ? x + 12 : x + w - 12, y + h / 2)
    ctx.textAlign = 'left'
  }
  let y = headingHeight
  for (const card of report.cards) {
    ctx.fillStyle = '#ffffff'; ctx.fillRect(padding, y, tableWidth, cardHeader)
    ctx.fillStyle = '#e82127'; ctx.fillRect(padding, y + 16, 4, 22)
    ctx.fillStyle = '#202329'; ctx.font = `bold 21px ${font}`
    ctx.fillText(card.title, padding + 16, y + cardHeader / 2)
    y += cardHeader
    let x = padding
    const headers = ['状态', '钢瓶规格', ...report.columns.map(column => column.label), card.summaryLabel]
    headers.forEach((label, i) => { cell(label, x, y, widths[i], headerHeight, '#eef0f3', true, i < 2); x += widths[i] })
    y += headerHeight
    for (const row of card.rows) {
      if (row.category_first) cell(row.category_label, padding, y, widths[0], rowHeight * row.category_rowspan, '#fafafa', true, true)
      x = padding + widths[0]
      cell(row.spec_name, x, y, widths[1], rowHeight, '#ffffff', true, true); x += widths[1]
      report.columns.forEach((column, i) => {
        cell(String(row.values[column.key] ?? 0), x, y, widths[i + 2], rowHeight, '#ffffff')
        if (row.modified_months.includes(column.key)) {
          ctx.fillStyle = '#e82127'; ctx.beginPath(); ctx.moveTo(x + widths[i + 2] - 8, y); ctx.lineTo(x + widths[i + 2], y); ctx.lineTo(x + widths[i + 2], y + 8); ctx.fill()
        }
        x += widths[i + 2]
      })
      cell(String(row.summary), x, y, widths[widths.length - 1], rowHeight, '#f8f9fa', true)
      y += rowHeight
    }
    x = padding
    const totals = ['合计', '全部状态', ...report.columns.map(column => String(card.totals[column.key] ?? 0)), String(card.summary)]
    totals.forEach((value, i) => { cell(value, x, y, widths[i], rowHeight, '#eef0f3', true, i < 2); x += widths[i] })
    y += rowHeight + gap
  }
  ctx.font = `13px ${font}`; ctx.fillStyle = '#6b7280'
  ctx.fillText('锦安特种设备检测 · 红色角标表示人工修改的盘点值', padding, height - 22)
  return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('图片生成失败，请重试')), 'image/png'))
}
