// Observe the owned WorkBuddy renderer over loopback CDP.
// Do not move the operator pointer. Do not rewrite dialog wording.
const readline = require('node:readline');
const { createWorkBuddyHooks, nativeRuntimePath } = require('./workbuddy_hooks.cjs');

let socket;
let sequence = 0;
const pending = new Map();
const hideSelectors = [
  '.user-menu-trigger',
  '.user-menu-trigger-miniprogram',
  '.conversation-list-invite-friends',
  '.conversation-list-invite-friends__card',
  '.msg-center-bell-btn',
];

async function connect(url) {
  if (new URL(url).hostname !== '127.0.0.1') throw Error('WorkBuddy CDP must use loopback');
  socket = new WebSocket(url);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('WorkBuddy CDP connection timed out')), 10000);
    socket.onopen = () => { clearTimeout(timer); resolve(); };
    socket.onerror = () => { clearTimeout(timer); reject(Error('WorkBuddy CDP connection failed')); };
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
      item.reject(Error('WorkBuddy CDP connection closed'));
    }
    pending.clear();
  };
  await call('Page.enable');
  await call('Runtime.enable');
}

function call(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(Error('WorkBuddy command timed out: ' + method));
    }, 15000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const response = await call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (response.exceptionDetails) {
    throw Error('WorkBuddy page observation failed: ' + response.exceptionDetails.text);
  }
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

function hideAccountInPage(selectors) {
  const style = document.getElementById('arena-hide-account') || document.createElement('style');
  style.id = 'arena-hide-account';
  style.textContent = selectors.join(',')
    + '{visibility:hidden!important;opacity:0!important;pointer-events:none!important;}';
  document.documentElement.appendChild(style);
  document.querySelector('button[aria-label="Collapse sidebar"]')?.click();
  return true;
}

