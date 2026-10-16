// Offline browser checks against the actual Streamlit server, or a supplied deployment URL.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage();
  const output=process.env.ARTIFACT_DIR||'artifacts';
  fs.mkdirSync(output,{recursive:true});
  const url=process.env.APP_URL||'http://127.0.0.1:8501';
  const version=process.env.EXPECTED_VERSION||'3.2.0';
  await page.goto(url);
  await page.getByText('Version '+version,{exact:true}).waitFor({timeout:60000});
  for(const size of [{width:1440,height:1000},{width:390,height:844}]){
    await page.setViewportSize(size);
    for(const name of ['Dashboard','Find Jobs','Job Tracker','My Resume','Career Analysis','Career Matches']){
      await page.getByRole('radio',{name,exact:true}).locator('xpath=ancestor::label').click();
      await page.getByRole('heading',{name:name==='My Resume'?'Resume':name,exact:true}).waitFor({timeout:15000});
      await page.waitForTimeout(350);
      assert.equal(await page.getByText(/No secrets found/).count(),0,'Optional secrets should not render errors');
      assert.equal(await page.locator('[data-testid="stException"]').count(),0,name+' exception');
      const layout=await page.evaluate(()=>{
        const main=document.querySelector('[data-testid="stMainBlockContainer"]');
        const rect=main.getBoundingClientRect();
        return {left:rect.left,right:innerWidth-rect.right,width:document.documentElement.scrollWidth,
          viewport:innerWidth,color:getComputedStyle(document.querySelector('[data-testid="stAppViewContainer"]')).backgroundColor};
      });
      assert.equal(layout.color,'rgb(39, 52, 47)',name+' forest green background');
      assert.ok(Math.abs(layout.left-layout.right)<22,name+' symmetric outer margins');
      assert.ok(layout.width<=layout.viewport+2,name+' horizontal overflow');
    }
    await page.getByRole('radio',{name:'Dashboard',exact:true}).locator('xpath=ancestor::label').click();
    await page.getByRole('heading',{name:'Dashboard',exact:true}).waitFor({timeout:15000});
    await page.waitForTimeout(350);
    await page.evaluate(()=>document.querySelector('[data-testid="stMain"]').scrollTo(0,0));
    await page.screenshot({path:output+'/dashboard-'+size.width+'.png',fullPage:true});
  }
  await browser.close();
  console.log('PASS six pages, desktop/mobile, forest-green background, symmetric margins, no horizontal overflow');
})().catch(error=>{console.error(error);process.exit(1)});
