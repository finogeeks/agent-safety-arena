// Offline regressions for Windows sharing conflicts in derived recording JSON.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {writeJson}=require('./metadata_io.cjs');

function fixture(t){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'agent-safe-metadata-'));
 t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 const file=path.join(dir,'native-status.json');fs.writeFileSync(file,'{"old":true}');
 return {dir,file};
}

test('transient sharing conflict preserves prior JSON until atomic replacement',t=>{
 const {file}=fixture(t),rename=fs.renameSync;let calls=0;
 t.mock.method(fs,'renameSync',(from,to)=>{
  if(++calls===1){assert.deepEqual(JSON.parse(fs.readFileSync(file,'utf8')),{old:true});throw Object.assign(Error('sharing'),{code:'EBUSY'});}
  return rename(from,to);
 });
 writeJson(file,{new:true});
 assert.equal(calls,2);assert.deepEqual(JSON.parse(fs.readFileSync(file,'utf8')),{new:true});
});

test('permanent sharing failure is bounded and preserves the last valid document',t=>{
 const {file,dir}=fixture(t);
 t.mock.method(fs,'renameSync',()=>{throw Object.assign(Error('locked'),{code:'EPERM'});});
 const start=Date.now();assert.throws(()=>writeJson(file,{new:true},{maxWaitMs:40}),/locked/);
 assert.ok(Date.now()-start<1000);assert.deepEqual(JSON.parse(fs.readFileSync(file,'utf8')),{old:true});
 assert.deepEqual(fs.readdirSync(dir),['native-status.json']);
});

test('non-sharing errors fail immediately without replacing valid JSON',t=>{
 const {file}=fixture(t);let calls=0;
 t.mock.method(fs,'renameSync',()=>{calls++;throw Object.assign(Error('invalid'),{code:'EINVAL'});});
 assert.throws(()=>writeJson(file,{new:true}),/invalid/);assert.equal(calls,1);
 assert.deepEqual(JSON.parse(fs.readFileSync(file,'utf8')),{old:true});
});
