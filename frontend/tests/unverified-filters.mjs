import assert from 'node:assert/strict'
import puppeteer from 'puppeteer-core'

const baseUrl = process.env.TEST_BASE_URL || 'http://127.0.0.1:5173'
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new', pipe: true,
  args: ['--no-sandbox', '--disable-gpu', '--no-first-run'],
})
const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())

try {
  const page = await browser.newPage()
  const user = { id: 1, username: 'admin', name: '测试管理员', is_active: true, is_superadmin: true, permissions: [] }
  let poolTotal = 0
  let batchPayload = null
  let exportCalls = 0
  let retryDocuments = [{ id: 99, document_no: 'JY20260913-R01', inspection_date: '2026-09-13', customer_name: '测试客户', total_quantity: 501 }]
  await page.setRequestInterception(true)
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname
    if (path === '/api/auth/me') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(user) })
    else if (path === '/api/unverified-bottles') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: poolTotal ? [{
      id: 1, inspection_document_id: 1, inspection_line_id: 1, document_no: 'JY20260912', inspection_date: '2026-09-12',
      sequence: 1, body_code: 'BOTTLE-0001', manufacture_date: '2022-01-17', manufacturer: '测试厂家',
      spec_name: '15kg', volume: '35.50', wall_thickness: '2.45', inspection_price: '30.00',
      customer_name: '测试客户', inspector_name: '测试员', error_message: '气瓶信息不存在',
    }] : [], total: poolTotal }) })
    else if (path === '/api/unverified-bottles/create-retry-document' && request.method() === 'POST') {
      batchPayload = JSON.parse(request.postData())
      poolTotal = 0
      request.respond({ status: 201, contentType: 'application/json', body: JSON.stringify(retryDocuments) })
    }
    else if (path === '/api/unverified-bottles/export-xls') {
      exportCalls += 1
      request.respond({ status: 200, contentType: 'application/vnd.ms-excel', headers: { 'Content-Disposition': "attachment; filename*=UTF-8''test.xls" }, body: 'test xls' })
    }
    else if (path.startsWith('/api/')) request.respond({ status: 200, contentType: 'application/json', body: '{}' })
    else request.continue()
  })
  await page.goto(baseUrl)
  await page.evaluate((value) => {
    localStorage.setItem('wms_token', 'test-token')
    localStorage.setItem('wms_user', JSON.stringify(value))
  }, user)

  for (const width of [1366, 1024, 768, 390]) {
    await page.setViewport({ width, height: 800, deviceScaleFactor: 1 })
    await page.goto(`${baseUrl}/unverified-bottles`, { waitUntil: 'networkidle0' })
    await page.waitForSelector('.pool-filters')
    const layout = await page.$eval('.pool-filters', (filter) => {
      const container = filter.getBoundingClientRect()
      const controls = [...filter.children].map((child) => {
        const { left, right, top, bottom, width } = child.getBoundingClientRect()
        return { left, right, top, bottom, width }
      })
      return { container: { left: container.left, right: container.right }, controls }
    })
    assert.equal(layout.controls.length, 5)
    for (const control of layout.controls) {
      assert.ok(control.left >= layout.container.left - 1, `${width}px: control extends left`)
      assert.ok(control.right <= layout.container.right + 1, `${width}px: control extends right`)
    }
    for (let i = 0; i < layout.controls.length; i++) for (let j = i + 1; j < layout.controls.length; j++) {
      const a = layout.controls[i]
      const b = layout.controls[j]
      const overlapsVertically = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1
      if (overlapsVertically) assert.ok(Math.min(a.right, b.right) - Math.max(a.left, b.left) <= 1, `${width}px: filters ${i} and ${j} overlap`)
    }
    if (width === 1366) assert.ok(layout.controls[2].width <= 181, `Bottle code filter is too wide: ${layout.controls[2].width}px`)
  }
  poolTotal = 501
  await page.setViewport({ width: 1366, height: 800, deviceScaleFactor: 1 })
  await page.goto(`${baseUrl}/unverified-bottles`, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.batch-toolbar button')
  assert.equal(await page.$eval('.retry-actions input', input => input.value), today)
  await page.click('.retry-actions .el-input__wrapper')
  await page.waitForSelector('.el-date-table td.available')
  const chosenDay = today.endsWith('-15') ? '16' : '15'
  const calendarCells = await page.$$('.el-date-table td.available:not(.prev-month):not(.next-month)')
  let choseDate = false
  for (const cell of calendarCells) {
    if (await cell.$eval('.el-date-table-cell__text', element => element.textContent?.trim()) !== chosenDay) continue
    if (!await cell.boundingBox()) continue
    await cell.click()
    choseDate = true
    break
  }
  assert.equal(choseDate, true)
  const chosenRetryDate = `${today.slice(0, 8)}${chosenDay}`
  await page.waitForFunction(date => document.querySelector('.retry-actions input')?.value === date, {}, chosenRetryDate)
  await page.evaluate(() => {
    const originalClick = HTMLAnchorElement.prototype.click
    HTMLAnchorElement.prototype.click = function () {
      if (!this.download) originalClick.call(this)
    }
  })
  const exported = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/unverified-bottles/export-xls')
  await page.click('.page-actions button:first-child')
  await exported
  assert.equal(exportCalls, 1)
  await page.$$eval('.el-table__body-wrapper tbody tr:first-child button', (buttons) => buttons.find((button) => button.textContent?.includes('编辑'))?.click())
  await page.waitForSelector('.spec-summary')
  assert.match(await page.$eval('.spec-summary', (element) => element.textContent), /15kg.*35\.50 L.*2\.45 mm.*30\.00/s)
  assert.equal(await page.$eval('input[placeholder="输入年月，如 2022.09"]', (input) => input.value), '2022.01')
  await page.$eval('.el-dialog__footer button', (button) => button.click())
  await page.waitForSelector('.el-dialog', { hidden: true })
  await page.click('.batch-toolbar button')
  await page.waitForSelector('.el-message-box')
  await page.click('.el-message-box__btns .el-button--primary')
  await page.waitForFunction(() => window.location.pathname === '/inspection-documents')
  assert.deepEqual(batchPayload, { inspection_date: chosenRetryDate })
  poolTotal = 501
  retryDocuments = [
    { id: 100, document_no: 'JY20260913-R02', inspection_date: '2026-09-13', customer_name: '甲客户', total_quantity: 301 },
    { id: 101, document_no: 'JY20260913-R03', inspection_date: '2026-09-13', customer_name: '乙客户', total_quantity: 200 },
  ]
  await page.goto(`${baseUrl}/unverified-bottles`, { waitUntil: 'networkidle0' })
  await page.type('input[placeholder="检验单号"]', '当前筛选单号')
  await page.keyboard.press('Enter')
  await page.waitForFunction(() => !document.querySelector('.el-loading-mask'))
  await page.click('.batch-toolbar button')
  await page.waitForSelector('.el-message-box')
  assert.match(await page.$eval('.el-message-box', element => element.textContent), /同一客户合并、不同客户分单/)
  await page.click('.el-message-box__btns .el-button--primary')
  await page.waitForFunction(() => [...document.querySelectorAll('.el-dialog__title')].some(element => element.textContent.includes('已按客户生成重检单')))
  assert.equal(new URL(page.url()).pathname, '/unverified-bottles')
  assert.deepEqual(batchPayload, { document_no: '当前筛选单号', inspection_date: today })
  const resultText = await page.$eval('.el-dialog__body', element => element.textContent)
  assert.match(resultText, /甲客户.*301.*乙客户.*200/s)
  assert.equal(await page.$$eval('.el-dialog .el-table__body tbody tr', elements => elements.length), 2)
  await page.setViewport({ width: 390, height: 844 })
  await new Promise(resolve => setTimeout(resolve, 500))
  await page.screenshot({ path: '../artifacts/retry-customers-mobile.png', fullPage: true })
  await page.$eval('.el-dialog .el-table__body tbody tr:nth-child(2) button', element => element.click())
  await page.waitForFunction(() => new URL(location.href).searchParams.get('document') === '101')
  console.log('未验证池筛选、全量导出、单客户重检、多客户结果列表及选择目标单据通过')
} finally {
  await browser.close()
}
