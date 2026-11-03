// Offline math invariants and browser QA. Run with bundled Node + NODE_PATH.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '..');
const m = require(path.join(root, 'docs/assets/signal-timing/report.js'));
function near(a,b,tol=1e-10){assert.ok(Math.abs(a-b)<tol,`${a} != ${b}`);}
near(m.aliasFrequency(18,30),-12);
for(let n=0;n<=30;n++) near(Math.sin(2*Math.PI*18*n/30),Math.sin(2*Math.PI*m.aliasFrequency(18,30)*n/30));
near(m.linearAt([[0,0],[1,2]],.25),.5);
near(m.bufferBudget(16,8,30,180,40).slack,8/30-.22);
assert.ok(m.bufferBudget(16,14,30,180,40).slack<0);
const a=m.simulatePlant({recordHz:10}),b=m.simulatePlant({recordHz:60});
assert.deepEqual(a.truth,b.truth); // Saving cadence cannot change this isolated plant.
assert.ok(b.recordingRms<a.recordingRms);
const g=m.simulatePlant({recordHz:60,gapMs:200});
assert.deepEqual(g.truth,b.truth);
assert.ok(g.maxGapMs>200 && g.recordingRms>b.recordingRms);
const evidence=JSON.parse(fs.readFileSync(path.join(root,'docs/assets/signal-timing/evidence.json')));
for(const s of ['left','right']){
  const st=evidence.stats[s];assert.equal(st.commands.count,179);assert.equal(st.feedback.count,508);
  assert.equal(st.error_samples,505);
  assert.ok(st.commands.span_hz>59 && st.commands.span_hz<61);
}
async function main(){
  const {chromium}=require('playwright');
  const options={headless:true};
  if(process.env.REPORT_CHROME)options.executablePath=process.env.REPORT_CHROME;
  const browser=await chromium.launch(options);
  const page=await browser.newPage();
  const errors=[], failed=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('requestfailed',r=>failed.push(r.url()));
  const out=path.join(root,'artifacts/validation/015-signal-report');
  fs.mkdirSync(out,{recursive:true});
  const result={math_invariants:'passed',views:[],errors,failed};
  try{
    await page.goto(pathToFileURL(path.join(root,'docs/signal-timing-report.html')).href);
    await page.locator('#real-chart svg').waitFor();
    assert.equal(await page.locator('math').count(),66);
    assert.ok(!(await page.locator('math').allTextContents()).some(s=>s.includes('\\')),
      'MathML must not display unconverted LaTeX commands');
    for(const width of [1440,768,390,320]){
      await page.setViewportSize({width,height:1000});
      await page.waitForTimeout(200);
      const size=await page.evaluate(()=>({w:innerWidth,scroll:document.documentElement.scrollWidth}));
      assert.ok(size.scroll<=size.w+1,JSON.stringify(size));
      await page.screenshot({path:path.join(out,`report-${width}.png`),fullPage:false});
      result.views.push({...size,svg:await page.locator('.chart svg').count()});
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('#sample-rate').fill('60');await page.locator('#sample-rate').dispatchEvent('input');
    assert.match(await page.locator('#sampling-status').innerText(),/^满足/);
    await page.locator('#record-rate').fill('5');await page.locator('#record-rate').dispatchEvent('input');
    const before=await page.locator('#plant-status').innerText();
    await page.locator('#record-rate').fill('120');await page.locator('#record-rate').dispatchEvent('input');
    assert.notEqual(before,await page.locator('#plant-status').innerText());
    await page.locator('#chunk-k').fill('14');await page.locator('#chunk-k').dispatchEvent('input');
    assert.match(await page.locator('#chunk-status').innerText(),/缺口/);
    await page.locator('#real-arm').selectOption('right');await page.locator('#real-joint').selectOption('6');
    assert.match(await page.locator('#real-status').innerText(),/第 6 关节/);
    await page.locator('#experiment-d').screenshot({path:path.join(out,'real-evidence.png')});
    await page.locator('.math-display').nth(2).screenshot({path:path.join(out,'ik-equation.png')});
    await page.locator('.math-display').nth(10).screenshot({path:path.join(out,'flow-equation.png')});
    await page.locator('#report').screenshot({path:path.join(out,'report-body.png')});
    result.interactions='sampling, recording, queue deficit, real arm/joint: passed';
    const localLinks=await page.locator('a[href],img[src],link[href],script[src]').evaluateAll(nodes=>nodes.map(n=>n.href||n.src).filter(Boolean));
    const missing=[];
    for(const u of localLinks){
      if(u.startsWith('file:')){
        const {fileURLToPath}=require('node:url');const url=new URL(u);url.hash='';
        if(!fs.existsSync(fileURLToPath(url)))missing.push(u);
      }
    }
    assert.deepEqual(missing,[]);
    assert.deepEqual(errors,[]);assert.deepEqual(failed,[]);
    result.links='all local resources exist';
    fs.writeFileSync(path.join(out,'qa.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1});
