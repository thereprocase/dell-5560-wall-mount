// Uses an already installed Playwright; no dependency installation or user profile.
const path=require('path');
const fs=require('fs');
const modulePath=process.env.PLAYWRIGHT_MODULE||path.resolve(__dirname,'../../freecad/showcase/tooling/node_modules/playwright');
const {chromium}=require(modulePath);
const base=process.argv[2]||'http://127.0.0.1:8877/simulation/revh-transient/';
(async()=>{
  const out=path.resolve(__dirname,'runs/report_browser');fs.mkdirSync(out,{recursive:true});
  const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1050}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base,{waitUntil:'networkidle'});
    await page.locator('#updated').filter({hasText:'Evidence updated'}).waitFor();
    const links=await page.locator('a:visible').evaluateAll(a=>[...new Set(a.map(x=>x.href))]);
    let checked=0;
    for(const link of links){
      if(new URL(link).origin!==new URL(base).origin)continue;
      const response=await page.request.get(link);checked++;
      if(!response.ok())errors.push('Broken local link '+new URL(link).pathname+' '+response.status());
    }
    await page.screenshot({path:path.join(out,'desktop-final.png'),fullPage:true});
    const status=await page.locator('#run-status').innerText();
    await page.setViewportSize({width:390,height:844});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
    if(overflow)errors.push('Mobile horizontal overflow');
    await page.screenshot({path:path.join(out,'mobile-final.png'),fullPage:true});
    await page.screenshot({path:path.join(out,'mobile-viewport.png')});
    const report={page:new URL(base).hostname==='127.0.0.1'?'local report':base,errors,local_links_checked:checked,mobile_overflow:overflow,displayed_status:status};
    fs.writeFileSync(path.join(out,'review.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));if(errors.length)process.exitCode=1;
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
