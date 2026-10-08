import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import puppeteer from 'puppeteer-core'
const origin = process.env.TEST_BASE_URL || 'http://localhost:5173'
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--no-sandbox'] })
try {
  const page = await browser.newPage()
  const errors = []; page.on('pageerror', e => errors.push(e.message))
  function report(daily) {
    const months = Array.from({ length: daily ? 31 : 12 }, (_, i) => ({ key: daily ? `2026-08-${String(i + 1).padStart(2, '0')}` : `2026-${String(i + 1).padStart(2, '0')}`, label: daily ? `8月${i + 1}日` : `${i + 1}月` }))
    const table = (prefix) => ({ rows: Array.from({ length: 4 }, (_, i) => ({
      metric: `${prefix}_${i < 2 ? 'PENDING' : 'SCRAP'}`, category: i < 2 ? 'PENDING' : 'SCRAP', category_label: i < 2 ? '待检' : '报废', category_first: i % 2 === 0, category_rowspan: 2,
      spec_id: i % 2 + 1, spec_name: i % 2 ? '末行规格50kg' : '15kg', values: Object.fromEntries(months.map((month, index) => [month.key, index === months.length - 1 ? 9876 : i + index])), modified_months: [months[0].key], summary: 9876,
    })), totals: Object.fromEntries(months.map(month => [month.key, 39504])), summary: 39504 })
    return { months, date_from: months[0].key, date_to: months.at(-1).key, source_id: 1, source_name: '完整图片测试公司', editable: true, sources: [{ id: 1, name: '完整图片测试公司', is_active: true }], tables: { inbound: table('INBOUND'), outbound: table('OUTBOUND'), balance: table('BALANCE') } }
  }
  await page.setRequestInterception(true)
  page.on('request', r => {
    const path = new URL(r.url()).pathname
    let data
    if (path === '/api/auth/me') data = { id: 1, name: '测试', username: 'admin', is_superadmin: true, permissions: [] }
    if (path === '/api/menu-settings') data = { groups: [], version: 0 }
    if (path === '/api/daily-inventory') data = report(true)
    if (path === '/api/monthly-inventory') data = report(false)
    if (data) r.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(data) }); else r.continue()
  })
  await page.goto(`${origin}/login`)
  await page.evaluate(() => localStorage.setItem('wms_token', 'inventory-image-test'))
  for (const [route, title, lastColumn] of [['daily-inventory', '日度盘点', '8月31日'], ['monthly-inventory', '月度盘点', '12月']]) {
    await page.setViewport({ width: 1440, height: 900 })
    await page.goto(`${origin}/${route}`, { waitUntil: 'networkidle0' })
    await page.waitForSelector('.inventory-section')
    assert.equal((await page.$$('button[aria-label$="复制结果"]')).length, 4)
    await page.evaluate(() => {
      window.drawn = []; window.copiedPng = null
      const draw = CanvasRenderingContext2D.prototype.fillText
      CanvasRenderingContext2D.prototype.fillText = function(text, ...args) { window.drawn.push(text); return draw.call(this, text, ...args) }
      Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { write: async items => {
        const blob = await items[0].getType('image/png')
        const bitmap = await createImageBitmap(blob)
        window.pngSize = { width: bitmap.width, height: bitmap.height }; bitmap.close()
        window.copiedPng = await new Promise(resolve => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.readAsDataURL(blob) })
      } } })
    })
    await page.click(`button[aria-label="${title}复制结果"]`)
    await page.waitForFunction(() => window.copiedPng)
    const full = await page.evaluate(() => ({ png: window.copiedPng, size: window.pngSize, drawn: window.drawn }))
    for (const text of ['入库', '出库', '结余', lastColumn, '末行规格50kg', '9876', '39504', '公司：完整图片测试公司']) assert.ok(full.drawn.includes(text), `${route}: missing ${text}`)
    assert.ok(full.size.width > 1440)
    await fs.writeFile(`../artifacts/${route}-full-result.png`, Buffer.from(full.png.split(',')[1], 'base64'))
    await page.evaluate(() => { window.copiedPng = null; window.drawn = [] })
    await page.click(`button[aria-label="${title} · 结余复制结果"]`)
    await page.waitForFunction(() => window.copiedPng)
    const single = await page.evaluate(() => ({ size: window.pngSize, drawn: window.drawn }))
    assert.ok(single.size.height < full.size.height)
    assert.ok(!single.drawn.includes('入库') && single.drawn.includes('结余'))
    // In HTTP environments image clipboard is unavailable: show the full PNG instead.
    await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined }))
    await page.click(`button[aria-label="${title} · 入库复制结果"]`)
    await page.waitForSelector('.image-preview img', { visible: true })
    await page.waitForFunction(() => document.querySelector('.image-preview img').naturalWidth > 1440)
    await page.keyboard.press('Escape')
    await page.setViewport({ width: 390, height: 844 })
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
  }
  assert.deepEqual(errors, [])
  console.log('Inventory image checks passed: both pages, whole report + per card, all 31 days/12 months, totals, PNG clipboard, HTTP fallback, mobile.')
} finally { await browser.close() }
