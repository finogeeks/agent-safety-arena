// Atomic derived metadata with bounded Windows sharing-conflict retries.
const fs=require('node:fs'),crypto=require('node:crypto');
const delay=new Int32Array(new SharedArrayBuffer(4));
function writeJson(file,value,{maxWaitMs=1000}={}){
 const temporary=file+'.writing-'+process.pid+'-'+crypto.randomUUID();
 const deadline=Date.now()+maxWaitMs;
 function retry(action){
  for(;;){
   try{return action();}
   catch(error){
    if(!['EBUSY','EPERM','EACCES'].includes(error.code)||Date.now()>=deadline)throw error;
    Atomics.wait(delay,0,0,20);
   }
  }
 }
 try{
  retry(()=>fs.writeFileSync(temporary,JSON.stringify(value,null,2),{flag:'wx'}));
  retry(()=>fs.renameSync(temporary,file));
 }finally{
  try{fs.unlinkSync(temporary);}catch(error){if(error.code!=='ENOENT')throw error;}
 }
}
module.exports={writeJson};
