import assert from 'node:assert/strict'
import { mkdir, readFile, rm } from 'node:fs/promises'
import { resolve } from 'node:path'
import puppeteer from 'puppeteer-core'
const origin=process.env.TEST_BASE_URL || 'http://127.0.0.1:5178'
const destination=resolve('../artifacts/receipt-word-test');await mkdir(destination,{recursive:true})
const filename='收发记录-诸城市惠泽燃气有限公司.docx'
await rm(resolve(destination,filename),{force:true})
const sample=`液化石油气
2026年9月24号收到诸城市惠泽燃气有限公司
液化石油气瓶共902个
2026年9月26号收到诸城市惠泽燃气有限公司
液化石油气瓶共902个
2026年9月26号出给诸城市惠泽燃气有限公司
液化石油气瓶共897个，其中检验合格的共893个（带回）
沙眼共4个（带回）
071220064461
005221980681
003210974252
071220099879
报废共3个（未带回）
003210974118
003221008110
003221596860
未检验的共2个（未带回）`
const browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--no-sandbox']})
try {
 const page=await browser.newPage();await page.setViewport({width:1440,height:1050});const errors=[];page.on('pageerror',e=>errors.push(e.message))
 const cdp=await page.createCDPSession();await cdp.send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:destination})
 let selection
 const make=(id)=>({id,document_no:`IN-${id}`,source_id:1,business_date:'2026-09-24',status:'POSTED',handler:'测试',lines:[],pending_quantity:902,temporary_quantity:0,scrap_quantity:0,total_quantity:902})
 await page.setRequestInterception(true)
 page.on('request',r=>{
  const u=new URL(r.url());let data
  if(u.pathname==='/api/auth/me') data={id:1,username:'tester',name:'测试',is_superadmin:true,permissions:[]}
  else if(u.pathname==='/api/menu-settings') data={version:0,groups:[]}
  else if(u.pathname==='/api/options') data={sources:[{id:1,name:'诸城市惠泽燃气有限公司'}],specs:[],users:[]}
  else if(u.pathname==='/api/bottle-inbounds') data={items:u.searchParams.get('page')==='2'?[make(21)]:Array.from({length:20},(_,i)=>make(i+1)),total:21}
  else if(u.pathname==='/api/bottle-outbounds') data={items:[{id:50,document_no:'OUT-50',source_id:1,business_date:'2026-09-26',status:'POSTED',customer:'诸城市惠泽燃气有限公司',lines:[],total_quantity:897,created_by_name:'测试'}],total:1}
  else if(u.pathname==='/api/bottle-receipt/preview') {selection=JSON.parse(r.postData());data={company:'锦安特种设备检测',customer:'诸城市惠泽燃气有限公司',date_from:'2026-09-24',date_to:'2026-09-26',inbound_count:2,outbound_count:1,inbound_total:1804,outbound_total:897,
   spec_summary:[{spec_id:1,spec_name:'15kg',inbound:1600,outbound:802},{spec_id:2,spec_name:'50kg',inbound:204,outbound:95}],
   documents:[...[1,21].map(id=>({id,direction:'inbound',document_no:`IN-${id}`,business_date:id===1?'2026-09-24':'2026-09-26',customer:'诸城市惠泽燃气有限公司',handler:'经办人员',note:'',total:902,lines:[{spec_id:1,spec_name:'15kg',pending:800,temporary:0,scrap:0,good:0,bad:0,total:800},{spec_id:2,spec_name:'50kg',pending:102,temporary:0,scrap:0,good:0,bad:0,total:102}]})),
   {id:50,direction:'outbound',document_no:'OUT-50',business_date:'2026-09-26',customer:'诸城市惠泽燃气有限公司',handler:'经办人员',note:'客户带回',total:897,lines:[{spec_id:1,spec_name:'15kg',good:800,bad:2,pending:0,temporary:0,scrap:0,total:802},{spec_id:2,spec_name:'50kg',good:93,bad:2,pending:0,temporary:0,scrap:0,total:95}]}],notes_text:sample,text:sample,warnings:[]}}
  else {r.continue();return}
  r.respond({status:200,contentType:'application/json',body:JSON.stringify(data)})
 })
 const pause=()=>new Promise(r=>setTimeout(r,500))
 async function clickText(selector,text){for(const el of await page.$$(selector)){if((await el.evaluate(e=>e.textContent)).trim()===text){await el.click();return}}throw Error('Missing '+text)}
 await page.goto(origin+'/login');await page.evaluate(()=>localStorage.setItem('wms_token','receipt-test'))
 await page.goto(origin+'/bottle-inbounds',{waitUntil:'networkidle2'})
 await page.waitForSelector('#pane-inbound .el-loading-mask',{hidden:true});await page.click('#pane-inbound .el-table__body .el-checkbox');await pause()
 const secondPage=page.waitForResponse(response=>response.url().includes('/api/bottle-inbounds')&&response.url().includes('page=2'));await page.click('#pane-inbound .btn-next');await secondPage;await pause();await pause()
 await page.waitForSelector('#pane-inbound .el-loading-mask',{hidden:true});await page.click('#pane-inbound .el-table__body .el-checkbox');await pause()
 await clickText('[role=tab]','出库');await page.waitForSelector('#pane-outbound .el-table__body .el-checkbox',{visible:true});await page.waitForSelector('#pane-outbound .el-loading-mask',{hidden:true});await page.click('#pane-outbound .el-table__body .el-checkbox');await pause()
 assert.ok((await page.$eval('.receipt-tools',e=>e.innerText)).includes('已选入库 2 单、出库 1 单'))
 await clickText('.receipt-tools button','导出 Word');await page.waitForSelector('textarea[aria-label="收发记录正文"]',{visible:true})
 assert.deepEqual(selection,{inbound_ids:[1,21],outbound_ids:[50]})
 await page.$eval('textarea[aria-label="收发记录正文"]',e=>{e.value=e.value.replace('2026年9月26号出给','另外还有上次所少的阀共10个\n2026年9月26号出给');e.dispatchEvent(new Event('input',{bubbles:true}))})
 await page.screenshot({path:resolve('../artifacts/receipt-preview.png'),fullPage:true});assert.ok((await page.$eval('.receipt-preview',e=>e.innerText)).includes('50kg'))
 await page.waitForFunction(()=>document.querySelector('.el-dialog')?.getAnimations().length===0);await pause();await clickText('.el-dialog button','下载 Word')

 let bytes
 for(let i=0;i<40;i++){try{bytes=await readFile(resolve(destination,filename));break}catch{await pause()}}
 if(!bytes) console.log(await page.$eval('body',e=>e.innerText));assert.ok(bytes?.length>1000,'Word download missing');assert.equal(bytes.subarray(0,2).toString(),'PK')
 await clickText('.el-dialog button','关闭');await pause();await clickText('.receipt-tools button','清空勾选');await pause()
 assert.ok((await page.$eval('.receipt-tools',e=>e.innerText)).includes('已选入库 0 单、出库 0 单'))
 assert.deepEqual(errors,[])
 console.log('Receipt Word verified: cross-page inbound + outbound selection, editable preview, download and clear.')
}finally{await browser.close()}
