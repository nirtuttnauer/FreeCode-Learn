const {contextBridge, ipcRenderer} = require('electron');
const operations = new Set(['bootstrap','open','save','run','stop','set_settings','edit_list','experiment','simulate','reset','revealWork','openSource','export','closeReady']);
contextBridge.exposeInMainWorld('freecode', {
  invoke(operation, params) {
    if (!operations.has(operation)) return Promise.reject(new Error('Unknown operation.'));
    return ipcRenderer.invoke('freecode', operation, params);
  },
  onCommand(callback) { ipcRenderer.on('command', (_, command) => callback(command)); }
});
