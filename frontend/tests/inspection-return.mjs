import assert from 'node:assert/strict'
import puppeteer from 'puppeteer-core'
const origin=process.env.TEST_BASE_URL || 'http://127.0.0.1:5178'
const browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--no-sandbox']})
try {
 const page=await browser.newPage(),errors=[];page.on('requestfailed',r=>console.log('Request failed',new URL(r.url()).pathname));page.on('pageerror',e=>errors.push(e.message));await page.setViewport({width:1440,height:1000})
 let row={id:70001,body_code:'RETURN-TEST',source_id:1,spec_id:1,zone:'GOOD',coding_date:'2026-09-27',coded_by_name:'测试',inspection_document_status:'UNINSPECTED',returned_to_customer:null}
 let saved,filter
 await page.setRequestInterception(true)
 page.on('request',r=>{
  const u=new URL(r.url());let data
  if(u.pathname==='/api/auth/me') data={id:1,username:'tester',name:'测试员',is_superadmin:true,permissions:[]}
  else if(u.pathname==='/api/menu-settings') data={version:0,groups:[]}
  else if(u.pathname==='/api/options') data={sources:[{id:1,name:'测试单位'}],specs:[{id:1,name:'测试规格'}]}
  else if(u.pathname==='/api/bottles' && r.method()==='GET') {filter=u.searchParams.get('returned_to_customer');data={items:u.searchParams.get('zone')===row.zone?[row]:[],total:u.searchParams.get('zone')===row.zone?1:0}}
  else if(u.pathname==='/api/bottles/70001/status') {saved=JSON.parse(r.postData());row={...row,...saved};data=row}
  else {r.continue();return}
  r.respond({status:200,contentType:'application/json',body:JSON.stringify(data)})
 })
 console.log('Opening login');await page.goto(origin+'/login');await page.evaluate(()=>localStorage.setItem('wms_token','return-ui-test'))
 await page.goto(origin+'/bottle-quality',{waitUntil:'networkidle2'});console.log('Opened quality')
 async function clickText(selector,text){for(const el of await page.$$(selector)){if((await el.evaluate(e=>e.textContent)).trim()===text){await el.click();return}}throw Error('Missing '+text)}
 console.log('Opening change');await clickText('button','转为不良品');await page.waitForSelector('.el-dialog',{visible:true})
 assert.ok((await page.$eval('.el-dialog',e=>e.innerText)).includes('是否退还客户'))
 await page.click('.el-dialog input[type=radio][value=true]')
 await clickText('.el-dialog button','确认调整');console.log('Clicked save');await new Promise(r=>setTimeout(r,600))
 console.log('Saved');assert.equal(saved.returned_to_customer,true);assert.equal(saved.zone,'BAD')
 await clickText('.el-radio-button','不良品库');await new Promise(r=>setTimeout(r,600))
 assert.ok((await page.$eval('.el-table',e=>e.innerText)).includes('退还客户'))
 await page.click('.inventory-filters .el-select');await clickText('.el-select-dropdown__item','退还客户：是');await new Promise(r=>setTimeout(r,600));assert.equal(filter,'true')
 await page.hover('.inventory-filters .el-select');await page.click('.inventory-filters .el-select__clear');await new Promise(r=>setTimeout(r,600));assert.equal(filter,null)
 await page.setViewport({width:390,height:844});await page.screenshot({path:'../artifacts/inspection-return-mobile.png',fullPage:true})
 assert.deepEqual(errors,[])
 console.log('Return flag UI verified: select/save, BAD column, filter/clear, mobile layout.')
}finally{await browser.close()}
