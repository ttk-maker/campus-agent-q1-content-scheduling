/* Presentation checks. Run with a local test server and an isolated database. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const html=fs.readFileSync('web/index.html','utf8');
const q=html.includes('id="review-form"')?'q1':html.includes('id="plan-form"')?'q2':'q4';
const base=process.env.WEB_URL||`http://127.0.0.1:${{q1:8766,q2:8768,q4:8770}[q]}`;
const out=process.env.UI_OUTPUT||'examples/ui-refinement/presentation';fs.mkdirSync(out,{recursive:true});
const checks=[],errors=[],measurements=[];
function ok(name,value){checks.push({name,passed:!!value});assert.ok(value,name);}
function luminance(hex){const a=hex.replace('#','').match(/../g).map(c=>parseInt(c,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return a[0]*.2126+a[1]*.7152+a[2]*.0722;}
(async()=>{
 const browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL||'chrome',headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`)});
 await page.goto(base);await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('已连接'));
 await page.keyboard.press('Tab');ok('keyboard skip link visible',await page.locator('.skip-link').evaluate(e=>e===document.activeElement&&e.getBoundingClientRect().top>=0));await page.keyboard.press('Enter');
 await page.locator('#scenario').focus();ok('keyboard focus ring visible',await page.locator('#scenario').evaluate(e=>getComputedStyle(e).outlineStyle==='solid'&&parseFloat(getComputedStyle(e).outlineWidth)>=3));
 const tokens=await page.evaluate(()=>Object.fromEntries(['ink','muted','line','control','paper','surface','soft','accent','accent-hover','focus','success-bg','success-text','warn-bg','warn-text','error-bg','error-text'].map(k=>[k,getComputedStyle(document.documentElement).getPropertyValue('--'+k).trim()])));
 for(const [fg,bg,min] of [['ink','surface',4.5],['muted','surface',4.5],['muted','paper',4.5],['muted','soft',4.5],['surface','accent',4.5],['surface','accent-hover',4.5],['success-text','success-bg',4.5],['warn-text','warn-bg',4.5],['error-text','error-bg',4.5],['control','surface',3],['focus','surface',3],['focus','paper',3]]){
  const a=luminance(tokens[fg]),b=luminance(tokens[bg]);const ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);measurements.push({fg,bg,ratio,min});ok(`contrast ${fg}/${bg}`,ratio>=min);
 }
 async function inspect(label){
  const data=await page.evaluate(()=>{const els=[...document.querySelectorAll('body *')].filter(e=>e.getClientRects().length&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()));return {fonts:[...new Set(els.map(e=>getComputedStyle(e).fontSize))],overflow:document.documentElement.scrollWidth>innerWidth,shadows:[...document.querySelectorAll('.card,.panel,.result-card,.shot')].filter(e=>e.getClientRects().length&&getComputedStyle(e).boxShadow!=='none').length};});
  ok(label+' four font sizes',data.fonts.every(s=>['14px','16px','20px','32px'].includes(s)));ok(label+' no page overflow',!data.overflow);ok(label+' no decorative card shadows',data.shadows===0);
 }
 await inspect('empty');await page.screenshot({path:path.join(out,'empty-desktop.png'),fullPage:true});
 async function run(name){await page.selectOption('#scenario',name);await page.click(q==='q1'?'#submit':'#run');await page.waitForFunction(id=>!document.querySelector(id).disabled,q==='q1'?'#submit':'#run',{timeout:30000});}
 await run('normal');await inspect('success');await page.screenshot({path:path.join(out,'success-desktop.png'),fullPage:true});
 await run(q==='q1'?'conflict':q==='q2'?'over_budget':'too_short');await inspect('attention');await page.screenshot({path:path.join(out,'attention-desktop.png'),fullPage:true});
 if(q==='q1')ok('confirmation remains explicit',await page.locator('.confirm-button').count()>0);
 else ok('incomplete state visible',(await page.textContent('#state'))===(q==='q2'?'无可行方案':'无法满足'));
 for(const width of [390,320]){await page.setViewportSize({width,height:844});await inspect('mobile '+width);await page.screenshot({path:path.join(out,`attention-${width}.png`),fullPage:true});}
 await page.setViewportSize({width:720,height:900});await page.evaluate(()=>{for(const [k,v] of [['small',28],['body',32],['section',40],['title',64]])document.documentElement.style.setProperty('--font-'+k,v+'px');});
 ok('200 percent text reflows without page overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(out,'text-200-percent.png'),fullPage:true});
 await page.goto(base+'/manual.html');await page.setViewportSize({width:390,height:844});await inspect('manual');await page.screenshot({path:path.join(out,'manual-mobile.png'),fullPage:true});
 ok('no browser or network errors',errors.length===0);
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({timestamp:new Date().toISOString(),project:q,checks,measurements,errors,passed:true},null,2));console.log(q,checks.length,'presentation checks passed');
 }finally{await browser.close()}
})().catch(e=>{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({passed:false,checks,errors,error:e.message,measurements},null,2));console.error(e);process.exit(1)});
