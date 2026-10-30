'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {app}=require('electron');
const output=process.env.FREECODE_TEST_OUTPUT||'/output';
const checks=[],errors=[];
let window,call,bundle,work;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function js(source){return window.webContents.executeJavaScript(source,true);}
async function wait(source,timeout=30000){const end=Date.now()+timeout;while(Date.now()<end){if(await js(source))return;await pause(150);}throw Error('Timed out: '+source);}
async function click(id){await js(`document.getElementById(${JSON.stringify(id)}).click()`);await pause(150);}
async function change(id,value){await js(`{const el=document.getElementById(${JSON.stringify(id)});el.value=${JSON.stringify(value)};el.dispatchEvent(new Event('change',{bubbles:true}));}`);await pause(300);}
async function check(name,fn){await fn();checks.push(name);console.log('PASS '+name);}
async function screenshot(name){await pause(250);await js('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');fs.writeFileSync(path.join(output,name+'.png'),(await window.webContents.capturePage()).toPNG());}
const watchdog=setTimeout(async()=>{console.error('STARTUP TIMEOUT');const windows=require('electron').BrowserWindow.getAllWindows();if(windows[0]){fs.writeFileSync(path.join(output,'startup-timeout.png'),(await windows[0].webContents.capturePage()).toPNG());console.error('URL',windows[0].webContents.getURL());console.error(await windows[0].webContents.executeJavaScript('document.documentElement.outerHTML').catch(e=>e.message));}app.exit(2);}, 360000).unref();
(async()=>{
  console.log('Starting PracticeCode smoke checks');
  ({window,call,bundle,work}=await require(process.env.FREECODE_TEST_APP||'/package/resources/app/main.cjs').ready);
  window.webContents.on('console-message',event=>{if(event.level==='error')errors.push(event.message);});
  await wait("document.body.dataset.ready==='true'");
  await check('Fresh offline account and complete catalog',async()=>{const data=await call('bootstrap');assert.equal(data.catalog.length,4086);assert.equal(data.lessons.length,JSON.parse(fs.readFileSync(path.join(bundle,"data/learning/catalog.json"))).length);assert.equal(data.playlists.length,18);assert.deepEqual(data.progress,{});assert.deepEqual(data.activity,[]);assert.equal(await js("document.querySelectorAll('[data-question]').length"),4086);});
  await check('Complete statement and playlist integrity',async()=>{const b=await call('bootstrap'),known=new Set(b.catalog.map(p=>p.id));for(const [folder,rows] of [['problems',b.catalog],['learning/problems',b.lessons]])for(const row of rows){const p=JSON.parse(fs.readFileSync(path.join(bundle,'data',folder,row.id+'.json')));assert.ok(p.statement.length>0);assert.ok(p.starters&&p.references);}for(const list of b.playlists)for(const group of list.groups)for(const id of group.questionIDs)assert.ok(known.has(id));});
  await check('Proportional interface font',async()=>{assert.ok(await js(`(()=>{const c=document.createElement('canvas').getContext('2d');c.font=getComputedStyle(document.body).font;return c.measureText('WWWW').width>c.measureText('iiii').width*2;})()`));});
  await check('Renderer isolation and IPC allowlist',async()=>{assert.equal(await js('typeof require'), 'undefined');assert.equal(await js('typeof process'), 'undefined');assert.equal(await js("window.practicecode.invoke('complete_run',{}).then(()=>false,()=>true)"),true);});
  await click('settings');await js("document.querySelector('[data-appearance=dark]').click()");await wait("document.documentElement.dataset.theme==='dark'");await js("document.getElementById('dialog').close()");await pause(250);await screenshot('practice-dark');
  await click('settings');await js("document.querySelector('[data-appearance=light]').click()");await wait("document.documentElement.dataset.theme==='light'");await js("document.getElementById('dialog').close()");await pause(250);await screenshot('practice-light');
  await check('Focus controls and test panel restoration',async()=>{await click('focus-code');assert.equal(await js("document.body.dataset.focus"),'code');assert.equal(await js("document.getElementById('console').hidden"),true);await click('restore-console');assert.equal(await js("document.getElementById('console').hidden"),false);await click('focus-code');await click('focus-question');assert.equal(await js("document.body.dataset.focus"),'question');await click('focus-question');});
  await check('Bundled diagram renders offline',async()=>{await js("document.querySelector('[data-question=\"2\"]').click()");await wait("document.getElementById('question-title').textContent.startsWith('2.')");await wait("document.getElementById('statement').contentDocument?.images.length>0 && [...document.getElementById('statement').contentDocument.images].every(i=>i.complete&&i.naturalWidth>0)");});
  await screenshot('diagram');
  // The only network namespace in this test is Docker --network none.
  await check('All local diagram assets decode through the packaged protocol',async()=>{
    const files=[...new Set([...fs.readdirSync(path.join(bundle,'data/problems')).map(f=>path.join(bundle,'data/problems',f)),...fs.readdirSync(path.join(bundle,'data/learning/problems')).map(f=>path.join(bundle,'data/learning/problems',f))].flatMap(f=>{const p=JSON.parse(fs.readFileSync(f));return [...p.statement.matchAll(/offline:\/\/assets\/([^"'<>\s]+)/g)].map(m=>m[1]);}))];
    assert.ok(files.length>1800);let failures=[];
    for(let i=0;i<files.length;i+=70){const batch=files.slice(i,i+70);const result=await js(`Promise.all(${JSON.stringify(batch)}.map(name=>new Promise(resolve=>{const image=new Image();image.onload=()=>resolve(null);image.onerror=()=>resolve(name);image.src='practicecode://library/assets/'+name;})))`);failures.push(...result.filter(Boolean));}
    assert.deepEqual(failures,[]);checks.push(files.length+' distinct diagram assets decoded');
  });
  await check('Run Python / JavaScript / C++ / Java with bundled runtimes',async()=>{
    for(const language of ['python','javascript','cpp','java']){
      const opened=await call('open',{id:1,language});assert.ok(opened.problem.references[language]);
      await call('save',{id:1,language,patch:{code:opened.problem.references[language]}});
      await js("document.querySelector('[data-question=\"1\"]').click()");await wait("document.getElementById('question-title').textContent.startsWith('1.')");
      await change('language',language);await wait(`document.getElementById('language').value===${JSON.stringify(language)}`);
      await click('run');
      await wait("!document.getElementById('run').textContent.includes('Stop')",180000);
      const account=await call('bootstrap');const run=account.activity.at(-1);assert.equal(run.language,language);assert.equal(run.success,true,await js("document.getElementById('results').textContent"));assert.equal(account.progress['1'].status,'Solved');checks.push('Bundled '+language+' function checks');
    }
  });
  await check('Bundled SQLite query and structured result table',async()=>{await call('save',{id:175,language:'sql',patch:{code:'SELECT 42 AS answer;',stdin:''}});await js("document.querySelector('[data-question=\"175\"]').click()");await wait("document.getElementById('language').value==='sql'");await click('run');await wait("document.querySelector('.result-table')?.textContent.includes('42')");assert.equal((await call('bootstrap')).progress['175'].status,'In progress');});
  await check('Structured cases preserve invalid drafts and block running',async()=>{await js("document.querySelector('[data-question=\"1\"]').click()");await wait("document.getElementById('language').value==='python'");await js("document.querySelector('#console-tabs [data-tab=\"Test cases\"]').click()");await wait("document.querySelector('[data-case]')!==null");await js("{const e=document.querySelector('[data-case=\"0\"][data-argument=\"0\"][data-part=text]');e.value='[';e.dispatchEvent(new Event('input',{bubbles:true}));}");await pause(700);assert.equal(await js("document.getElementById('run').disabled"),true);assert.equal((await call('open',{id:1,language:'python'})).workspace.testCaseDrafts[0].arguments[0].text,'[');await js("{const e=document.querySelector('[data-case=\"0\"][data-argument=\"0\"][data-part=text]');e.value='[2,7,11,15]';e.dispatchEvent(new Event('input',{bubbles:true}));}");await pause(700);assert.equal(await js("document.getElementById('run').disabled"),false);});
  await check('Editor line comments and undo',async()=>{const before=(await call('open',{id:1,language:'python'})).workspace.code;window.webContents.send('command','comment');await pause(800);const commented=(await call('open',{id:1,language:'python'})).workspace.code;assert.notEqual(commented,before);window.webContents.send('command','undo');await pause(800);assert.equal((await call('open',{id:1,language:'python'})).workspace.code,before);});
  await check('Learning tracks remain separate, global lesson navigation works',async()=>{await click('learning');await wait("document.querySelectorAll('[data-question]').length===16");await click('focus-code');await click('next');await wait("document.getElementById('step').textContent==='Step 2 of 16'");await click('focus-code');await change('collection','systems');await wait("document.querySelectorAll('[data-question]').length===12");});
  await check('Architecture diagram, experiment and written review persist ungraded',async()=>{
    await js("document.querySelector('#workspace-tabs [data-tab=Architecture]').click()");await wait("document.querySelectorAll('.node').length===3");await click('add-node');await wait("document.querySelectorAll('.node').length===4");await js("document.querySelectorAll('.node')[1].click()");await wait("document.querySelector('[data-node-field=name]').value==='API service'");
    await js("document.querySelector('[data-design-tab=Experiments]').click()");await wait("document.getElementById('model-result')?.textContent.includes('Capacity estimate')");await click('save-experiment');await wait("document.querySelectorAll('.experiment').length===1");
    await js("document.querySelector('[data-design-tab=Review]').click()");await js("{const e=document.querySelector('[data-review=requirements]');e.value='Handle 200 requests per second';e.dispatchEvent(new Event('input',{bubbles:true}));}");await pause(700);const stored=await call('open',{id:-2001,language:'python'});assert.equal(stored.workspace.design.requirements,'Handle 200 requests per second');assert.equal(stored.workspace.design.experiments.length,1);assert.equal((await call('bootstrap')).progress['-2001'].status,'In progress');
    await js("document.querySelector('[data-design-tab=Diagram]').click()");await wait("document.querySelectorAll('.node').length===4");await screenshot('architecture-light');
  });
  await check('Activity calendar and difficulty chart',async()=>{await click('problems');await click('run');await wait("!document.getElementById('run').textContent.includes('Stop')",180000);await click('statistics');assert.ok(await js("document.querySelectorAll('.activity-day').length>=365"));assert.ok(await js("document.querySelector('.pie').getAttribute('aria-label').includes('1 completed')"));assert.equal(await js("document.querySelectorAll('.remaining tbody tr').length"),3);await screenshot('statistics-light');await js("document.getElementById('dialog').close()");});
  await check('Small desktop layout retains all panes and actions',async()=>{window.setSize(1000,760);await pause(500);assert.ok(await js("(()=>{const r=document.getElementById('coding').getBoundingClientRect();return r.right<=innerWidth&&r.width>=310;})()"));await screenshot('practice-small-light');window.setSize(1480,940);});
  await check('Personal lists retain membership without changing code',async()=>{const lists=await call('edit_list',{action:'create',name:'Practice later'});await call('edit_list',{action:'toggle',listID:lists[0].id,questionID:1});const b=await call('bootstrap');assert.deepEqual(b.lists[0].questionIDs,[1]);});
  // The application must finish its own close/flush handshake before inspection.
  await js("document.querySelector('#statement-tabs [data-tab=Notes]').click()");
  await js("{const e=document.getElementById('notes');e.value='Saved even when quitting immediately';e.dispatchEvent(new Event('input',{bubbles:true}));}");
  app.once('will-quit',()=>{
    try {
      const progress=JSON.parse(fs.readFileSync(path.join(work,'progress.json')));
      assert.ok(Object.values(progress).some(p=>p.notes==='Saved even when quitting immediately'));
      checks.push('Autosave flushes before application close');
      assert.deepEqual(errors,[]);
      fs.writeFileSync(path.join(output,'report.json'),JSON.stringify({checks,errors,platform:process.platform,arch:process.arch,electron:process.versions.electron},null,2));
      console.log('ALL CHECKS PASSED');
    } catch(error) {fs.writeFileSync(path.join(output,'report.json'),JSON.stringify({checks,errors,failure:error.stack},null,2));process.exitCode=1;}
  });
  window.close();
})().catch(async error=>{console.error(error);try{if(window){await screenshot('failure');console.error(await js("document.getElementById('notice').textContent"));}}catch{}fs.writeFileSync(path.join(output,'report.json'),JSON.stringify({checks,errors,failure:error.stack},null,2));app.exit(1);});
