// Extract public assistant text only. Never turn reasoning into a model reply.
function completedReply(rows,human,start,end){
 const assistant=rows.filter(e=>e.type==='assistant/message'&&e.seq>human.seq&&e.seq<end.seq&&e.data.turn===start.data.turn&&e.data.message.content.some(x=>x.type==='text'&&x.text)).at(-1);
 const text=assistant?.data.message.content.filter(x=>x.type==='text').map(x=>x.text).join('\n')||'';
 return {assistant:assistant||null,text,finalTextMissing:end.data.reason.kind==='completed'&&!assistant};
}
module.exports={completedReply};
