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
  const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
  let suspectRows = [{ id: 10, inbound_id: null, body_code: 'TOO-LONG-CODE-0001', manufacture_date: null, manufacturer: null, source_id: 1, spec_id: 1, zone: 'GOOD', process_status: 'INSPECTED', coding_date: today, coding_sequence: 7, coding_note: null, coded_by: 1, coded_by_name: '测试员', coded_at: `${today}T08:00:00`, inspected_at: `${today}T08:00:00`, inspection_result: 'GOOD', inspection_document_status: 'UNINSPECTED', effective_coding_customer_id: 1, coding_customer_name: '测试客户' }]
  let savedPayload = null
  let deletedId = null
  await page.setRequestInterception(true)
  const recordRequests = []
  const reviewRequests = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (['/api/coding/review-bottles', '/api/coding/summary'].includes(url.pathname)) recordRequests.push(url)
    const path = new URL(request.url()).pathname
    if (path === '/api/auth/me') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(user) })
    else if (path === '/api/options') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ users: [], sources: [{ id: 1, name: '测试客户', is_active: true }], specs: [{ id: 1, name: '15kg', is_active: true }], manufacturers: [{ id: 1, name: '测试钢瓶厂', is_active: true }] }) })
    else if (path === '/api/bottles') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) })
    else if (path === '/api/coding/summary') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [], total: 0 }) })
    else if (path === '/api/coding/review-bottles') {
      reviewRequests.push(url)
      const matches = suspectRows.filter(row => row.body_code.includes(url.searchParams.get('body_code') || '') && row.coding_date >= url.searchParams.get('date_from') && row.coding_date <= url.searchParams.get('date_to') && (!url.searchParams.has('coding_customer_id') || row.effective_coding_customer_id === Number(url.searchParams.get('coding_customer_id'))))
      const offset = (Number(url.searchParams.get('page')) - 1) * Number(url.searchParams.get('page_size'))
      request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: matches.slice(offset, offset + Number(url.searchParams.get('page_size'))), total: matches.length, suspect_count: matches.filter(row => row.body_code.length > 13 || !row.manufacturer || !row.manufacture_date).length }) })
    }
    else if (/\/api\/bottles\/\d+\/coding$/.test(path) && request.method() === 'PUT') {
      savedPayload = JSON.parse(request.postData())
      const updated = { ...suspectRows[0], ...savedPayload }
      suspectRows = [updated]
      request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(updated) })
    }
    else if (/\/api\/bottles\/\d+\/coding$/.test(path) && request.method() === 'DELETE') {
      deletedId = Number(path.split('/')[3])
      suspectRows = suspectRows.filter(row => row.id !== deletedId)
      request.respond({ status: 204 })
    }
    else if (path === '/api/menu-settings') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ groups: [], version: 0 }) })
    else if (path.startsWith('/api/')) request.respond({ status: 200, contentType: 'application/json', body: '{}' })
    else request.continue()
  })
  await page.goto(`${baseUrl}/login`)
  await page.evaluate((value) => {
    localStorage.setItem('wms_token', 'test-token')
    localStorage.setItem('wms_user', JSON.stringify(value))
  }, user)
  await page.setViewport({ width: 1366, height: 768 })
  await page.goto(`${baseUrl}/coding`, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.suspect-filters .el-date-editor')
  assert.equal(await page.$$eval('.el-table', elements => elements.length), 1)
  const headers = await page.$eval('.suspect-section thead', element => element.textContent)
  for (const label of ['抄码客户', '原供瓶单位', '当前状态', '检验单', '备注', '抄码日期']) assert.ok(headers.includes(label), label)
  assert.equal(await page.$$eval('.suspect-filters .el-select', elements => elements.length), 1)
  assert.match(await page.$eval('.suspect-filters .el-select', element => element.textContent), /筛选抄码客户/)
  assert.equal(recordRequests.length, 2)
  assert.ok(recordRequests.every(url => !url.searchParams.has('coded_by')))
  assert.match(await page.$eval('.suspect-section', element => element.textContent), /今日抄码核对.*当天共 1 条.*1 条疑似有问题.*超过13位.*厂家为空.*日期为空/s)
  assert.equal(await page.$$eval('.suspect-section td.suspect-warning-cell', elements => elements.length), 3)
  await page.$$eval('.suspect-section tbody button', buttons => buttons.find(button => button.textContent?.trim() === '编辑')?.click())
  const codeInput = '.suspect-section tbody tr td:nth-child(2) input'
  await page.waitForSelector(codeInput)
  await page.click(codeInput, { clickCount: 3 })
  await page.type(codeInput, 'CODE-0001')
  const manufacturerInput = '.suspect-section tbody tr td:nth-child(3) input'
  await page.click(manufacturerInput)
  await page.type(manufacturerInput, '测试钢瓶厂')
  await page.keyboard.press('Enter')
  const manufactureDateInput = '.suspect-section tbody tr td:nth-child(4) input'
  await page.type(manufactureDateInput, '202206')
  assert.equal(await page.$eval(manufactureDateInput, input => input.value), '2022.06')
  await page.$$eval('.suspect-section tbody button', buttons => buttons.find(button => button.textContent?.trim() === '保存')?.click())
  await page.waitForFunction(() => document.querySelectorAll('.suspect-section td.suspect-warning-cell').length === 0)
  assert.deepEqual(savedPayload, { body_code: 'CODE-0001', manufacture_date: '2022-06-01', manufacturer: '测试钢瓶厂', source_id: 1, spec_id: 1 })
  await page.$$eval('.suspect-section tbody button', buttons => buttons.find(button => button.textContent?.trim() === '编辑')?.click())
  await page.waitForSelector(manufactureDateInput)
  assert.equal(await page.$eval(manufactureDateInput, input => input.value), '2022.06')
  await page.$$eval('.suspect-section tbody button', buttons => buttons.find(button => button.textContent?.trim() === '取消')?.click())
  await page.type('input[placeholder="查询核对瓶身编号"]', 'BOTTLE-123')
  const searched = page.waitForResponse(response => response.url().includes('/api/coding/summary') && response.url().includes('BOTTLE-123'))
  await page.keyboard.press('Enter')
  await searched
  await page.waitForSelector('.suspect-section .el-loading-mask', { hidden: true })
  assert.ok(recordRequests.slice(-2).every(url => url.searchParams.get('body_code') === 'BOTTLE-123' && !url.searchParams.has('coded_by')))
  const resetDone = page.waitForResponse(response => response.url().includes('/api/coding/summary') && !response.url().includes('body_code'))
  for (const button of await page.$$('.suspect-filters button')) {
    if ((await button.evaluate(el => el.textContent)).trim() === '重置') { await button.click(); break }
  }
  await resetDone
  assert.ok(recordRequests.slice(-2).every(url => !url.searchParams.has('coded_by') && !url.searchParams.has('body_code')))
  const layout = await page.evaluate(() => {
    const date = document.querySelector('.suspect-filters .el-date-editor').getBoundingClientRect()
    const code = document.querySelector('input[placeholder="查询核对瓶身编号"]').getBoundingClientRect()
    return { dateRight: date.right, codeLeft: code.left }
  })
  assert.ok(layout.dateRight <= layout.codeLeft + 1, JSON.stringify(layout))
  suspectRows = Array.from({ length: 25 }, (_, index) => ({ ...suspectRows[0], id: index + 100, body_code: `PAGE-${index + 1}` }))
  await page.$$eval('.suspect-filters button', buttons => buttons.find(button => button.textContent?.trim() === '查询')?.click())
  await page.waitForFunction(() => document.querySelectorAll('.suspect-section tbody tr').length === 20)
  await page.waitForSelector('.suspect-section .el-loading-mask', { hidden: true })
  await page.click('.suspect-section .btn-next')
  await page.waitForFunction(() => document.querySelectorAll('.suspect-section tbody tr').length === 5)
  assert.equal(reviewRequests.at(-1).searchParams.get('page'), '2')
  await page.type('input[placeholder="查询核对瓶身编号"]', 'PAGE-25')
  await page.keyboard.press('Enter')
  await page.waitForFunction(() => document.querySelectorAll('.suspect-section tbody tr').length === 1)
  assert.equal(reviewRequests.at(-1).searchParams.get('page'), '1')
  assert.equal(reviewRequests.at(-1).searchParams.get('body_code'), 'PAGE-25')
  await page.type('input[placeholder="查询核对瓶身编号"]', '-NONE')
  await page.keyboard.press('Enter')
  await page.waitForFunction(() => document.querySelector('.suspect-section').textContent.includes('当前条件没有抄码核对记录'))
  assert.ok(await page.$('.suspect-filters'))
  await page.$$eval('.suspect-filters button', buttons => buttons.find(button => button.textContent?.trim() === '重置')?.click())
  await page.waitForFunction(() => document.querySelectorAll('.suspect-section tbody tr').length === 20)
  assert.equal(reviewRequests.at(-1).searchParams.get('date_from'), today)
  assert.equal(reviewRequests.at(-1).searchParams.get('date_to'), today)
  assert.ok(!reviewRequests.at(-1).searchParams.has('body_code'))
  await page.waitForSelector('.suspect-section .el-loading-mask', { hidden: true })
  await page.click('.suspect-filters .el-select')
  await page.waitForSelector('.el-select-dropdown__item', { visible: true })
  await page.$$eval('.el-select-dropdown__item', options => options.find(option => option.textContent.trim() === '测试客户' && option.getBoundingClientRect().height > 0)?.click())
  const customerDone = page.waitForResponse(response => response.url().includes('/coding/review-bottles') && response.url().includes('coding_customer_id=1'))
  await page.$$eval('.suspect-filters button', buttons => buttons.find(button => button.textContent?.trim() === '查询')?.click())
  await customerDone
  assert.ok(recordRequests.slice(-2).every(url => url.searchParams.get('coding_customer_id') === '1'))
  suspectRows = suspectRows.slice(0, 21)
  suspectRows[0].inspection_document_status = 'INSPECTED'
  await page.$$eval('.suspect-filters button', buttons => buttons.find(button => button.textContent?.trim() === '查询')?.click())
  await page.waitForFunction(() => document.querySelector('.suspect-section').textContent.includes('当天共 21 条'))
  const locked = await page.$eval('.suspect-section tbody tr', row => row.textContent)
  assert.ok(locked.includes('已锁定') && locked.includes('编辑') && !locked.includes('撤销抄码'))
  await page.waitForSelector('.suspect-section .el-loading-mask', { hidden: true })
  await page.click('.suspect-section .btn-next')
  await page.waitForFunction(() => document.querySelectorAll('.suspect-section tbody tr').length === 1)
  await page.waitForSelector('.suspect-section .el-loading-mask', { hidden: true })
  await page.$$eval('.suspect-section tbody button', buttons => buttons.find(button => button.textContent?.trim() === '撤销抄码')?.click())
  await page.waitForSelector('.el-message-box', { visible: true })
  assert.match(await page.$eval('.el-message-box', element => element.textContent), /PAGE-21/)
  await page.$$eval('.el-message-box button', buttons => buttons.find(button => button.textContent?.trim() === '取消')?.click())
  assert.equal(deletedId, null)
  await page.waitForSelector('.el-message-box', { hidden: true })
  await page.$$eval('.suspect-section tbody button', buttons => buttons.find(button => button.textContent?.trim() === '撤销抄码')?.click())
  await page.waitForSelector('.el-message-box', { visible: true })
  await page.$$eval('.el-message-box button', buttons => buttons.find(button => button.textContent?.trim() === '确定')?.click())
  await page.waitForFunction(() => document.querySelectorAll('.suspect-section tbody tr').length === 20)
  assert.equal(deletedId, 120)
  assert.equal(reviewRequests.at(-1).searchParams.get('page'), '1')
  assert.equal(await page.$$eval('.el-table', elements => elements.length), 1)
  console.log('单表展示、编辑、客户及编号查询、分页、锁定、撤销确认及末页回退通过')

} finally {
  await browser.close()
}
