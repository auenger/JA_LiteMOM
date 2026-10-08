// Render real application screens with synthetic fixtures; no backend or production access.
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import puppeteer from 'puppeteer-core'

const baseUrl = process.env.TEST_BASE_URL || 'http://127.0.0.1:5173'
assert.ok(['localhost', '127.0.0.1'].includes(new URL(baseUrl).hostname), 'Use a local frontend for documentation screenshots')
const output = new URL('../../docs/screenshots/', import.meta.url)
await fs.mkdir(output, { recursive: true })
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
const user = { id: 1, username: 'demo', name: '演示管理员', is_active: true, is_superadmin: true, permissions: [] }
const sources = ['演示供瓶单位 A', '演示供瓶单位 B', '演示供瓶单位 C'].map((name, index) => ({ id: index + 1, name, is_active: true, is_default: index === 0, sort_order: index }))
const specs = ['15 kg', '5 kg', '50 kg'].map((name, index) => ({ id: index + 1, name, is_active: true, is_default: index === 0, sort_order: index }))
const manufacturers = [{ id: 1, name: '示例钢瓶制造厂', code_prefix: 'DEMO', is_active: true }]
const bottles = Array.from({ length: 26 }, (_, index) => ({
  id: index + 1, inbound_id: 1, body_code: `DEMO${String(index + 1).padStart(8, '0')}`, manufacture_date: '2022-06-01', manufacturer: manufacturers[0].name,
  source_id: index % 3 + 1, spec_id: index % 3 + 1, zone: 'GOOD', process_status: 'INSPECTED', coding_date: today, coding_sequence: index + 1,
  coding_note: index === 3 ? '已核对瓶身信息' : null, coded_by: 1, coded_by_name: '演示操作员', coded_at: `${today}T08:30:00`,
  inspected_at: `${today}T08:30:00`, inspection_result: 'GOOD', inspection_document_status: index > 3 ? 'INSPECTED' : 'UNINSPECTED',
  effective_coding_customer_id: index % 3 + 1, coding_customer_name: sources[index % 3].name,
}))
bottles[0].body_code = 'DEMO000000000001'
bottles[1].manufacturer = null
bottles[2].manufacture_date = null
const materials = ['银灰粉末', '钢瓶阀门', '密封圈', '保护罩', '标签纸', '回收废钢'].map((name, index) => ({
  id: index + 1, name, specification: ['20 kg / 袋', '标准型', '通用型', '15 kg 适配', '耐候型', '分类回收'][index],
  material_type: index === 5 ? 'SCRAP' : 'NORMAL', material_unit: index === 0 ? '袋' : '件', stock_unit: index === 0 ? 'kg' : '件',
  conversion_enabled: index === 0, conversion_ratio: index === 0 ? 20 : 1, price: [180, 12, 0.8, 5, 0.2, 2][index],
  stock: [3, 820, 1200, 360, 2400, 90][index], converted_stock: index === 0 ? 60 : 0, warning_enabled: true,
  safety_threshold: [100, 200, 500, 100, 500, 20][index], warning_status: index === 0 ? 'LOW' : 'NORMAL', is_active: true,
  supplier_prices: [{ id: index + 1, supplier_name: '演示供应商', purchase_price: [175, 11.5, 0.75, 4.8, 0.18, 1.9][index] }],
}))
const summary = { total: 26, items: sources.map((source, index) => ({ customer_name: source.name, user_name: '演示操作员', spec_name: specs[index].name, quantity: [9, 9, 8][index] })) }
const period = (factor) => ({ inbound: 360 * factor, outbound: 280 * factor, inspected: 320 * factor, uninspected: 28 * factor, temporary: 8 * factor, scrap: 4 * factor, batch_count: 6 * factor })
const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, pipe: true, args: ['--no-sandbox', '--disable-gpu', '--no-first-run'] })
try {
  const page = await browser.newPage()
  const problems = []
  page.on('pageerror', error => problems.push(error.message))
  await page.setRequestInterception(true)
  page.on('request', request => {
    const url = new URL(request.url())
    if (!url.pathname.startsWith('/api/')) {
      if (url.origin !== new URL(baseUrl).origin && url.protocol.startsWith('http')) return request.abort()
      return request.continue()
    }
    let data
    if (url.pathname === '/api/auth/me') data = user
    else if (url.pathname === '/api/menu-settings') data = { groups: [], version: 0 }
    else if (url.pathname === '/api/options') data = { sources, specs, manufacturers, users: [user], code_prefixes: [{ id: 1, name: '示例前缀', value: 'DEMO' }], inspection_notes: [], date_presets: ['2022.06', '2023.09'].map((value, index) => ({ id: index + 1, name: value, value })) }
    else if (url.pathname === '/api/coding/summary') data = summary
    else if (url.pathname === '/api/coding/review-bottles') data = { items: bottles.slice(0, Number(url.searchParams.get('page_size') || 20)), total: 26, suspect_count: 3, page: 1, page_size: Number(url.searchParams.get('page_size') || 20) }
    else if (url.pathname === '/api/materials') data = { items: materials, total: materials.length }
    else if (url.pathname === '/api/dashboard') data = { target_date: today, today_inbound_total: 360, today_batch_count: 6, zones: { pending: 128, temporary: 24, scrap: 16, good: 860, bad: 12 }, daily_summary: period(1), monthly_summary: period(8), yearly_summary: period(90), low_materials: [materials[0]] }
    else { problems.push(`Unexpected API request: ${request.method()} ${url.pathname}`); data = {} }
    request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(data) })
  })
  await page.goto(`${baseUrl}/login`)
  await page.evaluate(value => { localStorage.setItem('wms_token', 'documentation-demo'); localStorage.setItem('wms_user', JSON.stringify(value)) }, user)
  async function capture(route, filename, width = 1440, height = 1000) {
    await page.setViewport({ width, height, deviceScaleFactor: 1 })
    await page.goto(`${baseUrl}/${route}`, { waitUntil: 'networkidle0' })
    await page.waitForSelector('.app-shell')
    await page.waitForSelector('.el-loading-mask', { hidden: true })
    await page.evaluate(async () => { await document.fonts.ready; window.scrollTo(0, 0) })
    await new Promise(resolve => setTimeout(resolve, 500))
    if (route === 'coding') {
      await page.click('.table-pagination .el-select')
      await page.$$eval('.el-select-dropdown__item', items => items.find(item => item.textContent.trim() === '10条/页' && item.getBoundingClientRect().height > 0)?.click())
      await page.waitForFunction(() => document.querySelectorAll('.suspect-section tbody tr').length === 10)
      await page.waitForSelector('.el-loading-mask', { hidden: true })
      await page.evaluate(() => window.scrollTo(0, 0))
    }
    await page.screenshot({ path: new URL(filename, output).pathname, fullPage: true })
  }
  await capture('dashboard', 'dashboard.png')
  await capture('coding', 'coding.png', 2400, 980)
  assert.equal(await page.$$eval('.el-table', tables => tables.length), 1)
  await page.$$eval('.suspect-section tbody button', buttons => buttons.find(button => button.textContent.trim() === '编辑')?.click())
  await page.waitForSelector('.suspect-section tbody input')
  await page.screenshot({ path: new URL('coding-edit.png', output).pathname, fullPage: true })
  await capture('materials', 'materials.png', 1920, 900)
  await capture('quick-coding', 'quick-coding-mobile.png', 390, 844)
  await page.type('input[aria-label="瓶身编号"]', 'DEMO00000027')
  await page.type('input[aria-label="生产日期"]', '202206')
  await page.locator('input[aria-label="生产日期"]').fill('2022.06')
  await page.screenshot({ path: new URL('quick-coding-mobile.png', output).pathname, fullPage: true })
  assert.deepEqual(problems, [])
  console.log('Saved 5 documentation screenshots with synthetic data to docs/screenshots/')
} finally { await browser.close() }
