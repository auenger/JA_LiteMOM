import {
  AlignmentType, BorderStyle, Document, Packer, Paragraph, ShadingType,
  Table, TableCell, TableLayoutType, TableRow, TextRun, WidthType,
} from 'docx'

export interface ReceiptLine {
  spec_id: number; spec_name: string; pending: number; good: number; bad: number
  temporary: number; scrap: number; total: number
}
export interface ReceiptQualityBottle {
  spec_id: number; spec_name: string; zone: 'BAD' | 'SCRAP'; zone_name: string
  quantity: number; body_code: string; note: string
}
export interface ReceiptDocument {
  id: number; direction: 'inbound' | 'outbound'; document_no: string; business_date: string
  customer: string; handler: string; note: string; total: number; lines: ReceiptLine[]
  quality_bottles: ReceiptQualityBottle[]
}
export interface ReceiptReport {
  company: string; customer: string; date_from: string; date_to: string
  inbound_count: number; outbound_count: number; inbound_total: number; outbound_total: number
  spec_summary: Array<{ spec_id: number; spec_name: string; inbound: number; outbound: number }>
  documents: ReceiptDocument[]; notes_text: string; text: string; warnings: string[]
}

function quantitySummary(report: ReceiptReport, direction: 'inbound' | 'outbound') {
  const grouped = new Map<string, { business_date: string; spec_name: string; quantity: number }>()
  for (const document of report.documents.filter(item => item.direction === direction)) {
    for (const line of document.lines) {
      const key = `${document.business_date}|${line.spec_id}`
      const current = grouped.get(key) || { business_date: document.business_date, spec_name: line.spec_name, quantity: 0 }
      current.quantity += line.total
      grouped.set(key, current)
    }
  }
  return Array.from(grouped.values()).sort((a, b) => a.business_date.localeCompare(b.business_date) || a.spec_name.localeCompare(b.spec_name))
}

function qualitySummary(report: ReceiptReport) {
  return report.documents.flatMap(document => document.quality_bottles.map(item => ({
    business_date: document.business_date,
    spec_name: item.spec_name,
    zone_name: item.zone_name,
    quantity: item.quantity,
    body_code: item.body_code,
    note: item.note,
  }))).sort((a, b) => a.business_date.localeCompare(b.business_date) || a.spec_name.localeCompare(b.spec_name) || a.zone_name.localeCompare(b.zone_name))
}

const WIDTH = 9638
const border = { style: BorderStyle.SINGLE, size: 4, color: 'B8C3CF' }
const borders = { top: border, bottom: border, left: border, right: border }
function paragraph(text: string, options: { bold?: boolean; size?: number; center?: boolean; keep?: boolean; color?: string } = {}) {
  return new Paragraph({
    alignment: options.center ? AlignmentType.CENTER : AlignmentType.LEFT,
    keepNext: options.keep, spacing: { after: 100, line: 300 },
    children: [new TextRun({ text, font: '宋体', size: options.size || 22, bold: options.bold, color: options.color || '1F2933' })],
  })
}
function heading(text: string) {
  return new Paragraph({
    keepNext: true, spacing: { before: 220, after: 110 },
    children: [new TextRun({ text, font: '黑体', size: 25, bold: true, color: '243B53' })],
  })
}
function table(headers: string[], rows: Array<Array<string | number>>, widths: number[]) {
  const row = (values: Array<string | number>, isHeader = false) => new TableRow({
    tableHeader: isHeader, cantSplit: true,
    children: values.map((value, index) => new TableCell({
      width: { size: widths[index], type: WidthType.DXA }, borders,
      shading: isHeader ? { fill: 'E8EEF4', type: ShadingType.CLEAR } : undefined,
      children: [new Paragraph({
        alignment: index === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
        spacing: { after: 0, before: 0, line: 280 },
        children: [new TextRun({ text: String(value), font: '宋体', size: 21, bold: isHeader })],
      })],
    })),
  })
  return new Table({
    layout: TableLayoutType.FIXED, width: { size: WIDTH, type: WidthType.DXA }, columnWidths: widths,
    margins: { top: 90, bottom: 90, left: 100, right: 100 },
    rows: [row(headers, true), ...rows.map(values => row(values))],
  })
}

export async function buildReceiptWord(report: ReceiptReport): Promise<Blob> {
  const inboundRows = quantitySummary(report, 'inbound')
  const outboundRows = quantitySummary(report, 'outbound')
  const qualityRows = qualitySummary(report)
  const inboundTotal = inboundRows.reduce((sum, item) => sum + item.quantity, 0)
  const outboundTotal = outboundRows.reduce((sum, item) => sum + item.quantity, 0)
  const qualityTotal = qualityRows.reduce((sum, item) => sum + item.quantity, 0)
  const content: Array<Paragraph | Table> = [
    paragraph(report.company || '锦安特种设备检测', { bold: true, size: 34, center: true, keep: true }),
    paragraph('钢瓶出入库数据汇总', { bold: true, size: 28, center: true }),
    paragraph(`客户：${report.customer}`, { keep: true }),
  ]

  content.push(heading(`入库汇总（共 ${inboundTotal} 只）`))
  if (inboundRows.length) content.push(table(['入库日期', '钢瓶规格', '数量'], inboundRows.map(item => [item.business_date, item.spec_name, item.quantity]), [2800, 4438, 2400]))
  else content.push(paragraph('无入库数据。', { color: '687787' }))

  content.push(heading(`出库汇总（共 ${outboundTotal} 只）`))
  if (outboundRows.length) content.push(table(['出库日期', '钢瓶规格', '数量'], outboundRows.map(item => [item.business_date, item.spec_name, item.quantity]), [2800, 4438, 2400]))
  else content.push(paragraph('无出库数据。', { color: '687787' }))

  content.push(heading(`报废 / 不良品瓶子信息（共 ${qualityTotal} 只）`))
  if (qualityRows.length) content.push(table(['日期', '钢瓶规格', '类别', '数量', '瓶身编号', '备注'], qualityRows.map(item => [
    item.business_date, item.spec_name, item.zone_name, item.quantity, item.body_code || '未绑定瓶号', item.note || '-',
  ]), [1700, 1900, 1100, 900, 1900, 2138]))
  else content.push(paragraph('无报废或不良品瓶子信息。', { color: '687787' }))

  const generated = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date())
  content.push(paragraph(`导出日期：${generated}`, { size: 18, color: '687787' }))
  const document = new Document({
    creator: report.company, title: '钢瓶出入库数据汇总', subject: report.customer,
    styles: { default: { document: { run: { font: '宋体', size: 22 }, paragraph: { spacing: { after: 100, line: 300 } } } } },
    sections: [{
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
      children: content,
    }],
  })
  return Packer.toBlob(document)
}
