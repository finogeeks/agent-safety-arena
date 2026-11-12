const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/arena/adapters/agents/workbuddy_view.cjs', 'utf8');
let clicks = [];
const option = label => ({disabled:false, innerText:label,
  getBoundingClientRect(){return {width:100,height:30};},
  getAttribute(){return null;}, querySelector(){return {innerText:label};},
  click(){clicks.push(label);}});
const buttons = [option('1. Continue now'), option('2. Reject')];
const panel = {innerText:'Updated native wording',parentElement:null,
  getBoundingClientRect(){return {width:400,height:300};},
  querySelectorAll(){return buttons;}};
let panels = [panel];
const document = {querySelectorAll(){return panels;},getElementById(){return null;}};
const context = vm.createContext({
  require(name){
    if(name==='node:readline')return {createInterface(){return {on(){return this;}};}};
    if(name==='./workbuddy_hooks.cjs')return {};
    throw Error(name);
  },
  process:{stdin:{},stdout:{write(){}}},module:{exports:{}},setTimeout,clearTimeout,
  testEvaluate:expression=>vm.runInNewContext(expression,{document,Date,
    getComputedStyle(){return {visibility:'visible',display:'block'};}}),
});
vm.runInContext(source+'\nevaluate=async expression=>testEvaluate(expression);module.exports={dispatch};',context);
(async()=>{
  const result=await context.module.exports.dispatch({action:'choose-once',key:'old-key',
    text:'Original captured wording',label:'Original first label'});
  assert.deepEqual(clicks,['1. Continue now']);
  assert.equal(result.label,'1. Continue now');
  panels=[panel,panel];
  await assert.rejects(context.module.exports.dispatch({action:'choose-once',text:'old'}));
  assert.equal(clicks.length,1,'Ambiguous panels must not receive a click');
  console.log('WorkBuddy first-choice regression passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
