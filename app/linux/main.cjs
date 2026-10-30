'use strict';
const {app, BrowserWindow, ipcMain, protocol, net, dialog, shell, Menu, nativeTheme} = require('electron');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {pathToFileURL} = require('node:url');

const appRoot = __dirname;
const bundle = process.env.FREECODE_BUNDLE_ROOT || (fs.existsSync(path.join(appRoot, '../bundle/data')) ? path.resolve(appRoot, '../bundle') : path.resolve(appRoot, '../..'));
const work = process.env.OFFLINE_PRACTICE_WORK_DIR || path.join(process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local/share'), 'PracticeCode');
const python = path.join(bundle, 'runtimes', process.arch === 'arm64' ? 'arm64' : 'x86_64', 'python/bin/python3');
let window, backend, activeRun, nextID = 0, allowClose = false;
const pending = new Map();
protocol.registerSchemesAsPrivileged([{scheme: 'practicecode', privileges: {standard: true, secure: true, supportFetchAPI: true}}]);
app.setName('PracticeCode');
if (process.env.OFFLINE_PRACTICE_WORK_DIR) app.setPath('userData', path.join(work, 'ui-cache'));

function call(method, params = {}) {
  return new Promise((resolve, reject) => {
    if (!backend || backend.killed) return reject(new Error('The local state service is unavailable. Restart PracticeCode.'));
    const id = ++nextID;
    pending.set(id, {resolve, reject});
    backend.stdin.write(JSON.stringify({id, method, params}) + '\n', error => {
      if (error) { pending.delete(id); reject(error); }
    });
  });
}

function startBackend() {
  backend = spawn(python, ['-I', '-B', path.join(appRoot, 'backend.py')], {
    env: {...process.env, FREECODE_BUNDLE_ROOT: bundle, OFFLINE_PRACTICE_WORK_DIR: work}, stdio: ['pipe', 'pipe', 'pipe']
  });
  let buffer = '', errorText = '';
  backend.stdout.setEncoding('utf8');
  backend.stdout.on('data', chunk => {
    buffer += chunk;
    if (buffer.length > 16_000_000) return backend.kill();
    let newline;
    while ((newline = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newline); buffer = buffer.slice(newline + 1);
      try {
        const response = JSON.parse(line), waiting = pending.get(response.id);
        if (waiting) { pending.delete(response.id); response.error ? waiting.reject(new Error(response.error)) : waiting.resolve(response.result); }
      } catch { backend.kill(); }
    }
  });
  backend.stderr.on('data', chunk => { errorText = (errorText + chunk).slice(-10000); });
  const failed = error => {
    for (const waiting of pending.values()) waiting.reject(new Error(error?.message || errorText || 'The local state service stopped. Your files remain on disk.'));
    pending.clear(); backend = null;
  };
  backend.on('error', failed);
  backend.on('exit', () => failed());
}

async function run(params) {
  if (activeRun) throw new Error('A run is already active.');
  const prepared = await call('prepare_run', params);
  return new Promise(resolve => {
    let output = '', errors = '', stopped = false, settled = false;
    const processRun = spawn(python, ['-I', '-B', path.join(bundle, 'scripts/runner.py')], {env: process.env, detached: true, stdio: ['pipe', 'pipe', 'pipe']});
    const stop = () => { stopped = true; processRun.kill('SIGTERM'); };
    activeRun = {stop};
    const timeout = setTimeout(stop, 180000);
    processRun.stdout.on('data', chunk => { output += chunk; if (output.length > 2_000_000) stop(); });
    processRun.stderr.on('data', chunk => { errors = (errors + chunk).slice(-30000); });
    const finish = async error => {
      if (settled) return;
      settled = true; clearTimeout(timeout); activeRun = null;
      let result;
      try { result = stopped ? {success:false, message:'Stopped', output:'The run was stopped.', cases:[], stopped:true} : JSON.parse(output); }
      catch { result = {success:false, message:'Runner could not finish', output:error?.message || errors || 'Reinstall the full PracticeCode package if a runtime is missing.', cases:[]}; }
      try { resolve(await call('complete_run', {token: prepared.token, result})); }
      catch (failure) { resolve({result: {...result, output: (result.output || '') + '\nCould not save run: ' + failure.message}}); }
    };
    processRun.once('error', finish); processRun.once('close', () => finish());
    processRun.stdin.on('error', () => {});
    processRun.stdin.end(JSON.stringify(prepared.request));
  });
}

function validateSender(event) {
  if (!window || event.sender !== window.webContents || event.senderFrame !== window.webContents.mainFrame || event.senderFrame.url !== 'practicecode://app/index.html') throw new Error('Untrusted request.');
}

const ready = app.whenReady().then(async () => {
  protocol.handle('practicecode', request => {
    const url = new URL(request.url);
    const root = url.hostname === 'app' ? appRoot : url.hostname === 'library' ? path.join(bundle, 'data') : null;
    if (!root || request.method !== 'GET') return new Response('Not found', {status:404});
    let target;
    try { target = path.resolve(root, '.' + decodeURIComponent(url.pathname)); } catch { return new Response('Invalid path', {status:400}); }
    if (!target.startsWith(root + path.sep) || !fs.existsSync(target) || !fs.statSync(target).isFile()) return new Response('Not found', {status:404});
    const allowedApp = new Set(['index.html','renderer.js','ui.css','icon.png']);
    if (url.hostname === 'app' && !allowedApp.has(path.relative(root, target))) return new Response('Not found', {status:404});
    return net.fetch(pathToFileURL(target).toString());
  });
  startBackend();
  window = new BrowserWindow({width:1480, height:940, minWidth:900, minHeight:620, title:'PracticeCode', icon:path.join(appRoot,'icon.png'),
    backgroundColor:'#0A121C', webPreferences:{preload:path.join(appRoot,'preload.cjs'), contextIsolation:true, sandbox:true, nodeIntegration:false, webviewTag:false}});
  window.webContents.session.setPermissionRequestHandler((_, __, callback) => callback(false));
  window.webContents.session.setPermissionCheckHandler(() => false);
  window.webContents.session.webRequest.onBeforeRequest((details, callback) => callback({cancel: !details.url.startsWith('practicecode://') && !details.url.startsWith('file://') && !details.url.startsWith('devtools://')}));
  window.on('close', event => { if (!allowClose) { event.preventDefault(); window.webContents.send('command','close'); } });
  window.webContents.on('will-navigate', event => event.preventDefault());
  window.webContents.setWindowOpenHandler(() => ({action:'deny'}));
  ipcMain.handle('practicecode', async (event, operation, params = {}) => {
    validateSender(event);
    if (operation === 'closeReady') { allowClose = true; app.quit(); return true; }
    if (operation === 'export') {
      const opened = await call('open', {id:params.id, language:params.language});
      const extensions = {python:'py', javascript:'js', cpp:'cpp', java:'java', sql:'sql'};
      const answer = await dialog.showSaveDialog(window, {defaultPath:opened.problem.slug+'.'+extensions[params.language]});
      if (!answer.canceled) fs.writeFileSync(answer.filePath, opened.workspace.code);
      return !answer.canceled;
    }
    if (operation === 'exportWorkspace') {
      const opened = await call('open', {id:params.id, language:params.language});
      if (!opened.workspace.files) throw new Error('Open a course workspace first.');
      const answer = await dialog.showOpenDialog(window, {properties:['openDirectory','createDirectory'], buttonLabel:'Export workspace'});
      if (answer.canceled) return false;
      const target = path.join(answer.filePaths[0], 'Python Engineer-' + require('node:crypto').randomUUID().slice(0,8));
      fs.mkdirSync(target);
      for (const [name, text] of Object.entries(opened.workspace.files)) {
        const file = path.resolve(target,name);
        if (!file.startsWith(target+path.sep)) throw new Error('Invalid workspace file.');
        fs.mkdirSync(path.dirname(file), {recursive:true}); fs.writeFileSync(file,text);
      }
      shell.showItemInFolder(target); return true;
    }
    if (operation === 'run') return run(params);
    if (operation === 'stop') { activeRun?.stop(); return true; }
    if (operation === 'reset') {
      if (activeRun) throw new Error('Stop the current run before resetting.');
      const answer = await dialog.showMessageBox(window, {type:'warning', title:'Reset account', message:'Start fresh?', detail:'Saved code, lists, tests, notes, favorites, progress, and run history will move to a recovery backup. The library and appearance setting are kept.', buttons:['Cancel','Reset account'], defaultId:0, cancelId:0, noLink:true});
      return answer.response === 1 ? call('reset') : null;
    }
    if (operation === 'revealWork') { shell.showItemInFolder(path.join(work,'progress.json')); return true; }
    if (operation === 'openSource') {
      const problem = await call('open', {id:params.id, language: params.id < 0 ? 'python' : 'python'});
      const url = new URL(problem.problem.sourceURL);
      if (url.protocol !== 'https:') throw new Error('Only HTTPS source links can open.');
      await shell.openExternal(url.toString()); return true;
    }
    if (!['bootstrap','open','save','set_settings','edit_list','experiment','simulate'].includes(operation)) throw new Error('Unknown operation.');
    const result = await call(operation, params);
    if (operation === 'set_settings') nativeTheme.themeSource = result.appearanceMode;
    return result;
  });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    {label:'File', submenu:[{label:'Save', accelerator:'Control+S', click:()=>window.webContents.send('command','save')},{label:'Run code', accelerator:'Control+Return', click:()=>window.webContents.send('command','run')},{label:'Settings', accelerator:'Control+,', click:()=>window.webContents.send('command','settings')},{type:'separator'},{role:'quit'}]},
    {label:'Edit', submenu:[{label:'Undo',accelerator:'Control+Z',click:()=>window.webContents.send('command','undo')},{label:'Redo',accelerator:'Control+Shift+Z',click:()=>window.webContents.send('command','redo')},{type:'separator'},{role:'cut'},{role:'copy'},{role:'paste'},{role:'selectAll'},{label:'Toggle line comment',accelerator:'Control+/',click:()=>window.webContents.send('command','comment')}]},
    {label:'Learning', submenu:[{label:'Previous lesson',accelerator:'Control+Alt+Left',click:()=>window.webContents.send('command','previous')},{label:'Next lesson',accelerator:'Control+Alt+Right',click:()=>window.webContents.send('command','next')}]},
    {label:'View', submenu:[{role:'togglefullscreen'},{role:'zoomIn'},{role:'zoomOut'},{role:'resetZoom'}]}
  ]));
  const initial = await call('bootstrap'); nativeTheme.themeSource = initial.settings.appearanceMode || 'system';
  await window.loadURL('practicecode://app/index.html');
  return {window, call, bundle, work};
}).catch(error => { dialog.showErrorBox('PracticeCode could not start', error.message); app.quit(); throw error; });

app.on('before-quit', event => { if (!allowClose && window && !window.isDestroyed()) { event.preventDefault(); window.webContents.send('command','close'); return; } activeRun?.stop(); backend?.kill(); });
app.on('window-all-closed', () => app.quit());
module.exports = {ready};
