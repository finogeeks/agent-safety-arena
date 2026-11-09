// Observe the real DSH page in the trial's dedicated Chrome profile.
// Choices follow the caller's authorized capture-and-record checkpoint.
// Never replace a panel's wording or suppress an operator event.
const readline = require('node:readline');

let socket;
let sequence = 0;
const pending = new Map();
const openSidebar = 'button[aria-label="Open sidebar"],button[aria-label="打开侧边栏"]';
const collapseSidebar = 'button[aria-label="Collapse sidebar"],button[aria-label="收起侧边栏"]';
const sidebar = openSidebar + ',' + collapseSidebar;

async function connect(url) {
  if (new URL(url).hostname !== '127.0.0.1') throw Error('Chrome must use loopback');
  socket = new WebSocket(url);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('Chrome connection timed out')), 10000);
    socket.onopen = () => { clearTimeout(timer); resolve(); };
    socket.onerror = () => { clearTimeout(timer); reject(Error('Chrome connection failed')); };
  });
  socket.onmessage = event => {
    const response = JSON.parse(event.data);
    const item = pending.get(response.id);
    if (!item) return;
    pending.delete(response.id);
    clearTimeout(item.timer);
    response.error ? item.reject(Error(response.error.message)) : item.resolve(response.result);
  };
  socket.onclose = () => {
    for (const item of pending.values()) {
      clearTimeout(item.timer);
      item.reject(Error('Chrome connection closed'));
    }
    pending.clear();
  };
  await call('Page.enable');
}

function call(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(Error('Chrome command timed out: ' + method));
    }, 15000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const response = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (response.exceptionDetails) throw Error('DSH page observation failed: ' + response.exceptionDetails.text);
  return response.result.value;
}

async function until(expression, message) {
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 150));
  }
  throw Error(message);
}

function snapshotInPage() {
  const selector = '[data-approval-key],[data-question-key],[role="dialog"],[role="alertdialog"]';
  if (!window.__arenaCapture) {
    const state = window.__arenaCapture = { count: 0, nodes: new WeakMap(), active: new Set(), choices: [] };
    const record = event => {
      const panel = event.target.closest?.(selector);
      if (!panel) return;
      const key = panel.getAttribute('data-approval-key') || panel.getAttribute('data-question-key') || state.nodes.get(panel);
      if (!key) return;
      if (event.type === 'pointerdown') {
        const button = event.target.closest('button,[role="button"]');
        if (button) state.choices.push({ key, label: button.innerText || button.getAttribute('aria-label'), at: Date.now() });
      } else if (event.key === 'Enter' || event.key === 'Escape') {
        state.choices.push({ key, label: 'keyboard:' + event.key, at: Date.now() });
      }
    };
    document.addEventListener('pointerdown', record, { capture: true, passive: true });
    document.addEventListener('keydown', record, { capture: true, passive: true });
  }
  const state = window.__arenaCapture;
  const visible = [...document.querySelectorAll(selector)].filter(panel => {
    const rect = panel.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && getComputedStyle(panel).visibility !== 'hidden';
  });
  for (const old of state.active) if (!visible.includes(old)) state.nodes.delete(old);
  state.active = new Set(visible);
  const dialogs = visible.filter(panel => !panel.parentElement?.closest(selector)).map(panel => {
    if (!state.nodes.has(panel)) state.nodes.set(panel, 'dialog-' + (++state.count));
    return { key: panel.getAttribute('data-approval-key') || panel.getAttribute('data-question-key') || state.nodes.get(panel),
      native: panel.hasAttribute('data-approval-key'), text: panel.innerText,
      choices: [...panel.querySelectorAll('button')].map(button => button.innerText || button.getAttribute('aria-label')),
      busy: panel.getAttribute('aria-busy') === 'true' };
  }).filter(panel => !panel.busy);
  const uiLanguage = document.querySelector('button[aria-label="Open sidebar"],button[aria-label="Collapse sidebar"]') ? 'en'
    : document.querySelector('button[aria-label="打开侧边栏"],button[aria-label="收起侧边栏"]') ? 'zh-CN' : 'und';
  return { title: document.title, dialogs, choices: state.choices.splice(0), uiLanguage };
}

function continueButtonInPage(wanted) {
  const labelOf = button => (button.innerText || button.getAttribute('aria-label') || '').trim();
  const selector = '[data-approval-key],[data-question-key],[role="dialog"],[role="alertdialog"]';
  const panels = [...document.querySelectorAll(selector)].filter(panel => panel.getBoundingClientRect().height > 0);
  const roots = panels.length ? panels : [document.body || document.documentElement || document];
  const matches = [];
  for (const root of roots) {
    for (const button of root.querySelectorAll('button')) {
      if (!button.disabled && labelOf(button) === wanted) matches.push(button);
    }
  }
  return matches.length === 1 ? matches[0] : null;
}

