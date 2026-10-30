const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  await page.goto(process.env.APP_URL||'http://localhost:8503');
  await page.getByRole('radio',{name:'Find Jobs',exact:true}).locator('xpath=ancestor::label').click();
  const start=Date.now();
  await page.getByRole('button',{name:'Search',exact:true}).click();
  await page.getByText('Total jobs',{exact:true}).waitFor({timeout:8000});
  await page.locator('.job-role').first().waitFor({timeout:4000});
  assert.ok(Date.now()-start<8000,'first result before slow source completes');
  assert.equal(await page.locator('.job-role').count(),1);
  await page.getByRole('radio',{name:'Job Tracker',exact:true}).locator('xpath=ancestor::label').click();
  await page.getByRole('heading',{name:'Job Tracker',exact:true}).waitFor({timeout:4000});
  await page.getByRole('button',{name:'Stop search',exact:true}).click();
  await page.getByText('Search stopped; completed results retained',{exact:true}).waitFor({timeout:5000});
  await page.getByRole('radio',{name:'Find Jobs',exact:true}).locator('xpath=ancestor::label').click();
  await page.locator('.job-role').first().waitFor({timeout:4000});
  assert.equal(await page.locator('.job-role').count(),1,'completed result retained after cancellation');
  await page.getByRole('button',{name:'Search',exact:true}).click();
  await page.getByRole('button',{name:'Stop search',exact:true}).waitFor();
  await page.getByRole('button',{name:'Stop search',exact:true}).waitFor({state:'hidden',timeout:25000});
  await page.locator('.job-role').nth(1).waitFor({timeout:4000});
  assert.equal(await page.locator('.job-role').count(),2,'second search completes independently');
  assert.equal(await page.locator('[data-testid="stException"]').count(),0);
  console.log('PASS partial results, navigation during search, cancellation, retained results, new search completion');
 }finally{await browser.close();}
})().catch(e=>{
  console.error(e);
  const summary=String(e&&e.message||e).split('\n').slice(0,6).join(' | ').replace(/[\r%]/g,'');
  // Written synchronously, so process.exit() cannot drop it.
  require('node:fs').writeSync(1,'\n::error title=browser_search_workflow::'+summary+'\n');
  process.exit(1);
});