function snapshotInPage(selectors) {
  const selector = '[role="dialog"],[role="alertdialog"],._container_uq4jg_42';
  const labelOf = button => button.querySelector('[class*="_optionLabel_"]')?.innerText?.trim()
    || document.getElementById(button.getAttribute('aria-labelledby'))?.innerText?.trim()
    || button.innerText?.trim() || button.getAttribute('aria-label');
  if (!window.__arenaCapture) {
    const state = window.__arenaCapture = { count: 0, nodes: new WeakMap(), active: new Set(), choices: [] };
    const record = event => {
      const panel = event.target.closest?.(selector);
      if (!panel) return;
      const key = state.nodes.get(panel);
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
  const visiblePanels = [...document.querySelectorAll(selector)].filter(panel => {
    const rect = panel.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && getComputedStyle(panel).visibility !== 'hidden';
  });
  for (const old of state.active) if (!visiblePanels.includes(old)) state.nodes.delete(old);
  state.active = new Set(visiblePanels);
  const dialogs = visiblePanels.filter(panel => !panel.parentElement?.closest(selector)).map(panel => {
    if (!state.nodes.has(panel)) state.nodes.set(panel, 'dialog-' + (++state.count));
    return {
      key: state.nodes.get(panel),
      native: true,
      text: panel.innerText,
      choices: [...panel.querySelectorAll('button')].map(labelOf).filter(Boolean),
    };
  });
  const accountNodes = selectors.flatMap(sel => [...document.querySelectorAll(sel)]);
  const visibleAccount = accountNodes.filter(el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden'
      && style.display !== 'none' && style.opacity !== '0';
  });
  const emailLike = /[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/;
  const email = [...document.querySelectorAll('button,span,div')].filter(el => {
    const text = el.innerText || '';
    if (!emailLike.test(text) || text.length > 80) return false;
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.opacity !== '0';
  }).map(el => el.innerText.trim());
  const uiLanguage = document.querySelector('button[aria-label="Send"],button[aria-label="New Task"],button[aria-label="Collapse sidebar"]')
    || [...document.querySelectorAll('button')].some(button => (button.innerText || '').trim() === 'New Task')
    ? 'en' : 'und';
  const modelButton = document.querySelector('button[aria-label^="Select model"]');
  const model = (modelButton?.getAttribute('aria-label') || '').replace(/^Select model:\s*/i, '') || '';
  return {
    title: document.title,
    dialogs,
    choices: state.choices.splice(0),
    uiLanguage,
    model,
    permissions: 'not-exposed',
    accountVisible: visibleAccount.length > 0 || email.length > 0,
    visibleAccountText: [...visibleAccount.map(el => el.innerText || ''), ...email].join('\n'),
  };
}

function visibleComposerInPage() {
  return document.querySelector('[data-slate-editor="true"][contenteditable="true"]')
    || document.querySelector('[role="textbox"][contenteditable="true"]');
}

function sendButtonInPage() {
  return document.querySelector('button[aria-label="Send"]');
}

function sendIsEnabled(button) {
  if (!button) return false;
  const cls = String(button.className || '');
  return !button.disabled && button.getAttribute('aria-disabled') !== 'true'
    && !cls.includes('wb-button--disabled');
}

function viewInPage() {
  const composer = document.querySelector('[data-slate-editor="true"][contenteditable="true"]')
    || document.querySelector('[role="textbox"][contenteditable="true"]');
  const send = document.querySelector('button[aria-label="Send"]');
  const stop = document.querySelector('button[aria-label="Stop"]');
  const body = document.body?.innerText || '';
  const assistantNodes = [...document.querySelectorAll('[class*="assistant"],[data-role="assistant"],.markdown-body')];
  const assistantText = assistantNodes.map(el => el.innerText || '').join('\n').trim();
  const completed = /Completed\s+\d+s/.test(body) && !stop && !!assistantText;
  return {
    composerText: composer?.innerText || '',
    sendDisabled: !send || send.disabled || send.getAttribute('aria-disabled') === 'true'
      || String(send.className || '').includes('wb-button--disabled'),
    running: !!stop || (!send && !!document.querySelector('[class*="stop"]')),
    completed,
    assistantText,
    prompt: composer?.innerText || '',
  };
}

async function dispatch(request) {
  switch (request.action) {
    case 'connect':
      await connect(request.url);
      return true;
    case 'prepare': {
      await until(`!!(${visibleComposerInPage.toString()})()`,
        'WorkBuddy composer did not appear');
      const started = await evaluate(`(async()=>{if(!window.wb?.navigation?.goto)return false;await window.wb.navigation.goto('/home');return true;})()`);
      if (!started) throw Error('New Task was not found');
      await until(`!!(${visibleComposerInPage.toString()})()`,
        'WorkBuddy New Task composer did not appear');
      await evaluate('(' + hideAccountInPage.toString() + ')(' + JSON.stringify(hideSelectors) + ')');
      await evaluate('(' + snapshotInPage.toString() + ')(' + JSON.stringify(hideSelectors) + ')');
      return true;
    }
    case 'hook-prepare': {
      if (typeof request.modelId !== 'string' || !request.modelId.trim()) throw Error('Native modelId required');
      const session = await evaluate(`(async()=>{
        const state=await window.__wbInvoke('securityCenter:getState',undefined);
        if(typeof state?.sandboxEnabled!=='boolean')throw Error('Native sandbox state is unknown');
        if(${request.requireNativeSandbox !== false}&&state.sandboxEnabled!==true)throw Error('Native sandbox must remain enabled');
        const modulePath=(${nativeRuntimePath.toString()})(window.workbuddyDesktop.appVersion);
        const runtime=await import(new URL(modulePath,location.href).href);
        const find=name=>Object.values(runtime).find(f=>typeof f==='function'&&f.name===name);
        const ensure=find('ensureDaemon'),getClient=find('getDaemonRpcClient');
        if(!ensure||!getClient)throw Error('Unsupported native daemon exports');
        await ensure();
        const conv=await window.wb.conversations.create({title:'Arena controlled trial',
          cwd:${JSON.stringify(request.workspace)},model:${JSON.stringify(request.modelId)},mode:'craft',
          welcomeMode:'working',permissionMode:'bypassPermissions',useSandboxCLI:state.sandboxEnabled,isPlayground:false});
        if(!conv?.info?.id)throw Error('Owned session creation failed');
        const initial=await conv.requests(null);
        if(initial.items.length!==0)throw Error('Owned task has pre-existing requests');
        const sessionId=conv.info.id,topic='session:event:'+sessionId,client=getClient();
        window.__arenaOwnedHookSessionId=sessionId;
        window.__arenaOwnedHookClient=client;
        window.__arenaOwnedHookConversation=conv;
        window.__arenaSessionHooks=(${createWorkBuddyHooks.toString()})({
          invoke:(channel,context,...args)=>client.invoke(channel,...args),
          subscribe:fn=>{
            const a=client.on(topic,event=>fn(topic,event));
            const b=client.on('sandbox:interceptRequest',event=>fn('sandbox:interceptRequest',event));
            return()=>{a();b();};
          }},sessionId);
        await window.wb.navigation.goto('/conversation/'+encodeURIComponent(sessionId));
        return {sessionId,modelId:conv.configManager.model,permissionMode:conv.configManager.permissionMode,
          useSandboxCLI:conv.configManager.useSandboxCLI};
      })()`);
      await until(`!!(${visibleComposerInPage.toString()})()`, 'Owned session composer did not appear');
      return session;
    }
    case 'hook-submit': {
      await dispatch({ action: 'fill', text: request.text });
      await evaluate(`window.__arenaVisiblePrompt=${JSON.stringify(request.text)};window.__arenaSessionHooks.trackVisible(${JSON.stringify(request.text)},${JSON.stringify(request.requestId)})`);
      await new Promise(resolve => setTimeout(resolve, 5000));
      return await dispatch({ action: 'send' });
    }
    case 'hook-output':
      return await evaluate(`(async()=>{
        const hooks=window.__arenaSessionHooks;
        if(hooks.output().requestId){
          const page=await window.__arenaOwnedHookConversation.requests(null);
          const publicText=parts=>(parts||[]).filter(p=>p.type==='text'&&typeof p.text==='string').map(p=>p.text).join('');
          for(const r of page.items){
            const userText=publicText(r.userMessage?.content);
            if(userText!==window.__arenaVisiblePrompt)continue;
            hooks.settleVisible({id:r.id,state:r.state,userText,assistantText:publicText(r.assistantMessage?.content)});
          }
        }
        return hooks.output();
      })()`);
    case 'hook-cancel':
      return await evaluate(`window.__arenaOwnedHookClient.invoke('session:cancel',window.__arenaOwnedHookSessionId)`);
    case 'hide-account':
      return await evaluate('(' + hideAccountInPage.toString() + ')(' + JSON.stringify(hideSelectors) + ')');
    case 'layout':
      return true;
    case 'fill': {
      const plain = value => String(value || '').replace(/\r\n/g, '\n').replace(/[ \t]+\n/g, '\n').trim();
      const expected = plain(request.text);
      const focusEditor = `(()=>{const el=(${visibleComposerInPage.toString()})();if(!el)return false;el.focus();const range=document.createRange();range.selectNodeContents(el);const sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);return true;})()`;
      await until(focusEditor, 'WorkBuddy composer is missing');
      await call('Input.insertText', { text: request.text });
      const got = plain(await evaluate(`((${visibleComposerInPage.toString()})()?.innerText||'')`));
      if (got !== expected) {
        throw Error('Composer text does not match the case prompt (' + got.length + ' vs ' + expected.length + ')');
      }
      return true;
    }
    case 'send': {
      const sendReady = `(()=>{const b=(${sendButtonInPage.toString()})();const cls=String(b&&b.className||'');return !!(b&&!b.disabled&&b.getAttribute('aria-disabled')!=='true'&&!cls.includes('wb-button--disabled'));})()`;
      await until(sendReady, 'WorkBuddy Send did not enable after the prompt');
      const clicked = await evaluate(`(()=>{const b=(${sendButtonInPage.toString()})();const cls=String(b&&b.className||'');if(!b||b.disabled||b.getAttribute('aria-disabled')==='true'||cls.includes('wb-button--disabled'))return false;b.click();return true;})()`);
      if (!clicked) throw Error('WorkBuddy Send was not available');
      return true;
    }
    case 'cancel':
      await evaluate(`document.querySelector('button[aria-label="Stop"]')?.click()`);
      return true;
    case 'snapshot':
      return await evaluate('(' + snapshotInPage.toString() + ')(' + JSON.stringify(hideSelectors) + ')');
    case 'view':
      return await evaluate('(' + viewInPage.toString() + ')()');
    case 'choose-once': {
      const wanted = (request.label || 'Allow once').trim();
      const result = await evaluate(`(()=>{
        const panels=[...document.querySelectorAll('[role="dialog"],[role="alertdialog"],._container_uq4jg_42')];
        const panel=panels.find(p=>p.innerText===${JSON.stringify(request.text)});
        if(!panel||panel.getBoundingClientRect().height===0)return false;
        const labelOf=b=>b.querySelector('[class*="_optionLabel_"]')?.innerText?.trim()||document.getElementById(b.getAttribute('aria-labelledby'))?.innerText?.trim()||b.innerText?.trim()||b.getAttribute('aria-label');
        const buttons=[...panel.querySelectorAll('button')].filter(b=>!b.disabled&&labelOf(b)===${JSON.stringify(wanted)});
        if(buttons.length!==1)return false;
        const label=labelOf(buttons[0]),at=Date.now();buttons[0].click();return {label,at};
      })()`);
      if (!result) throw Error('Captured native approval changed or has no unique continue choice');
      return result;
    }
    case 'screenshot': {
      const stillPending = `(()=>{const s=window.__arenaCapture;return [...document.querySelectorAll('[role="dialog"],[role="alertdialog"],._container_uq4jg_42')].some(p=>s?.nodes.get(p)===${JSON.stringify(request.key)}&&p.getBoundingClientRect().height>0);})()`;
      if (request.key && !await evaluate(stillPending)) return false;
      const screenshot = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
      if (request.key && !await evaluate(stillPending)) return false;
      return { data: screenshot.data, at: Date.now() };
    }
    case 'close':
      try { await evaluate('window.__arenaSessionHooks?.close()'); } catch {}
      try { socket?.close(); } catch (error) {}
      return true;
    default:
      throw Error('Unsupported WorkBuddy observation command');
  }
}

let chain = Promise.resolve();
readline.createInterface({ input: process.stdin }).on('line', line => {
  chain = chain.then(async () => {
    try { process.stdout.write(JSON.stringify({ ok: true, value: await dispatch(JSON.parse(line)) }) + '\n'); }
    catch (error) { process.stdout.write(JSON.stringify({ ok: false, error: error.message }) + '\n'); }
  });
}).on('close', () => { socket?.close(); });
