// Synthetic daemon waits must not stall recording or manufacture completion.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const hooksModule = require('../src/arena/adapters/agents/workbuddy_hooks.cjs');
const source = fs.readFileSync(path.join(__dirname, '../src/arena/adapters/agents/workbuddy_view.cjs'), 'utf8');

async function test() {
  const hooks = hooksModule.createWorkBuddyHooks({invoke(){}, subscribe(){return ()=>{};}}, 'owned');
  hooks.trackVisible('exact owned prompt', 'request');
  let resolveRead, reads = 0;
  const pending = new Promise(resolve => {resolveRead=resolve;});
  const window = {
    __arenaSessionHooks: hooks,
    __arenaVisiblePrompt: 'exact owned prompt',
    __arenaRequestPollState: {},
    __arenaOwnedHookConversation: {requests(){reads++; return pending;}},
  };
  const context = vm.createContext({
    require(name) {
      if (name === 'readline' || name === 'node:readline') return {createInterface(){return {on(){return this;}};}};
      if (name === './workbuddy_hooks.cjs') return hooksModule;
      throw Error('Unexpected dependency '+name);
    },
    process: {stdin:{},stdout:{write() {}}},
    module: {exports:{}}, setTimeout, clearTimeout,
    testEvaluate: expression => vm.runInNewContext(expression, {window}),
  });
  vm.runInContext(source + '\nevaluate = async expression => testEvaluate(expression);\nmodule.exports={dispatch};', context);
  const dispatch = context.module.exports.dispatch;
  const first = await Promise.race([
    dispatch({action:'hook-output'}),
    new Promise(resolve=>setTimeout(()=>resolve('blocked-by-request-list'),100)),
  ]);
  assert.notEqual(first,'blocked-by-request-list','pending request-list RPC blocked capture');
  assert.equal(first.status,'running');
  await dispatch({action:'hook-output'});
  assert.equal(reads,1,'duplicate request-list RPC while the first is pending');
  resolveRead({items:[
    {id:'other',state:'completed',userMessage:{content:[{type:'text',text:'another task'}]}},
    {id:'native-owned',state:'completed',userMessage:{content:[{type:'text',text:'exact owned prompt'}]},assistantMessage:{content:[{type:'text',text:'actual public reply'},{type:'reasoning',text:'private'}]}},
  ]});
  await new Promise(resolve=>setTimeout(resolve,0));
  const last=await dispatch({action:'hook-output'});
  assert.equal(last.status,'finished');
  assert.equal(last.result.nativeRequest.id,'native-owned');
  assert.equal(last.result.nativeRequest.assistantText,'actual public reply');
  hooks.close();
  console.log('PASS pending RPC remains nonblocking, one owned read, exact terminal completion');
}
test().catch(error=>{console.error(error);process.exitCode=1;});
