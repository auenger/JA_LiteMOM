import assert from 'node:assert/strict'
import puppeteer from 'puppeteer-core'
const baseUrl = process.env.TEST_BASE_URL || 'http://127.0.0.1:5173'
const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: 'new', pipe: true, args: ['--no-sandbox', '--disable-gpu', '--no-first-run'] })
try {
  const page = await browser.newPage()
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message))
  const user = { id: 1, username: 'admin', name: '超级管理员', is_active: true, is_superadmin: true, permissions: [] }
  const documents = [], payloads = []
  const days = [
    { date: '2026-10-01', quantity: 3, customer_count: 1, generated: false, selectable: true },
    { date: '2026-10-02', quantity: 2, customer_count: 2, generated: false, selectable: true },
    { date: '2026-10-03', quantity: 0, customer_count: 0, generated: true, selectable: false },
    { date: '2026-10-04', quantity: 0, customer_count: 0, generated: false, selectable: false },
  ]
  await page.setRequestInterception(true)
  page.on('request', request => {
    const path = new URL(request.url()).pathname
    const json = value => request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(value) })
    if (path === '/api/auth/me') json(user)
    else if (path === '/api/options') json({ sources: [], specs: [], users: [] })
    else if (path === '/api/inspection-documents/generation-dates') json(days)
    else if (path === '/api/inspection-documents/generate') {
      const payload = JSON.parse(request.postData()); payloads.push(payload)
      for (let index = 1; index <= 2; index++) documents.push({ id: index, document_no: `JY${payload.document_date.replaceAll('-', '')}-${index}`, inspection_date: payload.document_date, source_dates: payload.inspection_dates, customer_name: index === 1 ? '甲客户' : '乙客户', inspector_name: '', total_quantity: index === 1 ? 4 : 1, lines: [], status: 'ACTIVE', created_at: '2026-10-02T10:00:00' })
      json(documents)
    } else if (path === '/api/inspection-documents') json({ items: documents, total: documents.length })
    else if (path === '/api/inspection-documents/1') json(documents[0])
    else if (path.startsWith('/api/')) json({})
    else request.continue()
  })
  await page.goto(baseUrl)
  await page.evaluate(value => { localStorage.setItem('wms_token', 'test-token'); localStorage.setItem('wms_user', JSON.stringify(value)) }, user)
  await page.goto(`${baseUrl}/inspection-documents?date=2026-10-01&generate=1`, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.generation-days .el-checkbox').catch(async error => { console.log(await page.evaluate(() => ({ url: location.href, body: document.body.innerText }))); throw error })
  assert.equal(payloads.length, 0, '快捷入口应先弹出选择框')
  assert.equal(await page.$eval('.generation-toolbar input', input => input.value), '2026-10')
  assert.deepEqual(await page.$$eval('.generation-days input', inputs => inputs.map(input => input.disabled)), [false, false, true, true])
  await page.$$eval('.generation-toolbar button', buttons => buttons.find(button => button.textContent.includes('全选')).click())
  assert.equal(await page.$$eval('.generation-days input:checked', inputs => inputs.length), 2)
  assert.match(await page.$eval('.el-dialog__body', element => element.textContent), /已选 2 天数据，共 5 只钢瓶/)
  assert.equal(await page.$$eval('.el-dialog__footer button', buttons => buttons.find(button => button.textContent.includes('按客户合并生成')).disabled), true, '未选检验单日期时不能生成')
  await page.click('input[placeholder="选择检验单日期"]')
  await page.keyboard.type('2026-10-08')
  await page.keyboard.press('Enter')
  await page.waitForFunction(() => document.querySelector('input[placeholder="选择检验单日期"]')?.value === '2026-10-08')
  await page.setViewport({ width: 390, height: 844 })
  await page.screenshot({ path: '../artifacts/inspection-generation-mobile.png', fullPage: true })
  assert.ok(await page.$eval('.el-dialog', element => element.getBoundingClientRect().width <= window.innerWidth))
  await page.$$eval('.el-dialog__footer button', buttons => buttons.find(button => button.textContent.includes('按客户合并生成')).click())
  await page.waitForSelector('.detail-header')
  assert.deepEqual(payloads, [{ inspection_dates: ['2026-10-01', '2026-10-02'], document_date: '2026-10-08' }])
  assert.match(await page.$eval('.detail-header', element => element.textContent), /检验日期 2026-10-08/)
  assert.match(await page.$eval('.detail-header', element => element.textContent), /来源日期 2026-10-01、2026-10-02/)
  assert.equal(await page.$$eval('.surface .el-table__body tbody tr', rows => rows.length), 2)
  console.log('数据日期多选、检验单日期必选、按客户合并提交和来源日期展示通过')
} finally { await browser.close() }