async function dispatch(request) {
  switch (request.action) {
    case 'connect': await connect(request.url); return true;
    case 'ready':
      // A new browser has no composer until its workspace is selected.
      await until(`!!document.querySelector(${JSON.stringify(sidebar)})`,
                  'DSH page did not finish loading');
      return true;
    case 'prepare': {
      await until(`!!document.querySelector(${JSON.stringify(sidebar)})`,
                  'DSH page did not load');
      await evaluate(`document.querySelector(${JSON.stringify(openSidebar)})?.click()`);
      const labels = JSON.stringify(['New session in ' + request.workspace, '在“' + request.workspace + '”中新建会话']);
      const ownedSession = `(()=>{
        const button=[...document.querySelectorAll('button')].find(b=>${labels}.includes(b.getAttribute('aria-label')));
        if(!button)return '';
        const workspace=button.closest('[data-row-key^="workspace:"]');
        if(!workspace){
          const row=document.querySelector('[data-row-key^="session:"][aria-selected="true"]');
          return row?row.getAttribute('data-row-key').slice('session:'.length):'';
        }
        const group=workspace.getAttribute('data-row-key').slice('workspace:'.length);
        const overflow=document.querySelector('[data-row-key="overflow:'+group+'"][aria-expanded="false"]');
        if(overflow)overflow.click();
        const rows=[...document.querySelectorAll('[data-row-key^="workspace:"],[data-row-key^="session:"]')];
        for(let i=rows.indexOf(workspace)+1;i<rows.length;i++){
          const key=rows[i].getAttribute('data-row-key');
          if(key.startsWith('workspace:'))break;
          if(rows[i].getAttribute('aria-selected')==='true')return key.slice('session:'.length);
        }
        return '';
      })()`;
      await until(`(()=>{const button=[...document.querySelectorAll('button')].find(b=>${labels}.includes(b.getAttribute('aria-label')));if(!button)return false;button.click();return true;})()`,
                  'Owned workspace did not appear in DSH');
      await until(`!!document.querySelector('[contenteditable="true"]')`, 'DSH conversation composer did not appear');
      try {
        await until(ownedSession, 'The selected DSH session did not appear in the sidebar');
      } catch (error) {
        const detail = await evaluate(`JSON.stringify([...document.querySelectorAll('[data-row-key]')].slice(0, 24).map(el => el.getAttribute('data-row-key') + '=' + el.getAttribute('aria-selected')))`);
        throw Error(error.message + ' rows ' + detail);
      }
      const selected = await evaluate(ownedSession);
      await evaluate(`document.querySelector(${JSON.stringify(collapseSidebar)})?.click()`);
      await evaluate('(' + snapshotInPage.toString() + ')()');
      return selected;
    }
    case 'verify-title':
      await until(`document.title.startsWith(${JSON.stringify(request.title)})`, 'Visible DSH session title does not match');
      return true;
    case 'layout': {
      const { windowId } = await call('Browser.getWindowForTarget');
      await call('Browser.setWindowBounds', { windowId, bounds: { windowState: 'normal' } });
      if (request.windowState === 'maximized') {
        await call('Browser.setWindowBounds', { windowId, bounds: { windowState: 'maximized' } });
      } else {
        const [left, top, width, height] = request.region;
        await call('Browser.setWindowBounds', { windowId, bounds: { left, top, width, height } });
      }
      if (request.activate !== false) await call('Page.bringToFront');
      return true;
    }
    case 'snapshot': return await evaluate('(' + snapshotInPage.toString() + ')()');
    case 'choose-once': {
      const wanted = (request.label || 'Allow once').trim();
      const result = await evaluate(`(()=>{
        const button=(${continueButtonInPage.toString()})(${JSON.stringify(wanted)});
        if(!button)return false;
        const label=(button.innerText||button.getAttribute('aria-label')||'').trim();
        const at=Date.now();
        button.click();
        return {label,at};
      })()`);
      if (!result) throw Error('No unique continue choice was visible');
      return result;
    }
    case 'screenshot': {
      const stillPending = `(()=>{const s=window.__arenaCapture;return [...document.querySelectorAll('[data-approval-key],[data-question-key],[role="dialog"],[role="alertdialog"]')].some(p=>(p.getAttribute('data-approval-key')||p.getAttribute('data-question-key')||s?.nodes.get(p))===${JSON.stringify(request.key)}&&p.getAttribute('aria-busy')!=='true'&&p.getBoundingClientRect().height>0);})()`;
      if (request.key && !await evaluate(stillPending)) return false;
      const screenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
      if (request.key && !await evaluate(stillPending)) return false;
      return { data: screenshot.data, at: Date.now() };
    }
    case 'close': await call('Browser.close'); return true;
    default: throw Error('Unsupported browser observation command');
  }
}

let chain = Promise.resolve();
readline.createInterface({ input: process.stdin }).on('line', line => {
  chain = chain.then(async () => {
    try { process.stdout.write(JSON.stringify({ ok: true, value: await dispatch(JSON.parse(line)) }) + '\n'); }
    catch (error) { process.stdout.write(JSON.stringify({ ok: false, error: error.message }) + '\n'); }
  });
}).on('close', () => { socket?.close(); });
