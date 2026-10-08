import assert from 'node:assert/strict'
import puppeteer from 'puppeteer-core'
const origin = process.env.TEST_BASE_URL || 'http://127.0.0.1:5178'
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--no-sandbox'] })
try {
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', err => errors.push(err.message))
  await page.setViewport({width: 1440, height: 900})
  await page.goto(`${origin}/login`)
  const materialName = `页面验证-${Date.now()}`
  await page.evaluate(async name => {
    const login = await fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:'admin',password:'Admin@123456'})}).then(r=>r.json())
    localStorage.setItem('wms_token', login.access_token)
    const response = await fetch('/api/materials', {method:'POST', headers:{'Content-Type':'application/json',Authorization:`Bearer ${login.access_token}`},body:JSON.stringify({name, material_unit:'袋',conversion_enabled:true,stock_unit:'kg',conversion_ratio:2.5})})
    if (!response.ok) throw new Error(await response.text())
  }, materialName)
  await page.goto(`${origin}/material-daily`, {waitUntil:'networkidle0'})
  const incoming = `input[aria-label="${materialName}当天入库"]`
  const outgoing = `input[aria-label="${materialName}当天出库"]`
  await page.waitForSelector(incoming)
  async function enter(selector, value) {
    await page.click(selector, {clickCount:3})
    await page.keyboard.type(value)
    const response = page.waitForResponse(r => r.url().includes('/api/material-daily/') && r.request().method()==='PUT')
    await page.keyboard.press('Tab')
    assert.equal((await response).status(),200)
    await page.waitForFunction(() => document.querySelector('[role="status"]')?.textContent.includes('已自动保存'))
  }
  await enter(incoming, '10')
  await enter(outgoing, '3')
  const rowText = await page.$eval(incoming, input => input.closest('tr').innerText)
  assert.match(rowText, /17.5 kg/)
  await page.reload({waitUntil:'networkidle0'})
  assert.equal(await page.$eval(outgoing, input => input.value), '3.00')
  await page.screenshot({path:'../artifacts/material-daily-desktop.png', fullPage:true})
  const logButton = await page.$$('button')
  for (const button of logButton) if ((await button.evaluate(el=>el.textContent)).includes('出入库日志')) { await button.click(); break }
  await page.waitForFunction(() => location.pathname === '/material-daily-logs' && document.querySelector('.el-table')?.innerText.includes('超级管理员'))
  assert.match(await page.$eval('.el-table', el=>el.innerText), /0 → 3/)
  await page.goto(`${origin}/material-daily`, {waitUntil:'networkidle0'})
  await page.setViewport({width:390,height:844})
  await page.reload({waitUntil:'networkidle0'})
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
  await page.screenshot({path:'../artifacts/material-daily-mobile.png', fullPage:true})
  assert.deepEqual(errors, [])
  console.log('Material daily browser checks passed: autosave, balance, reload, logs, mobile.')
} finally { await browser.close() }
