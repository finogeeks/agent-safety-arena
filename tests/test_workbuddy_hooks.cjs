const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createWorkBuddyHooks, nativeRuntimePath } = require('../src/arena/adapters/agents/workbuddy_hooks.cjs');

test('only the inspected vendor version has a native runtime mapping', () => {
  assert.equal(nativeRuntimePath('5.9.4'), './assets/runtime-Cq08wGJM.js');
  assert.equal(nativeRuntimePath('5.9.3'), './assets/runtime-Cq08wGJM.js');
  assert.throws(() => nativeRuntimePath('6.0.0'), /Unsupported WorkBuddy/);
});

test('visible composer observation works without Node lexical helpers in the page', () => {
  const source = fs.readFileSync(path.join(__dirname, '../src/arena/adapters/agents/workbuddy_view.cjs'), 'utf8');
  const fn = source.slice(source.indexOf('function viewInPage()'), source.indexOf('async function dispatch('));
  const input = { innerText: 'Synthetic prompt' };
  const send = { disabled: false, className: 'wb-button', getAttribute: () => null };
  const document = {
    body: { innerText: '' },
    querySelector: selector => selector.includes('data-slate-editor') ? input : selector === 'button[aria-label="Send"]' ? send : null,
    querySelectorAll: () => [],
  };
  const result = vm.runInNewContext(fn + '\nviewInPage()', { document });
  assert.equal(result.composerText, 'Synthetic prompt');
  assert.equal(result.sendDisabled, false);
  assert.equal(result.completed, false);
});

function fixture() {
  const calls = [];
  let listener;
  let resolve;
  let reject;
  let detached = false;
  const result = new Promise((yes, no) => { resolve = yes; reject = no; });
  const bridge = {
    invoke(...args) { calls.push(args); return result; },
    subscribe(fn) { listener = fn; return () => { detached = true; }; },
  };
  const hooks = createWorkBuddyHooks(bridge, 'owned-session');
  return { hooks, calls, resolve, reject,
    emit: (...args) => listener(...args), detached: () => detached };
}

test('input preserves exact text and request identity, and cannot send twice', () => {
  const f = fixture();
  const prompt = '  Synthetic input\r\nwith newline.\n';
  f.hooks.input(prompt, 'req-1');
  assert.deepEqual(f.calls, [[
    'session:sendMessage', undefined, 'owned-session',
    [{ type: 'text', text: prompt }],
    { messageId: 'req-1', 'codebuddy.ai': { userMessageId: 'req-1', clientRequestId: 'req-1' } },
  ]]);
  assert.throws(() => f.hooks.input(prompt, 'req-2'), /already submitted/);
  assert.throws(() => f.hooks.input(prompt, 'req-1'), /already submitted/);
});

test('output subscribes early, retains native permission, and excludes other sessions', () => {
  const f = fixture();
  f.emit('session:event:private-session', { sessionId: 'private-session', text: 'private' });
  f.emit('session:event:owned-session', { sessionId: 'private-session', text: 'private' });
  f.emit('session:upserted', { sessionId: 'private-session', text: 'private' });
  f.emit('session:event:owned-session', { sessionId: 'owned-session', type: 'permissionRequest', requestId: 'permission-1', request: { options: ['Allow once', 'Reject'] } });
  const out = f.hooks.output();
  assert.equal(out.events.length, 1);
  assert.equal(out.events[0].event.type, 'permissionRequest');
  assert.equal(out.events[0].sessionId, 'owned-session');
  assert.equal(out.status, 'ready');
  assert.deepEqual(f.calls, []);
});

test('sandbox events require the owned session identity', () => {
  const f = fixture();
  f.emit('sandbox:interceptRequest', { sessionId: 'private-session', requestId: 'p' });
  f.emit('sandbox:interceptRequest', { requestId: 'unknown' });
  f.emit('sandbox:interceptRequest', { sessionId: 'owned-session', requestId: 's' });
  assert.equal(f.hooks.output().events.length, 1);
  assert.equal(f.hooks.output().events[0].topic, 'sandbox:interceptRequest');
});

test('visible submission only tracks; an exact native terminal request completes it', () => {
  const f = fixture();
  f.hooks.trackVisible('Synthetic input\n', 'visible-1');
  assert.deepEqual(f.calls, []);
  f.hooks.settleVisible({ id: 'native-1', state: 'working', userText: 'Synthetic input\n', assistantText: '' });
  assert.equal(f.hooks.output().status, 'running');
  f.hooks.settleVisible({ id: 'other', state: 'completed', userText: 'Other input', assistantText: 'Other reply' });
  assert.equal(f.hooks.output().status, 'running');
  f.hooks.settleVisible({ id: 'native-1', state: 'completed', userText: 'Synthetic input\n', assistantText: 'Done' });
  assert.equal(f.hooks.output().status, 'finished');
  assert.equal(f.hooks.output().result.nativeRequest.id, 'native-1');
  assert.throws(() => f.hooks.trackVisible('Synthetic input\n', 'duplicate'), /already submitted/);
});

test('silence and permission events cannot complete a request; native result can', async () => {
  const f = fixture();
  f.hooks.input('Synthetic input', 'req-1');
  f.emit('session:event:owned-session', { type: 'permissionRequest', requestId: 3 });
  assert.equal(f.hooks.output().status, 'running');
  f.resolve({ stopReason: 'end_turn' });
  await new Promise(setImmediate);
  const out = f.hooks.output();
  assert.equal(out.status, 'finished');
  assert.deepEqual(out.result, { stopReason: 'end_turn' });
  assert.equal(out.requestId, 'req-1');
});

test('native failures and malformed results stay errors', async () => {
  for (const kind of ['rejected', 'malformed']) {
    const f = fixture();
    f.hooks.input('Synthetic input', 'req-1');
    if (kind === 'rejected') f.reject(new Error('Native transport failed'));
    else f.resolve({});
    await new Promise(setImmediate);
    assert.equal(f.hooks.output().status, 'error');
    assert.equal(f.hooks.output().result, null);
  }
});

test('close detaches and refuses further submission without extra native calls', () => {
  const f = fixture();
  f.hooks.close();
  f.hooks.close();
  assert.equal(f.detached(), true);
  assert.throws(() => f.hooks.input('Synthetic input', 'req-1'), /closed/);
  assert.deepEqual(f.calls, []);
});

test('invalid identities or inputs cannot submit', () => {
  assert.throws(() => createWorkBuddyHooks({}, ''), /session/i);
  const f = fixture();
  assert.throws(() => f.hooks.input('Synthetic input', ''), /request/i);
  assert.throws(() => f.hooks.input(null, 'req-1'), /prompt/i);
  assert.deepEqual(f.calls, []);
});
