import fs from 'node:fs/promises'
import puppeteer from 'puppeteer-core'

const baseUrl = process.env.TEST_BASE_URL || 'http://127.0.0.1:5173'
const chrome = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const artifacts = new URL('../../artifacts/', import.meta.url)
await fs.mkdir(artifacts, { recursive: true })

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: 'new',
  pipe: true,
  timeout: 60000,
  args: ['--no-sandbox', '--disable-gpu', '--no-first-run', '--disable-background-networking'],
})
const page = await browser.newPage()
const problems = []
page.on('console', (message) => {
  if (message.type() === 'error') problems.push(`console: ${message.text()}`)
})
page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`))
page.on('requestfailed', (request) => problems.push(`requestfailed: ${request.url()} ${request.failure()?.errorText}`))

await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 })
await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle0' })
await page.evaluate(() => localStorage.clear())
await page.reload({ waitUntil: 'networkidle0' })
await page.type('input[autocomplete="username"]', process.env.TEST_USERNAME || 'admin')
await page.type('input[autocomplete="current-password"]', process.env.TEST_PASSWORD || 'Admin@123456')
await page.click('.login-form-panel .el-button--primary')
await page.waitForSelector('.app-shell')

await page.goto(`${baseUrl}/monthly-inventory`, { waitUntil: 'networkidle0' })
await page.waitForSelector('.inventory-section')
const titles = await page.$$eval('.inventory-heading h2', (items) => items.map((item) => item.textContent?.trim()))
if (titles.join('|') !== '入库|出库|结余') problems.push(`unexpected table titles: ${titles.join('|')}`)
const desktopLayout = await page.$eval('.inventory-table-wrap', (wrap) => {
  const category = wrap.querySelector('thead .sticky-category')?.getBoundingClientRect()
  const spec = wrap.querySelector('thead .sticky-spec')?.getBoundingClientRect()
  const right = wrap.querySelector('thead .sticky-right')?.getBoundingClientRect()
  const frame = wrap.getBoundingClientRect()
  return { categoryLeft: category?.left, categoryRight: category?.right, specLeft: spec?.left, right: right?.right, frameLeft: frame.left, frameRight: frame.right }
})
if (Math.abs(desktopLayout.categoryLeft - desktopLayout.frameLeft) > 1) problems.push('desktop category column is not fixed left')
if (Math.abs(desktopLayout.specLeft - desktopLayout.categoryRight) > 1) problems.push('desktop specification column is not fixed after category')
if (Math.abs(desktopLayout.right - desktopLayout.frameRight) > 1) problems.push('desktop summary column is not fixed right')
await page.screenshot({ path: new URL('monthly-inventory-desktop.png', artifacts).pathname, fullPage: true })

for (const button of await page.$$('.page-actions .el-button')) {
  if ((await button.evaluate(item => item.textContent)).includes('查看变更日志')) { await button.click(); break }
}
await page.waitForSelector('.el-drawer', { visible: true })
const logHeading = await page.$eval('.el-drawer__title', (item) => item.textContent?.trim())
if (logHeading !== '盘点变更日志') problems.push(`unexpected log drawer title: ${logHeading}`)
await page.screenshot({ path: new URL('monthly-inventory-logs-desktop.png', artifacts).pathname, fullPage: true })
await page.keyboard.press('Escape')

await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 })
await page.reload({ waitUntil: 'networkidle0' })
await page.waitForSelector('.inventory-section')
const mobileLayout = await page.$eval('.inventory-table-wrap', (wrap) => {
  const left = wrap.querySelector('thead .sticky-spec')?.getBoundingClientRect()
  const right = wrap.querySelector('thead .sticky-right')?.getBoundingClientRect()
  return {
    centerWidth: (right?.left || 0) - (left?.right || 0),
    documentOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  }
})
if (mobileLayout.centerWidth < 115) problems.push(`mobile month viewport is too narrow: ${mobileLayout.centerWidth}px`)
if (mobileLayout.documentOverflow > 1) problems.push(`mobile page overflows: ${mobileLayout.documentOverflow}px`)
await page.screenshot({ path: new URL('monthly-inventory-mobile.png', artifacts).pathname, fullPage: true })

await browser.close()
if (problems.length) {
  console.error(problems.join('\n'))
  process.exit(1)
}
console.log('Monthly inventory browser test passed.')
