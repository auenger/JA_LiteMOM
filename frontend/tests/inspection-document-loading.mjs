import assert from 'node:assert/strict'
import puppeteer from 'puppeteer-core'

const baseUrl = process.env.TEST_BASE_URL || 'http://127.0.0.1:5173'
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new', pipe: true,
  args: ['--no-sandbox', '--disable-gpu', '--no-first-run'],
})

try {
  const page = await browser.newPage()
  const user = { id: 1, username: 'admin', name: '超级管理员', is_active: true, is_superadmin: true, permissions: [] }
  const lines = Array.from({ length: 120 }, (_, index) => ({
    id: index + 1, bottle_id: index + 1, spec_id: 1, sequence: index + 1,
    body_code: `BOTTLE-${String(index + 1).padStart(4, '0')}`, manufacture_date: index === 0 ? '2022-01-17' : '2022-01-01',
    manufacturer: '测试厂家', volume: '35.50', inspected_at: '2026-09-12T10:00:00',
    is_unverified: false,
  }))
  const document = {
    id: 1, document_no: 'JY20260912', inspection_date: '2026-09-12',
    customer_name: '测试客户', inspector_name: '测试员', status: 'ACTIVE',
    export_dates: {}, total_quantity: lines.length, created_at: '2026-09-12T10:00:00', is_archived: false, lines,
  }
  const editPayloads = []
  await page.setRequestInterception(true)
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname
    const json = (value) => request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(value) })
    if (path === '/api/auth/me') json(user)
    else if (path === '/api/options') json({ sources: [{ id: 1, name: '测试客户' }], specs: [{ id: 1, name: '15kg' }], users: [], date_presets: [{ id: 1, name: '常用日期', value: '2023.07' }] })
    else if (path === '/api/inspection-documents') json({ items: [document], total: 1 })
    else if (path === '/api/inspection-documents/1/lines/1' && request.method() === 'PUT') {
      const payload = JSON.parse(request.postData())
      editPayloads.push(payload)
      Object.assign(document.lines[0], payload)
      json(document)
    }
    else if (path === '/api/inspection-documents/1') setTimeout(() => json(document), 250)
    else if (path === '/api/inspection-documents/1/export-bottle-reports') {
      setTimeout(() => request.respond({ status: 200, contentType: 'application/zip', body: 'PK' }), 250)
    } else if (path.startsWith('/api/')) json({})
    else request.continue()
  })
  await page.goto(baseUrl)
  await page.evaluate((value) => {
    localStorage.setItem('wms_token', 'test-token')
    localStorage.setItem('wms_user', JSON.stringify(value))
  }, user)
  await page.goto(`${baseUrl}/inspection-documents`, { waitUntil: 'networkidle0' })
  await page.$eval('.surface .el-table .el-button', (button) => button.click())
  await page.waitForSelector('.document-detail .el-loading-mask', { visible: true })
  await page.waitForFunction(() => document.querySelector('.document-detail h2')?.textContent === 'JY20260912')
  await page.waitForSelector('.document-detail .el-loading-mask', { hidden: true })
  const renderedRows = await page.$$eval('.document-detail .el-table__body-wrapper tbody tr', (rows) => rows.length)
  assert.equal(renderedRows, 50)
  const totalText = await page.$eval('.document-detail .table-pagination', (element) => element.textContent)
  assert.match(totalText, /120/)
  await page.$$eval('.document-detail .el-table__body-wrapper tbody tr:first-child button', (buttons) => buttons.find((button) => button.textContent?.includes('编辑'))?.click())
  const dateInput = 'input[placeholder="输入生产日期，如 2022.09"]'
  await page.waitForSelector(dateInput, { visible: true })
  assert.equal(await page.$eval(dateInput, (input) => input.value), '2022.01')
  assert.equal((await page.$$('.el-dialog .el-date-picker')).length, 0)
  await page.$$eval('.el-dialog__footer button', (buttons) => buttons.find((button) => button.textContent?.includes('保存明细'))?.click())
  await page.waitForFunction(() => !document.querySelector('.el-dialog'))
  assert.equal(editPayloads[0].manufacture_date, '2022-01-17')
  await page.$$eval('.document-detail .el-table__body-wrapper tbody tr:first-child button', (buttons) => buttons.find((button) => button.textContent?.includes('编辑'))?.click())
  await page.waitForSelector(dateInput, { visible: true })
  await page.$eval('.date-shortcut-row button', (button) => button.click())
  assert.equal(await page.$eval(dateInput, (input) => input.value), '2023.07')
  await page.$$eval('.el-dialog__footer button', (buttons) => buttons.find((button) => button.textContent?.includes('保存明细'))?.click())
  await page.waitForFunction(() => !document.querySelector('.el-dialog'))
  assert.equal(editPayloads[1].manufacture_date, '2023-07-01')
  await page.evaluate(() => { HTMLAnchorElement.prototype.click = () => {} })
  await page.$$eval('.detail-header button', (buttons) => buttons.find((button) => button.textContent?.includes('导出未被驳回'))?.click())
  await page.waitForSelector('.el-dialog', { visible: true })
  await page.$$eval('.el-dialog__footer button', (buttons) => buttons.find((button) => button.textContent?.includes('导出 Word'))?.click())
  await page.waitForSelector('.document-detail .el-loading-mask', { visible: true })
  await page.waitForSelector('.document-detail .el-loading-mask', { hidden: true })
  console.log('检验单详情加载、分页、年月输入和批量报告加载提示通过')
} finally {
  await browser.close()
}
