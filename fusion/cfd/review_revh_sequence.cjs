// Browser acceptance for the hourly page, actual MP4 decoding and mobile layout.
const {chromium}=require('F:/Code/dell-5560-wall-mount-minimalist/freecad/showcase/tooling/node_modules/playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const base=process.argv[2]||'http://127.0.0.1:8881/simulation/revh-transient/sequence/';
const output=process.argv[3]||'fusion/cfd/runs/revh_fourhour_08/browser-initial';
(async()=>{
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1050}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const response=await page.goto(base,{waitUntil:'networkidle'});
  if(!response.ok())errors.push('Page HTTP '+response.status());
  const links=await page.locator('a[href]').evaluateAll(els=>[...new Set(els.map(a=>a.href))]);
  const badLinks=[];
  for(const link of links){
   if(!link.startsWith(new URL(base).origin))continue;
   const r=await page.request.head(link);
   if(!r.ok())badLinks.push({url:link,status:r.status()});
  }
  if(badLinks.length)errors.push('Broken internal links');
  const video=page.locator('#flow-video');let meta=null;
  if(await video.count()){
   // Python's local file server does not implement byte ranges. Decode its
   // complete file as a blob locally; public checks use the real HTTPS source.
   if(new URL(base).hostname==='127.0.0.1')await video.evaluate(async v=>{v.src=URL.createObjectURL(await (await fetch(v.querySelector('source').src)).blob());v.load();});
   await video.scrollIntoViewIfNeeded();await video.evaluate(v=>v.play());
   await page.waitForFunction(()=>document.querySelector('video').currentTime>.25);
   await video.evaluate(v=>v.pause());
   const source=await video.locator('source').getAttribute('src');
   const report=await (await page.request.get(new URL('progress.json',new URL(source,base)).href)).json();
   meta=await video.evaluate(v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,controls:v.controls,autoplay:v.autoplay,loop:v.loop,error:v.error}));
   const hashes=[],seekTimes=[];
   for(const fraction of [.15,.50,.85]){
    const index=Math.floor((report.source_frames-1)*fraction);
    const t=report.source_frame_start_s[index]+.01;
    await video.evaluate((v,t)=>new Promise(resolve=>{v.addEventListener('seeked',()=>requestAnimationFrame(()=>requestAnimationFrame(resolve)),{once:true});v.currentTime=t;}),t);
    seekTimes.push(await video.evaluate(v=>v.currentTime));
    const frame=await video.evaluate(v=>{const c=document.createElement('canvas');c.width=900;c.height=750;c.getContext('2d').drawImage(v,600,170,1100,780,0,0,900,750);return c.toDataURL();});
    hashes.push(crypto.createHash('sha256').update(frame).digest('hex'));
   }
   meta={...meta,playback_advanced:true,seek_times:seekTimes,distinct_decoded_flow_regions:new Set(hashes).size,source_frames:report.source_frames};
   if(new Set(hashes).size!==3)errors.push('Flow regions did not decode as three distinct states');
   if(Math.abs(meta.duration-report.video_duration_s)>.05||meta.width!==1800||meta.height!==1100||!meta.controls||meta.autoplay||meta.loop||meta.error)errors.push('Video presentation check failed');
   await video.screenshot({path:path.join(output,'video-desktop.png')});
  }
  await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  if(await video.count())await video.scrollIntoViewIfNeeded();
  const mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  if(mobileOverflow)errors.push('Mobile page overflow');
  const result={checked_utc:new Date().toISOString(),url:base,video:meta,internal_links_checked:links.length,badLinks,mobile_overflow:mobileOverflow,errors};
  fs.writeFileSync(path.join(output,'review.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
  if(errors.length)process.exitCode=1;
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
