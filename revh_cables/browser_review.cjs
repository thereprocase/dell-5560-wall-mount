const {chromium}=require(process.env.PLAYWRIGHT_MODULE || '../freecad/showcase/tooling/node_modules/playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const base=process.argv[2]||'http://127.0.0.1:8894/';
const uiOnly=process.argv.includes('--ui-only');
const out=path.join(__dirname,'browser');fs.mkdirSync(out,{recursive:true});
const check=(value,message)=>{if(!value)throw Error(message);};
const smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x);};
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,args:['--enable-webgl','--ignore-gpu-blocklist']});
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+new URL(r.url()).pathname);});
 await page.goto(new URL('revh-cables.html',base).href,{waitUntil:'networkidle'});
 await page.waitForFunction(()=>window.cableReview?.().ready);
 const state=()=>page.evaluate(()=>window.cableReview());
 const initial=await state();
 check(initial.visible===14,'Expected fourteen base parts with H-R1 hidden');
 check(JSON.stringify(initial.replacementIds.sort())===JSON.stringify(['05_left_fan_retainer','06_right_fan_retainer','09_left_fan_tray','10_right_fan_tray']),'Wrong replacement files');
 const move=async n=>{await page.locator('#cable-travel').fill(String(n));await page.locator('#cable-travel').dispatchEvent('input');return state();};
 const poses={};
 for(const n of [0,15,25,50,75,100]){
  const s=await move(n);poses[n]=s.positions;
  check(s.visible===14,'Part visibility changed during service');
  check(JSON.stringify(s.wirePositions)===JSON.stringify(initial.wirePositions),'Reference wires moved with covers');
  for(const [key,pos] of Object.entries(s.positions)){
   const distance=key.includes('push_pin')?24*smooth(n/15):key.includes('fan_retainer')?35*smooth((n-25)/75):0;
   const up=key.includes('push_pin')?20*smooth((n-15)/10):0;
   check(pos[0]===0&&Math.abs(pos[1]-(distance-up)/Math.SQRT2)<1e-8&&Math.abs(pos[2]-(distance+up)/Math.SQRT2)<1e-8,'Incorrect service motion: '+key);
  }
 }
 await page.locator('#model').screenshot({path:path.join(out,'desktop-covers-removed.png')});
 for(const n of [75,50,25,15,0])check(JSON.stringify((await move(n)).positions)===JSON.stringify(poses[n]),'Reinstallation differs from removal');
 await page.locator('#model').screenshot({path:path.join(out,'desktop-installed.png')});
 await page.locator('#cable-right').check();check((await state()).visible===7,'Right side should contain seven base parts');
 check((await state()).visibleWireCount===1,'Right-side view should have one reference cable');
 await page.locator('#cable-retainers').check();check((await state()).visible===9,'Optional H-R1 should add two right-side parts');
 await page.locator('#cable-detail').click();await move(100);
 await page.locator('#model').screenshot({path:path.join(out,'cable-exit-detail.png')});
 await page.locator('#cable-reset').click();check((await state()).phase==='Installed'&&(await state()).visible===18,'Reset should install all currently selected parts');
 let release;
 if(!uiOnly){
  const response=await page.request.get(new URL('assets/revh-cables-release.json',base).href);check(response.ok(),'Release report missing');
  release=await response.json();check(release.revision==='H-C1 prototype'&&release.unchanged_installed_parts===14,'Release scope mismatch');
  const download=await page.request.get(new URL('downloads/'+release.download.file,base).href);check(download.ok(),'Download missing');
  const bytes=await download.body();check(bytes.length===release.download.bytes,'Download size mismatch');
  check(crypto.createHash('sha256').update(bytes).digest('hex')===release.download.sha256,'Download checksum mismatch');
  check((await page.locator('#cable-estimates').innerText()).includes(release.replacement_set.estimated_filament_g.toFixed(2)),'Guide estimate is stale');
 }
 await page.setViewportSize({width:390,height:844});await page.reload({waitUntil:'networkidle'});await page.waitForFunction(()=>window.cableReview?.().ready);
 check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Mobile horizontal overflow');
 await page.locator('#model').screenshot({path:path.join(out,'mobile-model.png')});
 const missing=await page.locator('img').evaluateAll(xs=>xs.filter(x=>!x.complete||!x.naturalWidth).map(x=>x.getAttribute('src')));check(!missing.length,'Broken guide images');
 await page.goto(new URL('index.html',base).href,{waitUntil:'networkidle'});
 check(await page.locator('#revh-cables a[href="revh-cables.html"]').count()===1,'Main page cable entry missing');
 await page.waitForFunction(()=>window.minimalistReady&&window.showcaseReady);
 check((await page.locator('#m1-sequence-phase').innerText())==='Installed','Existing M1 sequence affected');
 if(process.env.CABLE_OFFLINE_GUIDE){
  await page.goto('file:///'+process.env.CABLE_OFFLINE_GUIDE.replaceAll('\\','/'),{waitUntil:'load'});
  check(!await page.locator('img').evaluateAll(xs=>xs.some(x=>!x.complete||!x.naturalWidth)),'Offline guide images missing');
  check(await page.locator('script').count()===0,'Offline guide should not require script fetches');
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Offline guide mobile overflow');
  await page.screenshot({path:path.join(out,'offline-guide.png')});
 }
 const report={pass:!errors.length,uiOnly,base:new URL(base).hostname==='127.0.0.1'?'local preview':base,errors,
  changedParts:initial.replacementIds,basePartCount:14,withOptionalRetainers:18,rightBasePartCount:7,
  sampledServicePositions:[0,15,25,50,75,100],onlyCoversAndPinsMove:true,pinsParkAboveCoverPath:true,wireAndTrayPositionsFixed:true,reversePosesIdentical:true,
  downloadChecksumVerified:!uiOnly,mobileOverflow:false,guideImageFailures:missing,existingViewersLoaded:true,
  offlineGuideVerified:Boolean(process.env.CABLE_OFFLINE_GUIDE),releaseNativeSha256:release?.native_sha256};
 const reportName=uiOnly?'review-ui.json':new URL(base).hostname==='127.0.0.1'?'review.json':'review-live.json';
 fs.writeFileSync(path.join(out,reportName),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report));await browser.close();check(!errors.length,errors.join('; '));
})().catch(e=>{console.error(e);process.exitCode=1;});
