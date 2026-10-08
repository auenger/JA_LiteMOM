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
  const user = { id: 1, username: 'test', name: '测试员', is_active: true, is_superadmin: true, permissions: [] }
  await page.setRequestInterception(true)
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname
    if (path === '/api/auth/me') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(user) })
    else if (path === '/api/options') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ sources: [{ id: 1, name: '测试客户', is_default: true }], specs: [{ id: 1, name: '15kg' }] }) })
    else if (path === '/api/quick-outbound/availability') request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ 1: { good: 10, temporary: 10, scrap: 10, bad: 10 } }) })
    else if (path.startsWith('/api/')) request.respond({ status: 200, contentType: 'application/json', body: '{}' })
    else request.continue()
  })
  await page.goto(baseUrl)
  await page.evaluate((value) => {
    localStorage.setItem('wms_token', 'test-token')
    localStorage.setItem('wms_user', JSON.stringify(value))
  }, user)

  for (const route of ['quick-inbound', 'quick-outbound']) {
    await page.goto(`${baseUrl}/${route}`, { waitUntil: 'networkidle0' })
    const selector = '.spec-lines input'
    await page.waitForSelector(selector)
    await page.click(selector)
    await new Promise((resolve) => setTimeout(resolve, 50))
    const selection = await page.$eval(selector, (input) => ({
      type: input.type, value: input.value, start: input.selectionStart, end: input.selectionEnd,
    }))
    assert.deepEqual(selection, { type: 'text', value: '0', start: 0, end: 1 }, route)
    await page.keyboard.type('5')
    assert.equal(await page.$eval(selector, (input) => input.value), '5', route)
  }
  console.log('快速入库和快速出库数量框聚焦全选通过')
} finally {
  await browser.close()
}
