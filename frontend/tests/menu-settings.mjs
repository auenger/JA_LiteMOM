import assert from 'node:assert/strict'
import puppeteer from 'puppeteer-core'
const origin = process.env.TEST_BASE_URL || 'http://127.0.0.1:5178'
const browser = await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--no-sandbox']})
let token, original
async function api(path, method='GET', body) {
  const response = await fetch(`${origin}/api${path}`,{method,headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},body:body ? JSON.stringify(body):undefined})
  assert.ok(response.ok, await response.clone().text())
  return response.json()
}
try {
  token = (await api('/auth/login','POST',{username:'admin',password:'Admin@123456'})).access_token
  original = await api('/menu-settings')
  const page = await browser.newPage()
  const errors=[];page.on('pageerror',e=>errors.push(e.message))
  await page.setViewport({width:1440,height:1000})
  await page.goto(`${origin}/login`)
  await page.evaluate(t=>localStorage.setItem('wms_token',t),token)
  await page.goto(`${origin}/menu-settings`,{waitUntil:'networkidle0'})
  await page.waitForSelector('[aria-label="原材料分组上移"]')
  async function clickText(label) { for(const button of await page.$$('button')) if((await button.evaluate(el=>el.textContent)).trim()===label){await button.click();return} throw Error(label) }
  await clickText('恢复默认')
  await page.click('[aria-label="原材料分组上移"]')
  await page.click('[aria-label="出入库日志上移"]')
  await page.$eval('[aria-label="原材料档案是否显示"]', el=>el.closest('.el-switch').click())
  const saved = page.waitForResponse(r=>r.url().endsWith('/api/menu-settings')&&r.request().method()==='PUT')
  await clickText('保存设置'); assert.equal((await saved).status(),200)
  await page.reload({waitUntil:'networkidle0'})
  assert.equal(await page.$eval('[aria-label="原材料档案是否显示"]',el=>el.getAttribute('aria-checked')),'false')
  const nav = await page.$eval('nav[aria-label="系统导航"]',el=>el.innerText)
  assert.ok(!nav.includes('原材料档案'))
  assert.ok(nav.indexOf('出入库日志') < nav.indexOf('原材料出入库管理'))
  assert.ok(nav.indexOf('出入库日志') < nav.indexOf('供应商'))
  assert.match(nav,/菜单设置/)
  await page.screenshot({path:'../artifacts/menu-settings-desktop.png',fullPage:true})
  // Create a group and rename a menu, then move the menu into the new group.
  await clickText('新增分组')
  await page.waitForSelector('.el-message-box__input input', { visible: true })
  await page.type('.el-message-box__input input', '常用业务')
  for(const button of await page.$$('.el-message-box button')) if((await button.evaluate(el=>el.textContent)).trim()==='新增'){await button.click();break}
  await page.waitForFunction(() => [...document.querySelectorAll('.group-heading strong')].some(el=>el.textContent==='常用业务'))
  await page.waitForSelector('.el-message-box', { hidden: true })
  const nameInput = 'input[aria-label="/material-daily-logs菜单名称"]'
  await page.$eval(nameInput, el => { el.focus(); el.select() }); await page.keyboard.type('材料变更明细')
  assert.equal(await page.$eval(nameInput, el => el.value), '材料变更明细')
  // Move an item into another group and confirm the persisted structure.
  const group=await page.$$('.menu-group')
  const materialGroup=group[1]
  const selector=await materialGroup.$('.el-select__wrapper')
  await selector.evaluate(el => el.click())
  await page.waitForFunction(() => [...document.querySelectorAll('.el-select-dropdown__item')].some(el=>el.getBoundingClientRect().height>0))
  for(const option of await page.$$('.el-select-dropdown__item')) if(await option.evaluate(el=>el.textContent.trim()==='常用业务' && el.getBoundingClientRect().height>0)){await option.click();break}
  const moved=page.waitForResponse(r=>r.url().endsWith('/api/menu-settings')&&r.request().method()==='PUT')
  await clickText('保存设置');assert.equal((await moved).status(),200)
  const settings=await api('/menu-settings')
  assert.ok(settings.groups.find(g=>g.label==='常用业务').items.some(i=>i.path==='/material-daily-logs' && i.label==='材料变更明细'), JSON.stringify(settings.groups))
  await page.reload({waitUntil:'networkidle0'})
  assert.match(await page.$eval('nav[aria-label="系统导航"]',el=>el.innerText), /常用业务[\s\S]*材料变更明细/)
  await page.setViewport({width:390,height:844})
  await page.reload({waitUntil:'networkidle0'})
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await page.screenshot({path:'../artifacts/menu-settings-mobile.png',fullPage:true})
  assert.deepEqual(errors,[])
  console.log('Menu browser checks passed: reorder groups/items, hide, move groups, persistence, protected entry, custom group/name, mobile.')
} finally {
  if(original){const current=await api('/menu-settings');await api('/menu-settings','PUT',{groups:original.groups,version:current.version})}
  await browser.close()
}
