'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {app}=require('electron');
const output=process.env.FREECODE_TEST_OUTPUT||'/output';
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let window,call,bundle,work;
const checks=[];
async function js(code){return window.webContents.executeJavaScript(code,true);}
async function wait(code){const end=Date.now()+130000;while(Date.now()<end){if(await js(code))return;await pause(100);}throw Error('Timed out: '+code);}
async function click(id){await js(`document.getElementById(${JSON.stringify(id)}).click()`);await pause(200);}
async function choose(id,value){await js(`{const e=document.getElementById(${JSON.stringify(id)});e.value=${JSON.stringify(value)};e.dispatchEvent(new Event('change',{bubbles:true}));}`);await pause(250);}
async function capture(name){await pause(250);fs.writeFileSync(path.join(output,name+'.png'),(await window.webContents.capturePage()).toPNG());}
const watchdog=setTimeout(()=>app.exit(2),240000);
(async()=>{
  ({window,call,bundle,work}=await require(process.env.FREECODE_TEST_APP).ready);
  await wait("document.body.dataset.ready==='true'");
  const boot=await call('bootstrap'),course=boot.courses.find(c=>c.id==='python-engineer');
  assert.ok(course);const ids=course.groups.flatMap(g=>g.questionIDs);assert.equal(ids.length,203);
  if(!boot.catalog.length){assert.equal(await js("document.getElementById('problems').hidden"),true);assert.equal(await js("document.getElementById('collection').value"),'python-engineer');checks.push('Public startup without private library');}
  else await click('learning');
  await choose('collection','python-engineer');
  await wait("!document.getElementById('course-tools').hidden");
  assert.ok(await js("document.getElementById('run').textContent.includes('required checks')"));
  const opened=await call('open',{id:ids[0],language:'python'});
  await call('save',{id:ids[0],language:'python',patch:{code:opened.problem.references.python}});
  // Reload using real sidebar selection to put the saved implementation in the editor.
  await js(`document.querySelector('[data-question="${ids[1]}"]').click()`);await pause(200);
  await js(`document.querySelector('[data-question="${ids[0]}"]').click()`);await pause(200);
  await click('run');await wait("!document.getElementById('run').textContent.includes('Stop')");
  const account=await call('bootstrap');assert.equal(account.progress[String(ids[0])].status,'Solved');
  assert.equal(account.activity.at(-1).success,true);checks.push('Course pytest runs using bundled Python and dependencies');
  await click('course-new');await wait("document.getElementById('course-filename')!==null");
  await js("document.getElementById('course-filename').value='test_learner.py'");await click('confirm-course-file');
  await wait("document.getElementById('course-file').value==='test_learner.py'");
  assert.ok((await call('open',{id:ids[1],language:'python'})).workspace.files['test_learner.py']!==undefined);
  checks.push('New file is shared by module steps');
  await choose('course-file',opened.problem.course.entrypoint);
  await wait("document.getElementById('course-file').value==='exercises_01.py'");
  await capture('python-engineer-light');
  await click('settings');await js("document.querySelector('[data-appearance=dark]').click()");await pause(200);await js("document.getElementById('dialog').close()");
  await capture('python-engineer-dark');
  const elementSizes=await js("(()=>{const e=document.getElementById('coding').getBoundingClientRect();return {right:e.right,width:e.width,viewport:innerWidth};})()");
  assert.ok(elementSizes.right<=elementSizes.viewport&&elementSizes.width>=300);checks.push('Course controls and editor fit the desktop layout');
  fs.writeFileSync(path.join(output,'course-report.json'),JSON.stringify({checks,errors:[],platform:process.platform,arch:process.arch},null,2));
  clearTimeout(watchdog);console.log('PASS: '+checks.join('; '));app.exit(0);
})().catch(async error=>{console.error(error);try{await capture('course-failure');}catch{}fs.writeFileSync(path.join(output,'course-report.json'),JSON.stringify({checks,errors:[error.stack]},null,2));app.exit(1);});
