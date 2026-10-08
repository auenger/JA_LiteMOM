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
let expectingUnauthorized = false
page.on('console', (message) => {
  if (message.type() === 'error' && !expectingUnauthorized && !message.text().includes('404 (Not Found)')) problems.push(`console: ${message.text()}`)
})
page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`))
page.on('requestfailed', (request) => problems.push(`requestfailed: ${request.url()} ${request.failure()?.errorText}`))

await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 })
const faviconResponse = await page.goto(`${baseUrl}/favicon.ico`, { waitUntil: 'networkidle0' })
if (faviconResponse?.status() !== 200 || !faviconResponse.headers()['content-type']?.includes('image')) problems.push('favicon.ico is not served as an image')
await page.goto(`${baseUrl}/login`, { waitUntil: 'networkidle0' })
const loginDefaults = await page.$$eval('input', (inputs) => inputs.map((input) => input.value).filter(Boolean))
if (loginDefaults.length) problems.push('login page exposes preset credentials')
const loginText = await page.$eval('.login-form-panel', (element) => element.textContent || '')
if (loginText.includes('Admin@123456') || loginText.includes('admin_backup')) problems.push('login page contains preset account information')
await page.screenshot({ path: new URL('login-desktop.png', artifacts).pathname, fullPage: true })
await page.evaluate((credentials) => {
  const setValue = (selector, value) => {
    const input = document.querySelector(selector)
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set
    setter?.call(input, value)
    input?.dispatchEvent(new Event('input', { bubbles: true }))
    input?.dispatchEvent(new Event('change', { bubbles: true }))
  }
  setValue('input[autocomplete="username"]', credentials.username)
  setValue('input[autocomplete="current-password"]', credentials.password)
}, { username: process.env.TEST_USERNAME || 'admin', password: process.env.TEST_PASSWORD || 'Admin@123456' })
await page.click('.login-form-panel .el-button--primary')
await page.waitForSelector('.app-shell')
await page.waitForNetworkIdle()
const restoredSession = page.waitForResponse((response) => response.url().includes('/api/auth/me'))
await page.reload({ waitUntil: 'networkidle0' })
const restoredSessionResponse = await restoredSession
if (restoredSessionResponse.status() !== 200 || page.url().includes('/login')) problems.push('login session is not restored after page refresh')
await page.screenshot({ path: new URL('dashboard-desktop.png', artifacts).pathname, fullPage: true })

await page.click('.collapse-button')
await new Promise((resolve) => setTimeout(resolve, 250))
await page.hover('.nav-item')
await page.waitForSelector('.el-popper', { visible: true, timeout: 2000 })
const collapsedIconVisible = await page.$eval('.nav-item .game-icon', (icon) => {
  const style = getComputedStyle(icon)
  return style.display !== 'none' && Number.parseFloat(style.width) > 0
})
const tooltipText = await page.$$eval('.el-popper', (items) => items.map((item) => item.textContent?.trim()).find(Boolean))
if (!collapsedIconVisible) problems.push('collapsed navigation icon is hidden')
if (tooltipText !== '工作台') problems.push(`collapsed navigation tooltip missing: ${tooltipText}`)
await page.click('.collapse-button')

const sidebarLayout = await page.evaluate(() => {
  const sidebar = document.querySelector('.sidebar')
  const nav = document.querySelector('.sidebar nav')
  const collapse = document.querySelector('.collapse-button')
  if (!sidebar || !nav || !collapse) return null
  nav.scrollTop = nav.scrollHeight
  const sidebarRect = sidebar.getBoundingClientRect()
  const navRect = nav.getBoundingClientRect()
  const collapseRect = collapse.getBoundingClientRect()
  const navItems = document.querySelectorAll('.nav-item')
  const lastItemRect = navItems.item(navItems.length - 1)?.getBoundingClientRect()
  return {
    sidebarBottom: sidebarRect.bottom,
    navBottom: navRect.bottom,
    collapseTop: collapseRect.top,
    collapseBottom: collapseRect.bottom,
    collapseHeight: collapseRect.height,
    sidebarOverflow: getComputedStyle(sidebar).overflowY,
    lastItemBottom: lastItemRect?.bottom,
  }
})
if (!sidebarLayout) problems.push('sidebar layout missing')
else {
  if (Math.abs(sidebarLayout.sidebarBottom - sidebarLayout.collapseBottom) > 1) problems.push('collapse navigation is not fixed to sidebar bottom')
  if (Math.abs(sidebarLayout.navBottom - sidebarLayout.collapseTop) > 1) problems.push('navigation scroll area overlaps collapse control')
  if (sidebarLayout.collapseHeight < 50) problems.push(`collapse navigation is too short: ${sidebarLayout.collapseHeight}`)
  if (sidebarLayout.sidebarOverflow !== 'hidden') problems.push(`sidebar itself should not scroll: ${sidebarLayout.sidebarOverflow}`)
  if (sidebarLayout.lastItemBottom && sidebarLayout.lastItemBottom > sidebarLayout.collapseTop) problems.push('last navigation item is hidden behind collapse control')
}

const routes = ['materials', 'suppliers', 'bottle-sources', 'bottle-specs', 'quick-configs', 'material-inbounds', 'material-outbounds', 'material-returns', 'bottle-inbounds', 'quick-inbound', 'quick-outbound', 'quick-coding', 'coding-pool', 'coding', 'bottle-quality', 'bottle-outbounds', 'bottle-zones', 'monthly-inventory', 'users']
for (const route of routes) {
  await page.goto(`${baseUrl}/${route}`, { waitUntil: 'networkidle0' })
  const heading = await page.$eval('.page-header h1', (element) => element.textContent?.trim())
  if (!heading) problems.push(`missing heading: ${route}`)
}

// Shared route components and repeated clicks on the active menu must both trigger a fresh query.
await page.goto(`${baseUrl}/material-inbounds`, { waitUntil: 'networkidle0' })
await Promise.all([
  page.waitForResponse((response) => response.url().includes('/api/material-documents?') && response.url().includes('document_type=OUTBOUND')),
  page.$$eval('.nav-item', (items) => items.find((item) => item.textContent?.trim() === '材料出库')?.click()),
])
await Promise.all([
  page.waitForResponse((response) => response.url().includes('/api/material-documents?') && response.url().includes('document_type=OUTBOUND')),
  page.$$eval('.nav-item', (items) => items.find((item) => item.textContent?.trim() === '材料出库')?.click()),
])
await page.goto(`${baseUrl}/materials`, { waitUntil: 'networkidle0' })
await Promise.all([
  page.waitForResponse((response) => response.url().includes('/api/materials?')),
  page.$$eval('.nav-item', (items) => items.find((item) => item.textContent?.trim() === '原材料档案')?.click()),
])
await page.goto(`${baseUrl}/materials`, { waitUntil: 'networkidle0' })
await page.screenshot({ path: new URL('materials-desktop.png', artifacts).pathname, fullPage: true })
await page.click('.page-actions .el-button--primary')
await page.waitForSelector('.el-dialog')
await page.screenshot({ path: new URL('material-form-desktop.png', artifacts).pathname, fullPage: true })
await page.keyboard.press('Escape')
await page.goto(`${baseUrl}/material-inbounds`, { waitUntil: 'networkidle0' })
await page.screenshot({ path: new URL('material-inbound-desktop.png', artifacts).pathname, fullPage: true })
const materialDetailLink = await page.$('.table-link')
if (materialDetailLink) {
  await materialDetailLink.click()
  await page.waitForSelector('.el-dialog .report-actions', { visible: true })
  const materialReportButtons = await page.$$('.el-dialog .report-actions .el-button')
  if (materialReportButtons.length !== 2) problems.push(`material document report actions missing: ${materialReportButtons.length}`)
  await page.keyboard.press('Escape')
}
await page.goto(`${baseUrl}/monthly-inventory`, { waitUntil: 'networkidle0' })
await page.waitForSelector('.inventory-section')
const monthlyTableTitles = await page.$$eval('.inventory-section .inventory-heading h2', (items) => items.map((item) => item.textContent?.trim()))
if (monthlyTableTitles.join('|') !== '入库|出库|结余') problems.push(`unexpected monthly inventory tables: ${monthlyTableTitles.join('|')}`)
const monthlyTableLayout = await page.$eval('.inventory-table', (table) => {
  const first = table.querySelector('thead .sticky-left')?.getBoundingClientRect()
  const last = table.querySelector('thead .sticky-right')?.getBoundingClientRect()
  const wrap = table.closest('.inventory-table-wrap')?.getBoundingClientRect()
  return { firstLeft: first?.left, lastRight: last?.right, wrapLeft: wrap?.left, wrapRight: wrap?.right }
})
if (Math.abs(monthlyTableLayout.firstLeft - monthlyTableLayout.wrapLeft) > 1) problems.push('monthly inventory specification column is not pinned left')
if (Math.abs(monthlyTableLayout.lastRight - monthlyTableLayout.wrapRight) > 1) problems.push('monthly inventory summary column is not pinned right')
await page.screenshot({ path: new URL('monthly-inventory-desktop.png', artifacts).pathname, fullPage: true })
await page.click('.page-actions .el-button')
await page.waitForSelector('.el-drawer', { visible: true })
await page.screenshot({ path: new URL('monthly-inventory-logs-desktop.png', artifacts).pathname, fullPage: true })
await page.keyboard.press('Escape')
await page.goto(`${baseUrl}/bottle-outbounds`, { waitUntil: 'networkidle0' })
const historyTabs = await page.$$eval('.history-tabs .el-tabs__item', (items) => items.map((item) => item.textContent?.trim()))
const historyFilters = await page.$$('.inbound-filters .el-date-editor, .inbound-filters > .el-select')
const activeHistoryTab = await page.$eval('.history-tabs .el-tabs__item.is-active', (item) => item.textContent?.trim())
if (historyTabs.join('|') !== '入库|出库') problems.push(`unexpected history tabs: ${historyTabs.join('|')}`)
if (historyFilters.length !== 2) problems.push(`unexpected history filter count: ${historyFilters.length}`)
if (activeHistoryTab !== '出库') problems.push(`legacy outbound route did not open outbound tab: ${activeHistoryTab}`)
if (await page.$('.page-actions .el-button--primary')) problems.push('history page still exposes a create action')
await page.goto(`${baseUrl}/quick-coding`, { waitUntil: 'networkidle0' })
const quickReportButtons = await page.$$('.page-actions .report-actions .el-button')
const quickMetrics = await page.$$('.quick-context > div')
if (quickReportButtons.length !== 3) problems.push(`quick coding report actions missing: ${quickReportButtons.length}`)
if (quickMetrics.length !== 3) problems.push(`quick coding daily total metric missing: ${quickMetrics.length}`)
const visibleIcons = await page.$$eval('.game-icon', (icons) => icons.filter((icon) => getComputedStyle(icon).maskImage !== 'none').length)
if (visibleIcons < 5) problems.push(`game icons not rendered: ${visibleIcons}`)
const missingButtonGaps = await page.$$eval('.el-button .game-icon', (icons) => icons.filter((icon) => {
  const gap = Number.parseFloat(getComputedStyle(icon.parentElement).columnGap)
  return !Number.isFinite(gap) || gap < 4
}).length)
if (missingButtonGaps) problems.push(`icon button spacing missing: ${missingButtonGaps}`)

await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 })
for (const route of routes) {
  await page.goto(`${baseUrl}/${route}`, { waitUntil: 'networkidle0' })
  const pageOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  if (pageOverflow > 1) problems.push(`mobile page overflows horizontally: ${route} (${pageOverflow}px)`)
  const undersizedPageFields = await page.$$eval('input, textarea, select', (fields) => fields.filter((field) => {
    const style = getComputedStyle(field)
    const rect = field.getBoundingClientRect()
    return style.display !== 'none' && rect.width > 0 && rect.height > 0 && Number.parseFloat(style.fontSize) < 16
  }).map((field) => `${field.tagName.toLowerCase()}:${getComputedStyle(field).fontSize}`))
  if (undersizedPageFields.length) problems.push(`mobile page fields can trigger focus zoom: ${route} (${undersizedPageFields.join(', ')})`)
}
await page.goto(`${baseUrl}/dashboard`, { waitUntil: 'networkidle0' })
const quickButton = await page.$('.mobile-quick-entry')
if (!quickButton) problems.push('missing mobile quick-entry button')
await page.click('.menu-toggle')
await page.waitForSelector('.mobile-open .sidebar')
await new Promise((resolve) => setTimeout(resolve, 250))
await page.screenshot({ path: new URL('dashboard-mobile.png', artifacts).pathname, fullPage: true })
await page.goto(`${baseUrl}/monthly-inventory`, { waitUntil: 'networkidle0' })
await page.waitForSelector('.inventory-section')
await page.screenshot({ path: new URL('monthly-inventory-mobile.png', artifacts).pathname, fullPage: true })
await page.goto(`${baseUrl}/materials`, { waitUntil: 'networkidle0' })
await page.click('.page-actions .el-button--primary')
await page.waitForSelector('.el-dialog', { visible: true })
await new Promise((resolve) => setTimeout(resolve, 300))
const mobileDialog = await page.$eval('.el-dialog', (dialog) => {
  const rect = dialog.getBoundingClientRect()
  const body = dialog.querySelector('.el-dialog__body')
  const footer = dialog.querySelector('.el-dialog__footer')?.getBoundingClientRect()
  return { width: rect.width, height: rect.height, bottom: rect.bottom, bodyOverflow: body ? getComputedStyle(body).overflowY : '', footerBottom: footer?.bottom || 0 }
})
const undersizedMobileFields = await page.$$eval('.el-dialog input, .el-dialog textarea, .el-dialog select', (fields) => fields.filter((field) => {
  const style = getComputedStyle(field)
  return style.display !== 'none' && Number.parseFloat(style.fontSize) < 16
}).map((field) => `${field.tagName.toLowerCase()}:${getComputedStyle(field).fontSize}`))
const modalQuickActionsVisible = await page.$eval('.mobile-quick-actions', (actions) => getComputedStyle(actions).display !== 'none')
await page.screenshot({ path: new URL('material-form-mobile.png', artifacts).pathname, fullPage: true })
if (mobileDialog.width > 370 || mobileDialog.height > 820 || mobileDialog.bottom > 844) problems.push(`mobile dialog exceeds viewport: ${JSON.stringify(mobileDialog)}`)
if (mobileDialog.bodyOverflow !== 'auto') problems.push(`mobile dialog body is not scrollable: ${mobileDialog.bodyOverflow}`)
if (mobileDialog.footerBottom > 844) problems.push('mobile dialog actions are outside viewport')
if (undersizedMobileFields.length) problems.push(`mobile fields can trigger focus zoom: ${undersizedMobileFields.join(', ')}`)
if (modalQuickActionsVisible) problems.push('mobile quick actions overlap an open dialog')
await page.keyboard.press('Escape')
await page.goto(`${baseUrl}/quick-inbound`, { waitUntil: 'networkidle0' })
const inboundHeading = await page.$eval('.page-header h1', (element) => element.textContent?.trim())
if (inboundHeading !== '快速入库') problems.push(`unexpected quick-inbound heading: ${inboundHeading}`)
const inboundDateValue = await page.$eval('#quick-inbound-date', (input) => input.value)
if (!/^\d{4}-\d{2}-\d{2}$/.test(inboundDateValue)) problems.push(`quick inbound date is not prefilled: ${inboundDateValue}`)
await page.screenshot({ path: new URL('quick-inbound-mobile.png', artifacts).pathname, fullPage: true })
await page.goto(`${baseUrl}/quick-coding`, { waitUntil: 'networkidle0' })
await page.waitForSelector('.quick-entry-page')
const quickHeading = await page.$eval('.page-header h1', (element) => element.textContent?.trim())
if (quickHeading !== '快捷抄码') problems.push(`unexpected quick-coding heading: ${quickHeading}`)
const quickFieldLabels = await page.$$eval('.quick-fields .el-form-item__label', (labels) => labels.map((label) => label.textContent?.trim()))
const expectedQuickFields = ['瓶身编号', '生产日期', '检测备注（选填）']
if (quickFieldLabels.join('|') !== expectedQuickFields.join('|')) problems.push(`unexpected quick-entry field order: ${quickFieldLabels.join('|')}`)
await page.waitForFunction(() => window.scrollY === 0, { timeout: 2000 }).catch(() => {})
const quickScroll = await page.evaluate(() => window.scrollY)
if (quickScroll !== 0) problems.push(`quick-entry did not reset scroll: ${quickScroll}`)
await page.screenshot({ path: new URL('quick-entry-mobile.png', artifacts).pathname, fullPage: true })

expectingUnauthorized = true
await page.evaluate(() => localStorage.setItem('wms_token', 'expired-test-token'))
await page.goto(`${baseUrl}/dashboard`, { waitUntil: 'networkidle0' })
if (!page.url().includes('/login')) problems.push('invalid persisted login session is not cleared')
expectingUnauthorized = false

await browser.close()
if (problems.length) {
  console.error(problems.join('\n'))
  process.exit(1)
}
console.log(`Browser smoke passed: ${routes.length + 2} pages, ${visibleIcons} visible game icons.`)
