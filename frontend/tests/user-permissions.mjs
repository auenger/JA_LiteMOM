import assert from 'node:assert/strict'
import puppeteer from 'puppeteer-core'
const origin = process.env.TEST_BASE_URL || 'http://127.0.0.1:5178'
const response = await fetch(`${origin}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'admin', password: 'Admin@123456' }) })
const token = (await response.json()).access_token
async function api(path, method='GET', data) {
  const result = await fetch(`${origin}/api${path}`, { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: data ? JSON.stringify(data) : undefined })
  assert.ok(result.ok, await result.clone().text()); return result.status === 204 ? null : result.json()
}
const username = `permission_${Date.now()}`
const user = await api('/users', 'POST', { username, name: '权限功能验证', password: 'TestPassword123', permissions: ['daily_inventory:view'] })
const catalog = await api('/permissions/catalog')
const browser = await puppeteer.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--no-sandbox'] })
try {
  const page = await browser.newPage(), errors=[];page.on('pageerror',e=>errors.push(e.message))
  await page.setViewport({width:1440,height:1000})
  await page.setRequestInterception(true)
  let ordinary = false
  page.on('request', request => {
    const path = new URL(request.url()).pathname
    if (path === '/api/menu-settings') request.respond({status:200,contentType:'application/json',body:JSON.stringify({version:0,groups:[{label:'自定义业务',items:[{path:'/daily-inventory',label:'每日盘存',hidden:false},{path:'/material-daily-logs',label:'材料流水',hidden:true}]}]})})
    else if(path === '/api/users' && request.method()==='GET') request.respond({status:200,contentType:'application/json',body:JSON.stringify({items:[user],total:1})})
    else if(path === '/api/auth/me' && ordinary) request.respond({status:200,contentType:'application/json',body:JSON.stringify({id:900,name:'普通管理人员',username:'ordinary',is_superadmin:false,permissions:['users:view','users:update']})})
    else request.continue()
  })
  await page.goto(`${origin}/login`);await page.evaluate(t=>localStorage.setItem('wms_token',t),token)
  async function openEditor(){await page.goto(`${origin}/users`,{waitUntil:'networkidle0'});for(const button of await page.$$('.el-table button'))if((await button.evaluate(el=>el.textContent)).trim()==='编辑'){await button.click();break}await page.waitForSelector('.permission-panel',{visible:true})}
  await openEditor()
  const content=await page.$eval('.permission-panel',el=>el.innerText)
  for(const title of ['自定义业务','每日盘存','材料流水','菜单已隐藏','瓶子生命周期','原材料入库','材料出库','退料入库','仅超级管理员可用'])assert.ok(content.includes(title),title)
  const actual=await page.$$eval('.permission-panel input[type=checkbox]',els=>els.map(el=>el.value))
  const expected=catalog.flatMap(group=>group.items.map(item=>item[0]))
  assert.deepEqual([...actual].sort(),[...expected].sort())
  assert.equal(await page.$eval('input[aria-label="登录账号"]',el=>el.disabled),false)
  await page.$eval('input[aria-label="登录账号"]',el=>{el.focus();el.select()});await page.keyboard.type(`${username}_new`)
  const saved=page.waitForResponse(r=>r.url().includes(`/api/users/${user.id}`)&&r.request().method()==='PUT')
  for(const button of await page.$$('.el-dialog__footer button'))if((await button.evaluate(el=>el.textContent)).trim()==='保存'){await button.click();break}
  assert.equal((await saved).status(),200)
  const users=await api('/users?page_size=100');assert.equal(users.items.find(item=>item.id===user.id).username,`${username}_new`)
  ordinary=true
  await openEditor()
  assert.equal(await page.$eval('input[aria-label="登录账号"]',el=>el.disabled),true)
  assert.deepEqual(errors,[])
  console.log('Permission editor verified: every permission present once, custom menu/group names and hidden items, superadmin rename, ordinary account locked.')
} finally {await browser.close();await api(`/users/${user.id}`,'DELETE')}
