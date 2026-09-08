const {chromium}=require(process.env.PLAYWRIGHT_MODULE || '../freecad/showcase/tooling/node_modules/playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const base=process.argv[2]||'http://127.0.0.1:8893/';
const out=path.join(__dirname,'browser');fs.mkdirSync(out,{recursive:true});
function assert(value,message){if(!value)throw Error(message);}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--enable-webgl','--ignore-gpu-blocklist']});
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+new URL(r.url()).pathname);});
 await page.goto(new URL('revh-retainers.html',base).href,{waitUntil:'networkidle'});
 await page.waitForFunction(()=>window.retainerReview?.().ready);
 const state=()=>page.evaluate(()=>window.retainerReview());
 const move=async n=>{await page.locator('#retainer-travel').fill(String(n));await page.locator('#retainer-travel').dispatchEvent('input');return state();};
 const poses={};
 for(const n of [0,20,40,70,100]){
  const s=await move(n);poses[n]=s.positions;assert(s.visible===18,'Expected all eighteen parts');
  for(const [key,pos] of Object.entries(s.positions)){
   if(Number(key.slice(0,2))<15)assert(pos.every(v=>v===0),'Original H part moved during retainer service');
   if(key.includes('keeper'))assert(pos[0]===0&&pos[1]===0&&Math.abs(pos[2]+(n>=40?16:n===20?8:0))<1e-9,'Keeper extraction axis or phase');
   if(key.includes('side_retainer'))assert(pos[1]===0&&pos[2]===0&&Math.abs(Math.abs(pos[0])-(n<=40?0:n===70?15:30))<1e-9,'Bar extraction phase');
  }
 }
 await page.locator('#model').screenshot({path:path.join(out,'desktop-removed.png')});
 for(const n of [70,40,20,0])assert(JSON.stringify((await move(n)).positions)===JSON.stringify(poses[n]),'Reinstallation differs from removal');
 await page.locator('#model').screenshot({path:path.join(out,'desktop-installed.png')});
 await page.locator('#retainer-right').check();assert((await state()).visible===9,'Right side should show nine parts');
 await page.locator('#retainer-ghost').check();await page.locator('#retainer-detail').click();
 await page.locator('#model').screenshot({path:path.join(out,'lower-catch.png')});
 await move(100);await page.locator('#retainer-reset').click();assert((await state()).phase==='Installed','Reset should reinstall retainers');
 const response=await page.request.get(new URL('assets/revh-retainers-release.json',base).href);assert(response.ok(),'Missing release report');
 const release=await response.json();assert(release.revision==='H-R1 prototype'&&release.unchanged_original_parts===14&&release.added_parts===4,'Release scope mismatch');
 const download=await page.request.get(new URL('downloads/'+release.download.file,base).href);assert(download.ok(),'Download missing');
 const bytes=await download.body();assert(bytes.length===release.download.bytes,'Archive size mismatch');assert(crypto.createHash('sha256').update(bytes).digest('hex')===release.download.sha256,'Archive checksum mismatch');
 await page.setViewportSize({width:390,height:844});await page.reload({waitUntil:'networkidle'});await page.waitForFunction(()=>window.retainerReview?.().ready);
 assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Mobile horizontal overflow');
 await page.locator('#model').screenshot({path:path.join(out,'mobile-model.png')});
 const images=await page.locator('img').evaluateAll(xs=>xs.filter(x=>!x.complete||!x.naturalWidth).map(x=>x.getAttribute('src')));assert(!images.length,'Broken guide images');
 await page.goto(new URL('index.html',base).href,{waitUntil:'networkidle'});
 assert(await page.locator('#revh-retainers a[href="revh-retainers.html"]').count()===1,'Main page entry missing');
 await page.waitForFunction(()=>window.minimalistReady&&window.showcaseReady);
 assert((await page.locator('#m1-sequence-phase').innerText())==='Installed','Minimalist sequence changed');
 if(process.env.RETAINER_OFFLINE_GUIDE){
  await page.goto('file:///'+process.env.RETAINER_OFFLINE_GUIDE.replaceAll('\\','/'),{waitUntil:'load'});
  const missing=await page.locator('img').evaluateAll(xs=>xs.filter(x=>!x.complete||!x.naturalWidth).map(x=>x.getAttribute('src')));
  assert(!missing.length,'Offline guide has missing images');
  assert(await page.locator('script').count()===0,'Offline guide should not depend on module fetches');
  assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Offline guide mobile overflow');
  await page.screenshot({path:path.join(out,'offline-guide.png')});
 }
 const report={offlineGuideVerified:Boolean(process.env.RETAINER_OFFLINE_GUIDE),base:new URL(base).hostname==='127.0.0.1'?'local preview':base,pass:errors.length===0,errors,parts:18,rightSideParts:9,phaseCheckpoints:[0,20,40,70,100],reversePosesIdentical:true,originalHPartsStationary:true,downloadSha256Verified:true,mobileOverflow:false,guideImageFailures:images,originalViewersLoaded:true,releaseNativeSha256:release.native_sha256};
 fs.writeFileSync(path.join(out,'review.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
 await browser.close();assert(!errors.length,errors.join('; '));
})().catch(e=>{console.error(e);process.exitCode=1;});
