/* Report-only numeric and offline browser verification. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL, fileURLToPath} = require('node:url');
const root = path.resolve(__dirname, '..');
const {response, budgets} = require(path.join(root, 'docs/assets/pipeline-model/reader.js'));
const near = (a,b,tol=1e-10) => assert.ok(Math.abs(a-b)<tol,`${a} != ${b}`);
near(.4+.25*(.03/.05),.55);
near((.55-.4)*.05,.0075);
near((.48-.4)*.05,.004);
near(1-response(.25,10).points[3].q,.253125);
near(response(.25,10).tau,3*response(.25,30).tau);
near(response(.25,10).tau,.3476059496782207);
near(.1*.084,.0084);
near(3*640*480*3*30/1e6,82.944);
near(3*640*480*2*30/1e6,55.296);
near(256*1024*1024/(82.944e6),3.2363456790123455);
near((16-1)/30,.5);
near(8/30-.18-.04,.04666666666666666);
assert.deepEqual(budgets(100,80,500,30).map(r=>r.ok),[false,true,true,true]);
assert.equal(budgets(80,80,500,30)[0].ok,false); // Strict future condition.
assert.ok(budgets(100,140,500,30).every(r=>r.ok));
assert.deepEqual(budgets(300,310,340,100).map(r=>r.ok),[true,true,true,true]);
assert.deepEqual(budgets(400,80,200,100).map(r=>r.ok),[false,false,false,false]);

async function main(){
  const {chromium} = require('playwright');
  const options = {headless:true};
  if(process.env.REPORT_CHROME) options.executablePath=process.env.REPORT_CHROME;
  const browser = await chromium.launch(options);
  const out=path.join(root,'artifacts/validation/016-pipeline-model');
  fs.mkdirSync(out,{recursive:true});
  const errors=[], failed=[];
  const result={math_invariants:'passed',views:[],errors,failed};
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('requestfailed',r=>failed.push(r.url()));
  try{
    await page.goto(pathToFileURL(path.join(root,'docs/pipeline-model.html')).href);
    await page.locator('#ik-chart svg').waitFor();
    result.mathml_count=await page.locator('math').count();
    assert.ok(result.mathml_count>=170);
    assert.ok(!(await page.locator('math').allTextContents()).some(s=>s.includes('\\')),'unconverted formula');
    assert.equal(await page.locator('.lesson:visible').count(),1);
    assert.equal(await page.locator('#lesson-progress').innerText(),'1 / 8');
    for(let i=0;i<8;i++){
      await page.locator('#lesson-select').selectOption(String(i));
      assert.equal(await page.locator('.lesson:visible').getAttribute('id'),`lesson-${i}`);
      const summary=page.locator(`#lesson-${i} summary`);
      await summary.click();
      assert.ok(await page.locator(`#lesson-${i} details`).getAttribute('open')!==null);
      assert.equal(await page.locator(`#lesson-${i} details strong`).last().innerText(),'设计规则：');
    }
    assert.ok(await page.locator('#next').isDisabled());
    await page.locator('#previous').click();
    assert.equal(await page.locator('#lesson-progress').innerText(),'7 / 8');
    await page.locator('#lesson-select').selectOption('0');
    await page.locator('#next').click();
    assert.equal(await page.locator('#lesson-progress').innerText(),'2 / 8');
    await page.locator('#lesson-select').selectOption('0');
    for(const width of [1440,768,390,320]){
      await page.setViewportSize({width,height:1000});
      await page.evaluate(()=>scrollTo(0,0));
      await page.waitForTimeout(100);
      const measure=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));
      assert.ok(measure.scroll<=width+1,JSON.stringify(measure));
      result.views.push(measure);
      await page.screenshot({path:path.join(out,`reader-${width}.png`)});
      await page.locator('#ik-experiment').screenshot({path:path.join(out,`ik-${width}.png`)});
      // Every lesson must fit, not only the initial lesson.
      for(let i=0;i<8;i++){
        await page.locator('#lesson-select').selectOption(String(i));
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      }
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('#lesson-select').selectOption('0');
    await page.locator('#ik-hz').fill('30');await page.locator('#ik-hz').dispatchEvent('input');
    assert.match(await page.locator('#ik-status').innerText(),/0.116 s/);
    await page.locator('#ik-alpha').fill('0.5');await page.locator('#ik-alpha').dispatchEvent('input');
    assert.match(await page.locator('#ik-status').innerText(),/0.048 s/);
    assert.match(await page.locator('#budget-status').innerText(),/1 项/);
    await page.locator('#lead').fill('140');await page.locator('#lead').dispatchEvent('input');
    assert.match(await page.locator('#budget-status').innerText(),/四个时间预算满足/);
    await page.locator('#latency').fill('500');await page.locator('#latency').dispatchEvent('input');
    assert.match(await page.locator('#budget-status').innerText(),/4 项/);
    await page.locator('#budget-experiment').screenshot({path:path.join(out,'budget-failure.png')});
    await page.locator('#model-report .math-display').nth(4).screenshot({path:path.join(out,'formula.png')});
    await page.locator('#model-report .math-display').nth(9).screenshot({path:path.join(out,'ik-equation.png')});
    await page.locator('#model-report .math-display').nth(25).screenshot({path:path.join(out,'flow-equation.png')});
    await page.locator('.system-map').screenshot({path:path.join(out,'system-map.png')});
    await page.locator('#model-report').screenshot({path:path.join(out,'full-model.png')});
    const links=await page.locator('a[href],link[href],script[src]').evaluateAll(ns=>ns.map(n=>n.href||n.src));
    for(const url of links){
      if(!url.startsWith('file:')) continue;
      assert.ok(fs.existsSync(fileURLToPath(url)),`missing local resource ${url}`);
    }
    const anchors=await page.locator('a[href^="#"]').evaluateAll(ns=>ns.map(n=>n.getAttribute('href').slice(1)));
    for(const id of anchors) assert.ok(await page.evaluate(id=>Boolean(document.getElementById(decodeURIComponent(id))),id),`missing anchor ${id}`);
    const ids=await page.locator('[id]').evaluateAll(ns=>ns.map(n=>n.id));
    assert.equal(new Set(ids).size,ids.length,'duplicate IDs');
    await page.emulateMedia({media:'print'});
    assert.equal(await page.locator('.lesson:visible').count(),8);
    await page.emulateMedia({media:'screen'});
    const fallback=await browser.newPage({javaScriptEnabled:false});
    await fallback.goto(pathToFileURL(path.join(root,'docs/pipeline-model.html')).href);
    assert.equal(await fallback.locator('.lesson:visible').count(),8);
    await fallback.close();
    assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);
    result.interactions='8 lessons, answers, prev/next, IK, budget pass/fail, print, no-JS: passed';
    result.local_links='passed';
    fs.writeFileSync(path.join(out,'qa.json'),JSON.stringify(result,null,2));
    process.stdout.write(JSON.stringify(result,null,2)+'\n');
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
