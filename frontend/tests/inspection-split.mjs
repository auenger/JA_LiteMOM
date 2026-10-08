import assert from 'node:assert/strict'
import puppeteer from 'puppeteer-core'
const baseUrl = process.env.TEST_BASE_URL || 'http://127.0.0.1:5173'
const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: 'new', pipe: true, args: ['--no-sandbox', '--disable-gpu', '--no-first-run'] })
try {
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const user = { id: 1, username: 'admin', name: '超级管理员', is_active: true, is_superadmin: true, permissions: [] }
  const customers = [{ id: 1, name: '拆单甲客户', is_active: true }, { id: 2, name: '拆单乙客户', is_active: true }, { id: 3, name: '拆单丙客户', is_active: true }]
  const lines = Array.from({ length: 7 }, (_, index) => ({ id: index + 1, bottle_id: index + 1, sequence: index < 5 ? index + 1 : index - 4, body_code: `SPLIT-${index + 1}`, manufacture_date: '2023-01-01', manufacturer: '厂家', volume: '35.5', is_unverified: false }))
  const doc = (id, customer, docLines) => ({ id, document_no: `JY20261006-${id}`, inspection_date: '2026-10-06', source_dates: ['2026-10-05', '2026-10-06'], source_id: customer.id, customer_name: customer.name, inspector_name: '', total_quantity: docLines.length, lines: docLines, status: 'ACTIVE', created_at: '2026-10-06T10:00:00', updated_at: '2026-10-06T10:00:00', export_dates: {}, is_archived: false, is_retry: false })
  const source = doc(1, customers[0], lines.slice(0, 5))
  const documents = [source, doc(2, customers[1], lines.slice(5))]
  const histories = [], commits = []
  await page.setRequestInterception(true)
  page.on('request', request => {
    const url = new URL(request.url()), path = url.pathname
    const json = value => request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(value) })
    if (path === '/api/auth/me') json(user)
    else if (path === '/api/options') json({ sources: customers, specs: [{ id: 1, name: '15kg' }], users: [] })
    else if (path === '/api/inspection-documents') json({ items: documents, total: documents.length })
    else if (path.endsWith('/split-history')) { const id = Number(path.split('/')[3]); const items = histories.filter(item => item.source_document_id === id || item.target_document_id === id); json({ items, total: items.length }) }
    else if (path.endsWith('/split-preview')) {
      const payload = JSON.parse(request.postData())
      const selectedLines = source.lines.filter(line => line.sequence >= payload.start_sequence && line.sequence <= payload.end_sequence)
      const target = documents.find(item => item.source_id === payload.customer_id && item.id !== source.id)
      json({ source_updated_at: source.updated_at, line_ids: selectedLines.map(line => line.id), lines: selectedLines, quantity: selectedLines.length, source_quantity_after: source.lines.length - selectedLines.length, customer_name: customers.find(item => item.id === payload.customer_id).name, target_candidates: target ? [target] : [], target: target || null, will_create: !target, requires_target_selection: false })
    } else if (path.endsWith('/split')) {
      const payload = JSON.parse(request.postData()); commits.push(payload)
      const selectedLines = source.lines.filter(line => payload.expected_line_ids.includes(line.id))
      let target = documents.find(item => item.source_id === payload.customer_id && item.id !== source.id)
      const created = !target
      if (!target) { target = doc(3, customers[2], []); documents.push(target) }
      const history = { id: histories.length + 1, source_document_id: source.id, target_document_id: target.id, source_document_no: source.document_no, target_document_no: target.document_no, source_customer_name: source.customer_name, target_customer_name: target.customer_name, start_sequence: payload.start_sequence, end_sequence: payload.end_sequence, quantity: selectedLines.length, target_created: created, snapshot: structuredClone(selectedLines), created_by_name: '超级管理员', created_at: '2026-10-06T10:05:00' }
      source.lines = source.lines.filter(line => !payload.expected_line_ids.includes(line.id))
      target.lines.push(...selectedLines)
      for (const item of [source, target]) { item.lines.forEach((line, index) => { line.sequence = index + 1 }); item.total_quantity = item.lines.length }
      history.source_emptied = !source.lines.length
      if (history.source_emptied) source.status = 'SPLIT_EMPTY'
      histories.push(history)
      json({ source, target, history })
    } else if (/\/api\/inspection-documents\/\d+$/.test(path)) json(documents.find(item => item.id === Number(path.split('/').at(-1))))
    else if (path === '/api/bottles') json({ items: [{ id: 1, source_id: 1, effective_coding_customer_id: 3, coding_customer_name: customers[2].name, body_code: 'SPLIT-1', coding_date: '2026-10-06', spec_id: 1, zone: 'GOOD', inspection_document_status: 'INSPECTED' }], total: 1 })
    else if (path === '/api/coding/summary') json({ total: 1, items: [{ user_name: '超级管理员', spec_name: '15kg', customer_name: customers[2].name, quantity: 1 }] })
    else if (path.startsWith('/api/')) json({})
    else request.continue()
  })
  await page.goto(baseUrl)
  await page.evaluate(value => { localStorage.setItem('wms_token', 'test-token'); localStorage.setItem('wms_user', JSON.stringify(value)) }, user)
  await page.goto(`${baseUrl}/inspection-documents?document=1`, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.detail-header')
  const clickText = async (selector, text) => page.$$eval(selector, (elements, text) => elements.find(element => element.textContent.includes(text)).click(), text)
  const chooseCustomer = async name => {
    await page.click('.split-fields .el-select__wrapper')
    await page.waitForFunction(name => [...document.querySelectorAll('.el-select-dropdown__item')].some(element => element.textContent.includes(name) && element.getBoundingClientRect().width > 0), {}, name)
    await page.$$eval('.el-select-dropdown__item', (elements, name) => elements.find(element => element.textContent.includes(name) && element.getBoundingClientRect().width > 0).click(), name)
  }
  await clickText('.detail-header button', '拆单 / 分单')
  await page.waitForSelector('.split-fields input')
  const numbers = await page.$$('.split-fields .el-input-number input')
  for (const [index, value] of [[0, '2'], [1, '3']]) { await numbers[index].click({ clickCount: 3 }); await page.keyboard.type(value); await page.keyboard.press('Tab') }
  await chooseCustomer('拆单乙客户')
  await clickText('.el-dialog button', '预览拆单')
  await page.waitForSelector('.split-preview')
  assert.match(await page.$eval('.split-preview', element => element.textContent), /目标单由 2 只变为 4 只/)
  await clickText('.el-dialog__footer button', '确认拆分并合并')
  await page.waitForFunction(() => document.querySelector('.detail-header')?.textContent.includes('3 只'))
  await page.waitForSelector('.split-history .el-table')
  assert.deepEqual(commits[0].expected_line_ids, [2, 3]); assert.equal(commits[0].confirm_create, false)
  await clickText('.split-history button', '查看快照')
  await page.waitForFunction(() => [...document.querySelectorAll('.el-dialog__title')].some(element => element.textContent.includes('明细快照') && element.getBoundingClientRect().width > 0))
  assert.match(await page.$$eval('.el-dialog__body', elements => elements.find(element => element.getBoundingClientRect().width > 0).textContent), /原序号 2～3/)
  await page.$$eval('.el-dialog__headerbtn', elements => elements.find(element => element.getBoundingClientRect().width > 0).click())
  await page.waitForFunction(() => [...document.querySelectorAll('.el-dialog')].every(element => element.getBoundingClientRect().width === 0))
  await clickText('.detail-header button', '拆单 / 分单')
  await chooseCustomer('拆单丙客户')
  await clickText('.el-dialog button', '预览拆单')
  await page.waitForSelector('.split-preview')
  assert.match(await page.$eval('.split-preview', element => element.textContent), /尚无检验单/)
  await page.setViewport({ width: 390, height: 844 })
  await page.screenshot({ path: '../artifacts/inspection-split-mobile.png', fullPage: true })
  await clickText('.el-dialog__footer button', '创建新单并拆分')
  await page.waitForFunction(() => document.querySelector('.detail-header')?.textContent.includes('已拆空'))
  await page.waitForFunction(() => document.querySelectorAll('.split-history .el-table__body tbody tr').length === 2)
  assert.equal(commits[1].confirm_create, true)
  assert.ok(!await page.$$eval('.detail-header button', elements => elements.some(element => element.textContent.includes('拆单 / 分单'))))
  await page.goto(`${baseUrl}/coding`, { waitUntil: 'networkidle0' })
  assert.match(await page.$eval('.el-table__body', element => element.textContent), /拆单丙客户.*拆单甲客户/s)
  assert.deepEqual(errors, [])
  console.log('连续区间拆单、合并已有单、新建提示、拆空保留、历史快照和抄码客户展示通过')
} finally { await browser.close() }
