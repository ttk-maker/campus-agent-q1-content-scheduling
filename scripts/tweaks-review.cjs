/* Live-control regression: use an isolated database, never the user's workbench. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const q=fs.readFileSync('web/index.html','utf8').match(/data-project="(q\d)"/)[1];
const base=process.env.WEB_URL||`http://127.0.0.1:${{q1:8766,q2:8768,q4:8770}[q]}`;
const out=process.env.TWEAKS_OUTPUT||'examples/tweaks/interaction';fs.mkdirSync(out,{recursive:true});
const checks=[],errors=[],contrast=[];let browser;
function ok(name,pass){checks.push({name,passed:!!pass});assert.ok(pass,name);}
function luminance(hex){const a=hex.replace('#','').match(/../g).map(c=>parseInt(c,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return a[0]*.2126+a[1]*.7152+a[2]*.0722;}
function hash(b){return crypto.createHash('sha256').update(b).digest('hex');}
(async()=>{
 const proof=JSON.parse(fs.readFileSync('examples/tweaks/baseline-integrity.json'));
 ok('backend source hashes unchanged',Object.entries(proof.src_lf_sha256).every(([p,h])=>hash(fs.readFileSync(p,'utf8').replace(/\r\n/g,'\n'))===h));
 ok('original business JavaScript prefix unchanged',hash(Buffer.from(fs.readFileSync('web/app.js','utf8').replace(/\r\n/g,'\n')).subarray(0,proof.app_prefix_lf_bytes))===proof.app_prefix_lf_sha256);
 browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL||'chrome',headless:true});
 const p=await browser.newPage({viewport:{width:1440,height:1000}});
 p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 p.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url())});
 await p.goto(base);await p.waitForFunction(()=>document.querySelector('#notice').textContent.includes('已连接'));
 const target=q==='q4'?'target':'budget',run=q==='q1'?'submit':'run';
 let posts=[];p.on('request',r=>{if(r.method()==='POST')posts.push({url:r.url(),body:r.postDataJSON()});});
 const snapshot=()=>p.evaluate(()=>[...document.querySelectorAll('.workspace input:not([type=range]),.workspace select,.workspace textarea')].map(e=>[e.id,e.value,e.checked]));
 const original=await snapshot();
 const choose=async(name,value)=>p.locator(`[data-setting="${name}"][data-value="${value}"]`).click();
 await p.locator('#open-display').click();
 ok('dialog opens with focus inside',await p.locator('#display-settings').evaluate(d=>d.open&&d.contains(document.activeElement)));
 for(let i=0;i<19;i++)await p.keyboard.press('Tab');
 ok('modal keyboard focus stays inside',await p.locator('#display-settings').evaluate(d=>d.contains(document.activeElement)));
 for(const theme of ['light','dark']){
  await choose('theme',theme);
  for(const accent of ['green','blue','clay','plum']){
   await choose('accent',accent);
   const tokens=await p.evaluate(()=>Object.fromEntries(['ink','muted','control','paper','surface','soft','accent','accent-hover','accent-soft','focus','button-text','success-bg','success-text','warn-bg','warn-text','error-bg','error-text'].map(k=>[k,getComputedStyle(document.documentElement).getPropertyValue('--'+k).trim()])));
   const pairs=[['ink','surface',4.5],['muted','paper',4.5],['muted','soft',4.5],['accent','accent-soft',4.5],['accent','surface',4.5],['button-text','accent',4.5],['button-text','accent-hover',4.5],['success-text','success-bg',4.5],['warn-text','warn-bg',4.5],['error-text','error-bg',4.5],['control','surface',3],['focus','surface',3]];
   const ratios=pairs.map(([fg,bg,min])=>{const a=luminance(tokens[fg]),b=luminance(tokens[bg]);return {fg,bg,min,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)}});
   contrast.push({theme,accent,ratios});ok(theme+'/'+accent+' readable semantic colors',ratios.every(r=>r.ratio>=r.min));
  }
 }
 await choose('type','large');await choose('density','compact');await choose('motion','subtle');
 ok('live larger body text',await p.locator('body').evaluate(e=>getComputedStyle(e).fontSize==='18px'));
 await p.emulateMedia({reducedMotion:'reduce'});
 ok('reduced motion overrides preference',await p.locator('#reset-display').evaluate(e=>getComputedStyle(e).transitionDuration==='0s'));
 await p.screenshot({path:path.join(out,'settings-dark.png'),fullPage:true});
 await p.keyboard.press('Escape');ok('Escape closes and restores focus',await p.locator('#open-display').evaluate(e=>e===document.activeElement&&!document.querySelector('dialog').open));
 ok('appearance leaves business inputs untouched',JSON.stringify(await snapshot())===JSON.stringify(original));
 ok('appearance makes no API writes',posts.length===0);
 await p.reload();await p.waitForFunction(()=>document.documentElement.dataset.type==='large');
 ok('display preferences persist',await p.evaluate(()=>['dark','plum','large','compact','subtle'].every((v,i)=>document.documentElement.dataset[['theme','accent','type','density','motion'][i]]===v)));
 await p.waitForFunction(()=>document.querySelector('#notice').textContent.includes('已连接'));
 await p.evaluate(()=>localStorage.setItem('unrelated-test-sentinel','keep'));
 const preReset=await snapshot();await p.click('#open-display');await p.click('#reset-display');await p.click('#close-display');
 ok('reset preserves business inputs and other storage',JSON.stringify(await snapshot())===JSON.stringify(preReset)&&await p.evaluate(()=>localStorage.getItem('unrelated-test-sentinel')==='keep'));
 ok('reset restores default display',await p.evaluate(()=>document.documentElement.dataset.theme==='light'&&document.documentElement.dataset.type==='normal'));
 // Exercise numeric precision, missing values and slider keyboard semantics.
 if(q==='q1')await p.locator('#advanced').evaluate(e=>e.open=true);
 const precise=q==='q2'?'125.37':q==='q4'?'28.7':'37';
 await p.fill('#'+target,precise);await p.waitForFunction(v=>document.querySelector('#parameter-range').value===v,precise);
 ok('numeric entry synchronizes without rounding or clamping',await p.inputValue('#'+target)===precise);
 if(q==='q2'){await p.fill('#budget','100000');await p.waitForFunction(()=>document.querySelector('#parameter-range').max==='100000');ok('large budget preserved',await p.inputValue('#budget')==='100000');}
 await p.fill('#'+target,'');await p.waitForFunction(()=>document.querySelector('#parameter-range').hidden);
 ok('missing numeric input stays missing',await p.inputValue('#'+target)==='');
 await p.fill('#'+target,precise);await p.waitForFunction(()=>!document.querySelector('#parameter-range').hidden);
 await p.focus('#parameter-range');await p.keyboard.press('ArrowRight');
 ok('keyboard slider updates original numeric input',Math.abs(Number(await p.inputValue('#'+target))-(Number(precise)+(q==='q1'?1:q==='q2'?.01:.1)))<.000001);
 ok('parameter changes do not run Agent',posts.length===0);
 await p.selectOption('#scenario','normal');
 await p.waitForFunction(()=>!document.querySelector('#parameter-range').hidden);
 // Delay response so the disabled running state is observable without model calls.
 await p.route('**/api/jobs',async route=>{await new Promise(r=>setTimeout(r,400));await route.continue();});
 await p.click('#'+run);await p.waitForFunction(()=>document.querySelector('#parameter-range').disabled);
 ok('new slider disabled during execution',await p.isDisabled('#parameter-range'));
 await p.waitForFunction(id=>!document.getElementById(id).disabled,run,{timeout:30000});await p.unroute('**/api/jobs');
 ok('explicit run submits unchanged API payload',posts.length===1&&posts[0].url.endsWith('/api/jobs')&&posts[0].body.mode==='mock'&&!!posts[0].body.request.request_id);
 const resultSelector=q==='q1'?'#results':'#result';
 const result=await p.locator(resultSelector).innerText();const storage=await p.evaluate(()=>Object.fromEntries(Object.entries(localStorage).filter(([k])=>!k.includes('-display-'))));
 await p.fill('#'+target,q==='q1'?'33':q==='q2'?'9.99':'29.5');
 await p.waitForFunction(()=>document.querySelector('#parameter-value').textContent.includes(document.querySelector('#parameter-range').value));
 ok('input preview updates without rewriting result',await p.locator(resultSelector).innerText()===result&&posts.length===1);
 ok('preview clearly distinguishes pending inputs',(await p.locator('.live-brief').innerText()).includes('下方结果不会随预览更新'));
 await p.click('#open-display');await choose('theme','dark');await choose('accent','blue');await p.click('#close-display');
 ok('theme preserves computed result and saved job storage',await p.locator(resultSelector).innerText()===result&&JSON.stringify(await p.evaluate(()=>Object.fromEntries(Object.entries(localStorage).filter(([k])=>!k.includes('-display-')))))===JSON.stringify(storage));
 await p.screenshot({path:path.join(out,'success-dark.png'),fullPage:true});
 await p.click('#open-display');await p.click('#reset-display');await p.click('#close-display');
 await p.screenshot({path:path.join(out,'success-desktop.png'),fullPage:true});
 for(const width of [390,320]){
  await p.setViewportSize({width,height:844});await p.click('#open-display');await choose('type','large');
  ok(width+' large-text dialog fits viewport',await p.locator('#display-settings').evaluate(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&e.scrollWidth<=e.clientWidth}));
  await p.screenshot({path:path.join(out,'settings-'+width+'.png'),fullPage:true});await p.keyboard.press('Escape');
  ok(width+' large-text page has no horizontal overflow',await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await p.screenshot({path:path.join(out,'mobile-'+width+'.png'),fullPage:true});
 }
 await p.evaluate(q=>localStorage.setItem(`agent-${q}-display-v1`,'{"theme":"bogus","type":"tiny","accent":"url(evil)"}'),q);
 await p.reload();await p.waitForFunction(()=>document.documentElement.dataset.theme==='light');
 ok('invalid stored settings fall back to safe defaults',await p.evaluate(()=>document.documentElement.dataset.accent==='green'&&document.documentElement.dataset.type==='normal'));
 await p.evaluate(q=>localStorage.setItem(`agent-${q}-display-v1`,'{broken'),q);await p.reload();
 await p.waitForFunction(()=>document.documentElement.dataset.theme==='light');ok('malformed preferences do not break page',await p.locator('#open-display').isVisible());
 const restricted=await browser.newPage();await restricted.addInitScript(()=>{const get=Storage.prototype.getItem,set=Storage.prototype.setItem;Storage.prototype.getItem=function(k){if(k.includes('-display-'))throw new DOMException('blocked','SecurityError');return get.call(this,k)};Storage.prototype.setItem=function(k,v){if(k.includes('-display-'))throw new DOMException('blocked','SecurityError');return set.call(this,k,v)}});
 await restricted.goto(base);await restricted.click('#open-display');await restricted.click('[data-setting="theme"][data-value="dark"]');
 ok('blocked preference storage still allows temporary theme',await restricted.evaluate(()=>document.documentElement.dataset.theme==='dark')&&(await restricted.locator('#display-note').innerText()).includes('不允许'));
 await restricted.close();ok('no browser, CSP, or HTTP errors',errors.length===0);
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({project:q,timestamp:new Date().toISOString(),passed:true,checks,contrast,errors},null,2));console.log(q,checks.length,'live-control checks passed');
})().catch(e=>{fs.writeFileSync(path.join(out,'report.json'),JSON.stringify({project:q,passed:false,checks,contrast,errors,error:e.stack},null,2));console.error(e);process.exitCode=1}).finally(async()=>{if(browser)await browser.close()});
