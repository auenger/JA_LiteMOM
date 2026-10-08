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
  await page.setViewport({ width: 375, height: 812, deviceScaleFactor: 1 })
  const user = { id: 1, username: 'test', name: '测试员', is_active: true, is_superadmin: true, permissions: [] }
  await page.setRequestInterception(true)
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname
    if (path === '/api/auth/me') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(user) })
    else if (path === '/api/options') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({
      sources: [], manufacturers: [], specs: [{ id: 1, name: '15kg', sort_order: 1, is_default: true, is_active: true }],
      code_prefixes: [{ id: 1, name: '常用前缀', value: '055' }],
      inspection_notes: [{ id: 1, name: '正常', value: '正常' }],
      date_presets: [{ id: 1, name: '去年生产', value: '2025.09' }],
    }) })
    else if (path === '/api/coding/pool') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({
      total_remaining: 10,
      batches: { items: [{ id: 1, remaining: 10, specs: [{ spec_id: 1, spec_name: '15kg', remaining: 10 }] }] },
    }) })
    else if (path === '/api/coding/summary') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ total: 0, items: [] }) })
    else if (path.startsWith('/api/')) request.respond({ status: 200, contentType: 'application/json', body: '{}' })
    else request.continue()
  })

  await page.goto(baseUrl)
  await page.evaluate((value) => {
    localStorage.setItem('wms_token', 'test-token')
    localStorage.setItem('wms_user', JSON.stringify(value))
  }, user)
  await page.goto(`${baseUrl}/quick-coding`, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.choice-button')

  const layout = await page.evaluate(() => {
    const page = document.querySelector('.quick-entry-page')
    const sections = [...page.querySelectorAll('.quick-form .quick-section')].map((el) => el.getAttribute('aria-label'))
    const topLevel = [...page.children].map((el) => el.classList.contains('quick-form') ? '录入区' : el.classList.contains('page-header') ? '页面说明' : el.classList.contains('quick-context') ? '统计' : '其他')
    const dateButton = [...page.querySelectorAll('.shortcut-row button')].find((el) => el.textContent.includes('2025.09'))
    const choice = page.querySelector('.choice-button')
    const spec = choice.querySelector('span:not(.game-icon)')
    return {
      sections, topLevel, dateButtonText: dateButton?.textContent.trim(),
      choicePadding: getComputedStyle(choice).paddingTop,
      shortcutPadding: getComputedStyle(dateButton).paddingTop,
      fieldMargin: getComputedStyle(page.querySelector('.quick-fields .el-form-item')).marginBottom,
      visibleFieldLabels: page.querySelectorAll('.quick-fields .el-form-item__label').length,
      visibleSectionTitles: page.querySelectorAll('.quick-form .quick-label').length,
      inputNames: [...page.querySelectorAll('.quick-fields input')].map((input) => input.getAttribute('aria-label')).filter(Boolean),
      overflow: document.documentElement.scrollWidth > window.innerWidth,
      removedHints: !page.textContent.includes('只显示当前来源仍有待抄码余量的规格') && !page.textContent.includes('扫描编号后按回车可直接抄码'),
    }
  })
  assert.deepEqual(layout.sections, ['选择供瓶单位', '录入钢瓶信息', '选择钢瓶规格'])
  assert.deepEqual(layout.topLevel.slice(0, 3), ['录入区', '页面说明', '统计'])
  assert.equal(layout.dateButtonText, '2025.09')
  assert.equal(layout.choicePadding, '4px')
  assert.equal(layout.shortcutPadding, '2px')
  assert.equal(layout.fieldMargin, '8px')
  assert.equal(layout.visibleFieldLabels, 0)
  assert.equal(layout.visibleSectionTitles, 0)
  assert.ok(layout.inputNames.includes('瓶身编号'))
  assert.ok(layout.inputNames.includes('生产厂家'))
  assert.ok(layout.inputNames.includes('生产日期'))
  assert.ok(!layout.inputNames.includes('检测备注（选填）'))
  assert.equal(layout.overflow, false)
  assert.equal(layout.removedHints, true)
  assert.match(await page.$eval('.date-missing-warning', element => element.textContent), /请选择对应的生产日期.*未填写仍可保存.*标黄提醒/)
  await page.$$eval('.shortcut-row button', buttons => buttons.find(button => button.textContent.includes('2025.09'))?.click())
  await page.waitForFunction(() => !document.querySelector('.date-missing-warning'))
  const codeSelector = 'input[aria-label="瓶身编号"]'
  await page.type(codeSelector, '055111111111')
  await page.$eval(codeSelector, (input) => input.blur())
  await page.click(codeSelector)
  await new Promise((resolve) => setTimeout(resolve, 30))
  const selection = await page.$eval(codeSelector, (input) => ({
    value: input.value, start: input.selectionStart, end: input.selectionEnd,
  }))
  assert.equal(selection.value, '055111111111')
  assert.equal(selection.start, 0)
  assert.equal(selection.end, selection.value.length)
  await page.keyboard.type('ABCDEFGHIJKLMN')
  await page.waitForSelector('.code-length-warning')
  assert.match(await page.$eval('.code-length-warning', element => element.textContent), /超过 13 位.*仍可正常保存.*当前 14 位/)
  assert.equal(await page.$$('.quick-fields .el-form-item__error').then(elements => elements.length), 0)
  console.log('快捷抄码手机端生产日期默认提醒及超过 13 位仅提醒通过')
} finally {
  await browser.close()
}
