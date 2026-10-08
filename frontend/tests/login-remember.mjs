import assert from 'node:assert/strict'
import puppeteer from 'puppeteer-core'

const baseUrl = process.env.TEST_BASE_URL || 'http://127.0.0.1:5173'
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: 'new',
  pipe: true,
  args: ['--no-sandbox', '--disable-gpu', '--no-first-run'],
})

try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1366, height: 768, deviceScaleFactor: 1 })
  const user = {
    id: 1, username: 'login-test', name: '登录测试', role_name: '测试人员',
    is_active: true, is_superadmin: true, must_change_password: false, permissions: [],
  }
  await page.setRequestInterception(true)
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (url.pathname === '/api/auth/login') {
      request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ access_token: 'test-token', user }) })
    } else if (url.pathname === '/api/auth/me') {
      request.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(user) })
    } else if (url.pathname.startsWith('/api/')) {
      request.respond({ status: 200, contentType: 'application/json', body: '{}' })
    } else {
      request.continue()
    }
  })

  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle0' })
  await page.screenshot({ path: '/tmp/ailite-login-desktop.png' })
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 })
  await page.screenshot({ path: '/tmp/ailite-login-mobile.png' })
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false)
  assert.equal(await page.$eval('.login-watermark a', (link) => link.href), 'https://siliroot.com/')
  assert.match(await page.$eval('.login-watermark', (element) => element.textContent), /苏州硅基源流/)
  await page.setViewport({ width: 1366, height: 768, deviceScaleFactor: 1 })
  assert.equal(await page.$eval('input[autocomplete="username"]', (input) => input.value), '')
  assert.match(await page.$eval('.login-brand h1', (element) => element.textContent), /锦安特种设备检测/)
  await page.type('input[autocomplete="username"]', 'login-test')
  await page.type('input[autocomplete="current-password"]', 'Remember@123')
  await page.click('.login-submit')
  await page.waitForFunction(() => Boolean(localStorage.getItem('wms_login_credentials')))
  await page.waitForSelector('.topbar-watermark a')
  await page.screenshot({ path: '/tmp/ailite-header-desktop.png' })
  assert.equal(await page.$eval('.topbar-watermark a', (link) => link.href), 'https://siliroot.com/')
  assert.match(await page.$eval('.topbar-watermark', (element) => element.textContent), /苏州硅基源流/)
  assert.equal(await page.$eval('.topbar-watermark', (element) => getComputedStyle(element).color), 'rgba(212, 175, 55, 0.4)')
  const subtitleAlignment = await page.evaluate(() => {
    const subtitle = document.querySelector('.brand-copy small').getBoundingClientRect()
    const watermark = document.querySelector('.topbar-watermark').getBoundingClientRect()
    return { subtitleY: subtitle.y + subtitle.height / 2, watermarkY: watermark.y + watermark.height / 2 }
  })
  assert.ok(Math.abs(subtitleAlignment.subtitleY - subtitleAlignment.watermarkY) < 2, JSON.stringify(subtitleAlignment))
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 })
  await page.screenshot({ path: '/tmp/ailite-header-mobile.png' })
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth), false)
  await page.setViewport({ width: 1366, height: 768, deviceScaleFactor: 1 })
  assert.deepEqual(await page.evaluate(() => JSON.parse(localStorage.getItem('wms_login_credentials'))), {
    username: 'login-test', password: 'Remember@123',
  })

  await page.click('.user-chip')
  await page.waitForSelector('.el-dialog')
  const passwordInputs = await page.$$('.el-dialog input')
  await passwordInputs[0].type('Remember@123')
  await passwordInputs[1].type('Changed@123')
  await passwordInputs[2].type('Changed@123')
  await page.click('.el-dialog__footer .el-button--primary')
  await page.waitForFunction(() => JSON.parse(localStorage.getItem('wms_login_credentials')).password === 'Changed@123')

  await page.evaluate(() => { localStorage.removeItem('wms_token'); localStorage.removeItem('wms_user') })
  await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle0' })
  assert.equal(await page.$eval('input[autocomplete="username"]', (input) => input.value), 'login-test')
  assert.equal(await page.$eval('input[autocomplete="current-password"]', (input) => input.value), 'Changed@123')

  await page.click('.login-remember .el-checkbox')
  await page.click('.login-submit')
  await page.waitForFunction(() => localStorage.getItem('wms_remember_login') === 'false')
  assert.equal(await page.evaluate(() => localStorage.getItem('wms_login_credentials')), null)
  console.log('登录凭据保存、自动填充和取消记住均通过')
} finally {
  await browser.close()
}
