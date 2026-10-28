const test=require('node:test'),assert=require('node:assert/strict');
const {completedReply}=require('./native_completion.cjs');
const human={seq:18},start={data:{turn:1}},end={seq:28,data:{reason:{kind:'completed'}}};
test('reasoning-only completed turn records missing text without inventing a reply',()=>{
 const rows=[{type:'assistant/message',seq:26,data:{turn:1,message:{content:[{type:'reasoning',text:'private reasoning fixture'}]}}}];
 assert.deepEqual(completedReply(rows,human,start,end),{assistant:null,text:'',finalTextMissing:true});
});
test('public text stays exact and reasoning is excluded',()=>{
 const message={type:'assistant/message',seq:26,data:{turn:1,message:{content:[{type:'reasoning',text:'private fixture'},{type:'text',text:'Actual reply.'}]}}};
 const result=completedReply([message],human,start,end);
 assert.equal(result.text,'Actual reply.');assert.equal(result.assistant.seq,26);assert.equal(result.finalTextMissing,false);
});
test('another turn or post-end text cannot replace the missing reply',()=>{
 const message=(seq,turn)=>({type:'assistant/message',seq,data:{turn,message:{content:[{type:'text',text:'wrong turn'}]}}});
 assert.equal(completedReply([message(20,2),message(30,1)],human,start,end).finalTextMissing,true);
});
