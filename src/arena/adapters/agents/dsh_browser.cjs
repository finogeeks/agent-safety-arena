// Observe the real DSH page in the trial's dedicated Chrome profile.
// Never answer an approval, replace its wording, or suppress an operator event.
const readline = require('node:readline');

let socket;
let sequence = 0;
const pending = new Map();

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
  const selector = '[data-approval-key],[role="dialog"],[role="alertdialog"]';
  if (!window.__arenaCapture) {
    const state = window.__arenaCapture = { count: 0, nodes: new WeakMap(), active: new Set(), choices: [] };
    const record = event => {
      const panel = event.target.closest?.(selector);
      if (!panel) return;
      const key = panel.getAttribute('data-approval-key') || state.nodes.get(panel);
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
    return { key: panel.getAttribute('data-approval-key') || state.nodes.get(panel),
      native: panel.hasAttribute('data-approval-key'), text: panel.innerText,
      choices: [...panel.querySelectorAll('button')].map(button => button.innerText || button.getAttribute('aria-label')),
      busy: panel.getAttribute('aria-busy') === 'true' };
  }).filter(panel => !panel.busy);
  return { title: document.title, dialogs, choices: state.choices.splice(0) };
}

async function dispatch(request) {
  switch (request.action) {
    case 'connect': await connect(request.url); return true;
    case 'ready':
      await until(`!!document.querySelector('button[aria-label="Open sidebar"],button[aria-label="Collapse sidebar"]')&&!!document.querySelector('[contenteditable="true"]')`,
                  'DSH page did not finish loading');
      return true;
    case 'prepare': {
      await until(`!!document.querySelector('button[aria-label="Open sidebar"],button[aria-label="Collapse sidebar"]')`,
                  'DSH page did not load');
      await evaluate(`document.querySelector('button[aria-label="Open sidebar"]')?.click()`);
      const label = JSON.stringify('New session in ' + request.workspace);
      await until(`(()=>{const button=[...document.querySelectorAll('button')].find(b=>b.getAttribute('aria-label')===${label});if(!button)return false;button.click();return true;})()`,
                  'Owned workspace did not appear in DSH');
      await until(`!!document.querySelector('[contenteditable="true"]')`, 'DSH conversation composer did not appear');
      await evaluate(`document.querySelector('button[aria-label="Collapse sidebar"]')?.click()`);
      await evaluate('(' + snapshotInPage.toString() + ')()');
      return true;
    }
    case 'verify-title':
      await until(`document.title.startsWith(${JSON.stringify(request.title)})`, 'Visible DSH session title does not match');
      return true;
    case 'layout': {
      const { windowId } = await call('Browser.getWindowForTarget');
      await call('Browser.setWindowBounds', { windowId, bounds: { windowState: 'normal' } });
      const [left, top, width, height] = request.region;
      await call('Browser.setWindowBounds', { windowId, bounds: { left, top, width, height } });
      await call('Page.bringToFront');
      return true;
    }
    case 'snapshot': return await evaluate('(' + snapshotInPage.toString() + ')()');
    case 'screenshot': {
      const stillPending = `(()=>{const s=window.__arenaCapture;return [...document.querySelectorAll('[data-approval-key],[role="dialog"],[role="alertdialog"]')].some(p=>(p.getAttribute('data-approval-key')||s?.nodes.get(p))===${JSON.stringify(request.key)}&&p.getAttribute('aria-busy')!=='true'&&p.getBoundingClientRect().height>0);})()`;
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
