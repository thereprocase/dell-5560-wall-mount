const {chromium}=require(process.argv[3] || 'playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const base=process.argv[2] || 'http://127.0.0.1:8899/';
 const options={headless:true};
 if(process.platform==='win32')options.executablePath='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
 const browser=await chromium.launch(options),page=await browser.newPage();
 const errors=[],badResponses=[],widths=[280,390,768,1440,2560,3840];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(r.status()>=400&&r.url().startsWith(base))badResponses.push({status:r.status(),url:r.url()})});
 const output=path.join(__dirname,'browser');fs.mkdirSync(output,{recursive:true});
 await page.goto(new URL('revh-duct-d4.html',base).href,{waitUntil:'networkidle'});
 for(const width of widths){
  await page.setViewportSize({width,height:1000});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Page overflow at '+width);
  const cards=await page.locator('#print .gl-featured article').count();if(cards!==2)throw Error('Expected two duct projects');
  if(!await page.locator('img').evaluateAll(nodes=>nodes.every(n=>n.complete&&n.naturalWidth>0)))throw Error('Image failed');
  if(width===390||width===1440)await page.screenshot({path:path.join(output,'guide-'+width+'.png'),fullPage:true});
 }
 if(errors.length||badResponses.length)throw Error(JSON.stringify({errors,badResponses}));
 fs.writeFileSync(path.join(output,'review.json'),JSON.stringify({passed:true,widths_checked:widths,no_horizontal_overflow:true,project_cards:2,images_loaded:true,page_errors:errors,local_http_errors:badResponses},null,2)+'\n');
 await browser.close();
})();
